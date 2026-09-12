#!/usr/bin/env python3
"""Build an allowlisted, aggregate-only XP 2027 preparation archive."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "output/xp2027/xp2027-submission-preparation.zip"
ALLOWLIST = [
    ROOT / "LICENSE",
    ROOT / "output/pdf/XP2027_temporal_agile_practice_recommendation_draft.pdf",
    ROOT / "submission/xp2027/manuscript/PAPER.md",
    ROOT / "submission/xp2027/manuscript/references.bib",
    ROOT / "submission/xp2027/RESEARCH_PROTOCOL.md",
    ROOT / "submission/xp2027/REPRODUCIBILITY.md",
    ROOT / "submission/xp2027/LITERATURE_REVIEW.md",
    ROOT / "submission/xp2027/AI_USE_DISCLOSURE.md",
    ROOT / "submission/xp2027/evidence/metrics.json",
    ROOT / "submission/xp2027/evidence/PRIMARY_RESULTS.md",
    ROOT / "submission/xp2027/artifact/README.md",
    ROOT / "scripts/build_xp2027_evidence.py",
    ROOT / "scripts/build_xp2027_paper.py",
    ROOT / "tests/test_xp2027_evidence.py",
]
FORBIDDEN_NAMES = {"combined_dataset.xlsx", "level_definitions.xlsx"}
FORBIDDEN_TEXT = [re.compile(r"data/raw/", re.I), re.compile(r"\bAvaya\b", re.I)]
TEXT_SUFFIXES = {".md", ".py", ".json", ".bib", ".txt"}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def validate_file(path: Path) -> None:
    """Reject absent, raw-data, or suspicious allowlisted files."""
    if not path.is_file():
        raise RuntimeError(f"Required package file is missing: {path.relative_to(ROOT)}")
    if path.name in FORBIDDEN_NAMES or path.suffix.lower() in {".xlsx", ".xls", ".csv"}:
        raise RuntimeError(f"Raw or row-level data file cannot be packaged: {path}")
    if path.suffix.lower() in TEXT_SUFFIXES:
        text = path.read_text(encoding="utf-8")
        if path.name == "metrics.json":
            payload = json.loads(text)
            forbidden_keys = {"team", "team_name", "rows", "records", "cases_by_team"}

            def walk(value: object) -> None:
                if isinstance(value, dict):
                    bad = forbidden_keys.intersection(str(key).lower() for key in value)
                    if bad:
                        raise RuntimeError(f"Aggregate metrics contain row-level keys: {sorted(bad)}")
                    for child in value.values():
                        walk(child)
                elif isinstance(value, list):
                    for child in value:
                        walk(child)

            walk(payload)
        elif path.name not in {"build_xp2027_evidence.py", "test_xp2027_evidence.py", "README.md"}:
            for pattern in FORBIDDEN_TEXT:
                if pattern.search(text):
                    raise RuntimeError(f"Potential confidential field/path in {path.relative_to(ROOT)}: {pattern.pattern}")


def build_archive(output: Path) -> Path:
    """Validate and write the deterministic allowlisted ZIP archive."""
    for path in ALLOWLIST:
        validate_file(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(ALLOWLIST, key=lambda item: item.as_posix()):
            relative = path.relative_to(ROOT)
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(2026, 9, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(output) as archive:
        members = archive.namelist()
        if any(Path(member).name in FORBIDDEN_NAMES for member in members):
            raise RuntimeError("Archive contains a forbidden source-data file")
        if archive.testzip() is not None:
            raise RuntimeError("Archive integrity check failed")
    return output


def main() -> int:
    """Build the archive."""
    path = build_archive(parse_args().output)
    print(f"Wrote sanitized XP 2027 archive to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
