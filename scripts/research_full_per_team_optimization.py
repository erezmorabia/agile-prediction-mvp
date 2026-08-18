#!/usr/bin/env python3
"""Stress-test fully optimized per-team three-factor configurations.

This is intentionally exploratory: a team chooses its peer/sequence component
configuration, factor mix, and popularity recency from only its own completed
three-month outcomes.  It is useful to quantify whether that flexibility helps,
but the small number of per-team labels makes it unsuitable as confirmation.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for path in (PROJECT_ROOT, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from research_popularity_strategies import build_recommender  # noqa: E402
from research_three_factor_blend import (  # noqa: E402
    RECENCY_WEIGHTS,
    FactorCase,
    build_cases,
    recommendations,
    weight_triples,
)

POLICIES = tuple(itertools.product(weight_triples(), RECENCY_WEIGHTS))
DEFAULT_POLICY_INDEX = POLICIES.index(((0.0, 0.0, 1.0), 0.5))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/raw/combined_dataset.xlsx")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--fixed-two-month-windows",
        action="store_true",
        help="Fix both the peer look-ahead and sequence recency windows at two months.",
    )
    return parser.parse_args()


def config_key(config: dict[str, float | int]) -> str:
    return json.dumps(config, sort_keys=True, separators=(",", ":"))


def component_configurations(fixed_two_month_windows: bool) -> tuple[dict[str, float | int], ...]:
    """Return the broad grid or its two-month-window constrained subset."""
    lookaheads = (2,) if fixed_two_month_windows else (1, 2, 3, 5)
    recencies = (2,) if fixed_two_month_windows else (1, 2, 3)
    return tuple(
        {
            "k_similar": k_similar,
            "similar_teams_lookahead_months": lookahead,
            "recent_improvements_months": recent,
            "min_similarity_threshold": minimum_similarity,
        }
        for k_similar, lookahead, recent, minimum_similarity in itertools.product(
            (5, 10, 19), lookaheads, recencies, (0.0, 0.5, 0.75)
        )
    )


def measure(cases: list[FactorCase]) -> tuple[tuple[float, ...], dict[str, tuple[float, ...]]]:
    """Cache every candidate policy's aggregate and team-level binary hit outcome."""
    aggregate: list[float] = []
    team_hits: dict[str, list[float]] = {case.team: [] for case in cases}
    for weights, recency in POLICIES:
        hits = {
            case.team: float(bool(set(recommendations(case, weights, recency)) & case.actual)) for case in cases
        }
        aggregate.append(sum(hits.values()) / len(cases) if cases else 0.0)
        for team, hit in hits.items():
            team_hits[team].append(hit)
    return tuple(aggregate), {team: tuple(hits) for team, hits in team_hits.items()}


def prefer(candidate: tuple[int, int]) -> tuple[float, float, float, float, float]:
    """Deterministic ties prefer popularity-heavy, lower-recency policies."""
    weights, recency = POLICIES[candidate[1]]
    return weights[2], -recency, -weights[0], -weights[1], -candidate[0]


def main() -> int:
    args = parse_args()
    processor, recommender, practices = build_recommender(args.data)
    months = sorted(processor.get_all_months())
    outer_months = months[3:]
    component_configs = component_configurations(args.fixed_two_month_windows)
    cached_cases: dict[tuple[int, int], tuple[list[FactorCase], bool]] = {}
    cached_metrics: dict[tuple[int, int], tuple[tuple[float, ...], dict[str, tuple[float, ...]]]] = {}

    for config_index, config in enumerate(component_configs, start=1):
        for month in outer_months:
            cases, full_window = build_cases(processor, recommender, practices, month, config)
            cache_key = (config_index - 1, month)
            cached_cases[cache_key] = (cases, full_window)
            cached_metrics[cache_key] = measure(cases)
        print(f"Prepared component configuration {config_index}/{len(component_configs)}", flush=True)

    def select_global(completed_months: list[int]) -> tuple[int, int]:
        if not completed_months:
            return 0, DEFAULT_POLICY_INDEX
        choices = itertools.product(range(len(component_configs)), range(len(POLICIES)))
        return max(
            choices,
            key=lambda candidate: (
                sum(cached_metrics[(candidate[0], month)][0][candidate[1]] for month in completed_months)
                / len(completed_months),
                *prefer(candidate),
            ),
        )

    def select_team(team: str, completed_months: list[int], fallback: tuple[int, int]) -> tuple[int, int, int]:
        usable_months = [
            month for month in completed_months if team in cached_metrics[(0, month)][1]
        ]
        if not usable_months:
            return fallback[0], fallback[1], 0
        choices = itertools.product(range(len(component_configs)), range(len(POLICIES)))
        choice = max(
            choices,
            key=lambda candidate: (
                sum(cached_metrics[(candidate[0], month)][1][team][candidate[1]] for month in usable_months)
                / len(usable_months),
                *prefer(candidate),
            ),
        )
        return choice[0], choice[1], len(usable_months)

    rows: list[dict[str, Any]] = []
    popularity_indices = [
        index for index, (weights, _) in enumerate(POLICIES) if weights == (0.0, 0.0, 1.0)
    ]
    for outer_index, month in enumerate(outer_months):
        month_index = months.index(month)
        completed_months = [prior for prior in outer_months[:outer_index] if months.index(prior) + 2 < month_index]
        global_choice = select_global(completed_months)
        base_config = 0
        if completed_months:
            popularity_index = max(
                popularity_indices,
                key=lambda policy_index: (
                    sum(cached_metrics[(base_config, prior)][0][policy_index] for prior in completed_months)
                    / len(completed_months),
                    -POLICIES[policy_index][1],
                ),
            )
        else:
            popularity_index = DEFAULT_POLICY_INDEX

        cases, full_window = cached_cases[(global_choice[0], month)]
        global_hr = cached_metrics[(global_choice[0], month)][0][global_choice[1]]
        popularity_hr = cached_metrics[(base_config, month)][0][popularity_index]
        per_team_hits: list[float] = []
        team_rows: list[dict[str, Any]] = []
        for case in cases:
            config_index, policy_index, evidence = select_team(case.team, completed_months, global_choice)
            selected_cases, _ = cached_cases[(config_index, month)]
            selected_case = next(item for item in selected_cases if item.team == case.team)
            weights, recency = POLICIES[policy_index]
            hit = float(bool(set(recommendations(selected_case, weights, recency)) & selected_case.actual))
            per_team_hits.append(hit)
            team_rows.append(
                {
                    "team": case.team,
                    "completed_team_cases": evidence,
                    "component_config": component_configs[config_index],
                    "weights": {"similarity": weights[0], "sequence": weights[1], "popularity": weights[2]},
                    "popularity_recency_weight": recency,
                    "hit": hit,
                }
            )
        global_weights, global_recency = POLICIES[global_choice[1]]
        _, popularity_recency = POLICIES[popularity_index]
        rows.append(
            {
                "month": month,
                "eligible_cases": len(cases),
                "full_outcome_window": full_window,
                "completed_inner_months": completed_months,
                "global_component_config": component_configs[global_choice[0]],
                "global_weights": {"similarity": global_weights[0], "sequence": global_weights[1], "popularity": global_weights[2]},
                "global_recency_weight": global_recency,
                "global_fully_optimized_hit_rate": global_hr,
                "time_aware_popularity_recency_weight": popularity_recency,
                "time_aware_popularity_hit_rate": popularity_hr,
                "per_team_fully_optimized_hit_rate": sum(per_team_hits) / len(per_team_hits) if per_team_hits else 0.0,
                "team_policies": team_rows,
            }
        )
        print(f"Completed selection for {month}: {len(completed_months)} completed inner months", flush=True)

    def summarize(selection: list[dict[str, Any]]) -> dict[str, float]:
        if not selection:
            return {}
        global_hr = sum(row["global_fully_optimized_hit_rate"] for row in selection) / len(selection)
        popularity_hr = sum(row["time_aware_popularity_hit_rate"] for row in selection) / len(selection)
        per_team_hr = sum(row["per_team_fully_optimized_hit_rate"] for row in selection) / len(selection)
        return {
            "global_fully_optimized": global_hr,
            "time_aware_popularity": popularity_hr,
            "per_team_fully_optimized": per_team_hr,
            "per_team_time_aware_gap": per_team_hr - popularity_hr,
        }

    report = {
        "study": "fully nested per-team component and factor optimization (exploratory research only)",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "protocol": {
            "component_configurations": len(component_configs),
            "component_grid": {
                "k_similar": (5, 10, 19),
                "similar_teams_lookahead_months": (2,) if args.fixed_two_month_windows else (1, 2, 3, 5),
                "recent_improvements_months": (2,) if args.fixed_two_month_windows else (1, 2, 3),
                "min_similarity_threshold": (0.0, 0.5, 0.75),
            },
            "factor_weight_combinations": len(weight_triples()),
            "popularity_recency_choices": RECENCY_WEIGHTS,
            "total_per_team_candidate_policies": len(component_configs) * len(POLICIES),
            "selection": "maximize each team's mean HR@2 on its earlier fully completed outcomes",
            "bootstrap": "global 100% popularity with 50% recent / 50% historical popularity",
            "outcome_availability_rule": "inner_month_index + 2 < outer_month_index",
            "warning": "At most four completed team outcomes exist; this is an overfitting stress test, not confirmation.",
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
