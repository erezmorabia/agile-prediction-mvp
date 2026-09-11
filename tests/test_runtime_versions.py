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
