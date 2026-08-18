#!/usr/bin/env python3
"""Run a fully nested, no-future-leak popularity strategy evaluation.

The 162 personalized-model configurations, policy parameters, and bootstrap
configuration are predeclared below. For an outer month, a prior month can
inform selection only after its full three-month outcome window closed.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for path in (PROJECT_ROOT, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from research_popularity_strategies import (  # noqa: E402
    BLEND_WEIGHTS,
    SWITCH_THRESHOLDS,
    TOP_N,
    build_cases,
    build_recommender,
    blended_recommendations,
    hit_rate,
    split_recommendations,
    time_aware_popularity,
)

RECENCY_WEIGHTS = (0.0, 0.25, 0.50, 0.75, 1.0)


BOOTSTRAP_CONFIG = {
    "k_similar": 10,
    "similarity_weight": 0.6,
    "similar_teams_lookahead_months": 3,
    "recent_improvements_months": 3,
    "min_similarity_threshold": 0.5,
}


def configuration_grid(two_month_personalization: bool = False) -> list[dict[str, float | int]]:
    """Return the predeclared configuration grid (or its fixed two-month subset)."""
    return [
        {
            "similarity_weight": similarity_weight,
            "k_similar": k_similar,
            "similar_teams_lookahead_months": lookahead,
            "recent_improvements_months": recent,
            "min_similarity_threshold": minimum_similarity,
        }
        for similarity_weight, k_similar, lookahead, recent, minimum_similarity in itertools.product(
            (0.5, 0.6, 0.7),
            (5, 10, 19),
            (2,) if two_month_personalization else (1, 3, 5),
            (2,) if two_month_personalization else (1, 3),
            (0.0, 0.5, 0.75),
        )
    ]


def key(config: dict[str, float | int]) -> str:
    """Create a deterministic key for a configuration."""
    return json.dumps(config, sort_keys=True, separators=(",", ":"))


def metric_bundle(cases, convergence: float) -> dict[str, float]:
    """Evaluate all predeclared popularity policies over fixed cases."""
    values = {
        "personalized": hit_rate(cases, lambda case: case.personalized),
        "popularity": hit_rate(cases, lambda case: case.popularity),
        "split": hit_rate(cases, split_recommendations),
    }
    for threshold in SWITCH_THRESHOLDS:
        values[f"switch:{threshold:.3f}"] = hit_rate(
            cases, lambda case, threshold=threshold: case.popularity if convergence >= threshold else case.personalized
        )
    for weight in BLEND_WEIGHTS:
        values[f"blend:{weight:.2f}"] = hit_rate(cases, lambda case, weight=weight: blended_recommendations(case, weight))
        for recency in RECENCY_WEIGHTS:
            values[f"blend:{weight:.2f}:recent:{recency:.2f}"] = hit_rate(
                cases, lambda case, weight=weight, recency=recency: blended_recommendations(case, weight, recency)
            )
    for recency in RECENCY_WEIGHTS:
        values[f"recent:{recency:.2f}"] = hit_rate(cases, lambda case, recency=recency: time_aware_popularity(case, recency))
    return values


def choose_recent(rows: list[dict[str, Any]]) -> float:
    """Select recent-popularity weight from prior completed outer outcomes."""
    if not rows:
        return 0.5
    return max(RECENCY_WEIGHTS, key=lambda value: (sum(r["policy_metrics"][f"recent:{value:.2f}"] for r in rows) / len(rows), -value))


def choose_blend(rows: list[dict[str, Any]], recency: float) -> float:
    """Select personalized blend weight conditional on the selected recency weight."""
    if not rows:
        return 0.5
    return max(
        BLEND_WEIGHTS,
        key=lambda value: (
            sum(r["policy_metrics"][f"blend:{value:.2f}:recent:{recency:.2f}"] for r in rows) / len(rows),
            -value,
        ),
    )


def choose_joint_blend(rows: list[dict[str, Any]]) -> tuple[float, float]:
    """Jointly select recency and personalized weights from completed outcomes only."""
    if not rows:
        return 0.5, 0.5
    candidates = list(itertools.product(RECENCY_WEIGHTS, BLEND_WEIGHTS))
    return max(
        candidates,
        key=lambda candidate: (
            sum(
                row["policy_metrics"][f"blend:{candidate[1]:.2f}:recent:{candidate[0]:.2f}"] for row in rows
            )
            / len(rows),
            -candidate[0],
            -candidate[1],
        ),
    )


def choose(items: list[dict[str, Any]], metric: str, candidates: tuple[float, ...], prefix: str, default: float) -> float:
    """Select the parameter with best mean prior completed outcome; use default when empty."""
    if not items:
        return default
    return max(
        candidates,
        key=lambda candidate: (
            sum(item["policy_metrics"][f"{prefix}:{candidate:.3f}" if prefix == "switch" else f"{prefix}:{candidate:.2f}"] for item in items)
            / len(items),
            -candidate,
        ),
    )


def select_config(
    grid: list[dict[str, float | int]], completed_months: list[int], cache: dict[tuple[str, int], dict[str, Any]]
) -> dict[str, float | int]:
    """Choose the personalized configuration by prior completed popularity gap only."""
    if not completed_months:
        return BOOTSTRAP_CONFIG
    def score(config: dict[str, float | int]) -> float:
        return sum(
            cache[(key(config), month, 3)]["metrics"]["personalized"]
            - cache[(key(config), month, 3)]["metrics"]["popularity"]
            for month in completed_months
        ) / len(completed_months)
    return max(grid, key=lambda config: (score(config), key(config)))


def main() -> int:
    """Execute and persist the fully nested study."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/raw/combined_dataset.xlsx")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--staged-horizon", action="store_true", help="Use 1/2/3-month observable bootstrap labels.")
    parser.add_argument("--popularity-bootstrap", action="store_true", help="Use time-aware popularity until nested tuning begins.")
    parser.add_argument(
        "--two-month-personalization",
        action="store_true",
        help="Fix the similarity look-ahead and sequence recency windows to two months.",
    )
    args = parser.parse_args()
    processor, recommender, practices = build_recommender(args.data)
    months = sorted(processor.get_all_months())
    outer_months = months[3:]
    grid = configuration_grid(args.two_month_personalization)
    bootstrap_config = (
        {**BOOTSTRAP_CONFIG, "similar_teams_lookahead_months": 2, "recent_improvements_months": 2}
        if args.two_month_personalization
        else BOOTSTRAP_CONFIG
    )
    cache: dict[tuple[str, int, int], dict[str, Any]] = {}

    def evaluate(config: dict[str, float | int], month: int, horizon: int = 3) -> dict[str, Any]:
        cache_key = (key(config), month, horizon)
        if cache_key not in cache:
            cases, convergence, full_window = build_cases(
                processor, recommender, practices, month, config, require_personalized=False, outcome_months=horizon
            )
            cache[cache_key] = {
                "metrics": metric_bundle(cases, convergence),
                "eligible_cases": len(cases),
                "convergence_hhi": convergence,
                "full_outcome_window": full_window,
            }
        return cache[cache_key]

    rows: list[dict[str, Any]] = []
    for outer_index, month in enumerate(outer_months):
        month_index = months.index(month)
        completed_months = (
            outer_months[:outer_index]
            if args.staged_horizon
            else [prior for prior in outer_months[:outer_index] if months.index(prior) + 2 < month_index]
        )
        for prior in completed_months:
            horizon = min(3, month_index - months.index(prior)) if args.staged_horizon else 3
            for config in grid:
                evaluate(config, prior, horizon)
        if args.staged_horizon and completed_months:
            def staged_score(config):
                return sum(evaluate(config, prior, min(3, month_index - months.index(prior)))["metrics"]["personalized"] - evaluate(config, prior, min(3, month_index - months.index(prior)))["metrics"]["popularity"] for prior in completed_months) / len(completed_months)
            selected_config = max(grid, key=lambda config: (staged_score(config), key(config)))
        else:
            selected_config = select_config(grid, completed_months, cache)
        if not completed_months:
            selected_config = bootstrap_config
        selected_result = evaluate(selected_config, month)
        completed_rows = [row for row in rows if row["month"] in completed_months]
        if args.staged_horizon:
            completed_rows = [
                {
                    "policy_metrics": evaluate(
                        row["selected_personalized_config"],
                        row["month"],
                        min(3, month_index - months.index(row["month"])),
                    )["metrics"]
                }
                for row in completed_rows
            ]
        threshold = choose(completed_rows, "", SWITCH_THRESHOLDS, "switch", 0.045)
        recency, weight = choose_joint_blend(completed_rows)
        if args.popularity_bootstrap and not completed_months:
            recency, weight = 0.5, 0.0
        policy_metrics = selected_result["metrics"]
        rows.append(
            {
                "month": month,
                "completed_inner_months": completed_months,
                "selection_mode": "nested" if completed_months else "predeclared_bootstrap",
                "selected_personalized_config": selected_config,
                "selected_switch_threshold": threshold,
                "selected_blend_weight": weight,
                "selected_recency_weight": recency,
                "eligible_cases": selected_result["eligible_cases"],
                "convergence_hhi": selected_result["convergence_hhi"],
                "full_outcome_window": selected_result["full_outcome_window"],
                "policy_metrics": policy_metrics,
                "selected": {
                    "popularity": policy_metrics["popularity"],
                    "time_aware_popularity": policy_metrics[f"recent:{recency:.2f}"],
                    "personalized": policy_metrics["personalized"],
                    "switch": policy_metrics[f"switch:{threshold:.3f}"],
                    "split": policy_metrics["split"],
                    "blend": policy_metrics[f"blend:{weight:.2f}:recent:{recency:.2f}"],
                },
            }
        )
        print(f"Completed {month}: {len(completed_months)} completed inner months", flush=True)

    def summarize(selection: list[dict[str, Any]]) -> dict[str, float]:
        result = {
            name: sum(row["selected"][name] for row in selection) / len(selection) if selection else 0.0
            for name in ("popularity", "time_aware_popularity", "personalized", "switch", "split", "blend")
        }
        result.update({f"{name}_popularity_gap": result[name] - result["popularity"] for name in result if name != "popularity"})
        return result

    report = {
        "study": "fully nested popularity strategy evaluation",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "protocol": {
            "grid_size": len(grid),
            "top_n": TOP_N,
            "config_selection": "maximize personalized HR@2 minus popularity HR@2 over fully completed inner months",
            "outcome_availability_rule": "inner_month_index + 2 < outer_month_index",
            "cohort": "all cases with observed outcomes and two eligible popularity recommendations",
            "personalized_failure": "remain in cohort; pure personalized policy receives no hit",
            "bootstrap_config": bootstrap_config,
            "two_month_personalization": args.two_month_personalization,
            "switch_thresholds": SWITCH_THRESHOLDS,
            "blend_weights": BLEND_WEIGHTS,
            "recency_weights": RECENCY_WEIGHTS,
            "blend_selection": "joint selection over every recency/personalized-weight pair",
        },
        "primary_summary": summarize([row for row in rows if row["full_outcome_window"]]),
        "sensitivity_summary": summarize(rows),
        "per_month": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["primary_summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
