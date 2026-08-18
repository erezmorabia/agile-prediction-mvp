"""
Unit tests for src/ml/policy.py's PolicyEngine, on a small synthetic dataset (fast, no
Excel file required). See tests/test_blend_reproduction.py for the numeric reproduction
test against the real dataset.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import pytest

from src.data import DataProcessor
from src.ml import SequenceMapper, SimilarityEngine
from src.ml.policy import (
    POLICY_GRID,
    WEIGHT_TRIPLES,
    Policy,
    PolicyEngine,
    SelectedPolicy,
    _preference_key,
)

PRACTICES = ["P1", "P2", "P3", "P4"]
MONTHS = [101, 102, 103, 104, 105, 106, 107]  # 7 months -> prediction months = 104..107

# team -> practice -> per-month raw scores (0-3 scale), 7 entries each
TEAM_SCORES = {
    "TeamA": {
        "P1": [0, 0, 1, 1, 2, 2, 3],
        "P2": [0, 1, 1, 2, 2, 3, 3],
        "P3": [1, 1, 1, 1, 2, 2, 2],
        "P4": [0, 0, 0, 1, 1, 1, 2],
    },
    "TeamB": {
        "P1": [0, 1, 1, 1, 2, 2, 2],
        "P2": [1, 1, 2, 2, 2, 3, 3],
        "P3": [0, 0, 1, 1, 1, 2, 2],
        "P4": [1, 1, 1, 1, 2, 2, 3],
    },
    "TeamC": {
        "P1": [1, 1, 1, 2, 2, 2, 3],
        "P2": [0, 0, 0, 1, 1, 2, 2],
        "P3": [1, 2, 2, 2, 3, 3, 3],
        "P4": [0, 1, 1, 1, 1, 1, 2],
    },
    "TeamD": {
        "P1": [0, 0, 0, 0, 1, 1, 1],
        "P2": [1, 1, 1, 2, 2, 2, 2],
        "P3": [0, 1, 1, 2, 2, 2, 3],
        "P4": [1, 1, 2, 2, 2, 3, 3],
    },
    # Three of four practices already maxed out at every month; P4 improves but never
    # reaches 3 (normalized 1.0). Fewer than 2 non-maxed candidates at every baseline.
    "TeamMaxed": {
        "P1": [3, 3, 3, 3, 3, 3, 3],
        "P2": [3, 3, 3, 3, 3, 3, 3],
        "P3": [3, 3, 3, 3, 3, 3, 3],
        "P4": [1, 1, 1, 1, 2, 2, 2],
    },
}


@pytest.fixture(scope="module")
def engine():
    rows = []
    for team, practice_scores in TEAM_SCORES.items():
        for i, month in enumerate(MONTHS):
            row = {"Team Name": team, "Month": month}
            for practice in PRACTICES:
                row[practice] = practice_scores[practice][i]
            rows.append(row)
    df = pd.DataFrame(rows)
    processor = DataProcessor(df, PRACTICES)
    processor.process()
    similarity = SimilarityEngine(processor)
    sequences = SequenceMapper(processor, PRACTICES)
    return PolicyEngine(similarity, sequences, PRACTICES)


def test_grid_is_675_and_weights_sum_to_one(engine):
    assert len(POLICY_GRID) == 675
    for policy in POLICY_GRID:
        total = policy.similarity_weight + policy.sequence_weight + policy.popularity_weight
        assert total == pytest.approx(1.0, abs=1e-9)


def test_weight_triples_are_15():
    assert len(WEIGHT_TRIPLES) == 15
    assert (0.0, 0.0, 1.0) in WEIGHT_TRIPLES


def test_tie_break_is_a_strict_total_order():
    """The (popularity_weight, recency, similarity_weight, sequence_weight, peer_count,
    min_similarity) tuple that _preference_key sorts on must be injective over the grid -
    i.e. no two distinct policies can tie all the way down, so selection is always
    reproducible regardless of hash seed or iteration order."""
    keys = [_preference_key(p) for p in POLICY_GRID]
    assert len(set(keys)) == len(POLICY_GRID)


def test_maxed_out_team_never_recommendable_or_evaluable(engine):
    for month in engine.prediction_months():
        recommendable, components = engine.is_recommendable("TeamMaxed", month)
        assert recommendable is False
        assert components is not None  # baseline exists, just not enough candidates
        assert len(components.candidates) < 2

        result = engine.recommend("TeamMaxed", month)
        assert result.insufficient_practices is True
        assert result.practices == ()

    for month in engine.prediction_months():
        teams_in_cohort = {case.components.team for case in engine.evaluable_cases(month)}
        assert "TeamMaxed" not in teams_in_cohort


def test_recommendable_team_gets_two_practices(engine):
    for team in ("TeamA", "TeamB", "TeamC", "TeamD"):
        for month in engine.prediction_months():
            recommendable, components = engine.is_recommendable(team, month)
            assert recommendable is True
            result = engine.recommend(team, month)
            assert result.insufficient_practices is False
            assert len(result.practices) == 2


def test_bootstrap_iff_no_completed_prior_months(engine):
    for month in engine.prediction_months():
        selected = engine.select_policy(month)
        expected_bootstrap = len(engine.completed_prior_months(month)) == 0
        assert selected.is_bootstrap == expected_bootstrap
        assert (selected.completed_prior_months == ()) == expected_bootstrap


def test_popularity_arm_never_uses_reported_month_outcome(engine):
    for month in engine.prediction_months():
        blend = engine.select_policy(month)
        popularity_arm = engine.select_popularity_arm(month)
        # Both selections draw from exactly the same "completed prior months" set, which
        # by construction excludes the reported month itself.
        assert month not in blend.completed_prior_months
        assert month not in popularity_arm.completed_prior_months
        assert popularity_arm.completed_prior_months == tuple(engine.completed_prior_months(month))
        assert popularity_arm.policy.similarity_weight == 0.0
        assert popularity_arm.policy.sequence_weight == 0.0


def test_evaluable_cohort_is_cached_and_policy_independent(engine):
    month = engine.prediction_months()[-1]
    first = engine.evaluable_cases(month)
    second = engine.evaluable_cases(month)
    assert first is second  # cached, not recomputed

    # Scoring the same cohort under two very different policies must not change which
    # cases are IN the cohort (evaluable_cases takes no policy argument at all - this
    # just documents/locks that invariant).
    from src.ml.policy import BOOTSTRAP_POLICY

    other_policy = next(p for p in POLICY_GRID if p.similarity_weight == 1.0)
    for case in first:
        engine.top_practices(case.components, BOOTSTRAP_POLICY)
        engine.top_practices(case.components, other_policy)
    assert engine.evaluable_cases(month) == first


def test_no_similar_teams_found_reflects_selected_threshold_not_unfiltered_fetch(engine, monkeypatch):
    """Regression test: `no_similar_teams_found` must reflect whether the *selected
    policy's* min_similarity leaves zero peers, not whether find_similar_teams found
    anything at all at threshold 0.0. A non-zero threshold can filter every peer out
    even when the unfiltered fetch was non-empty - `recommend()` previously reported
    False in that case because it read CaseComponents.no_similar_teams_found (set at
    fetch time, threshold 0.0) instead of recomputing against the policy actually used."""
    month = engine.prediction_months()[-1]
    team = "TeamA"
    _recommendable, components = engine.is_recommendable(team, month)
    assert components.peers, "fixture must have at least one peer at threshold 0.0"

    # A policy whose threshold excludes every peer this small fixture can produce.
    excluding_policy = Policy(
        peer_count=5,
        min_similarity=0.999999,
        similarity_weight=0.5,
        sequence_weight=0.25,
        popularity_weight=0.25,
        recency_weight=0.5,
    )
    assert engine._selected_peer_indices(components, excluding_policy) == []

    monkeypatch.setattr(
        engine,
        "select_policy",
        lambda _month: SelectedPolicy(
            policy=excluding_policy, is_bootstrap=False, completed_prior_months=(month,), mean_prior_hit_rate=0.5
        ),
    )

    result = engine.recommend(team, month)
    assert result.no_similar_teams_found is True
    # Sequence + popularity must still carry the blend - similarity contributes zero,
    # not "no recommendations at all".
    assert len(result.practices) == 2
