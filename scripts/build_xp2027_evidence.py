#!/usr/bin/env python3
"""Build deterministic, aggregate-only evidence for the XP 2027 paper.

The script evaluates the tested production PolicyEngine and fixed, predeclared
ablations. It never emits team names or row-level organizational data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data import DataLoader, DataProcessor, DataValidator  # noqa: E402
from src.ml import SequenceMapper, SimilarityEngine  # noqa: E402
from src.ml.policy import (  # noqa: E402
    BOOTSTRAP_POLICY,
    POLICY_GRID,
    POPULARITY_ARM_POLICIES,
    Policy,
    PolicyEngine,
    _preference_key,
    policy_summary,
)
from src.validation.backtest import BacktestEngine  # noqa: E402
from src.validation.metrics import MetricsCalculator  # noqa: E402

DEFAULT_SEED = 22997
DEFAULT_BOOTSTRAP_REPLICATES = 10_000
TOP_N = 2


@dataclass(frozen=True)
class CaseScore:
    """Policy-independent identifiers and aggregate-safe per-method scores."""

    team: str
    month: int
    complete_team_window: bool
    candidate_count: int
    improved_count: int
    method_hits: dict[str, float]
    method_precisions: dict[str, float]
    method_recalls: dict[str, float]
    method_mrrs: dict[str, float]
    method_recommendations: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class PolicyGridCaseHits:
    """XP-only per-case hit vector for every unchanged production policy."""

    team: str
    month: int
    hits: tuple[float, ...]


FIXED_POLICIES: dict[str, Policy] = {
    "historical_popularity": Policy(10, 0.5, 0.0, 0.0, 1.0, 0.0),
    "recent_popularity": Policy(10, 0.5, 0.0, 0.0, 1.0, 1.0),
    "similarity_only": Policy(10, 0.5, 1.0, 0.0, 0.0, 0.5),
    "transition_only": Policy(10, 0.5, 0.0, 1.0, 0.0, 0.5),
    "equal_three_factor": Policy(10, 0.5, 1 / 3, 1 / 3, 1 / 3, 0.5),
    "similarity_transition": Policy(10, 0.5, 0.5, 0.5, 0.0, 0.5),
    "similarity_popularity": Policy(10, 0.5, 0.5, 0.0, 0.5, 0.5),
    "transition_popularity": Policy(10, 0.5, 0.0, 0.5, 0.5, 0.5),
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/raw/combined_dataset.xlsx"))
    parser.add_argument("--output-dir", type=Path, default=Path("submission/xp2027/evidence"))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--bootstrap-replicates", type=int, default=DEFAULT_BOOTSTRAP_REPLICATES)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_engine(data_path: Path) -> PolicyEngine:
    """Build the production policy engine from the requested workbook."""
    loader = DataLoader(str(data_path))
    frame = loader.load()
    validator = DataValidator(frame, loader.practices)
    validator.validate()
    practices, _excluded = validator.filter_high_missing_practices(loader.practices, threshold=90.0)
    processor = DataProcessor(frame, practices)
    processor.process()
    similarity = SimilarityEngine(processor)
    sequences = SequenceMapper(processor, practices)
    return PolicyEngine(similarity, sequences, practices)


def _score_recommendations(ordered: tuple[str, ...], actual: frozenset[str]) -> tuple[float, float, float, float]:
    """Return hit, precision, recall, and MRR for one ranked recommendation."""
    recommended = set(ordered)
    hits = len(recommended & actual)
    return (
        float(hits > 0),
        hits / len(ordered) if ordered else 0.0,
        hits / len(actual) if actual else 0.0,
        MetricsCalculator.calculate_mrr(list(ordered), set(actual)),
    )


def build_case_scores(engine: PolicyEngine) -> tuple[list[CaseScore], list[dict[str, Any]]]:
    """Score every evaluable case under the selected model and fixed ablations."""
    records: list[CaseScore] = []
    month_rows: list[dict[str, Any]] = []

    for month in engine.prediction_months():
        selected = engine.select_policy(month)
        popularity = engine.select_popularity_arm(month)
        cases = engine.evaluable_cases(month)
        method_policies = {
            "selected_blend": selected.policy,
            "time_aware_popularity": popularity.policy,
            **FIXED_POLICIES,
        }

        for case in cases:
            actual = case.actual_improved
            candidates = set(case.components.candidates)
            improved_count = len(actual & candidates)
            history = engine.processor.get_team_history(case.components.team)
            later_snapshots = [
                candidate
                for candidate in sorted(history)
                if candidate > case.components.baseline_month
            ][:3]
            method_hits: dict[str, float] = {}
            method_precisions: dict[str, float] = {}
            method_recalls: dict[str, float] = {}
            method_mrrs: dict[str, float] = {}
            method_recommendations: dict[str, tuple[str, ...]] = {}

            for name, policy in method_policies.items():
                ordered = engine.top_practices(case.components, policy)
                hit, precision, recall, mrr = _score_recommendations(ordered, actual)
                method_hits[name] = hit
                method_precisions[name] = precision
                method_recalls[name] = recall
                method_mrrs[name] = mrr
                method_recommendations[name] = ordered

            method_hits["random_expected"] = BacktestEngine._expected_random_hit_rate(
                len(candidates), improved_count, TOP_N
            )
            method_precisions["random_expected"] = improved_count / len(candidates)
            method_recalls["random_expected"] = min(TOP_N, len(candidates)) / len(candidates)
            method_mrrs["random_expected"] = BacktestEngine._expected_random_mrr(
                len(candidates), improved_count, TOP_N
            )

            records.append(
                CaseScore(
                    team=case.components.team,
                    month=month,
                    complete_team_window=len(later_snapshots) == 3,
                    candidate_count=len(candidates),
                    improved_count=improved_count,
                    method_hits=method_hits,
                    method_precisions=method_precisions,
                    method_recalls=method_recalls,
                    method_mrrs=method_mrrs,
                    method_recommendations=method_recommendations,
                )
            )

        month_rows.append(
            {
                "month": month,
                "full_outcome_window": engine.full_outcome_window(month),
                "evaluable_cases": len(cases),
                "selected_policy": policy_summary(selected),
                "popularity_arm_recency_weight": popularity.policy.recency_weight,
            }
        )

    return records, month_rows


def build_unconditional_complete_window_scores(engine: PolicyEngine) -> list[CaseScore]:
    """Score every recommendable primary case with three observed future snapshots.

    Unlike the frozen primary cohort, this exploratory cohort retains cases with no
    recorded improvement. Their observed alignment metrics and random expectation are
    zero because there is no later event for any ranking method to identify.
    """
    records: list[CaseScore] = []

    for month in engine.prediction_months():
        if not engine.full_outcome_window(month):
            continue
        selected = engine.select_policy(month)
        popularity = engine.select_popularity_arm(month)
        method_policies = {
            "selected_blend": selected.policy,
            "time_aware_popularity": popularity.policy,
            **FIXED_POLICIES,
        }

        for team in engine.processor.get_all_teams():
            recommendable, components = engine.is_recommendable(team, month)
            if not recommendable or components is None:
                continue
            history = engine.processor.get_team_history(team)
            later_snapshots = [
                candidate
                for candidate in sorted(history)
                if candidate > components.baseline_month
            ][:3]
            if len(later_snapshots) != 3:
                continue

            baseline = history[components.baseline_month]
            actual = {
                engine.practices[index]
                for outcome_month in later_snapshots
                for index, (before, after) in enumerate(
                    zip(baseline, history[outcome_month], strict=True)
                )
                if after > before
            }
            candidates = set(components.candidates)
            actual_eligible = frozenset(actual & candidates)
            improved_count = len(actual_eligible)
            method_hits: dict[str, float] = {}
            method_precisions: dict[str, float] = {}
            method_recalls: dict[str, float] = {}
            method_mrrs: dict[str, float] = {}
            method_recommendations: dict[str, tuple[str, ...]] = {}

            for name, policy in method_policies.items():
                ordered = engine.top_practices(components, policy)
                hit, precision, recall, mrr = _score_recommendations(ordered, actual_eligible)
                method_hits[name] = hit
                method_precisions[name] = precision
                method_recalls[name] = recall
                method_mrrs[name] = mrr
                method_recommendations[name] = ordered

            method_hits["random_expected"] = BacktestEngine._expected_random_hit_rate(
                len(candidates), improved_count, TOP_N
            )
            method_precisions["random_expected"] = (
                improved_count / len(candidates) if candidates else 0.0
            )
            method_recalls["random_expected"] = (
                min(TOP_N, len(candidates)) / len(candidates)
                if improved_count and candidates
                else 0.0
            )
            method_mrrs["random_expected"] = BacktestEngine._expected_random_mrr(
                len(candidates), improved_count, TOP_N
            )

            records.append(
                CaseScore(
                    team=team,
                    month=month,
                    complete_team_window=True,
                    candidate_count=len(candidates),
                    improved_count=improved_count,
                    method_hits=method_hits,
                    method_precisions=method_precisions,
                    method_recalls=method_recalls,
                    method_mrrs=method_mrrs,
                    method_recommendations=method_recommendations,
                )
            )

    return records


def build_policy_grid_case_hits(
    engine: PolicyEngine,
    months: list[int],
) -> list[PolicyGridCaseHits]:
    """Precompute XP-only case hits for the unchanged 675-policy production grid."""
    records: list[PolicyGridCaseHits] = []
    for month in months:
        for case in engine.evaluable_cases(month):
            records.append(
                PolicyGridCaseHits(
                    team=case.components.team,
                    month=month,
                    hits=tuple(
                        float(bool(set(engine.top_practices(case.components, policy)) & case.actual_improved))
                        for policy in POLICY_GRID
                    ),
                )
            )
    return records


def _mean(values: list[float]) -> float:
    """Return a numeric mean, using zero only for an empty input."""
    return sum(values) / len(values) if values else 0.0


def aggregate_scope(
    records: list[CaseScore],
    months: list[int],
    practices: list[str],
) -> dict[str, Any]:
    """Aggregate per-case method metrics by month, then macro-average months."""
    selected = [record for record in records if record.month in months]
    method_names = sorted(selected[0].method_hits) if selected else []
    by_month = {month: [record for record in selected if record.month == month] for month in months}
    methods: dict[str, dict[str, Any]] = {}

    for method in method_names:
        hit_by_month = [_mean([record.method_hits[method] for record in by_month[month]]) for month in months]
        precision_by_month = [
            _mean([record.method_precisions[method] for record in by_month[month]]) for month in months
        ]
        recall_by_month = [_mean([record.method_recalls[method] for record in by_month[month]]) for month in months]
        mrr_by_month = [_mean([record.method_mrrs[method] for record in by_month[month]]) for month in months]
        recommended = {
            practice
            for record in selected
            for practice in record.method_recommendations.get(method, ())
        }
        methods[method] = {
            "monthly_macro_hit_rate_at_2": _mean(hit_by_month),
            "pooled_descriptive_hit_rate_at_2": _mean([record.method_hits[method] for record in selected]),
            "monthly_macro_precision_at_2": _mean(precision_by_month),
            "monthly_macro_recall_at_2": _mean(recall_by_month),
            "monthly_macro_mrr": _mean(mrr_by_month),
            "recommendation_coverage": len(recommended) / len(practices) if method != "random_expected" else None,
            "per_month_hit_rate_at_2": {
                str(month): value for month, value in zip(months, hit_by_month, strict=True)
            },
        }

    blend = methods.get("selected_blend", {})
    for values in methods.values():
        values["blend_gap"] = (
            blend.get("monthly_macro_hit_rate_at_2", 0.0) - values["monthly_macro_hit_rate_at_2"]
        )

    return {
        "months": months,
        "month_count": len(months),
        "outcome_bearing_cases": len(selected),
        "unique_teams": len({record.team for record in selected}),
        "methods": methods,
    }


def aggregate_unconditional_scope(
    records: list[CaseScore],
    months: list[int],
    practices: list[str],
) -> dict[str, Any]:
    """Aggregate the exploratory complete-window cohort, including no-change cases."""
    result = aggregate_scope(records, months, practices)
    total = result.pop("outcome_bearing_cases")
    outcome_bearing = sum(record.improved_count > 0 for record in records if record.month in months)
    result.update(
        {
            "total_recommendable_cases": total,
            "outcome_bearing_cases": outcome_bearing,
            "no_improvement_cases": total - outcome_bearing,
            "outcome_bearing_share": outcome_bearing / total if total else 0.0,
            "estimand": "observed ranking alignment across all recommendable complete-window cases",
            "status": "exploratory post-protocol analysis",
        }
    )
    return result


def strict_complete_window_audit(engine: PolicyEngine) -> dict[str, int | float]:
    """Count recommendable primary cases with exactly three later team snapshots."""
    total = 0
    outcome_bearing = 0
    no_improvement = 0
    for month in engine.prediction_months():
        if not engine.full_outcome_window(month):
            continue
        for team in engine.processor.get_all_teams():
            recommendable, components = engine.is_recommendable(team, month)
            if not recommendable or components is None:
                continue
            history = engine.processor.get_team_history(team)
            later = [candidate for candidate in sorted(history) if candidate > components.baseline_month][:3]
            if len(later) != 3:
                continue
            total += 1
            baseline = history[components.baseline_month]
            improved = any(
                any(after > before for before, after in zip(baseline, history[outcome_month], strict=True))
                for outcome_month in later
            )
            if improved:
                outcome_bearing += 1
            else:
                no_improvement += 1
    return {
        "complete_team_window_cases": total,
        "outcome_bearing_cases": outcome_bearing,
        "no_improvement_cases": no_improvement,
        "outcome_bearing_share": outcome_bearing / total if total else 0.0,
    }


def team_cluster_bootstrap(
    records: list[CaseScore],
    months: list[int],
    *,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    """Compute paired percentile intervals by resampling complete team histories."""
    selected = [record for record in records if record.month in months]
    teams = sorted({record.team for record in selected})
    by_team: dict[str, list[CaseScore]] = defaultdict(list)
    for record in selected:
        by_team[record.team].append(record)
    methods = sorted(selected[0].method_hits) if selected else []
    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {method: [] for method in methods}
    gaps: dict[str, list[float]] = {method: [] for method in methods if method != "selected_blend"}

    for _ in range(replicates):
        multiplicities = Counter(rng.choice(teams, size=len(teams), replace=True).tolist())
        method_values: dict[str, float] = {}
        for method in methods:
            month_means: list[float] = []
            for month in months:
                numerator = 0.0
                denominator = 0
                for team, multiple in multiplicities.items():
                    for record in by_team[team]:
                        if record.month == month:
                            numerator += multiple * record.method_hits[method]
                            denominator += multiple
                if denominator:
                    month_means.append(numerator / denominator)
            method_values[method] = _mean(month_means)
            samples[method].append(method_values[method])
        for method in gaps:
            gaps[method].append(method_values["selected_blend"] - method_values[method])

    def interval(values: list[float]) -> list[float]:
        return [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]

    return {
        "seed": seed,
        "replicates": replicates,
        "cluster": "team identity with all team-month cases retained",
        "selection_refit_in_replicate": False,
        "interpretation": "conditional on the monthly policies fitted to the observed histories",
        "method_hit_rate_intervals": {method: interval(values) for method, values in samples.items()},
        "selected_blend_gap_intervals": {method: interval(values) for method, values in gaps.items()},
    }


def selection_refit_team_bootstrap(
    engine: PolicyEngine,
    records: list[PolicyGridCaseHits],
    months: list[int],
    *,
    replicates: int,
    seed: int,
    batch_size: int = 1_000,
) -> dict[str, Any]:
    """Repeat walk-forward policy selection inside each team-cluster bootstrap.

    This XP-only robustness analysis leaves ``PolicyEngine`` and ``POLICY_GRID``
    unchanged. Each replicate resamples complete team identities, reselects policies
    from completed prior prediction months, and evaluates those policies on the later
    resampled cases. Months without closed prior outcomes retain ``BOOTSTRAP_POLICY``.
    """
    teams = sorted({record.team for record in records})
    team_index = {team: index for index, team in enumerate(teams)}
    policy_count = len(POLICY_GRID)
    bootstrap_index = POLICY_GRID.index(BOOTSTRAP_POLICY)
    popularity_indices = np.asarray(
        [POLICY_GRID.index(policy) for policy in POPULARITY_ARM_POLICIES],
        dtype=int,
    )
    preference_order = np.asarray(
        sorted(range(policy_count), key=lambda index: _preference_key(POLICY_GRID[index]), reverse=True),
        dtype=int,
    )

    presence_by_month = {month: np.zeros(len(teams), dtype=float) for month in months}
    hits_by_month = {
        month: np.zeros((len(teams), policy_count), dtype=float)
        for month in months
    }
    for record in records:
        row = team_index[record.team]
        presence_by_month[record.month][row] = 1.0
        hits_by_month[record.month][row] = np.asarray(record.hits, dtype=float)

    rng = np.random.default_rng(seed)
    blend_samples: list[float] = []
    popularity_samples: list[float] = []
    gap_samples: list[float] = []
    blend_selection_counts = {month: Counter() for month in months}
    popularity_selection_counts = {month: Counter() for month in months}
    probabilities = np.full(len(teams), 1.0 / len(teams))

    def select_blend_indices(training_rates: np.ndarray) -> np.ndarray:
        maxima = training_rates.max(axis=1, keepdims=True)
        tied = np.isclose(training_rates, maxima, rtol=0.0, atol=1e-15)
        preferred_ties = tied[:, preference_order]
        preferred_positions = preferred_ties.argmax(axis=1)
        return preference_order[preferred_positions]

    for start in range(0, replicates, batch_size):
        size = min(batch_size, replicates - start)
        multiplicities = rng.multinomial(len(teams), probabilities, size=size)
        month_rates: dict[int, np.ndarray] = {}
        for month in months:
            denominators = multiplicities @ presence_by_month[month]
            numerators = multiplicities @ hits_by_month[month]
            month_rates[month] = np.divide(
                numerators,
                denominators[:, None],
                out=np.zeros_like(numerators),
                where=denominators[:, None] > 0,
            )

        batch_blend: list[np.ndarray] = []
        batch_popularity: list[np.ndarray] = []
        for month in months:
            completed = [candidate for candidate in engine.completed_prior_months(month) if candidate in months]
            if completed:
                training = np.mean([month_rates[candidate] for candidate in completed], axis=0)
                blend_indices = select_blend_indices(training)
                popularity_training = training[:, popularity_indices]
                popularity_indices_selected = popularity_indices[popularity_training.argmax(axis=1)]
            else:
                blend_indices = np.full(size, bootstrap_index, dtype=int)
                popularity_indices_selected = np.full(size, bootstrap_index, dtype=int)

            target_rates = month_rates[month]
            rows = np.arange(size)
            batch_blend.append(target_rates[rows, blend_indices])
            batch_popularity.append(target_rates[rows, popularity_indices_selected])
            blend_selection_counts[month].update(blend_indices.tolist())
            popularity_selection_counts[month].update(popularity_indices_selected.tolist())

        blend_values = np.mean(batch_blend, axis=0)
        popularity_values = np.mean(batch_popularity, axis=0)
        blend_samples.extend(blend_values.tolist())
        popularity_samples.extend(popularity_values.tolist())
        gap_samples.extend((blend_values - popularity_values).tolist())

    def interval(values: list[float]) -> list[float]:
        return [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]

    def selection_summary(counts_by_month: dict[int, Counter]) -> dict[str, Any]:
        summaries: dict[str, Any] = {}
        for month, counts in counts_by_month.items():
            most_common = counts.most_common(3)
            summaries[str(month)] = {
                "distinct_policies": len(counts),
                "top_selections": [
                    {
                        "policy": _policy_dict(POLICY_GRID[index]),
                        "count": count,
                        "share": count / replicates,
                    }
                    for index, count in most_common
                ],
            }
        return summaries

    return {
        "seed": seed,
        "replicates": replicates,
        "cluster": "team identity with all team-month cases retained",
        "selection_refit_in_replicate": True,
        "policy_grid_size": policy_count,
        "interpretation": "whole walk-forward selection-and-evaluation pipeline under team resampling",
        "method_hit_rate_intervals": {
            "selected_blend": interval(blend_samples),
            "time_aware_popularity": interval(popularity_samples),
        },
        "selected_blend_gap_interval": interval(gap_samples),
        "selection_frequency": {
            "selected_blend": selection_summary(blend_selection_counts),
            "time_aware_popularity": selection_summary(popularity_selection_counts),
        },
    }


def _policy_dict(policy: Policy) -> dict[str, Any]:
    return asdict(policy)


def _write_markdown_table(
    path: Path,
    primary: dict[str, Any],
    intervals: dict[str, Any],
    unconditional: dict[str, Any],
    unconditional_intervals: dict[str, Any],
    selection_refit: dict[str, Any],
) -> None:
    labels = {
        "selected_blend": "Selected three-factor blend",
        "time_aware_popularity": "Nested time-aware popularity",
        "random_expected": "Candidate-aware random expectation",
        "historical_popularity": "Historical popularity",
        "recent_popularity": "Recent popularity",
        "similarity_only": "Similarity only",
        "transition_only": "Practice transitions only",
        "equal_three_factor": "Equal three-factor blend",
        "similarity_transition": "Similarity + transitions",
        "similarity_popularity": "Similarity + popularity",
        "transition_popularity": "Transitions + popularity",
    }
    lines = [
        "# Generated Primary Results",
        "",
        "| Method | Monthly macro HR@2 | 95% team-cluster bootstrap CI | Gap from selected blend |",
        "| --- | ---: | ---: | ---: |",
    ]
    for method, values in primary["methods"].items():
        low, high = intervals["method_hit_rate_intervals"][method]
        gap = values["blend_gap"]
        lines.append(
            f"| {labels.get(method, method)} | {values['monthly_macro_hit_rate_at_2']:.1%} | "
            f"[{low:.1%}, {high:.1%}] | {gap:+.1%} |"
        )
    lines.extend(
        [
            "",
            "## Exploratory all-recommendable complete-window analysis",
            "",
            f"This post-protocol analysis retains all {unconditional['total_recommendable_cases']} recommendable "
            f"cases with three observed future snapshots: {unconditional['outcome_bearing_cases']} "
            f"({unconditional['outcome_bearing_share']:.1%}) contain an eligible recorded increase and "
            f"{unconditional['no_improvement_cases']} do not. A case with no recorded increase contributes zero "
            "observed alignment to every method.",
            "",
            "| Method | Monthly macro observed alignment@2 | 95% team-cluster bootstrap CI |",
            "| --- | ---: | ---: |",
        ]
    )
    for method in ("selected_blend", "time_aware_popularity", "random_expected"):
        values = unconditional["methods"][method]
        low, high = unconditional_intervals["method_hit_rate_intervals"][method]
        lines.append(
            f"| {labels[method]} | {values['monthly_macro_hit_rate_at_2']:.1%} | "
            f"[{low:.1%}, {high:.1%}] |"
        )
    blend_low, blend_high = selection_refit["method_hit_rate_intervals"]["selected_blend"]
    popularity_low, popularity_high = selection_refit["method_hit_rate_intervals"][
        "time_aware_popularity"
    ]
    gap_low, gap_high = selection_refit["selected_blend_gap_interval"]
    adaptive_selection = selection_refit["selection_frequency"]["selected_blend"]
    adaptive_rows = [
        (month, values)
        for month, values in adaptive_selection.items()
        if values["distinct_policies"] > 1
    ]
    adaptive_summary = "; ".join(
        f"{month}: {values['distinct_policies']} policies, modal share "
        f"{values['top_selections'][0]['share']:.1%}"
        for month, values in adaptive_rows
    )
    lines.extend(
        [
            "",
            "## Selection-refit robustness analysis",
            "",
            "This post-protocol team-cluster bootstrap repeats the complete walk-forward choice among 675 policies "
            "inside every replicate. The observed point estimates remain those in the primary table; these intervals "
            "add variability from selecting a policy on resampled completed months.",
            "",
            f"- Selected blend: [{blend_low:.1%}, {blend_high:.1%}]",
            f"- Time-aware popularity: [{popularity_low:.1%}, {popularity_high:.1%}]",
            f"- Paired blend-popularity gap: [{gap_low:.1%}, {gap_high:.1%}]",
            f"- Adaptive-month blend selection: {adaptive_summary}",
            "",
            "Generated by `scripts/build_xp2027_evidence.py`; do not edit numerical values manually.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_report(data_path: Path, seed: int, replicates: int) -> dict[str, Any]:
    """Run the frozen analysis and return an aggregate-only report."""
    engine = build_engine(data_path)
    records, per_month = build_case_scores(engine)
    primary_months = [row["month"] for row in per_month if row["full_outcome_window"]]
    sensitivity_months = [row["month"] for row in per_month]
    primary = aggregate_scope(records, primary_months, engine.practices)
    sensitivity = aggregate_scope(records, sensitivity_months, engine.practices)
    strict_team_complete = aggregate_scope(
        [record for record in records if record.complete_team_window],
        primary_months,
        engine.practices,
    )
    intervals = team_cluster_bootstrap(
        records,
        primary_months,
        replicates=replicates,
        seed=seed,
    )
    unconditional_records = build_unconditional_complete_window_scores(engine)
    unconditional = aggregate_unconditional_scope(
        unconditional_records,
        primary_months,
        engine.practices,
    )
    unconditional_intervals = team_cluster_bootstrap(
        unconditional_records,
        primary_months,
        replicates=replicates,
        seed=seed + 1,
    )
    policy_grid_hits = build_policy_grid_case_hits(engine, primary_months)
    selection_refit = selection_refit_team_bootstrap(
        engine,
        policy_grid_hits,
        primary_months,
        replicates=replicates,
        seed=seed + 2,
    )
    return {
        "schema_version": 4,
        "protocol_status": "frozen before extended analysis",
        "input": {
            "file": data_path.name,
            "sha256": sha256_file(data_path),
            "raw_observations": engine.processor.raw_observation_count,
            "unique_team_month_observations": engine.processor.unique_observation_count,
            "teams": len(engine.processor.get_all_teams()),
            "practices": len(engine.practices),
            "snapshots": len(engine.processor.get_all_months()),
            "snapshot_dates": engine.processor.get_all_months(),
        },
        "fixed_ablation_policies": {name: _policy_dict(policy) for name, policy in FIXED_POLICIES.items()},
        "primary": primary,
        "sensitivity": sensitivity,
        "strict_team_complete_sensitivity": strict_team_complete,
        "strict_complete_window_audit": strict_complete_window_audit(engine),
        "exploratory_unconditional_complete_window": unconditional,
        "exploratory_unconditional_uncertainty": unconditional_intervals,
        "selection_refit_robustness": selection_refit,
        "uncertainty": intervals,
        "per_month": per_month,
        "interpretation": {
            "estimand": "ranking alignment conditional on at least one observed improvement",
            "causal": False,
            "generalization": "single organization only",
        },
    }


def validate_reference_results(report: dict[str, Any]) -> None:
    """Fail if the production-model reproduction drifts from the documented reference."""
    primary = report["primary"]
    methods = primary["methods"]
    expected = {
        "selected_blend": 0.5797859547859547,
        "time_aware_popularity": 0.5566378066378066,
        "random_expected": 0.30605548520204895,
    }
    if primary["outcome_bearing_cases"] != 121:
        raise RuntimeError(f"Expected 121 primary cases, got {primary['outcome_bearing_cases']}")
    for method, value in expected.items():
        observed = methods[method]["monthly_macro_hit_rate_at_2"]
        if not math.isclose(observed, value, abs_tol=1e-12):
            raise RuntimeError(f"Reference drift for {method}: expected {value}, got {observed}")
    audit = report["strict_complete_window_audit"]
    expected_audit = (298, 120, 178)
    observed_audit = (
        audit["complete_team_window_cases"],
        audit["outcome_bearing_cases"],
        audit["no_improvement_cases"],
    )
    if observed_audit != expected_audit:
        raise RuntimeError(f"Strict cohort drift: expected {expected_audit}, got {observed_audit}")
    strict = report["strict_team_complete_sensitivity"]
    strict_expected = {
        "outcome_bearing_cases": 120,
        "selected_blend": 0.5726430976430976,
        "time_aware_popularity": 0.5494949494949495,
        "random_expected": 0.30332899082624165,
    }
    if strict["outcome_bearing_cases"] != strict_expected["outcome_bearing_cases"]:
        raise RuntimeError(
            "Strict sensitivity drift: expected "
            f"{strict_expected['outcome_bearing_cases']} cases, got {strict['outcome_bearing_cases']}"
        )
    for method in ("selected_blend", "time_aware_popularity", "random_expected"):
        observed = strict["methods"][method]["monthly_macro_hit_rate_at_2"]
        if not math.isclose(observed, strict_expected[method], abs_tol=1e-12):
            raise RuntimeError(
                f"Strict sensitivity drift for {method}: expected {strict_expected[method]}, got {observed}"
            )
    unconditional = report["exploratory_unconditional_complete_window"]
    unconditional_expected = {
        "total_recommendable_cases": 298,
        "outcome_bearing_cases": 120,
        "no_improvement_cases": 178,
        "selected_blend": 0.231074585305929,
        "time_aware_popularity": 0.22164998213132586,
        "random_expected": 0.12193039142263669,
    }
    for count_name in (
        "total_recommendable_cases",
        "outcome_bearing_cases",
        "no_improvement_cases",
    ):
        if unconditional[count_name] != unconditional_expected[count_name]:
            raise RuntimeError(
                f"Exploratory unconditional drift for {count_name}: expected "
                f"{unconditional_expected[count_name]}, got {unconditional[count_name]}"
            )
    for method in ("selected_blend", "time_aware_popularity", "random_expected"):
        observed = unconditional["methods"][method]["monthly_macro_hit_rate_at_2"]
        if not math.isclose(observed, unconditional_expected[method], abs_tol=1e-12):
            raise RuntimeError(
                f"Exploratory unconditional drift for {method}: expected "
                f"{unconditional_expected[method]}, got {observed}"
            )
    if "selection_refit_robustness" in report:
        refit = report["selection_refit_robustness"]
        expected_gap_interval = (-0.04449139538293956, 0.12509194324194328)
        observed_gap_interval = tuple(refit["selected_blend_gap_interval"])
        if any(
            not math.isclose(observed, expected, abs_tol=1e-12)
            for observed, expected in zip(
                observed_gap_interval,
                expected_gap_interval,
                strict=True,
            )
        ):
            raise RuntimeError(
                "Selection-refit interval drift: expected "
                f"{expected_gap_interval}, got {observed_gap_interval}"
            )
        expected_distinct = {"20200803": 15, "20200906": 31}
        frequencies = refit["selection_frequency"]["selected_blend"]
        observed_distinct = {
            month: frequencies[month]["distinct_policies"]
            for month in expected_distinct
        }
        if observed_distinct != expected_distinct:
            raise RuntimeError(
                f"Selection-frequency drift: expected {expected_distinct}, got {observed_distinct}"
            )


def main() -> int:
    """Build, validate, and persist the evidence package."""
    args = parse_args()
    if args.bootstrap_replicates <= 0:
        raise SystemExit("--bootstrap-replicates must be positive")
    report = build_report(args.data, args.seed, args.bootstrap_replicates)
    validate_reference_results(report)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown_table(
        args.output_dir / "PRIMARY_RESULTS.md",
        report["primary"],
        report["uncertainty"],
        report["exploratory_unconditional_complete_window"],
        report["exploratory_unconditional_uncertainty"],
        report["selection_refit_robustness"],
    )
    print(f"Wrote aggregate-only XP 2027 evidence to {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
