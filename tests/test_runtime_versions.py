"""Tests for the Python-version guards on the application entry points."""

import pytest

from src import main, web_main


@pytest.mark.parametrize("entrypoint", [main, web_main])
def test_python_39_is_rejected(entrypoint):
    """Python versions below 3.10 must be rejected before application imports."""
    assert entrypoint._python_version_supported((3, 9, 18)) is False


@pytest.mark.parametrize("entrypoint", [main, web_main])
@pytest.mark.parametrize("version", [(3, 10, 0), (3, 14, 1), (4, 0, 0)])
def test_python_310_and_newer_are_accepted(entrypoint, version):
    """Python 3.10 and newer must pass the entry-point guard."""
    assert entrypoint._python_version_supported(version) is True


def test_web_server_port_defaults_to_8000(monkeypatch):
    """The web server must retain port 8000 as its default."""
    monkeypatch.delenv("PORT", raising=False)

    assert web_main._server_port() == 8000


@pytest.mark.parametrize("value", ["1", "8001", "65535"])
def test_web_server_port_accepts_valid_values(value):
    """Valid TCP ports must be accepted from configuration."""
    assert web_main._server_port(value) == int(value)


@pytest.mark.parametrize("value", ["", "invalid", "0", "65536"])
def test_web_server_port_rejects_invalid_values(value):
    """Invalid port configuration must fail with an actionable error."""
    with pytest.raises(ValueError, match="PORT must be an integer"):
        web_main._server_port(value)


def test_web_exits_before_startup_for_invalid_port(monkeypatch, caplog):
    """Invalid port configuration must stop startup before application imports."""
    monkeypatch.setattr(web_main.sys, "argv", ["web_main.py", "data/raw/combined_dataset.xlsx"])
    monkeypatch.setenv("PORT", "invalid")

    assert web_main.main() == 1
    assert "PORT must be an integer" in caplog.text


def test_web_exits_without_replacing_existing_port_listener(monkeypatch, caplog):
    """An occupied port must produce guidance rather than replacing its listener."""
    monkeypatch.setattr(web_main.sys, "argv", ["web_main.py", "data/raw/combined_dataset.xlsx"])
    monkeypatch.setattr(web_main, "_port_is_available", lambda _port: False)
    monkeypatch.setenv("PORT", "8000")

    assert web_main.main() == 1
    assert "Port 8000 is already in use" in caplog.text
    assert "set PORT to another value" in caplog.text
    assert "8001" in caplog.text


def test_cli_exits_before_startup_on_unsupported_python(monkeypatch, capsys):
    """The CLI must explain the minimum version before doing startup work."""
    monkeypatch.setattr(main, "_python_version_supported", lambda: False)

    assert main.main() == 1
    assert "Python 3.10 or newer is required" in capsys.readouterr().out


def test_web_exits_before_startup_on_unsupported_python(monkeypatch, caplog):
    """The web entry point must explain the minimum version before importing the app."""
    monkeypatch.setattr(web_main, "_python_version_supported", lambda: False)

    assert web_main.main() == 1
    assert "Python 3.10 or newer is required" in caplog.text


def test_cli_missing_default_workbook_returns_failure(monkeypatch, capsys):
    """A missing default workbook must produce a nonzero process result."""
    monkeypatch.setattr(main.sys, "argv", ["main.py"])
    monkeypatch.setattr(main.os.path, "exists", lambda _path: False)

    assert main.main() == 1
    assert "File not found" in capsys.readouterr().out


def test_cli_missing_explicit_workbook_returns_failure(monkeypatch, capsys):
    """A missing user-supplied workbook must produce a nonzero process result."""
    missing_path = "data/raw/does-not-exist.xlsx"
    monkeypatch.setattr(main.sys, "argv", ["main.py", missing_path])
    monkeypatch.setattr(main.os.path, "exists", lambda _path: False)

    assert main.main() == 1
    assert missing_path in capsys.readouterr().out
