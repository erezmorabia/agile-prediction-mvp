"""
BacktestEngine: Validate recommendations against historical data.
"""

import logging
from collections.abc import Callable

from scipy.special import comb

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Run backtest validation using historical data."""

    def __init__(self, recommender_engine, processor):
        """
        Initialize BacktestEngine.

        Args:
            recommender_engine: RecommendationEngine instance
            processor: DataProcessor instance
        """
        self.recommender = recommender_engine
        self.processor = processor

    def run_backtest(
        self, train_ratio: float = None, config: dict = None, cancellation_check: Callable[[], bool] | None = None
    ) -> dict:
        """
        Run rolling window backtest validation on historical data.

        Uses a time-series cross-validation approach where for each test month starting
        from month 4, the model is trained only on data from previous months, then
        predictions are validated against actual improvements that occurred.

        Validation Window:
        The backtest checks for improvements in a 3-month window (test_month, test_month+1,
        test_month+2) to account for adoption timelines. This aligns with the recommendation
        logic which looks up to 3 months ahead. A prediction is considered correct if the
        recommended practice improved in any of these 3 months.

        Rolling Window Process:
        For each month starting from month 4 (index 3):
        1. Train: Use all months before the test month (sliding window)
        2. Predict: Generate recommendations for each team using their previous month as baseline
        3. Validate: Check if recommended practices actually improved in test_month, test_month+1, or test_month+2
        4. Calculate: Accuracy = (correct predictions) / (total predictions)

        Teams with no improvements in the validation window are excluded from accuracy
        calculation, as this is not a model failure but rather indicates no improvements occurred.

        Random Baseline:
        Calculates the probability of getting at least one correct recommendation by random
        selection, accounting for the average number of improvements per case. This provides
        a meaningful baseline for comparison.

        Args:
            train_ratio (float, optional): Ignored parameter kept for API compatibility.
                The rolling window approach uses all available past months, not a fixed ratio.
            config (dict, optional): Configuration dictionary with recommendation parameters:
                - top_n (int): Number of recommendations to generate. Defaults to 2.
                - k_similar (int): Number of similar teams to consider. Defaults to 19.
                - similarity_weight (float): Weight for similarity vs sequences (0.0-1.0). Defaults to 0.6.
                - similar_teams_lookahead_months (int): Months to look ahead for improvements. Defaults to 3.
                - recent_improvements_months (int): Months to check back for recent improvements. Defaults to 3.
                - min_similarity_threshold (float): Minimum similarity threshold (0.0-1.0). Defaults to 0.75.
            cancellation_check (Callable[[], bool], optional): Function that returns True if
                cancellation was requested. Called periodically during execution. If True,
                returns partial results with 'cancelled': True.

        Returns:
            dict: Backtest results dictionary containing:
                - status (str): 'success'
                - per_month_results (list): List of dicts with keys:
                    - month (int): Test month
                    - train_months (list): Months used for training
                    - predictions (int): Number of predictions made
                    - correct (int): Number of correct predictions
                    - accuracy (float): Accuracy for this month (0.0-1.0)
                    - teams_tested (int): Number of teams tested
                - total_predictions (int): Total predictions across all months
                - correct_predictions (int): Total correct predictions
                - overall_accuracy (float): Average accuracy across all months (0.0-1.0)
                - random_baseline (float): Probability of correct prediction by random selection
                - improvement_gap (float): overall_accuracy - random_baseline
                - improvement_factor (float): overall_accuracy / random_baseline
                - teams_tested (int): Number of unique teams tested
                - avg_improvements_per_case (float): Average number of practices improved per case
                - cancelled (bool): True if backtest was cancelled mid-execution

        Raises:
            ValueError: If less than 4 months of data available (need at least 4 for rolling window)

        Example:
            >>> results = backtest.run_backtest(config={'top_n': 2, 'k_similar': 19})
            >>> print(f"Accuracy: {results['overall_accuracy']:.1%}")
            >>> print(f"Improvement over random: {results['improvement_factor']:.1f}x")
            Accuracy: 45.2%
            Improvement over random: 1.9x

        Note:
            - Requires at least 4 months of data (start from month 4)
            - Sequences are learned up to each test month (sliding window, prevents data leakage)
            - Only teams with improvements in the validation window are counted
            - Cancellation checks occur at start of each month and every 10 teams
        """
        months = sorted(self.processor.get_all_months())
        teams = self.processor.get_all_teams()

        if len(months) < 4:
            return {"error": "Need at least 4 time periods (start from month 4)", "cancelled": False}

        # Extract configuration with defaults (optimized values from optimization results)
        if config is None:
            config = {}
        top_n = config.get("top_n", 2)
        k_similar = config.get("k_similar", 19)
        similarity_weight = config.get("similarity_weight", 0.6)
        similar_teams_lookahead_months = config.get("similar_teams_lookahead_months", 3)
        recent_improvements_months = config.get("recent_improvements_months", 3)
        min_similarity_threshold = config.get("min_similarity_threshold", 0.75)

        # Rolling window: start from month 4 (index 3, 0-based)
        per_month_results = []
        total_predictions = 0
        total_correct = 0
        all_teams_tested = set()  # Track all teams that made predictions

        # Track improvements per case for random baseline calculation
        improvements_per_case = []  # List of number of practices improved per case

        logger.debug(
            f"[CANCELLATION] BacktestEngine: Starting backtest with {len(months)} months, cancellation_check={'provided' if cancellation_check else 'None'}"
        )

        for test_month_idx in range(3, len(months)):  # Start from month 4 (index 3)
            # Check for cancellation at start of each month iteration
            if cancellation_check:
                is_cancelled = cancellation_check()
                if is_cancelled:
                    logger.info(
                        f"[CANCELLATION] BacktestEngine: Cancellation detected at month {test_month_idx + 1}/{len(months)} - returning partial results"
                    )
                    # Return partial results
                    return self._build_partial_results(
                        per_month_results,
                        total_predictions,
                        total_correct,
                        improvements_per_case,
                        all_teams_tested,
                        top_n,
                    )

            test_month = months[test_month_idx]
            train_months = months[:test_month_idx]  # All months before test month

            if not train_months:
                continue

            # Check for cancellation before potentially long-running sequence learning
            if cancellation_check and cancellation_check():
                logger.info(
                    f"[CANCELLATION] BacktestEngine: Cancellation detected before sequence learning for month {test_month_idx + 1}/{len(months)} - returning partial results"
                )
                return self._build_partial_results(
                    per_month_results, total_predictions, total_correct, improvements_per_case, all_teams_tested, top_n
                )

            # Learn sequences up to test_month (using sliding window)
            # This ensures sequences are only learned from months < test_month
            # The sequences will be cached and reused if needed
            self.recommender.sequence_mapper.learn_sequences_up_to_month(test_month)

            # Run backtest for this month
            month_predictions = 0
            month_correct = 0
            teams_tested_this_month = set()

            team_count = 0  # Track team count for cancellation checks
            for team in teams:
                # Check for cancellation every 10 teams (starting from team 1)
                team_count += 1
                if cancellation_check and team_count % 10 == 0:
                    is_cancelled = cancellation_check()
                    if is_cancelled:
                        logger.info(
                            f"[CANCELLATION] BacktestEngine: Cancellation detected at team {team_count}/{len(teams)} in month {test_month_idx + 1} - returning partial results"
                        )
                        # Return partial results
                        return self._build_partial_results(
                            per_month_results,
                            total_predictions,
                            total_correct,
                            improvements_per_case,
                            all_teams_tested,
                            top_n,
                        )
                try:
                    history = self.processor.get_team_history(team)
                    team_months = sorted([m for m in months if m in history])

                    if test_month not in history:
                        continue

                    test_idx = team_months.index(test_month)
                    if test_idx <= 0:
                        continue  # Need at least one previous month

                    prev_month = team_months[test_idx - 1]

                    # What did team actually improve in test_month, test_month + 1, AND test_month + 2?
                    # Check improvements in all 3 months to account for adoption timelines
                    # This aligns with recommendation logic which looks up to 3 months ahead
                    prev_vector = history[prev_month]
                    test_vector = history[test_month]

                    # Check improvements in test_month (immediate next month)
                    actual_improved_month1 = set()
                    for j, (p, t) in enumerate(zip(prev_vector, test_vector)):
                        if t > p:
                            actual_improved_month1.add(self.recommender.practices[j])

                    # Check improvements in test_month + 1 (month after that) if it exists
                    actual_improved_month2 = set()
                    if test_idx + 1 < len(team_months):
                        next_month = team_months[test_idx + 1]
                        next_vector = history[next_month]
                        for j, (p, n) in enumerate(zip(prev_vector, next_vector)):
                            if n > p:
                                actual_improved_month2.add(self.recommender.practices[j])

                    # Check improvements in test_month + 2 (third month ahead) if it exists
                    actual_improved_month3 = set()
                    if test_idx + 2 < len(team_months):
                        month_after_2 = team_months[test_idx + 2]
                        month_after_2_vector = history[month_after_2]
                        for j, (p, m2) in enumerate(zip(prev_vector, month_after_2_vector)):
                            if m2 > p:
                                actual_improved_month3.add(self.recommender.practices[j])

                    # Combine improvements from all 3 months
                    actual_improved = actual_improved_month1 | actual_improved_month2 | actual_improved_month3

                    # Skip teams with no improvements in any of the 3 validation months
                    # This ensures we only count predictions for teams that actually improved something.
                    # Teams with no improvements shouldn't be counted as "failures" since no prediction
                    # could succeed when no improvements occurred - this isn't a model failure.
                    if not actual_improved:
                        continue  # Skip if no improvements in any of the 3 months

                    # Track number of improvements for random baseline calculation
                    improvements_per_case.append(len(actual_improved))

                    # What did we recommend?
                    # Note: allow_first_three_months=True because in backtest, we may use
                    # month 2 to predict month 3, which is valid for validation purposes
                    try:
                        recommendations = self.recommender.recommend(
                            team,
                            prev_month,
                            top_n=top_n,
                            k_similar=k_similar,
                            allow_first_three_months=True,
                            similarity_weight=similarity_weight,
                            similar_teams_lookahead_months=similar_teams_lookahead_months,
                            recent_improvements_months=recent_improvements_months,
                            min_similarity_threshold=min_similarity_threshold,
                        )
                        recommended = set([r[0] for r in recommendations])

                        month_predictions += 1
                        total_predictions += 1
                        teams_tested_this_month.add(team)
                        all_teams_tested.add(team)

                        # Check for hits
                        if recommended & actual_improved:  # Intersection
                            month_correct += 1
                            total_correct += 1
                    except ValueError:
                        # Skip if month validation fails (e.g., month in first 3 months)
                        # This can happen if prev_month is in the first 3 months
                        continue
                    except Exception:
                        # Log other errors but continue
                        continue
                except:
                    continue

            # Calculate accuracy for this month
            month_accuracy = month_correct / month_predictions if month_predictions > 0 else 0

            per_month_results.append(
                {
                    "month": test_month,
                    "train_months": train_months,
                    "predictions": month_predictions,
                    "correct": month_correct,
                    "accuracy": month_accuracy,
                    "teams_tested": len(teams_tested_this_month),
                }
            )

        # Calculate overall accuracy (average of per-month accuracies)
        if per_month_results:
            overall_accuracy = sum(r["accuracy"] for r in per_month_results) / len(per_month_results)
        else:
            overall_accuracy = 0

        # Calculate correct random baseline
        # P(at least one correct) = 1 - C(n-k_avg, top_n) / C(n, top_n)
        # Where n = total practices, k_avg = average improvements per case, top_n = recommendations
        n = len(self.recommender.practices)  # Total practices (30 after filtering)
        random_baseline = 0.0
        improvement_gap = 0.0

        if improvements_per_case and n > 0:
            k_avg = sum(improvements_per_case) / len(improvements_per_case)
            # Calculate probability of getting at least one correct with random selection
            if k_avg > 0 and top_n > 0 and n >= k_avg and n >= top_n:
                # P(none correct) = C(n-k_avg, top_n) / C(n, top_n)
                try:
                    p_none = comb(n - k_avg, top_n, exact=True) / comb(n, top_n, exact=True)
                    random_baseline = 1.0 - p_none
                except (ValueError, ZeroDivisionError):
                    # Fallback to simple approximation if combination calculation fails
                    random_baseline = min(1.0, (k_avg / n) * top_n)
            else:
                # Edge case: use simple approximation
                random_baseline = min(1.0, (k_avg / n) * top_n) if n > 0 else 0.0

            improvement_gap = overall_accuracy - random_baseline

        # Calculate improvement factor (for backward compatibility)
        improvement_factor = overall_accuracy / random_baseline if random_baseline > 0 else 0

        return {
            "status": "success",
            "per_month_results": per_month_results,
            "total_predictions": total_predictions,
            "correct_predictions": total_correct,
            "overall_accuracy": overall_accuracy,
            "random_baseline": random_baseline,
            "improvement_gap": improvement_gap,
            "improvement_factor": improvement_factor,
            "teams_tested": len(all_teams_tested),
            "avg_improvements_per_case": sum(improvements_per_case) / len(improvements_per_case)
            if improvements_per_case
            else 0,
            "cancelled": False,
        }

    def _build_partial_results(
        self,
        per_month_results: list,
        total_predictions: int,
        total_correct: int,
        improvements_per_case: list,
        all_teams_tested: set,
        top_n: int,
    ) -> dict:
        """
        Build partial results dictionary when backtest is cancelled mid-execution.

        Calculates statistics from completed months only, including overall accuracy,
        random baseline, and improvement metrics. Used when cancellation_check returns
        True during backtest execution.

        Args:
            per_month_results (list): List of result dictionaries for months completed
                so far. Each dict contains 'month', 'predictions', 'correct', 'accuracy', etc.
            total_predictions (int): Total number of predictions made before cancellation.
            total_correct (int): Total number of correct predictions before cancellation.
            improvements_per_case (list): List of integers representing number of improvements
                per case (team/month combination) tested so far. Used for random baseline calculation.
            all_teams_tested (set): Set of team names that were tested before cancellation.
            top_n (int): Number of recommendations generated per prediction. Used for
                random baseline probability calculation.

        Returns:
            dict: Partial backtest results dictionary with same structure as run_backtest()
                return value, but with 'cancelled': True. Contains:
                - All fields from run_backtest() return value
                - cancelled (bool): Always True
                - Statistics calculated only from completed months

        Note:
            - Random baseline is recalculated using only the partial data
            - Overall accuracy is average of completed months only
            - Results are valid but incomplete (represent subset of full backtest)
        """
        logger.info(
            f"[CANCELLATION] BacktestEngine: Building partial results - {len(per_month_results)} months completed, {total_predictions} predictions, {total_correct} correct"
        )
        # Calculate overall accuracy from completed months only
        if per_month_results:
            overall_accuracy = sum(r["accuracy"] for r in per_month_results) / len(per_month_results)
        else:
            overall_accuracy = 0

        # Calculate random baseline from partial data
        n = len(self.recommender.practices)  # Total practices
        random_baseline = 0.0
        improvement_gap = 0.0

        if improvements_per_case and n > 0:
            k_avg = sum(improvements_per_case) / len(improvements_per_case)
            # Calculate probability of getting at least one correct with random selection
            if k_avg > 0 and top_n > 0 and n >= k_avg and n >= top_n:
                # P(none correct) = C(n-k_avg, top_n) / C(n, top_n)
                try:
                    p_none = comb(n - k_avg, top_n, exact=True) / comb(n, top_n, exact=True)
                    random_baseline = 1.0 - p_none
                except (ValueError, ZeroDivisionError):
                    # Fallback to simple approximation if combination calculation fails
                    random_baseline = min(1.0, (k_avg / n) * top_n)
            else:
                # Edge case: use simple approximation
                random_baseline = min(1.0, (k_avg / n) * top_n) if n > 0 else 0.0

            improvement_gap = overall_accuracy - random_baseline

        # Calculate improvement factor
        improvement_factor = overall_accuracy / random_baseline if random_baseline > 0 else 0

        return {
            "status": "success",
            "per_month_results": per_month_results,
            "total_predictions": total_predictions,
            "correct_predictions": total_correct,
            "overall_accuracy": overall_accuracy,
            "random_baseline": random_baseline,
            "improvement_gap": improvement_gap,
            "improvement_factor": improvement_factor,
            "teams_tested": len(all_teams_tested),
            "avg_improvements_per_case": sum(improvements_per_case) / len(improvements_per_case)
            if improvements_per_case
            else 0,
            "cancelled": True,
        }

    def get_accuracy_summary(self, backtest_results: dict) -> str:
        """
        Get human-readable accuracy summary.

        Args:
            backtest_results (dict): Results from run_backtest()

        Returns:
            str: Formatted summary
        """
        if "error" in backtest_results:
            return f"Error: {backtest_results['error']}"

        accuracy = backtest_results["overall_accuracy"]
        baseline = backtest_results["random_baseline"]
        improvement = accuracy / baseline if baseline > 0 else 0

        summary = f"""
BACKTEST RESULTS
================
Total Predictions: {backtest_results["total_predictions"]}
Correct Predictions: {backtest_results["correct_predictions"]}
Overall Accuracy: {accuracy:.1%}
Random Baseline: {baseline:.1%}
Improvement Over Baseline: {improvement:.1f}x

Teams Tested: {backtest_results["teams_tested"]}
Train Period: {len(backtest_results["train_months"])} months
Test Period: {len(backtest_results["test_months"])} months
"""
        return summary
