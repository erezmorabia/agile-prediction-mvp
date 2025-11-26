"""
OptimizationEngine: Find optimal parameter configuration by testing combinations.
"""

import json
import logging
from collections.abc import Generator
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any, Callable

from .backtest import BacktestEngine

logger = logging.getLogger(__name__)


class OptimizationEngine:
    """Find optimal configuration by testing parameter combinations."""

    def __init__(self, backtest_engine: BacktestEngine):
        """
        Initialize OptimizationEngine.

        Args:
            backtest_engine: BacktestEngine instance
        """
        self.backtest_engine = backtest_engine
        self._cancelled = False  # Cancellation flag

    def generate_parameter_combinations(
        self,
        top_n_range: list[int] | None = None,
        similarity_weight_range: list[float] | None = None,
        k_similar_range: list[int] | None = None,
        similar_teams_lookahead_months_range: list[int] | None = None,
        recent_improvements_months_range: list[int] | None = None,
        min_similarity_threshold_range: list[float] | None = None,
        fixed_params: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Generate all parameter combinations.

        Args:
            top_n_range: List of top_n values (default: [2, 3, 4, 5])
            similarity_weight_range: List of similarity_weight values (default: [0.6, 0.7, 0.8])
            k_similar_range: List of k_similar values (default: [5, 10, 15, 19, 20])
            similar_teams_lookahead_months_range: List of lookahead months (default: [3])
            recent_improvements_months_range: List of recent months (default: [3])
            min_similarity_threshold_range: List of min_similarity values (default: [0.0, 0.5, 0.75])
            fixed_params: Fixed parameter values (overrides ranges)

        Yields:
            Dictionary with parameter configuration
        """
        # Default ranges
        if top_n_range is None:
            top_n_range = [2, 3, 4, 5]  # Removed 1 (too few recommendations)
        if similarity_weight_range is None:
            similarity_weight_range = [0.6, 0.7, 0.8]  # Focus around 0.7
        if k_similar_range is None:
            k_similar_range = [5, 10, 15, 19, 20]  # Added 19 and 20 (user found 19 gives 1.9x improvement)
        if similar_teams_lookahead_months_range is None:
            similar_teams_lookahead_months_range = [3]
        if recent_improvements_months_range is None:
            recent_improvements_months_range = [3]
        if min_similarity_threshold_range is None:
            min_similarity_threshold_range = [0.0, 0.5, 0.75]  # Added 0.75 back (user found it improves results)
        if fixed_params is None:
            fixed_params = {}

        # Generate all combinations
        for top_n, similarity_weight, k_similar, lookahead, recent, min_sim in product(
            top_n_range,
            similarity_weight_range,
            k_similar_range,
            similar_teams_lookahead_months_range,
            recent_improvements_months_range,
            min_similarity_threshold_range,
        ):
            config = {
                "top_n": top_n,
                "similarity_weight": similarity_weight,
                "k_similar": k_similar,
                "similar_teams_lookahead_months": lookahead,
                "recent_improvements_months": recent,
                "min_similarity_threshold": min_sim,
            }

            # Apply fixed parameters (override generated values)
            config.update(fixed_params)

            yield config

    def cancel(self) -> None:
        """
        Cancel the current optimization process.

        Sets an internal cancellation flag that is checked during optimization.
        When set, the optimization loop will break at the next check point and
        return partial results. The cancellation is checked:
        - At the start of each parameter combination test
        - During backtest execution (via cancellation_check callback)

        Returns:
            None: Modifies internal state (sets self._cancelled = True)

        Note:
            - Cancellation is not immediate - it takes effect at the next check point
            - Partial results are returned with 'cancelled': True
            - Call reset_cancellation() before starting a new optimization
        """
        logger.info("[CANCELLATION] OptimizationEngine.cancel() called - setting _cancelled = True")
        self._cancelled = True
        logger.info(f"[CANCELLATION] OptimizationEngine: _cancelled flag is now {self._cancelled}")

    def reset_cancellation(self) -> None:
        """
        Reset cancellation flag to allow a new optimization to start.

        Should be called before starting a new optimization to ensure the
        cancellation flag is cleared. Automatically called at the start
        of find_optimal_config().

        Returns:
            None: Modifies internal state (sets self._cancelled = False)
        """
        self._cancelled = False

    def save_results(self, results: dict[str, Any]) -> str | None:
        """
        Save optimization results to JSON file.

        Args:
            results: Results dictionary from find_optimal_config()

        Returns:
            Path to saved file, or None if save failed
        """
        try:
            # Create results directory if it doesn't exist
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"optimization_{timestamp}.json"
            filepath = results_dir / filename

            # Add timestamp to results
            results_to_save = results.copy()
            results_to_save["timestamp"] = datetime.now().isoformat()

            # Save to JSON file
            with open(filepath, "w") as f:
                json.dump(results_to_save, f, indent=2)

            logger.info(f"Optimization results saved to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.warning(f"Failed to save optimization results: {e}")
            return None

    @staticmethod
    def load_latest_results() -> dict[str, Any] | None:
        """
        Load the most recent optimization results file.

        Returns:
            Results dictionary, or None if no results found
        """
        try:
            results_dir = Path("results")
            if not results_dir.exists():
                return None

            # Find all optimization result files
            result_files = list(results_dir.glob("optimization_*.json"))
            if not result_files:
                return None

            # Sort by modification time (most recent first)
            result_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            latest_file = result_files[0]

            # Load JSON file
            with open(latest_file) as f:
                results = json.load(f)

            logger.info(f"Loaded latest optimization results from {latest_file}")
            return results
        except Exception as e:
            logger.warning(f"Failed to load latest optimization results: {e}")
            return None

    def find_optimal_config(
        self,
        min_accuracy: float = 0.40,
        top_n_range: list[int] | None = None,
        similarity_weight_range: list[float] | None = None,
        k_similar_range: list[int] | None = None,
        similar_teams_lookahead_months_range: list[int] | None = None,
        recent_improvements_months_range: list[int] | None = None,
        min_similarity_threshold_range: list[float] | None = None,
        fixed_params: dict[str, Any] | None = None,
        progress_callback: Callable[[int, int, dict[str, Any]], None] | None = None,
        early_stop_threshold: float = 0.25,
        early_stop_min_tested: float = 0.5,
    ) -> dict[str, Any]:
        """
        Find optimal configuration by testing parameter combinations via grid search.

        Performs exhaustive grid search over specified parameter ranges, testing each
        combination via backtest validation. Tracks the best configuration based on
        improvement_gap (difference between model accuracy and random baseline).

        Early Stopping:
        To save computation time, optimization can stop early if an excellent solution
        is found. Early stopping occurs when:
        - improvement_gap > early_stop_threshold (default 0.25 = 25%), AND
        - At least early_stop_min_tested fraction has been tested (default 0.5 = 50%), OR
        - improvement_gap > 0.30 (excellent solution, stop immediately)
        Alternatively, if improvement_gap > 0.20 and at least 50% tested, also stops early.

        Cancellation:
        Optimization can be cancelled by calling cancel() from another thread/process.
        Cancellation is checked at the start of each parameter combination test and
        during backtest execution. Partial results are returned with 'cancelled': True.

        Results Saving:
        Results are automatically saved to results/optimization_YYYYMMDD_HHMMSS.json
        for later retrieval via load_latest_results().

        Args:
            min_accuracy (float, optional): Minimum accuracy threshold (0.0-1.0) that a
                configuration must meet to be considered valid. Defaults to 0.40 (40%).
            top_n_range (List[int], optional): List of top_n values to test.
                Defaults to [2, 3, 4, 5].
            similarity_weight_range (List[float], optional): List of similarity_weight
                values to test (0.0-1.0). Defaults to [0.6, 0.7, 0.8].
            k_similar_range (List[int], optional): List of k_similar values to test.
                Defaults to [5, 10, 15, 19, 20].
            similar_teams_lookahead_months_range (List[int], optional): List of lookahead
                month values to test. Defaults to [3].
            recent_improvements_months_range (List[int], optional): List of recent months
                values to test. Defaults to [3].
            min_similarity_threshold_range (List[float], optional): List of min_similarity
                threshold values to test (0.0-1.0). Defaults to [0.0, 0.5, 0.75].
            fixed_params (Dict[str, Any], optional): Dictionary of parameter values to fix
                (override ranges). Keys match parameter names. Useful for testing subsets.
            progress_callback (callable, optional): Optional callback function called during
                optimization. Signature: callback(current: int, total: int, config: dict).
                Called every 10 iterations and at start.
            early_stop_threshold (float, optional): Stop early if improvement_gap exceeds
                this value (0.0-1.0). Defaults to 0.25 (25% improvement gap).
            early_stop_min_tested (float, optional): Minimum fraction (0.0-1.0) of combinations
                that must be tested before early stopping can occur. Defaults to 0.5 (50%).

        Returns:
            Dict[str, Any]: Results dictionary containing:
                - optimal_config (dict): Best configuration found (None if none met threshold)
                - model_accuracy (float): Accuracy of optimal config (0.0-1.0)
                - random_baseline (float): Random baseline for optimal config
                - improvement_gap (float): improvement_gap of optimal config
                - improvement_factor (float): model_accuracy / random_baseline
                - total_predictions (int): Total predictions made with optimal config
                - correct_predictions (int): Correct predictions with optimal config
                - total_combinations_tested (int): Number of combinations evaluated
                - total_combinations_available (int): Total combinations in grid
                - valid_combinations (int): Number that met min_accuracy threshold
                - all_results (list): Top 50 valid results sorted by improvement_gap (descending)
                - early_stopped (bool): True if stopped early due to excellent solution
                - cancelled (bool): True if optimization was cancelled
                - results_file (str, optional): Path to saved results file

        Raises:
            Exception: Any exception during backtest execution is caught and that
                combination is skipped (does not stop optimization).

        Example:
            >>> optimizer = OptimizationEngine(backtest_engine)
            >>> results = optimizer.find_optimal_config(min_accuracy=0.40)
            >>> print(f"Best config: {results['optimal_config']}")
            >>> print(f"Accuracy: {results['model_accuracy']:.1%}")
            Best config: {'top_n': 2, 'k_similar': 19, ...}
            Accuracy: 45.2%

        Note:
            - Total combinations = product of all range lengths (can be large)
            - Each combination requires a full backtest (may take minutes)
            - Results are sorted by improvement_gap, not raw accuracy
            - Cancellation flag is automatically reset at start
            - Results are automatically saved to JSON file
        """
        # Reset cancellation flag
        logger.info("[CANCELLATION] OptimizationEngine: Starting find_optimal_config - resetting cancellation flag")
        self.reset_cancellation()

        # Generate all combinations
        combinations = list(
            self.generate_parameter_combinations(
                top_n_range=top_n_range,
                similarity_weight_range=similarity_weight_range,
                k_similar_range=k_similar_range,
                similar_teams_lookahead_months_range=similar_teams_lookahead_months_range,
                recent_improvements_months_range=recent_improvements_months_range,
                min_similarity_threshold_range=min_similarity_threshold_range,
                fixed_params=fixed_params,
            )
        )

        total_combinations = len(combinations)
        logger.info(f"[CANCELLATION] OptimizationEngine: Generated {total_combinations} combinations to test")
        valid_results = []
        best_config = None
        best_improvement_gap = float("-inf")
        early_stopped = False
        cancelled = False

        # Test each combination
        for idx, config in enumerate(combinations):
            # Log progress every 10 iterations (or at start)
            if idx == 0 or (idx + 1) % 10 == 0:
                percentage = ((idx + 1) / total_combinations * 100) if total_combinations > 0 else 0
                logger.info(
                    f"[CANCELLATION] OptimizationEngine: Progress: {idx + 1}/{total_combinations} combinations tested ({percentage:.1f}%)"
                )

            # Check for cancellation
            if self._cancelled:
                percentage = ((idx + 1) / total_combinations * 100) if total_combinations > 0 else 0
                logger.info(
                    f"[CANCELLATION] OptimizationEngine: Cancellation detected at iteration {idx + 1}/{total_combinations} ({percentage:.1f}% complete) - breaking loop"
                )
                cancelled = True
                break

            # Progress callback
            if progress_callback:
                progress_callback(idx + 1, total_combinations, config)

            logger.debug(
                f"[CANCELLATION] OptimizationEngine: Starting backtest for combination {idx + 1}/{total_combinations}, _cancelled={self._cancelled}"
            )

            try:
                # Run backtest with this configuration
                # Pass cancellation check lambda so backtest can check cancellation during execution
                result = self.backtest_engine.run_backtest(config=config, cancellation_check=lambda: self._cancelled)

                # Check if backtest was cancelled mid-execution
                if result.get("cancelled", False):
                    percentage = ((idx + 1) / total_combinations * 100) if total_combinations > 0 else 0
                    logger.info(
                        f"[CANCELLATION] OptimizationEngine: Backtest returned cancelled=True at iteration {idx + 1}/{total_combinations} ({percentage:.1f}% complete) - breaking loop"
                    )
                    cancelled = True
                    break

                if "error" in result:
                    continue

                accuracy = result.get("overall_accuracy", 0.0)

                # Filter by minimum accuracy
                if accuracy >= min_accuracy:
                    improvement_gap = result.get("improvement_gap", 0.0)
                    random_baseline = result.get("random_baseline", 0.0)

                    valid_results.append(
                        {
                            "config": config,
                            "model_accuracy": accuracy,
                            "random_baseline": random_baseline,
                            "improvement_gap": improvement_gap,
                            "improvement_factor": result.get("improvement_factor", 0.0),
                            "total_predictions": result.get("total_predictions", 0),
                            "correct_predictions": result.get("correct_predictions", 0),
                        }
                    )

                    # Track best configuration
                    if improvement_gap > best_improvement_gap:
                        best_improvement_gap = improvement_gap
                        best_config = {
                            "config": config,
                            "model_accuracy": accuracy,
                            "random_baseline": random_baseline,
                            "improvement_gap": improvement_gap,
                            "improvement_factor": result.get("improvement_factor", 0.0),
                            "total_predictions": result.get("total_predictions", 0),
                            "correct_predictions": result.get("correct_predictions", 0),
                        }

                        # Early stopping: if we found an excellent solution
                        tested_fraction = (idx + 1) / total_combinations
                        if improvement_gap > early_stop_threshold:
                            if tested_fraction >= early_stop_min_tested or improvement_gap > 0.30:
                                # Excellent solution found, stop early
                                early_stopped = True
                                break
                        elif improvement_gap > 0.20 and tested_fraction >= 0.5:
                            # Good solution found after testing at least 50%
                            early_stopped = True
                            break

            except KeyboardInterrupt:
                # Handle Ctrl-C gracefully
                cancelled = True
                break
            except Exception:
                # Skip configurations that cause errors
                continue

        # Sort valid results by improvement_gap (descending)
        valid_results.sort(key=lambda x: x["improvement_gap"], reverse=True)

        # Calculate total combinations tested (defensive: handle edge case where loop never runs)
        # If cancelled/early_stopped, use idx + 1 (number of iterations completed)
        # Otherwise use total_combinations (all were tested)
        # If idx is not defined (loop never ran), default to 0
        try:
            tested_count = idx + 1 if cancelled or early_stopped else total_combinations
        except NameError:
            # Loop never ran (edge case: empty combinations list)
            tested_count = 0

        # Calculate completion percentage
        completion_pct = (tested_count / total_combinations * 100) if total_combinations > 0 else 0
        status_msg = "cancelled" if cancelled else ("early stopped" if early_stopped else "completed")
        logger.info(
            f"[CANCELLATION] OptimizationEngine: Optimization {status_msg} - tested {tested_count}/{total_combinations} combinations ({completion_pct:.1f}%), found {len(valid_results)} valid results"
        )

        # Build results dictionary
        results = {
            "optimal_config": best_config["config"] if best_config else None,
            "model_accuracy": best_config["model_accuracy"] if best_config else 0.0,
            "random_baseline": best_config["random_baseline"] if best_config else 0.0,
            "improvement_gap": best_config["improvement_gap"] if best_config else 0.0,
            "improvement_factor": best_config["improvement_factor"] if best_config else 0.0,
            "total_predictions": best_config["total_predictions"] if best_config else 0,
            "correct_predictions": best_config["correct_predictions"] if best_config else 0,
            "total_combinations_tested": tested_count,
            "total_combinations_available": total_combinations,
            "valid_combinations": len(valid_results),
            "all_results": valid_results[:50],  # Top 50 results (increased from 10)
            "early_stopped": early_stopped,
            "cancelled": cancelled,
        }

        # Auto-save results (don't fail if save fails)
        results_file = self.save_results(results)
        if results_file:
            results["results_file"] = results_file

        return results
