"""
API Service Layer: Wraps ML components for web API.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)
from src.data import DataProcessor
from src.data.practice_definitions import PracticeDefinitionsLoader
from src.ml import RecommendationEngine
from src.validation import BacktestEngine
from src.validation.optimizer import OptimizationEngine


class APIService:
    """Service layer that wraps ML components for API endpoints."""

    def __init__(self, recommender: RecommendationEngine, processor: DataProcessor):
        """
        Initialize API service.

        Args:
            recommender: RecommendationEngine instance
            processor: DataProcessor instance
        """
        self.recommender = recommender
        self.processor = processor
        self.backtest_engine = BacktestEngine(recommender, processor)
        self.optimizer_engine = OptimizationEngine(self.backtest_engine)
        # Load practice definitions (optional, fails gracefully if file not found)
        # Try primary filename first, with fallback for legacy filename
        definitions_file = None
        import os

        for filename in ["data/raw/practice_level_definitions.xlsx", "data/raw/ractice_level_definitions.xlsx"]:
            if os.path.exists(filename):
                definitions_file = filename
                break

        if definitions_file:
            self.practice_definitions_loader = PracticeDefinitionsLoader(definitions_file)
            self.practice_definitions = self.practice_definitions_loader.get_definitions()
            self.practice_remarks = self.practice_definitions_loader.get_remarks()
        else:
            self.practice_definitions_loader = None
            self.practice_definitions = {}
            self.practice_remarks = {}
        self.missing_values_details = None  # Will be set by web_main.py

    def get_all_teams(self) -> list[dict[str, Any]]:
        """
        Get all teams with metadata.

        Returns:
            List of team info dictionaries with name and data count
        """
        teams = self.processor.get_all_teams()
        result = []

        for team in teams:
            history = self.processor.get_team_history(team)
            num_months = len(history)
            months = sorted(history.keys())

            result.append(
                {
                    "name": team,
                    "num_months": num_months,
                    "months": months,
                    "first_month": months[0] if months else None,
                    "last_month": months[-1] if months else None,
                }
            )

        # Sort by number of months (descending), then alphabetically
        result.sort(key=lambda x: (-x["num_months"], x["name"]))
        return result

    def get_teams_with_improvements(self) -> list[dict[str, Any]]:
        """
        Get teams and months to predict where improvements occurred.
        Only shows months 3+ as month to predict (we need months 1-2 as history).

        Returns:
            List of team/month combinations with improvements (month to predict is month 3+)
        """
        teams_with_improvements = []
        all_teams = self.processor.get_all_teams()

        # Get first two months to filter out (month to predict starts from month 3)
        all_available_months = sorted(self.processor.get_all_months())
        if len(all_available_months) >= 3:
            first_two_months = set(all_available_months[:2])  # Filter out months 1-2
        else:
            first_two_months = set()

        for team in all_teams:
            history = self.processor.get_team_history(team)
            months = sorted(history.keys())

            # Check each month (except the first one)
            for i in range(1, len(months)):
                prev_month = months[i - 1]
                month_to_predict = months[i]

                # Only show months 3+ as month to predict (filter out months 1-2)
                if month_to_predict in first_two_months:
                    continue

                prev_vector = history[prev_month]
                predicted_vector = history[month_to_predict]

                # Count improvements
                improvements = []
                for j, (prev, pred) in enumerate(zip(prev_vector, predicted_vector)):
                    if pred > prev:
                        improvements.append(self.recommender.practices[j])

                if improvements:
                    teams_with_improvements.append(
                        {
                            "team": team,
                            "month": month_to_predict,  # Month to predict
                            "next_month": month_to_predict,  # Keep for compatibility, but it's the same
                            "num_improvements": len(improvements),
                            "improvements": improvements,
                        }
                    )

        return teams_with_improvements

    def get_team_months(self, team_name: str) -> list[int] | None:
        """
        Get available months to predict for a team.
        Only includes months where:
        1. The month is month 3 or later (globally)
        2. The team has a previous month in their history (to use as baseline)

        Args:
            team_name: Name of the team

        Returns:
            List of months (sorted) or None if team not found
            Only includes months that can be predicted (month 3+ globally AND team has previous month)
        """
        if team_name not in self.processor.get_all_teams():
            return None

        history = self.processor.get_team_history(team_name)
        all_months = sorted(history.keys())

        # Filter to show only months 3+ globally (month to predict starts from month 3)
        # We need to filter out months 1-2, so only months 3+ are shown
        all_available_months = sorted(self.processor.get_all_months())
        if len(all_available_months) >= 3:
            first_two_months = set(all_available_months[:2])  # Filter out months 1-2 globally
            months_3plus = [m for m in all_months if m not in first_two_months]
        else:
            months_3plus = []

        # Further filter: only include months where the team has a previous month in their history
        # This handles cases where a team's first month of data is month 4 or later
        months_to_predict = []
        for month in months_3plus:
            month_idx = all_months.index(month)
            if month_idx > 0:  # Team has a previous month in their history
                months_to_predict.append(month)

        return months_to_predict

    def get_recommendations(self, team_name: str, month: int, top_n: int = 2, k_similar: int = 19) -> dict[str, Any]:
        """
        Get recommendations for a team for a specific month to predict.

        Args:
            team_name: Name of the team
            month: Month to predict (yyyymmdd format) - must be month 4 or later
            top_n: Number of recommendations to return
            k_similar: Number of similar teams to consider

        Returns:
            Dictionary with recommendations and validation info
        """
        # Validate team and month
        if team_name not in self.processor.get_all_teams():
            return {"error": f'Team "{team_name}" not found'}

        history = self.processor.get_team_history(team_name)
        if month not in history:
            return {"error": f"No data for team on month {month}"}

        # Validate that month to predict is month 3 or later
        all_available_months = sorted(self.processor.get_all_months())
        if len(all_available_months) >= 3:
            first_two_months = set(all_available_months[:2])
            if month in first_two_months:
                return {
                    "error": "Month to predict must be month 3 or later. We need at least 2 months of history to make predictions.",
                    "details": f"Month {month} is in the first 2 months.",
                }

        months = sorted(history.keys())
        month_to_predict_idx = months.index(month)

        # Find previous month to use as baseline
        if month_to_predict_idx == 0:
            return {"error": f"Cannot predict month {month} - no previous month available"}

        prev_month = months[month_to_predict_idx - 1]  # Use previous month as baseline

        # Get recommendations using previous month as baseline
        recommendations = self.recommender.recommend(team_name, prev_month, top_n=top_n, k_similar=k_similar)

        # Check for actual improvements in the predicted month and next 2 months
        month_to_predict = month
        prev_vector = history[prev_month]
        predicted_vector = history[month_to_predict]

        month_after = None
        month_after_2 = None
        actual_improvements = []
        validation_summary = {}

        # Get what actually improved in the predicted month
        improvements_month1 = {}
        for j, (prev, pred) in enumerate(zip(prev_vector, predicted_vector)):
            if pred > prev:
                practice_name = self.recommender.practices[j]
                improvement = pred - prev
                improvements_month1[practice_name] = {
                    "improvement": float(improvement),
                    "improvement_pct": float(improvement * 100),
                    "improved_in": [month_to_predict],
                }

        # Check if month_after exists and get improvements there too
        improvements_month2 = {}
        if month_to_predict_idx + 1 < len(months):
            month_after = months[month_to_predict_idx + 1]
            month_after_vector = history[month_after]

            for j, (prev, after) in enumerate(zip(prev_vector, month_after_vector)):
                if after > prev:
                    practice_name = self.recommender.practices[j]
                    improvement = after - prev
                    improvements_month2[practice_name] = {
                        "improvement": float(improvement),
                        "improvement_pct": float(improvement * 100),
                        "improved_in": [month_after],
                    }

        # Check if month_after_2 exists and get improvements there too (third month ahead)
        improvements_month3 = {}
        if month_to_predict_idx + 2 < len(months):
            month_after_2 = months[month_to_predict_idx + 2]
            month_after_2_vector = history[month_after_2]

            for j, (prev, after2) in enumerate(zip(prev_vector, month_after_2_vector)):
                if after2 > prev:
                    practice_name = self.recommender.practices[j]
                    improvement = after2 - prev
                    improvements_month3[practice_name] = {
                        "improvement": float(improvement),
                        "improvement_pct": float(improvement * 100),
                        "improved_in": [month_after_2],
                    }

        # Combine improvements from all 3 months (predicted month, month_after, month_after_2)
        # If a practice improved in multiple months, combine the information
        all_practices = (
            set(improvements_month1.keys()) | set(improvements_month2.keys()) | set(improvements_month3.keys())
        )
        for practice_name in all_practices:
            improved_in_months = []
            best_improvement = None
            best_improvement_value = 0.0

            if practice_name in improvements_month1:
                improved_in_months.append(month_to_predict)
                if improvements_month1[practice_name]["improvement"] > best_improvement_value:
                    best_improvement = improvements_month1[practice_name]
                    best_improvement_value = improvements_month1[practice_name]["improvement"]

            if practice_name in improvements_month2:
                if month_after not in improved_in_months:
                    improved_in_months.append(month_after)
                if improvements_month2[practice_name]["improvement"] > best_improvement_value:
                    best_improvement = improvements_month2[practice_name]
                    best_improvement_value = improvements_month2[practice_name]["improvement"]

            if practice_name in improvements_month3:
                if month_after_2 not in improved_in_months:
                    improved_in_months.append(month_after_2)
                if improvements_month3[practice_name]["improvement"] > best_improvement_value:
                    best_improvement = improvements_month3[practice_name]
                    best_improvement_value = improvements_month3[practice_name]["improvement"]

            if best_improvement:
                actual_improvements.append(
                    {
                        "practice": practice_name,
                        "improvement": best_improvement["improvement"],
                        "improvement_pct": best_improvement["improvement_pct"],
                        "improved_in": sorted(improved_in_months),
                    }
                )

        # Calculate validation summary AFTER processing all practices
        # This ensures validation_summary is always created, even when no improvements occurred
        recommended_practices = [r[0] for r in recommendations]
        validated_count = sum(1 for imp in actual_improvements if imp["practice"] in recommended_practices)

        # Calculate accuracy only if there were actual improvements
        # If no improvements occurred, set accuracy to None - this isn't a model failure,
        # it just means the team didn't improve anything in the validation window
        if actual_improvements and recommendations:
            accuracy = validated_count / len(recommendations)
        else:
            accuracy = None  # No accuracy when no improvements occurred

        validation_summary = {
            "next_month": month_to_predict,  # The predicted month
            "month_after": month_after if month_to_predict_idx + 1 < len(months) else None,
            "month_after_2": month_after_2 if month_to_predict_idx + 2 < len(months) else None,
            "actual_improvements": actual_improvements,
            "validated_count": validated_count,
            "total_recommendations": len(recommendations),
            "accuracy": accuracy,
            "team_improved_anything": len(actual_improvements) > 0,
        }

        # Format recommendations
        formatted_recs = []
        for practice, score, current_level in recommendations:
            # Convert normalized level back to original 0-3 scale
            original_level = current_level * 3
            # Determine level number (0, 1, 2, or 3)
            if current_level < 0.17:
                level_num = 0
                level_description = "Not implemented"
            elif current_level < 0.5:
                level_num = 1
                level_description = "Basic level"
            elif current_level < 0.84:
                level_num = 2
                level_description = "Intermediate level"
            else:
                level_num = 3
                level_description = "Mature level"

            # Format as "Level X (Description)"
            level_display = f"Level {level_num} ({level_description})"

            # Get explanation with similar teams details
            similar_teams_list = []
            why = "Recommended based on improvement sequences"
            try:
                explanation = self.recommender.get_recommendation_explanation(team_name, prev_month, practice)
                similar_count = explanation.get("similar_teams_improved", 0)
                total_checked = explanation.get("total_similar_teams_checked", 0)
                has_sequence_boost = explanation.get("has_sequence_boost", False)
                similar_teams_list = explanation.get("similar_teams_list", [])

                # Determine why based on both similarity and sequence contribution
                if similar_count > 0 and has_sequence_boost:
                    # Both contributed
                    why = f"{similar_count} similar team(s) improved this practice + sequence patterns"
                elif similar_count > 0:
                    # Only similarity contributed
                    why = f"{similar_count} similar team(s) improved this practice"
                elif has_sequence_boost:
                    # Only sequences contributed
                    why = "Recommended based on improvement sequences"
                else:
                    # Neither contributed (fallback - shouldn't happen often)
                    why = "Recommended based on improvement sequences"
            except:
                pass

            # Check if validated and which month(s) it improved in
            validated = False
            improved_in_months = None
            if month_to_predict:
                for imp in actual_improvements:
                    if imp["practice"] == practice:
                        validated = True
                        improved_in_months = imp.get("improved_in", [])
                        break

            # Format similar teams list
            formatted_similar_teams = []
            for st in similar_teams_list:
                formatted_similar_teams.append(
                    {
                        "team": st["team"],
                        "month": int(st["month"]),
                        "similarity": float(st["similarity"]),
                        "similar_at_month": int(st.get("similar_at_month", st["month"])),
                    }
                )

            formatted_recs.append(
                {
                    "practice": practice,
                    "score": float(score),
                    "current_level": float(current_level),
                    "original_level": float(original_level),
                    "level_num": level_num,
                    "level_description": level_description,
                    "level_display": level_display,
                    "why": why,
                    "similar_teams": formatted_similar_teams,
                    "validated": validated,
                    "improved_in_months": [int(m) for m in improved_in_months] if improved_in_months else None,
                }
            )

        # Get practice profile (use prev_month as baseline)
        practice_profile = self._get_practice_profile(team_name, prev_month)

        return {
            "team": team_name,
            "month": month_to_predict,  # Return the month to predict, not the baseline month
            "recommendations": formatted_recs,
            "validation": validation_summary if validation_summary else None,
            "practice_profile": practice_profile,
        }

    def run_backtest(self, train_ratio: float = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Run rolling window backtest validation.

        Args:
            train_ratio: Ignored (kept for API compatibility)
            config: Optional configuration dict with fine-tuning parameters

        Returns:
            Dictionary with backtest results including per-month accuracy
            Matches BacktestResponse model structure
        """
        # Convert config dict to format expected by backtest engine
        config_dict = None
        if config:
            config_dict = {
                "top_n": config.get("top_n", 2),
                "k_similar": config.get("k_similar", 19),
                "similarity_weight": config.get("similarity_weight", 0.6),
                "similar_teams_lookahead_months": config.get("similar_teams_lookahead_months", 3),
                "recent_improvements_months": config.get("recent_improvements_months", 3),
                "min_similarity_threshold": config.get("min_similarity_threshold", 0.75),
            }

        result = self.backtest_engine.run_backtest(train_ratio=train_ratio, config=config_dict)

        # Remove 'status' field if present (not in BacktestResponse model)
        if "status" in result:
            del result["status"]

        # Ensure per_month_results is properly formatted
        if "per_month_results" in result:
            # Ensure each result has all required fields
            formatted_per_month = []
            for r in result["per_month_results"]:
                formatted_per_month.append(
                    {
                        "month": int(r["month"]),
                        "train_months": [int(m) for m in r["train_months"]],
                        "predictions": int(r["predictions"]),
                        "correct": int(r["correct"]),
                        "accuracy": float(r["accuracy"]),
                        "teams_tested": int(r["teams_tested"]),
                    }
                )
            result["per_month_results"] = formatted_per_month

        # Improvement factor is already calculated in backtest engine
        if "improvement_factor" not in result and "overall_accuracy" in result and "random_baseline" in result:
            baseline = result["random_baseline"]
            accuracy = result["overall_accuracy"]
            result["improvement_factor"] = accuracy / baseline if baseline > 0 else 0.0

        # Ensure all required fields are present and properly typed
        if "total_predictions" in result:
            result["total_predictions"] = int(result["total_predictions"])
        if "correct_predictions" in result:
            result["correct_predictions"] = int(result["correct_predictions"])
        if "overall_accuracy" in result:
            result["overall_accuracy"] = float(result["overall_accuracy"])
        if "random_baseline" in result:
            result["random_baseline"] = float(result["random_baseline"])
        if "improvement_gap" in result:
            result["improvement_gap"] = float(result["improvement_gap"])
        elif "overall_accuracy" in result and "random_baseline" in result:
            result["improvement_gap"] = float(result["overall_accuracy"] - result["random_baseline"])
        if "improvement_factor" in result:
            result["improvement_factor"] = float(result["improvement_factor"])
        if "teams_tested" in result:
            result["teams_tested"] = int(result["teams_tested"])
        if "avg_improvements_per_case" in result:
            result["avg_improvements_per_case"] = float(result["avg_improvements_per_case"])
        else:
            result["avg_improvements_per_case"] = 0.0

        return result

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
    ) -> dict[str, Any]:
        """
        Find optimal configuration by testing parameter combinations.

        Args:
            min_accuracy: Minimum accuracy threshold (default: 0.40)
            top_n_range: Optional list of top_n values to test
            similarity_weight_range: Optional list of similarity_weight values to test
            k_similar_range: Optional list of k_similar values to test
            similar_teams_lookahead_months_range: Optional list of lookahead months to test
            recent_improvements_months_range: Optional list of recent months to test
            min_similarity_threshold_range: Optional list of min_similarity values to test
            fixed_params: Fixed parameter values (overrides ranges)

        Returns:
            Dictionary with optimal configuration and results
        """
        logger.info(
            f"[CANCELLATION] Service.find_optimal_config called - Optimizer instance: {id(self.optimizer_engine)}"
        )
        result = self.optimizer_engine.find_optimal_config(
            min_accuracy=min_accuracy,
            top_n_range=top_n_range,
            similarity_weight_range=similarity_weight_range,
            k_similar_range=k_similar_range,
            similar_teams_lookahead_months_range=similar_teams_lookahead_months_range,
            recent_improvements_months_range=recent_improvements_months_range,
            min_similarity_threshold_range=min_similarity_threshold_range,
            fixed_params=fixed_params,
        )

        return result

    def cancel_optimization(self):
        """Cancel the current optimization."""
        logger.info("[CANCELLATION] Service layer: Setting cancellation flag on optimizer engine")
        self.optimizer_engine.cancel()
        logger.info("[CANCELLATION] Service layer: Cancellation flag set successfully")

    def get_system_stats(self) -> dict[str, Any]:
        """
        Get system statistics.

        Returns:
            Dictionary with system statistics matching SystemStats model
        """
        try:
            # Validate that processor and recommender are available
            if not hasattr(self, 'processor') or self.processor is None:
                raise ValueError("Data processor is not initialized")
            if not hasattr(self, 'recommender') or self.recommender is None:
                raise ValueError("Recommendation engine is not initialized")
            
            teams = self.processor.get_all_teams()
            months = sorted(self.processor.get_all_months())

            # Calculate stats
            total_observations = 0
            for team in teams:
                history = self.processor.get_team_history(team)
                total_observations += len(history)

            # Get similarity stats if available
            similarity_stats = None
            if hasattr(self.recommender, "similarity_engine"):
                if hasattr(self.recommender.similarity_engine, "get_similarity_stats"):
                    similarity_stats = self.recommender.similarity_engine.get_similarity_stats()

            # Validate practices list exists
            if not hasattr(self.recommender, 'practices') or not self.recommender.practices:
                logger.warning("Recommender practices list is empty or missing")
                practices_list = []
            else:
                practices_list = list(self.recommender.practices)

            result = {
                "num_teams": int(len(teams)),
                "num_practices": int(len(practices_list)),
                "num_months": int(len(months)),
                "total_observations": int(total_observations),
                "months": [int(m) for m in months],  # Ensure integers
                "practices": practices_list,  # Ensure list
                "similarity_stats": similarity_stats,
            }

            # Add practice definitions if available
            if self.practice_definitions:
                # Only include definitions for practices that exist in the system
                practice_defs = {}
                practice_remarks_dict = {}
                for practice in practices_list:
                    if practice in self.practice_definitions:
                        practice_defs[practice] = self.practice_definitions[practice]
                        if practice in self.practice_remarks:
                            practice_remarks_dict[practice] = self.practice_remarks[practice]
                if practice_defs:
                    result["practice_definitions"] = practice_defs
                    if practice_remarks_dict:
                        result["practice_remarks"] = practice_remarks_dict

            # Add missing values details if available
            # Ensure it matches MissingValuesDetails structure
            if self.missing_values_details:
                # Ensure all fields are properly typed
                missing_vals = {
                    "total_missing": int(self.missing_values_details.get("total_missing", 0)),
                    "by_practice": self.missing_values_details.get("by_practice", {}),
                    "by_month": {int(k): v for k, v in self.missing_values_details.get("by_month", {}).items()},
                    "practices_with_missing": list(self.missing_values_details.get("practices_with_missing", [])),
                    "months_with_missing": [int(m) for m in self.missing_values_details.get("months_with_missing", [])],
                }
                result["missing_values"] = missing_vals

            return result
        except Exception as e:
            logger.error(f"Error getting system stats: {e}", exc_info=True)
            raise

    def get_improvement_sequences(self) -> dict[str, Any]:
        """
        Get all learned improvement sequences.

        Returns:
            Dictionary with sequences, stats, and metadata
        """
        sequence_mapper = self.recommender.sequence_mapper

        # Get all sequences
        sequences = sequence_mapper.get_all_sequences(min_count=1)

        # Get stats
        stats = sequence_mapper.get_sequence_stats()

        # Format sequences for API
        formatted_sequences = []
        for from_practice, to_practice, count, probability in sequences:
            formatted_sequences.append(
                {
                    "from_practice": from_practice,
                    "to_practice": to_practice,
                    "count": count,
                    "probability": round(probability, 4),
                }
            )

        # Group by from_practice for easier frontend display
        grouped_sequences = {}
        for seq in formatted_sequences:
            from_p = seq["from_practice"]
            if from_p not in grouped_sequences:
                grouped_sequences[from_p] = []
            grouped_sequences[from_p].append(
                {"to_practice": seq["to_practice"], "count": seq["count"], "probability": seq["probability"]}
            )

        return {
            "sequences": formatted_sequences,
            "grouped_sequences": grouped_sequences,
            "stats": stats,
            "total_sequences": len(formatted_sequences),
            "total_practices_with_transitions": len(grouped_sequences),
        }

    def _get_practice_profile(self, team_name: str, current_month: int) -> dict[str, list[str]]:
        """
        Get practice maturity profile for a team at a specific month.

        Categorizes all practices into maturity levels based on their normalized
        scores (0-1 scale). Practices are grouped into 4 levels:
        - Level 0: Not implemented (< 0.17 normalized, < 0.5 original)
        - Level 1: Basic level (0.17-0.5 normalized, 0.5-1.5 original)
        - Level 2: Intermediate level (0.5-0.84 normalized, 1.5-2.5 original)
        - Level 3: Mature level (>= 0.84 normalized, >= 2.5 original)

        Args:
            team_name (str): Name of the team to get profile for.
                Must exist in the processor's team list.
            current_month (int): Month in yyyymmdd format (e.g., 20200107).
                Must exist in the team's history.

        Returns:
            Dict[str, List[str]]: Dictionary with keys 'level_0', 'level_1', 'level_2', 'level_3',
                each containing a sorted list of practice names at that maturity level.
                Returns empty lists for all levels if team/month not found.

        Example:
            >>> profile = service._get_practice_profile("Team Alpha", 20200107)
            >>> profile['level_0']
            ['Practice A', 'Practice B']
            >>> profile['level_3']
            ['Practice C']
        """
        history = self.processor.get_team_history(team_name)
        if current_month not in history:
            return {"level_0": [], "level_1": [], "level_2": [], "level_3": []}

        practice_vector = history[current_month]
        profile = {"level_0": [], "level_1": [], "level_2": [], "level_3": []}

        for j, normalized_value in enumerate(practice_vector):
            practice_name = self.recommender.practices[j]

            # Group by level (same logic as CLI)
            if normalized_value < 0.17:  # < 0.5 original
                profile["level_0"].append(practice_name)
            elif normalized_value < 0.5:  # 0.5-1.5 original
                profile["level_1"].append(practice_name)
            elif normalized_value < 0.84:  # 1.5-2.5 original
                profile["level_2"].append(practice_name)
            else:  # >= 2.5 original
                profile["level_3"].append(practice_name)

        # Sort practices alphabetically within each level
        for level in profile:
            profile[level] = sorted(profile[level])

        return profile
