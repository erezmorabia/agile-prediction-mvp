"""Tests for the aggregate-only XP 2027 research evidence builder."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from scripts.build_xp2027_evidence import (
    DEFAULT_SEED,
    aggregate_scope,
    aggregate_unconditional_scope,
    build_case_scores,
    build_engine,
    build_policy_grid_case_hits,
    build_unconditional_complete_window_scores,
    selection_refit_team_bootstrap,
    strict_complete_window_audit,
    team_cluster_bootstrap,
    validate_reference_results,
)
from scripts.build_xp2027_paper import (
    load_manuscript,
    load_metrics,
    manuscript_story,
    validate_bibliography,
)
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
    unconditional_records = build_unconditional_complete_window_scores(engine)
    report = {
        "primary": aggregate_scope(records, primary_months, engine.practices),
        "strict_team_complete_sensitivity": aggregate_scope(
            [record for record in records if record.complete_team_window],
            primary_months,
            engine.practices,
        ),
        "strict_complete_window_audit": strict_complete_window_audit(engine),
        "exploratory_unconditional_complete_window": aggregate_unconditional_scope(
            unconditional_records,
            primary_months,
            engine.practices,
        ),
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


def test_exploratory_unconditional_cohort_retains_no_improvement_cases(evidence):
    engine, _records, rows = evidence
    primary_months = [row["month"] for row in rows if row["full_outcome_window"]]
    records = build_unconditional_complete_window_scores(engine)
    aggregate = aggregate_unconditional_scope(records, primary_months, engine.practices)
    assert aggregate["total_recommendable_cases"] == 298
    assert aggregate["outcome_bearing_cases"] == 120
    assert aggregate["no_improvement_cases"] == 178
    assert aggregate["methods"]["selected_blend"]["monthly_macro_hit_rate_at_2"] == pytest.approx(
        0.231074585305929
    )
    assert aggregate["methods"]["time_aware_popularity"][
        "monthly_macro_hit_rate_at_2"
    ] == pytest.approx(0.22164998213132586)
    assert sum(record.improved_count == 0 for record in records) == 178
    assert all(
        all(hit == 0.0 for hit in record.method_hits.values())
        for record in records
        if record.improved_count == 0
    )


def test_bootstrap_is_deterministic(evidence):
    _engine, records, rows = evidence
    primary_months = [row["month"] for row in rows if row["full_outcome_window"]]
    first = team_cluster_bootstrap(records, primary_months, replicates=100, seed=DEFAULT_SEED)
    second = team_cluster_bootstrap(records, primary_months, replicates=100, seed=DEFAULT_SEED)
    assert first == second


def test_selection_refit_bootstrap_is_deterministic_and_temporal(evidence):
    engine, _records, rows = evidence
    primary_months = [row["month"] for row in rows if row["full_outcome_window"]]
    grid_hits = build_policy_grid_case_hits(engine, primary_months)
    first = selection_refit_team_bootstrap(
        engine,
        grid_hits,
        primary_months,
        replicates=40,
        seed=DEFAULT_SEED + 2,
        batch_size=20,
    )
    second = selection_refit_team_bootstrap(
        engine,
        grid_hits,
        primary_months,
        replicates=40,
        seed=DEFAULT_SEED + 2,
        batch_size=20,
    )
    assert first == second
    assert first["selection_refit_in_replicate"] is True
    for month in primary_months[:3]:
        assert first["selection_frequency"]["selected_blend"][str(month)][
            "distinct_policies"
        ] == 1


def test_aggregate_output_does_not_expose_team_names(evidence):
    engine, records, rows = evidence
    primary_months = [row["month"] for row in rows if row["full_outcome_window"]]
    aggregate = aggregate_scope(records, primary_months, engine.practices)
    serialized = str(aggregate)
    assert all(record.team not in serialized for record in records)


def test_paper_and_bibliography_are_synchronized():
    validate_bibliography(load_manuscript())


def test_wrapped_research_questions_remain_single_bullets():
    story = manuscript_story(load_manuscript(), load_metrics())
    paragraph_text = [
        flowable.getPlainText()
        for flowable in story
        if callable(getattr(flowable, "getPlainText", None))
    ]
    expected_questions = [
        "RQ1: How effectively can organization-specific maturity histories identify practices associated "
        "with a team's next recorded improvement under walk-forward evaluation?",
        "RQ2: What incremental value and stability do peer similarity and practice-transition evidence "
        "provide beyond time-aware organizational popularity?",
    ]
    assert all(question in paragraph_text for question in expected_questions)


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
