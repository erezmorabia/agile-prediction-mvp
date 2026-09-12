"""Tests for the aggregate-only XP 2027 research evidence builder."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from scripts.build_xp2027_evidence import (
    DEFAULT_SEED,
    aggregate_scope,
    build_case_scores,
    build_engine,
    strict_complete_window_audit,
    team_cluster_bootstrap,
    validate_reference_results,
)
from scripts.build_xp2027_paper import load_manuscript, validate_bibliography
from scripts.package_xp2027_submission import ALLOWLIST

DATA_PATH = Path("data/raw/combined_dataset.xlsx")
pytestmark = pytest.mark.skipif(not DATA_PATH.exists(), reason="requires the reference workbook")


@pytest.fixture(scope="module")
def evidence():
    engine = build_engine(DATA_PATH)
    records, rows = build_case_scores(engine)
    return engine, records, rows


def test_reference_results_and_strict_cohort_reproduce(evidence):
    engine, records, rows = evidence
    primary_months = [row["month"] for row in rows if row["full_outcome_window"]]
    report = {
        "primary": aggregate_scope(records, primary_months, engine.practices),
        "strict_team_complete_sensitivity": aggregate_scope(
            [record for record in records if record.complete_team_window],
            primary_months,
            engine.practices,
        ),
        "strict_complete_window_audit": strict_complete_window_audit(engine),
    }
    validate_reference_results(report)


def test_case_scores_have_no_policy_dependent_cohort_drift(evidence):
    _engine, records, _rows = evidence
    counts = Counter(record.month for record in records)
    assert counts == {
        20200503: 21,
        20200608: 22,
        20200705: 27,
        20200803: 24,
        20200906: 27,
        20201005: 24,
        20201104: 6,
    }
    assert all(set(record.method_hits) == set(records[0].method_hits) for record in records)
    assert sum(record.complete_team_window for record in records if record.month <= 20200906) == 120


def test_bootstrap_is_deterministic(evidence):
    _engine, records, rows = evidence
    primary_months = [row["month"] for row in rows if row["full_outcome_window"]]
    first = team_cluster_bootstrap(records, primary_months, replicates=100, seed=DEFAULT_SEED)
    second = team_cluster_bootstrap(records, primary_months, replicates=100, seed=DEFAULT_SEED)
    assert first == second


def test_aggregate_output_does_not_expose_team_names(evidence):
    engine, records, rows = evidence
    primary_months = [row["month"] for row in rows if row["full_outcome_window"]]
    aggregate = aggregate_scope(records, primary_months, engine.practices)
    serialized = str(aggregate)
    assert all(record.team not in serialized for record in records)


def test_paper_and_bibliography_are_synchronized():
    validate_bibliography(load_manuscript())


def test_package_allowlist_contains_no_gitignored_files():
    ignored = [path for path in ALLOWLIST if path.is_file() and _is_gitignored(path)]
    assert ignored == []


def _is_gitignored(path: Path) -> bool:
    import subprocess

    result = subprocess.run(
        ["git", "check-ignore", "--quiet", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
