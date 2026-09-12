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
from src.ml.policy import Policy, PolicyEngine, policy_summary  # noqa: E402
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


def _policy_dict(policy: Policy) -> dict[str, Any]:
    return asdict(policy)


def _write_markdown_table(path: Path, primary: dict[str, Any], intervals: dict[str, Any]) -> None:
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
    return {
        "schema_version": 2,
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
    _write_markdown_table(args.output_dir / "PRIMARY_RESULTS.md", report["primary"], report["uncertainty"])
    print(f"Wrote aggregate-only XP 2027 evidence to {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
