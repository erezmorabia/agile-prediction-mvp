#!/usr/bin/env python3
"""Run the isolated popularity-baseline strategy study.

This script deliberately imports the production recommender without modifying it.
It evaluates three pre-specified policy families: switch, split, and score blend.
For every outer test month, policy parameters are chosen solely from preceding
outer-month results. This first-pass harness holds a full-dataset-tuned
personalized configuration fixed, so its outputs are diagnostic—not a
leak-free confirmation. The fully nested replacement must select that
configuration from prior completed outcomes as well.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data import DataLoader, DataProcessor, DataValidator
from src.ml import RecommendationEngine, SequenceMapper, SimilarityEngine


TOP_N = 2
PERSONALIZED_CONFIG = {
    "k_similar": 19,
    "similarity_weight": 0.7,
    "similar_teams_lookahead_months": 3,
    "recent_improvements_months": 3,
    "min_similarity_threshold": 0.75,
}
SWITCH_THRESHOLDS = (0.043, 0.045, 0.047, 0.049)
BLEND_WEIGHTS = (0.0, 0.25, 0.50, 0.75)


@dataclass(frozen=True)
class Case:
    """Keep all precomputed recommendations and later observed outcomes for one team/month."""

    personalized: tuple[str, ...]
    personalized_scores: dict[str, float]
    popularity: tuple[str, ...]
    popularity_scores: dict[str, float]
    recent_popularity_scores: dict[str, float]
    actual: frozenset[str]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/raw/combined_dataset.xlsx", help="Input workbook path.")
    parser.add_argument("--output", type=Path, help="JSON report path (default: timestamped file in results/).")
    return parser.parse_args()


def build_recommender(data_path: str) -> tuple[DataProcessor, RecommendationEngine, list[str]]:
    """Load and filter the source data using the application's normal preparation flow."""
    loader = DataLoader(data_path)
    frame = loader.load()
    validator = DataValidator(frame, loader.practices)
    practices, _ = validator.filter_high_missing_practices(loader.practices, threshold=90.0)
    processor = DataProcessor(frame, practices)
    processor.process()
    similarity = SimilarityEngine(processor)
    sequences = SequenceMapper(processor, practices)
    return processor, RecommendationEngine(similarity, sequences, practices), practices


def actual_improvements(
    history: dict[int, Any], months: list[int], test_index: int, practices: list[str], outcome_months: int = 3
) -> frozenset[str]:
    """Find improvements from the baseline through the available three-month outcome window."""
    baseline = history[months[test_index - 1]]
    improved: set[str] = set()
    for index in range(test_index, min(test_index + outcome_months, len(months))):
        if months[index] not in history:
            continue
        for practice, before, after in zip(practices, baseline, history[months[index]]):
            if after > before:
                improved.add(practice)
    return frozenset(improved)


def convergence_hhi(processor: DataProcessor, practices: list[str], cutoff: int) -> float:
    """Measure prior organization-wide concentration of improvements (Herfindahl index)."""
    counts: Counter[str] = Counter()
    for team in processor.get_all_teams():
        history = processor.get_team_history(team)
        team_months = sorted(month for month in history if month < cutoff)
        for previous, current in zip(team_months, team_months[1:]):
            for practice, before, after in zip(practices, history[previous], history[current]):
                if after > before:
                    counts[practice] += 1
    total = sum(counts.values())
    return sum((count / total) ** 2 for count in counts.values()) if total else 0.0


def normalized_scores(scores: dict[str, float]) -> dict[str, float]:
    """Normalize non-negative scores to [0, 1] while retaining deterministic zero values."""
    maximum = max(scores.values(), default=0.0)
    return {practice: value / maximum if maximum else 0.0 for practice, value in scores.items()}


def ranked_popularity(recommender: RecommendationEngine, baseline: Any) -> tuple[tuple[str, ...], dict[str, float]]:
    """Build eligible popularity rankings using only state and counts known before prediction."""
    popularity = recommender.sequence_mapper.get_practice_popularity()
    maxed_out = {practice for practice, level in zip(recommender.practices, baseline) if level >= 1.0}
    eligible = {practice: float(score) for practice, score in popularity.items() if practice not in maxed_out}
    ranked = tuple(sorted(eligible, key=lambda practice: (-eligible[practice], practice)))
    return ranked[:TOP_N], normalized_scores(eligible)


def recent_popularity(processor: DataProcessor, practices: list[str], baseline_month: int) -> dict[str, float]:
    """Score organization-wide improvements in the immediately preceding observed transition."""
    months = sorted(processor.get_all_months())
    index = months.index(baseline_month)
    if index == 0:
        return {}
    previous = months[index - 1]
    counts: Counter[str] = Counter()
    for team in processor.get_all_teams():
        history = processor.get_team_history(team)
        if previous in history and baseline_month in history:
            for practice, before, after in zip(practices, history[previous], history[baseline_month]):
                if after > before:
                    counts[practice] += 1
    return normalized_scores({practice: float(score) for practice, score in counts.items()})


def time_aware_popularity(case: Case, recency_weight: float) -> tuple[str, ...]:
    """Rank eligible practices by a normalized historical/recent popularity mixture."""
    practices = set(case.popularity_scores) | set(case.recent_popularity_scores)
    scores = {
        practice: (1.0 - recency_weight) * case.popularity_scores.get(practice, 0.0)
        + recency_weight * case.recent_popularity_scores.get(practice, 0.0)
        for practice in practices
    }
    return tuple(sorted(scores, key=lambda practice: (-scores[practice], practice))[:TOP_N])


def build_cases(
    processor: DataProcessor,
    recommender: RecommendationEngine,
    practices: list[str],
    test_month: int,
    personalized_config: dict[str, float | int] | None = None,
    require_personalized: bool = True,
    outcome_months: int = 3,
) -> tuple[list[Case], float, bool]:
    """Precompute all recommendation ingredients for one outer test month."""
    months = sorted(processor.get_all_months())
    test_index = months.index(test_month)
    baseline_month = months[test_index - 1]
    config = personalized_config or PERSONALIZED_CONFIG
    convergence = convergence_hhi(processor, practices, baseline_month)
    recent_scores = recent_popularity(processor, practices, baseline_month)
    # Popularity is cohort-defining in the fully nested study, so learn it before
    # any personalized call can fail. This preserves a configuration-independent
    # population across every candidate configuration.
    recommender.sequence_mapper.learn_sequences_up_to_month(baseline_month)
    cases: list[Case] = []
    for team in processor.get_all_teams():
        history = processor.get_team_history(team)
        if baseline_month not in history or test_month not in history:
            continue
        actual = actual_improvements(history, months, test_index, practices, outcome_months)
        if not actual:
            continue
        popularity, popularity_scores = ranked_popularity(recommender, history[baseline_month])
        if len(popularity) != TOP_N:
            continue
        try:
            # Request every scored eligible practice. This preserves the unchanged production
            # ranking while giving the research-only blend a complete personalized score vector.
            recommendations = recommender.recommend(
                team,
                baseline_month,
                top_n=len(practices),
                allow_first_three_months=True,
                **config,
            )
        except ValueError:
            if require_personalized:
                continue
            recommendations = []
        personalized_scores = {practice: float(score) for practice, score, _ in recommendations}
        personalized = tuple(practice for practice, _, _ in recommendations[:TOP_N])
        if require_personalized and len(personalized) != TOP_N:
            continue
        eligible_recent = {practice: score for practice, score in recent_scores.items() if practice in popularity_scores}
        cases.append(
            Case(personalized, normalized_scores(personalized_scores), popularity, popularity_scores, eligible_recent, actual)
        )
    full_window = test_index + 2 < len(months)
    return cases, convergence, full_window


def hit_rate(cases: list[Case], recommendation_fn) -> float:
    """Calculate HR@2 for a policy over a fixed eligible-case population."""
    if not cases:
        return 0.0
    return sum(bool(set(recommendation_fn(case)) & case.actual) for case in cases) / len(cases)


def split_recommendations(case: Case) -> tuple[str, ...]:
    """Use one popularity practice and one distinct personalized practice."""
    selected = [case.popularity[0]]
    selected.extend(practice for practice in case.personalized if practice not in selected)
    selected.extend(practice for practice in case.popularity if practice not in selected)
    return tuple(selected[:TOP_N])


def blended_recommendations(case: Case, weight: float, recency_weight: float = 0.0) -> tuple[str, ...]:
    """Rank eligible practices by a deterministic blend of personalized and popularity scores."""
    popularity = {
        practice: (1.0 - recency_weight) * case.popularity_scores.get(practice, 0.0)
        + recency_weight * case.recent_popularity_scores.get(practice, 0.0)
        for practice in set(case.popularity_scores) | set(case.recent_popularity_scores)
    }
    practices = set(case.personalized_scores) | set(popularity)
    scores = {
        practice: weight * case.personalized_scores.get(practice, 0.0)
        + (1.0 - weight) * popularity.get(practice, 0.0)
        for practice in practices
    }
    return tuple(sorted(scores, key=lambda practice: (-scores[practice], practice))[:TOP_N])


def choose_parameter(history: list[dict[str, Any]], key: str, candidates: tuple[float, ...], default: float) -> float:
    """Choose a parameter from prior outer outcomes only; use a predeclared default to bootstrap."""
    if not history:
        return default
    averages = {
        candidate: sum(row["metrics"][f"{key}:{candidate:.2f}"] for row in history) / len(history)
        for candidate in candidates
    }
    return max(candidates, key=lambda candidate: (averages[candidate], -candidate))


def mean(rows: list[dict[str, Any]], metric: str) -> float:
    """Return a macro-average safely."""
    return sum(row["metrics"][metric] for row in rows) / len(rows) if rows else 0.0


def main() -> int:
    """Run the study and write a standalone JSON report."""
    args = parse_args()
    processor, recommender, practices = build_recommender(args.data)
    months = sorted(processor.get_all_months())
    test_months = months[3:]
    all_rows: list[dict[str, Any]] = []

    for test_month in test_months:
        cases, convergence, full_window = build_cases(processor, recommender, practices, test_month)
        metrics = {"popularity": hit_rate(cases, lambda case: case.popularity), "split": hit_rate(cases, split_recommendations)}
        for threshold in SWITCH_THRESHOLDS:
            metrics[f"switch:{threshold:.2f}"] = hit_rate(
                cases, lambda case, threshold=threshold: case.popularity if convergence >= threshold else case.personalized
            )
        for weight in BLEND_WEIGHTS:
            metrics[f"blend:{weight:.2f}"] = hit_rate(cases, lambda case, weight=weight: blended_recommendations(case, weight))

        prior_rows = all_rows[:]  # These rows are the only outcomes available to parameter selection.
        threshold = choose_parameter(prior_rows, "switch", SWITCH_THRESHOLDS, default=0.045)
        weight = choose_parameter(prior_rows, "blend", BLEND_WEIGHTS, default=0.50)
        all_rows.append(
            {
                "month": test_month,
                "full_outcome_window": full_window,
                "eligible_cases": len(cases),
                "convergence_hhi": convergence,
                "selected_switch_threshold": threshold,
                "selected_blend_weight": weight,
                "metrics": metrics,
                "selected": {
                    "popularity": metrics["popularity"],
                    "switch": metrics[f"switch:{threshold:.2f}"],
                    "split": metrics["split"],
                    "blend": metrics[f"blend:{weight:.2f}"],
                },
            }
        )

    primary_rows = [row for row in all_rows if row["full_outcome_window"]]
    def summary(rows: list[dict[str, Any]]) -> dict[str, float]:
        popularity = sum(row["selected"]["popularity"] for row in rows) / len(rows) if rows else 0.0
        return {
            policy: mean([{**row, "metrics": row["selected"]} for row in rows], policy) for policy in ("popularity", "switch", "split", "blend")
        } | {f"{policy}_popularity_gap": mean([{**row, "metrics": row["selected"]} for row in rows], policy) - popularity for policy in ("switch", "split", "blend")}

    report = {
        "study": "popularity baseline strategies",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "data": args.data,
        "protocol": {
            "top_n": TOP_N,
            "primary_population": "outer test months with complete three-month outcome windows",
            "sensitivity_population": "all seven eligible outer test months",
            "selection": "thresholds and blend weights use prior outer-month outcomes only",
            "policies": ["switch", "split", "blend"],
        },
        "primary_summary": summary(primary_rows),
        "sensitivity_summary": summary(all_rows),
        "per_month": all_rows,
    }
    output = args.output or Path("results") / f"popularity_strategy_research_{datetime.now():%Y%m%d_%H%M%S}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    print(json.dumps(report["primary_summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
