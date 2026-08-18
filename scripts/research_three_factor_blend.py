#!/usr/bin/env python3
"""Evaluate a direct similarity / sequence / popularity blend without app changes.

For every prediction month, factor weights and popularity recency are selected
only from earlier outer months whose complete three-month outcome window has
closed.  The component windows are fixed at two months, following the prior
two-month study.  This script deliberately reproduces the component-scoring
steps from RecommendationEngine rather than altering production code.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for path in (PROJECT_ROOT, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from research_popularity_strategies import (  # noqa: E402
    TOP_N,
    actual_improvements,
    build_recommender,
    normalized_scores,
    ranked_popularity,
    recent_popularity,
)

WEIGHT_STEP = 0.25
RECENCY_WEIGHTS = (0.0, 0.25, 0.50, 0.75, 1.0)
COMPONENT_CONFIG = {
    "k_similar": 10,
    "similar_teams_lookahead_months": 2,
    "recent_improvements_months": 2,
    "min_similarity_threshold": 0.5,
}


@dataclass(frozen=True)
class FactorCase:
    """One fixed-cohort team/month example with independently normalized factors."""

    team: str
    similarity_scores: dict[str, float]
    sequence_scores: dict[str, float]
    historical_popularity_scores: dict[str, float]
    recent_popularity_scores: dict[str, float]
    popularity: tuple[str, ...]
    actual: frozenset[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/raw/combined_dataset.xlsx")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def weight_triples() -> tuple[tuple[float, float, float], ...]:
    """Return the 15 coarse simplex points whose three weights total exactly one."""
    units = round(1.0 / WEIGHT_STEP)
    return tuple(
        (similarity / units, sequence / units, (units - similarity - sequence) / units)
        for similarity in range(units + 1)
        for sequence in range(units - similarity + 1)
    )


def factor_scores(
    recommender, team: str, baseline_month: int, component_config: dict[str, float | int] = COMPONENT_CONFIG
) -> tuple[dict[str, float], dict[str, float]]:
    """Reproduce the production similarity and sequence components before their blend."""
    history = recommender.processor.get_team_history(team)
    current_scores = history[baseline_month]
    months = sorted(history)
    current_index = months.index(baseline_month)
    recommender.sequence_mapper.learn_sequences_up_to_month(baseline_month)

    similarity_scores: defaultdict[str, float] = defaultdict(float)
    try:
        similar_teams = recommender.similarity_engine.find_similar_teams(
            team,
            baseline_month,
            k=component_config["k_similar"],
            min_similarity=component_config["min_similarity_threshold"],
        )
    except ValueError:
        similar_teams = []
    for similar_team, peer_similarity, historical_month in similar_teams:
        try:
            similar_history = recommender.processor.get_team_history(similar_team)
            historical_state = similar_history[historical_month]
            similar_months = sorted(similar_history)
            historical_index = similar_months.index(historical_month)
            best_improvements: dict[str, float] = {}
            for months_ahead in range(1, int(component_config["similar_teams_lookahead_months"]) + 1):
                if historical_index + months_ahead >= len(similar_months):
                    break
                future_month = similar_months[historical_index + months_ahead]
                if future_month > baseline_month:
                    break
                for practice, before, after in zip(
                    recommender.practices, historical_state, similar_history[future_month]
                ):
                    if after > before:
                        best_improvements[practice] = max(best_improvements.get(practice, 0.0), after - before)
            for practice, magnitude in best_improvements.items():
                similarity_scores[practice] += peer_similarity * magnitude
        except (KeyError, ValueError, IndexError):
            continue

    recently_improved: set[str] = set()
    for months_back in range(1, min(int(component_config["recent_improvements_months"]), current_index) + 1):
        past_scores = history[months[current_index - months_back]]
        recently_improved.update(
            practice for practice, before, after in zip(recommender.practices, past_scores, current_scores) if after > before
        )
    sequence_scores: defaultdict[str, float] = defaultdict(float)
    for practice in recommender.practices:
        if practice not in recently_improved:
            continue
        for following_practice, probability in recommender.sequence_mapper.get_typical_next_practices(practice, top_n=3):
            sequence_scores[following_practice] += probability
    return normalized_scores(dict(similarity_scores)), normalized_scores(dict(sequence_scores))


def build_cases(
    processor,
    recommender,
    practices: list[str],
    test_month: int,
    component_config: dict[str, float | int] = COMPONENT_CONFIG,
) -> tuple[list[FactorCase], bool]:
    """Build a fixed, popularity-defined cohort and all three score vectors."""
    months = sorted(processor.get_all_months())
    test_index = months.index(test_month)
    baseline_month = months[test_index - 1]
    recommender.sequence_mapper.learn_sequences_up_to_month(baseline_month)
    recent_scores = recent_popularity(processor, practices, baseline_month)
    cases: list[FactorCase] = []
    for team in processor.get_all_teams():
        history = processor.get_team_history(team)
        if baseline_month not in history or test_month not in history:
            continue
        actual = actual_improvements(history, months, test_index, practices)
        if not actual:
            continue
        popularity, historical_scores = ranked_popularity(recommender, history[baseline_month])
        if len(popularity) != TOP_N:
            continue
        similarity, sequence = factor_scores(recommender, team, baseline_month, component_config)
        available = {practice for practice, level in zip(practices, history[baseline_month]) if level < 1.0}
        cases.append(
            FactorCase(
                team,
                {practice: similarity.get(practice, 0.0) for practice in available},
                {practice: sequence.get(practice, 0.0) for practice in available},
                {practice: historical_scores.get(practice, 0.0) for practice in available},
                {practice: recent_scores.get(practice, 0.0) for practice in available},
                popularity,
                actual,
            )
        )
    return cases, test_index + 2 < len(months)


def recommendations(case: FactorCase, weights: tuple[float, float, float], recency: float) -> tuple[str, ...]:
    """Rank the direct three-factor score; weights are similarity, sequence, popularity."""
    similarity_weight, sequence_weight, popularity_weight = weights
    practices = set(case.similarity_scores) | set(case.sequence_scores) | set(case.historical_popularity_scores)
    scores = {
        practice: (
            similarity_weight * case.similarity_scores.get(practice, 0.0)
            + sequence_weight * case.sequence_scores.get(practice, 0.0)
            + popularity_weight
            * (
                (1.0 - recency) * case.historical_popularity_scores.get(practice, 0.0)
                + recency * case.recent_popularity_scores.get(practice, 0.0)
            )
        )
        for practice in practices
    }
    return tuple(sorted(scores, key=lambda practice: (-scores[practice], practice))[:TOP_N])


def hit_rate(cases: list[FactorCase], weights: tuple[float, float, float], recency: float) -> float:
    if not cases:
        return 0.0
    return sum(bool(set(recommendations(case, weights, recency)) & case.actual) for case in cases) / len(cases)


def main() -> int:
    args = parse_args()
    processor, recommender, practices = build_recommender(args.data)
    months = sorted(processor.get_all_months())
    outer_months = months[3:]
    triples = weight_triples()
    cache: dict[int, tuple[list[FactorCase], bool]] = {}

    def evaluate(month: int) -> tuple[list[FactorCase], bool]:
        if month not in cache:
            cache[month] = build_cases(processor, recommender, practices, month)
        return cache[month]

    rows: list[dict[str, Any]] = []
    for outer_index, month in enumerate(outer_months):
        month_index = months.index(month)
        completed_months = [prior for prior in outer_months[:outer_index] if months.index(prior) + 2 < month_index]
        completed_cases = [evaluate(prior)[0] for prior in completed_months]

        if completed_cases:
            candidates = list(itertools.product(triples, RECENCY_WEIGHTS))
            selected_weights, selected_recency = max(
                candidates,
                key=lambda candidate: (
                    sum(hit_rate(cases, candidate[0], candidate[1]) for cases in completed_cases) / len(completed_cases),
                    candidate[0][2],
                    -candidate[1],
                    -candidate[0][0],
                    -candidate[0][1],
                ),
            )
            baseline_recency = max(
                RECENCY_WEIGHTS,
                key=lambda recency: (
                    sum(hit_rate(cases, (0.0, 0.0, 1.0), recency) for cases in completed_cases) / len(completed_cases),
                    -recency,
                ),
            )
            mode = "nested"
        else:
            selected_weights, selected_recency = (0.0, 0.0, 1.0), 0.5
            baseline_recency = 0.5
            mode = "predeclared_popularity_bootstrap"

        cases, full_window = evaluate(month)
        rows.append(
            {
                "month": month,
                "eligible_cases": len(cases),
                "full_outcome_window": full_window,
                "completed_inner_months": completed_months,
                "selection_mode": mode,
                "selected_weights": {"similarity": selected_weights[0], "sequence": selected_weights[1], "popularity": selected_weights[2]},
                "selected_recency_weight": selected_recency,
                "three_factor_hit_rate": hit_rate(cases, selected_weights, selected_recency),
                "time_aware_popularity_recency_weight": baseline_recency,
                "time_aware_popularity_hit_rate": hit_rate(cases, (0.0, 0.0, 1.0), baseline_recency),
                "static_popularity_hit_rate": hit_rate(cases, (0.0, 0.0, 1.0), 0.0),
            }
        )
        print(f"Completed {month}: {len(completed_months)} completed inner months", flush=True)

    def summarize(selection: list[dict[str, Any]]) -> dict[str, float]:
        if not selection:
            return {}
        three_factor = sum(row["three_factor_hit_rate"] for row in selection) / len(selection)
        time_aware = sum(row["time_aware_popularity_hit_rate"] for row in selection) / len(selection)
        static = sum(row["static_popularity_hit_rate"] for row in selection) / len(selection)
        return {
            "three_factor": three_factor,
            "time_aware_popularity": time_aware,
            "static_popularity": static,
            "three_factor_time_aware_gap": three_factor - time_aware,
        }

    report = {
        "study": "fully nested direct three-factor blend (research only)",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "protocol": {
            "component_configuration": COMPONENT_CONFIG,
            "factor_weight_grid": triples,
            "factor_weight_rule": "similarity + sequence + popularity = 1.0",
            "popularity_recency_weights": RECENCY_WEIGHTS,
            "weight_selection": "jointly maximize mean HR@2 over earlier fully completed outer months",
            "outcome_availability_rule": "inner_month_index + 2 < outer_month_index",
            "bootstrap": "100% popularity with 50% recent / 50% historical popularity",
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
