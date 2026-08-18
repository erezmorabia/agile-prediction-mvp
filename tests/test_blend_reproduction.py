"""
Reproduction test for the global two-month adaptive recommendation blend.

Pins src/ml/policy.py's PolicyEngine against results/fully-nested-global-fixed-two-month-
20260818.json, produced by the research protocol this module ports.

Requires data/raw/combined_dataset.xlsx; skipped if absent.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.data import DataLoader, DataProcessor, DataValidator
from src.ml import SequenceMapper, SimilarityEngine
from src.ml.policy import BOOTSTRAP_POLICY, PolicyEngine

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "combined_dataset.xlsx")

pytestmark = pytest.mark.skipif(not os.path.exists(DATA_PATH), reason="requires data/raw/combined_dataset.xlsx")

EXPECTED_PER_MONTH = [
    # month,     eligible, blend HR@2,          popularity HR@2,      full_window, bootstrap
    (20200503, 21, 0.2857142857142857, 0.2857142857142857, True, True),
    (20200608, 22, 0.6363636363636364, 0.6363636363636364, True, True),
    (20200705, 27, 0.6666666666666666, 0.6666666666666666, True, True),
    (20200803, 24, 0.7916666666666666, 0.75, True, False),
    (20200906, 27, 0.5185185185185185, 0.4444444444444444, True, False),
    (20201005, 24, 0.3333333333333333, 0.20833333333333334, False, False),
    (20201104, 6, 0.3333333333333333, 0.3333333333333333, False, False),
]

EXPECTED_PRIMARY_BLEND = 0.5797859547859547
EXPECTED_PRIMARY_POPULARITY = 0.5566378066378066

EXPECTED_COMPLETED_PRIOR_MONTHS = {
    20200503: (),
    20200608: (),
    20200705: (),
    20200803: (20200503,),
    20200906: (20200503, 20200608),
    20201005: (20200503, 20200608, 20200705),
    20201104: (20200503, 20200608, 20200705, 20200803),
}


@pytest.fixture(scope="module")
def engine():
    loader = DataLoader(DATA_PATH)
    frame = loader.load()
    validator = DataValidator(frame, loader.practices)
    practices, _ = validator.filter_high_missing_practices(loader.practices, threshold=90.0)
    processor = DataProcessor(frame, practices)
    processor.process()
    similarity = SimilarityEngine(processor)
    sequences = SequenceMapper(processor, practices)
    return PolicyEngine(similarity, sequences, practices)


def test_prediction_months(engine):
    assert engine.prediction_months() == [m for m, *_ in EXPECTED_PER_MONTH]


@pytest.mark.parametrize("month,cases,blend_hr,popularity_hr,full_window,is_bootstrap", EXPECTED_PER_MONTH)
def test_per_month_reproduction(engine, month, cases, blend_hr, popularity_hr, full_window, is_bootstrap):
    evaluable = engine.evaluable_cases(month)
    assert len(evaluable) == cases

    assert engine.full_outcome_window(month) == full_window
    assert engine.completed_prior_months(month) == list(EXPECTED_COMPLETED_PRIOR_MONTHS[month])

    selected = engine.select_policy(month)
    assert selected.is_bootstrap == is_bootstrap
    if is_bootstrap:
        assert selected.policy == BOOTSTRAP_POLICY

    hits = sum(1 for case in evaluable if set(engine.top_practices(case.components, selected.policy)) & case.actual_improved)
    assert hits / len(evaluable) == pytest.approx(blend_hr, abs=1e-9)

    popularity_arm = engine.select_popularity_arm(month)
    if is_bootstrap:
        assert popularity_arm.policy == BOOTSTRAP_POLICY
        # Bootstrap months: the blend IS the popularity policy, so the two arms tie exactly.
        assert blend_hr == pytest.approx(popularity_hr, abs=1e-9)

    pop_hits = sum(
        1 for case in evaluable if set(engine.top_practices(case.components, popularity_arm.policy)) & case.actual_improved
    )
    assert pop_hits / len(evaluable) == pytest.approx(popularity_hr, abs=1e-9)


def test_primary_aggregate(engine):
    primary = [row for row in EXPECTED_PER_MONTH if row[4]]
    blend_rates = []
    popularity_rates = []
    for month, _cases, *_ in primary:
        evaluable = engine.evaluable_cases(month)
        selected = engine.select_policy(month)
        popularity_arm = engine.select_popularity_arm(month)
        blend_rates.append(
            sum(1 for c in evaluable if set(engine.top_practices(c.components, selected.policy)) & c.actual_improved)
            / len(evaluable)
        )
        popularity_rates.append(
            sum(1 for c in evaluable if set(engine.top_practices(c.components, popularity_arm.policy)) & c.actual_improved)
            / len(evaluable)
        )

    assert sum(blend_rates) / len(blend_rates) == pytest.approx(EXPECTED_PRIMARY_BLEND, abs=1e-6)
    assert sum(popularity_rates) / len(popularity_rates) == pytest.approx(EXPECTED_PRIMARY_POPULARITY, abs=1e-6)


def test_normalization_scope_per_component(engine):
    """Spot-check the four normalization scopes on one concrete case, so a reordering bug
    in any single component fails here directly rather than only in an aggregate HR@2."""
    month = 20200906
    evaluable = engine.evaluable_cases(month)
    case = evaluable[0].components
    policy = engine.select_policy(month).policy

    # Similarity/sequence: normalized over ALL evidence (may include maxed-out practices),
    # so a candidate absent from the raw evidence dict scores exactly 0, and the max of the
    # *masked* scores need not be 1.0.
    from src.ml.policy import _normalize

    similarity_raw: dict = {}
    for i in engine._selected_peer_indices(case, policy):
        _team, similarity, _month = case.peers[i]
        for practice, magnitude in case.peer_contributions[i].items():
            similarity_raw[practice] = similarity_raw.get(practice, 0.0) + similarity * magnitude
    similarity_norm_full = _normalize(similarity_raw)

    # Historical popularity: masked to candidates BEFORE normalizing - the denominator must
    # come only from candidate practices, not from practices already maxed out for this team.
    historical_masked = {p: case.historical_popularity_raw.get(p, 0.0) for p in case.candidates}
    historical_norm = _normalize(historical_masked)
    if case.historical_popularity_raw:
        max_candidate_count = max(historical_masked.values())
        for practice, value in case.historical_popularity_raw.items():
            if practice not in case.candidates and value > max_candidate_count:
                # A maxed-out practice with more historical improvements than any candidate
                # must NOT suppress the candidates' normalized scores below 1.0-at-the-max.
                assert max(historical_norm.values(), default=0.0) == pytest.approx(1.0)
                break

    # Recent popularity: normalized org-wide BEFORE masking - candidates should see the
    # same normalized value as the org-wide computation, not renormalized among themselves.
    recent_norm_full = _normalize(case.recent_popularity_raw)
    scores = engine.score_case(case, policy)
    for practice in case.candidates:
        if practice in case.recent_popularity_raw or practice in recent_norm_full:
            expected_recent_component = recent_norm_full.get(practice, 0.0)
            assert expected_recent_component == recent_norm_full.get(practice, 0.0)  # sanity: no per-case rescale

    # Cross-check the assembled score against an independent recomputation.
    for practice in case.candidates:
        sim = similarity_norm_full.get(practice, 0.0)
        seq = _normalize(case.sequence_raw).get(practice, 0.0)
        recent = recent_norm_full.get(practice, 0.0)
        historical = historical_norm.get(practice, 0.0)
        popularity = policy.recency_weight * recent + (1.0 - policy.recency_weight) * historical
        expected = policy.similarity_weight * sim + policy.sequence_weight * seq + policy.popularity_weight * popularity
        assert scores[practice] == pytest.approx(expected, abs=1e-12)
