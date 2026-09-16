#!/usr/bin/env python3
"""Compile and validate the provisional Springer/Overleaf XP 2027 manuscript."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "submission/xp2027/manuscript"
INPUT = MANUSCRIPT_DIR / "main.tex"
OUTPUT = ROOT / "output/pdf/Morabia_Tyszberowicz_XP2027_Paper_Draft.pdf"


def _compiler() -> str:
    """Return an installed Tectonic executable."""
    compiler = shutil.which("tectonic")
    if compiler:
        return compiler
    homebrew_compiler = Path("/opt/homebrew/bin/tectonic")
    if homebrew_compiler.is_file():
        return str(homebrew_compiler)
    raise RuntimeError(
        "Tectonic is required for the local build. Install it with "
        "`brew install tectonic`, or upload the manuscript directory to Overleaf."
    )


def _validate_sources() -> None:
    """Require the complete self-contained Overleaf source set."""
    required = [INPUT, MANUSCRIPT_DIR / "references.bib", MANUSCRIPT_DIR / "llncs.cls", MANUSCRIPT_DIR / "splncs04.bst"]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing Overleaf source files: {missing}")


def _validate_pdf(path: Path, log: str) -> None:
    """Validate authorship, core results, references, and rendering diagnostics."""
    reader = PdfReader(str(path))
    text = " ".join(" ".join((page.extract_text() or "").split()) for page in reader.pages)
    required_text = [
        "Erez Morabia",
        "Shmuel Tyszberowicz",
        "58.0%",
        "55.7%",
        "30.6%",
        "Author Contributions",
        "Disclosure of Interests",
        "References",
    ]
    missing = [value for value in required_text if value not in text]
    if missing:
        raise RuntimeError(f"Compiled manuscript is missing required text: {missing}")
    if "??" in text or "Missing character" in log:
        raise RuntimeError("Compiled manuscript contains an unresolved reference or missing character")
    if "Overfull \\hbox" in log or "Overfull \\vbox" in log:
        raise RuntimeError("Compiled manuscript contains an overfull box")
    if not 5 <= len(reader.pages) <= 15:
        raise RuntimeError(f"Unexpected Springer manuscript length: {len(reader.pages)} pages")


def build() -> Path:
    """Compile the manuscript with Tectonic and copy the validated PDF to output."""
    _validate_sources()
    with tempfile.TemporaryDirectory(prefix="xp2027-latex-") as temporary:
        build_dir = Path(temporary)
        result = subprocess.run(
            [_compiler(), "-X", "compile", "--keep-logs", "-o", str(build_dir), str(INPUT)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeError(f"Tectonic compilation failed:\n{result.stdout}\n{result.stderr}")
        compiled = build_dir / "main.pdf"
        log_path = build_dir / "main.log"
        if not compiled.is_file() or not log_path.is_file():
            raise RuntimeError("Tectonic did not produce the expected PDF and log")
        _validate_pdf(compiled, log_path.read_text(encoding="utf-8", errors="replace"))
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(compiled, OUTPUT)
    return OUTPUT


def main() -> int:
    """Build the provisional Springer manuscript."""
    path = build()
    pages = len(PdfReader(str(path)).pages)
    print(f"Wrote {pages}-page Springer/Overleaf manuscript to {path}")
    if pages > 8:
        print("Note: the current full-content conversion exceeds the prior-year provisional 8-page short-paper limit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
