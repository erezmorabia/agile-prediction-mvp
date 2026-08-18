"""
BacktestEngine: Validate the global two-month adaptive blend against historical data.
"""

import logging

from scipy.special import comb

from src.ml.policy import TOP_N, policy_summary

from .metrics import MetricsCalculator

logger = logging.getLogger(__name__)

# Returned for a scope (primary/sensitivity) with zero qualifying months. Rate fields
# are None (not 0.0) so callers can render "not enough completed months" instead of
# a misleading 0%.
_EMPTY_SCOPE = {
    "months_included": 0,
    "total_predictions": 0,
    "correct_predictions": 0,
    "overall_accuracy": None,
    "random_baseline": None,
    "improvement_gap": None,
    "improvement_factor": None,
    "time_aware_popularity_accuracy": None,
    "blend_minus_popularity": None,
    "overall_precision": None,
    "overall_recall": None,
    "overall_mrr": None,
    "random_precision": None,
    "random_recall": None,
    "random_mrr": None,
    "precision_gap": None,
    "recall_gap": None,
    "mrr_gap": None,
    "precision_improvement_factor": None,
    "recall_improvement_factor": None,
    "mrr_improvement_factor": None,
    "teams_tested": 0,
    "avg_improvements_per_case": None,
}


class BacktestEngine:
    """Run backtest validation of the global two-month adaptive blend using historical data."""

    def __init__(self, recommender_engine, processor):
        """
        Initialize BacktestEngine.

        Args:
            recommender_engine: RecommendationEngine instance (its `.policy_engine`
                supplies the cohort, the monthly policy selection, and the scoring -
                the same PolicyEngine the live flow and the CLI use).
            processor: DataProcessor instance
        """
        self.recommender = recommender_engine
        self.processor = processor
        self.policy_engine = recommender_engine.policy_engine

    @staticmethod
    def _expected_random_mrr(n: int, k: int, top_n: int) -> float:
        """
        Exact expected MRR for a random top-N pick out of n practices, k of which are correct.

        Uses the negative hypergeometric rank distribution: the probability that the first
        correct practice lands at rank r (drawing without replacement) is
        P(R=r) = C(n-r, k-1) / C(n, k). Unlike precision/recall's random baselines, this is
        not linear in k, so it must be computed per case (using that case's actual k) rather
        than from an average k_avg.
        """
        if n <= 0 or k <= 0 or top_n <= 0:
            return 0.0
        try:
            denom = comb(n, k, exact=True)
            if denom == 0:
                return 0.0
            expected = 0.0
            for r in range(1, min(top_n, n) + 1):
                numer = comb(n - r, k - 1, exact=True)
                expected += (numer / denom) / r
            return expected
        except (ValueError, ZeroDivisionError):
            return 0.0

    @staticmethod
    def _baseline_from_k_avg(k_avg: float, total_practices: int, top_n: int) -> float:
        """
        Probability of getting at least one correct recommendation by random selection.

        P(at least one correct) = 1 - C(n-k_avg, top_n) / C(n, top_n), where n = total
        practices, k_avg = average number of practices improved per case, top_n =
        number of recommendations drawn.
        """
        if total_practices <= 0:
            return 0.0
        if k_avg > 0 and top_n > 0 and total_practices >= k_avg and total_practices >= top_n:
            try:
                p_none = comb(total_practices - k_avg, top_n, exact=False) / comb(total_practices, top_n, exact=False)
                return 1.0 - p_none
            except (ValueError, ZeroDivisionError):
                return min(1.0, (k_avg / total_practices) * top_n)
        return min(1.0, (k_avg / total_practices) * top_n)

    def _empty_month_row(self, month: int) -> dict:
        engine = self.policy_engine
        selected = engine.select_policy(month)
        popularity_arm = engine.select_popularity_arm(month)
        return {
            "month": month,
            "full_outcome_window": engine.full_outcome_window(month),
            "evaluable_cases": 0,
            "predictions": 0,
            "correct": 0,
            "accuracy": 0.0,
            "time_aware_popularity_accuracy": 0.0,
            "blend_minus_popularity": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "mrr": 0.0,
            "teams_tested": 0,
            "selected_policy": policy_summary(selected),
            "popularity_arm_recency_weight": popularity_arm.policy.recency_weight,
        }

    def _score_month(self, month: int, total_practices: int):
        """Score one prediction month over its fixed evaluable cohort."""
        engine = self.policy_engine
        cases = engine.evaluable_cases(month)
        if not cases:
            return self._empty_month_row(month), [], []

        selected = engine.select_policy(month)
        popularity_arm = engine.select_popularity_arm(month)

        predictions = 0
        correct = 0
        popularity_correct = 0
        precision_sum = 0.0
        recall_sum = 0.0
        mrr_sum = 0.0
        improvements_per_case = []
        expected_mrr_per_case = []

        for case in cases:
            actual = case.actual_improved
            improvements_per_case.append(len(actual))
            expected_mrr_per_case.append(self._expected_random_mrr(total_practices, len(actual), TOP_N))

            ordered = list(engine.top_practices(case.components, selected.policy))
            recommended = set(ordered)
            predictions += 1
            if recommended & actual:
                correct += 1

            popularity_recommended = set(engine.top_practices(case.components, popularity_arm.policy))
            if popularity_recommended & actual:
                popularity_correct += 1

            precision_sum += MetricsCalculator.calculate_hit_rate(ordered, actual)
            recall_sum += len(recommended & actual) / len(actual)
            mrr_sum += MetricsCalculator.calculate_mrr(ordered, actual)

        accuracy = correct / predictions
        popularity_accuracy = popularity_correct / predictions
        row = {
            "month": month,
            "full_outcome_window": engine.full_outcome_window(month),
            "evaluable_cases": len(cases),
            "predictions": predictions,
            "correct": correct,
            "accuracy": accuracy,
            "time_aware_popularity_accuracy": popularity_accuracy,
            "blend_minus_popularity": accuracy - popularity_accuracy,
            "precision": precision_sum / predictions,
            "recall": recall_sum / predictions,
            "mrr": mrr_sum / predictions,
            "teams_tested": predictions,
            "selected_policy": policy_summary(selected),
            "popularity_arm_recency_weight": popularity_arm.policy.recency_weight,
        }
        return row, improvements_per_case, expected_mrr_per_case

    def _aggregate_scope(
        self,
        rows: list,
        raw_improvements_by_month: dict,
        raw_expected_mrr_by_month: dict,
        total_practices: int,
    ) -> dict:
        """Macro-average (per-month mean) aggregate over one scope (primary or
        sensitivity). Random baselines mirror the same aggregation as their headline
        counterparts so the two are directly comparable - see the module-level note in
        the original implementation and docs/known-issues/04-accuracy-vs-baseline-
        aggregation-mismatch.md.
        """
        if not rows:
            return dict(_EMPTY_SCOPE)

        months = [r["month"] for r in rows]
        total_predictions = sum(r["predictions"] for r in rows)
        correct_predictions = sum(r["correct"] for r in rows)
        overall_accuracy = sum(r["accuracy"] for r in rows) / len(rows)
        overall_popularity = sum(r["time_aware_popularity_accuracy"] for r in rows) / len(rows)
        overall_precision = sum(r["precision"] for r in rows) / len(rows)
        overall_recall = sum(r["recall"] for r in rows) / len(rows)
        overall_mrr = sum(r["mrr"] for r in rows) / len(rows)

        pooled_improvements = [k for m in months for k in raw_improvements_by_month.get(m, [])]
        pooled_expected_mrr = [v for m in months for v in raw_expected_mrr_by_month.get(m, [])]

        random_baseline = 0.0
        random_precision = 0.0
        random_recall = 0.0
        random_mrr = 0.0
        improvement_gap = 0.0
        precision_gap = 0.0
        recall_gap = 0.0
        mrr_gap = 0.0
        k_avg = 0.0

        if pooled_improvements and total_practices > 0:
            k_avg = sum(pooled_improvements) / len(pooled_improvements)

            per_month_baselines = []
            for m in months:
                case_list = raw_improvements_by_month.get(m, [])
                month_k_avg = sum(case_list) / len(case_list) if case_list else 0.0
                per_month_baselines.append(self._baseline_from_k_avg(month_k_avg, total_practices, TOP_N))
            random_baseline = sum(per_month_baselines) / len(per_month_baselines) if per_month_baselines else 0.0

            improvement_gap = overall_accuracy - random_baseline
            random_precision = min(1.0, k_avg / total_practices)
            random_recall = min(1.0, TOP_N / total_practices)
            if pooled_expected_mrr:
                random_mrr = sum(pooled_expected_mrr) / len(pooled_expected_mrr)

            precision_gap = overall_precision - random_precision
            recall_gap = overall_recall - random_recall
            mrr_gap = overall_mrr - random_mrr

        improvement_factor = overall_accuracy / random_baseline if random_baseline > 0 else 0.0
        precision_improvement_factor = overall_precision / random_precision if random_precision > 0 else 0.0
        recall_improvement_factor = overall_recall / random_recall if random_recall > 0 else 0.0
        mrr_improvement_factor = overall_mrr / random_mrr if random_mrr > 0 else 0.0

        return {
            "months_included": len(rows),
            "total_predictions": total_predictions,
            "correct_predictions": correct_predictions,
            "overall_accuracy": overall_accuracy,
            "random_baseline": random_baseline,
            "improvement_gap": improvement_gap,
            "improvement_factor": improvement_factor,
            "time_aware_popularity_accuracy": overall_popularity,
            "blend_minus_popularity": overall_accuracy - overall_popularity,
            "overall_precision": overall_precision,
            "overall_recall": overall_recall,
            "overall_mrr": overall_mrr,
            "random_precision": random_precision,
            "random_recall": random_recall,
            "random_mrr": random_mrr,
            "precision_gap": precision_gap,
            "recall_gap": recall_gap,
            "mrr_gap": mrr_gap,
            "precision_improvement_factor": precision_improvement_factor,
            "recall_improvement_factor": recall_improvement_factor,
            "mrr_improvement_factor": mrr_improvement_factor,
            "teams_tested": total_predictions,
            "avg_improvements_per_case": k_avg,
        }

    def run_backtest(self) -> dict:
        """
        Run the global two-month adaptive blend backtest over every prediction month.

        For each prediction month: build the fixed evaluable cohort first (independent
        of any policy), select that month's global blend policy and its independently
        selected time-aware-popularity comparison arm from strictly earlier prediction
        months whose full outcome window has already closed, then score every case
        under both. No model parameters are accepted - the monthly policy is the only
        configuration authority (see docs/GLOBAL_TWO_MONTH_BLEND_IMPLEMENTATION_
        REQUIREMENTS-refined.md).

        Returns:
            dict: {
                "status": "success",
                "per_month_results": [...],  # every prediction month, each tagged
                    with "full_outcome_window" and "selected_policy"
                "primary": {...},       # aggregate over full-outcome-window months only
                "sensitivity": {...},   # aggregate over every prediction month
            }
            or {"error": ...} if fewer than 4 months of data exist.

            "primary"/"sensitivity" each have the shape of _EMPTY_SCOPE's keys, with
            rate fields None (not 0.0) when zero months qualify.
        """
        engine = self.policy_engine
        months = engine.prediction_months()
        if not months:
            return {"error": "Need at least 4 time periods (start from month 4)"}

        total_practices = len(self.recommender.practices)
        per_month_results = []
        raw_improvements_by_month: dict = {}
        raw_expected_mrr_by_month: dict = {}

        for month in months:
            row, improvements, expected_mrr = self._score_month(month, total_practices)

            per_month_results.append(row)
            raw_improvements_by_month[month] = improvements
            raw_expected_mrr_by_month[month] = expected_mrr

        primary_rows = [r for r in per_month_results if r["full_outcome_window"]]
        sensitivity_rows = per_month_results

        return {
            "status": "success",
            "per_month_results": per_month_results,
            "primary": self._aggregate_scope(
                primary_rows, raw_improvements_by_month, raw_expected_mrr_by_month, total_practices
            ),
            "sensitivity": self._aggregate_scope(
                sensitivity_rows, raw_improvements_by_month, raw_expected_mrr_by_month, total_practices
            ),
        }
