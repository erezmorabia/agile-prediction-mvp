#!/usr/bin/env python3
"""Compare global, per-team, and confidence-shrunk three-factor policies.

All policy decisions use only team/month outcomes whose three-month label had
already completed before the current prediction month.  The component scores
and fixed two-month windows come from research_three_factor_blend.py.
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

from research_popularity_strategies import TOP_N, build_recommender  # noqa: E402
from research_three_factor_blend import (  # noqa: E402
    RECENCY_WEIGHTS,
    FactorCase,
    build_cases,
    hit_rate,
    recommendations,
    weight_triples,
)

DEFAULT_POLICY = ((0.0, 0.0, 1.0), 0.5)
TEAM_PRIOR_EQUIVALENT_CASES = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/raw/combined_dataset.xlsx")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def choose_policy(groups: list[list[FactorCase]], candidates) -> tuple[tuple[float, float, float], float]:
    """Choose a policy by macro-average HR@2 across completed groups."""
    if not groups:
        return DEFAULT_POLICY
    return max(
        candidates,
        key=lambda candidate: (
            sum(hit_rate(group, candidate[0], candidate[1]) for group in groups) / len(groups),
            candidate[0][2],  # deterministic ties favor the simpler popularity-heavy policy
            -candidate[1],
            -candidate[0][0],
            -candidate[0][1],
        ),
    )


def team_cases_by_name(groups: list[list[FactorCase]]) -> dict[str, list[list[FactorCase]]]:
    """Keep one completed single-case group for every available team/month label."""
    by_team: dict[str, list[list[FactorCase]]] = defaultdict(list)
    for group in groups:
        for case in group:
            by_team[case.team].append([case])
    return by_team


def direct_hit(case: FactorCase, policy: tuple[tuple[float, float, float], float]) -> float:
    return float(bool(set(recommendations(case, policy[0], policy[1])) & case.actual))


def main() -> int:
    args = parse_args()
    processor, recommender, practices = build_recommender(args.data)
    months = sorted(processor.get_all_months())
    outer_months = months[3:]
    candidates = list(itertools.product(weight_triples(), RECENCY_WEIGHTS))
    cache: dict[int, tuple[list[FactorCase], bool]] = {}

    def evaluate(month: int) -> tuple[list[FactorCase], bool]:
        if month not in cache:
            cache[month] = build_cases(processor, recommender, practices, month)
        return cache[month]

    rows: list[dict[str, Any]] = []
    for outer_index, month in enumerate(outer_months):
        month_index = months.index(month)
        completed_months = [prior for prior in outer_months[:outer_index] if months.index(prior) + 2 < month_index]
        completed_groups = [evaluate(prior)[0] for prior in completed_months]
        global_policy = choose_policy(completed_groups, candidates)
        popularity_policy = choose_policy(completed_groups, [((0.0, 0.0, 1.0), recency) for recency in RECENCY_WEIGHTS])
        local_groups = team_cases_by_name(completed_groups)
        cases, full_window = evaluate(month)

        pure_team_hits: list[float] = []
        adaptive_hits: list[float] = []
        policy_rows: list[dict[str, Any]] = []
        for case in cases:
            prior_groups = local_groups.get(case.team, [])
            local_policy = choose_policy(prior_groups, candidates) if prior_groups else global_policy
            evidence = sum(len(group) for group in prior_groups)
            confidence = evidence / (evidence + TEAM_PRIOR_EQUIVALENT_CASES)
            adaptive_weights = tuple(
                (1.0 - confidence) * global_policy[0][index] + confidence * local_policy[0][index]
                for index in range(3)
            )
            adaptive_policy = (
                adaptive_weights,
                (1.0 - confidence) * global_policy[1] + confidence * local_policy[1],
            )
            pure_team_hits.append(direct_hit(case, local_policy))
            adaptive_hits.append(direct_hit(case, adaptive_policy))
            policy_rows.append(
                {
                    "team": case.team,
                    "completed_team_cases": evidence,
                    "team_confidence": confidence,
                    "per_team_weights": {
                        "similarity": local_policy[0][0],
                        "sequence": local_policy[0][1],
                        "popularity": local_policy[0][2],
                    },
                    "per_team_recency_weight": local_policy[1],
                    "adaptive_weights": {
                        "similarity": adaptive_policy[0][0],
                        "sequence": adaptive_policy[0][1],
                        "popularity": adaptive_policy[0][2],
                    },
                    "adaptive_recency_weight": adaptive_policy[1],
                }
            )

        rows.append(
            {
                "month": month,
                "eligible_cases": len(cases),
                "full_outcome_window": full_window,
                "completed_inner_months": completed_months,
                "global_weights": {
                    "similarity": global_policy[0][0],
                    "sequence": global_policy[0][1],
                    "popularity": global_policy[0][2],
                },
                "global_recency_weight": global_policy[1],
                "global_three_factor_hit_rate": hit_rate(cases, global_policy[0], global_policy[1]),
                "time_aware_popularity_recency_weight": popularity_policy[1],
                "time_aware_popularity_hit_rate": hit_rate(cases, popularity_policy[0], popularity_policy[1]),
                "per_team_configuration_hit_rate": sum(pure_team_hits) / len(pure_team_hits) if pure_team_hits else 0.0,
                "adaptive_confidence_hit_rate": sum(adaptive_hits) / len(adaptive_hits) if adaptive_hits else 0.0,
                "team_policies": policy_rows,
            }
        )
        print(f"Completed {month}: {len(completed_months)} completed inner months", flush=True)

    def summarize(selection: list[dict[str, Any]]) -> dict[str, float]:
        if not selection:
            return {}
        names = (
            "global_three_factor_hit_rate",
            "time_aware_popularity_hit_rate",
            "per_team_configuration_hit_rate",
            "adaptive_confidence_hit_rate",
        )
        result = {name: sum(row[name] for row in selection) / len(selection) for name in names}
        result["per_team_time_aware_gap"] = (
            result["per_team_configuration_hit_rate"] - result["time_aware_popularity_hit_rate"]
        )
        result["adaptive_time_aware_gap"] = result["adaptive_confidence_hit_rate"] - result["time_aware_popularity_hit_rate"]
        return result

    report = {
        "study": "fully nested team-adaptive direct three-factor blend (research only)",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "protocol": {
            "factor_weight_rule": "similarity + sequence + popularity = 1.0",
            "factor_weight_grid": weight_triples(),
            "popularity_recency_weights": RECENCY_WEIGHTS,
            "global_policy": "selected from all earlier fully completed team/month outcomes",
            "per_team_policy": "selected from that team's earlier fully completed outcomes; global policy when none exist",
            "adaptive_confidence": "linear shrinkage from global policy to per-team policy",
            "team_prior_equivalent_cases": TEAM_PRIOR_EQUIVALENT_CASES,
            "team_confidence": "completed_team_cases / (completed_team_cases + team_prior_equivalent_cases)",
            "outcome_availability_rule": "inner_month_index + 2 < outer_month_index",
            "cohort": "all cases with observed outcomes and two eligible popularity recommendations",
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
