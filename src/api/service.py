"""
API Service Layer: Wraps ML components for web API.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)
from src.data import DataProcessor
from src.data.practice_definitions import PracticeDefinitionsLoader
from src.ml import RecommendationEngine
from src.ml.policy import policy_summary
from src.validation import BacktestEngine


class APIService:
    """Service layer that wraps ML components for API endpoints."""

    def __init__(self, recommender: RecommendationEngine, processor: DataProcessor):
        """
        Initialize API service.

        Args:
            recommender: RecommendationEngine instance
            processor: DataProcessor instance
        """
        # The RecommendationEngine that route handlers ultimately call into.
        self.recommender = recommender

        # Gives access to team histories, shared with the engines below.
        self.processor = processor

        # Wraps the same recommender/processor pair for the backtest endpoint.
        self.backtest_engine = BacktestEngine(recommender, processor)

        # Locate the practice definitions file - optional, and tolerant of a
        # legacy misspelled filename still present in some data exports.
        definitions_file = None
        import os

        for filename in ["data/raw/practice_level_definitions.xlsx", "data/raw/ractice_level_definitions.xlsx"]:
            if os.path.exists(filename):
                definitions_file = filename
                break

        if definitions_file:
            # File found: load definitions/remarks for the Statistics tab.
            self.practice_definitions_loader = PracticeDefinitionsLoader(definitions_file)
            self.practice_definitions = self.practice_definitions_loader.get_definitions()
            self.practice_remarks = self.practice_definitions_loader.get_remarks()
        else:
            # File not found: fail gracefully with empty definitions rather than crashing.
            self.practice_definitions_loader = None
            self.practice_definitions = {}
            self.practice_remarks = {}

        # Filled in later by web_main.py with details about missing/dropped data.
        self.missing_values_details = None

        # Filled in later by web_main.py with the path to the loaded Excel file.
        self.data_file_path: str | None = None

    def get_all_teams(self) -> list[dict[str, Any]]:
        """
        Get all teams with metadata.

        Returns:
            List of team info dictionaries with name and data count
        """
        teams = self.processor.get_all_teams()
        result = []

        # Build one info entry per team.
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
        Only shows valid prediction months (global index 3+) as month to predict.

        Returns:
            List of team/month combinations with improvements (month to predict is a
            valid prediction month per PolicyEngine.prediction_months())
        """
        teams_with_improvements = []
        all_teams = self.processor.get_all_teams()

        valid_prediction_months = set(self.recommender.policy_engine.prediction_months())

        # Check every team, one at a time, for month-to-month improvements.
        for team in all_teams:
            history = self.processor.get_team_history(team)
            months = sorted(history.keys())

            # Check each month (except the first one)
            for i in range(1, len(months)):
                prev_month = months[i - 1]
                month_to_predict = months[i]

                # Only show valid prediction months
                if month_to_predict not in valid_prediction_months:
                    continue

                prev_vector = history[prev_month]
                predicted_vector = history[month_to_predict]

                # Count improvements
                improvements = []
                # Compare the two months' scores, practice by practice.
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
        1. The month is a valid global prediction month (PolicyEngine.prediction_months())
        2. The team has a usable baseline snapshot before it

        Args:
            team_name: Name of the team

        Returns:
            List of months (sorted) or None if team not found
        """
        if team_name not in self.processor.get_all_teams():
            return None

        engine = self.recommender.policy_engine
        history = self.processor.get_team_history(team_name)
        valid_prediction_months = set(engine.prediction_months())

        return [
            month
            for month in sorted(history.keys())
            if month in valid_prediction_months and engine.baseline_month_for(team_name, month) is not None
        ]

    def get_recommendations(self, team_name: str, month: int) -> dict[str, Any]:
        """
        Get recommendations for a team for a specific month to predict, using that
        month's globally selected policy (similarity / sequence / time-aware popularity
        blend). Always returns exactly two recommendations, unless the team has fewer
        than two non-maxed candidate practices left to improve.

        Args:
            team_name: Name of the team
            month: Month to predict (yyyymmdd format) - must be a valid prediction month

        Returns:
            Dictionary with recommendations, validation info, and the selected policy's
            audit record.
        """
        # Validate team and month
        if team_name not in self.processor.get_all_teams():
            return {"error": f'Team "{team_name}" not found'}

        history = self.processor.get_team_history(team_name)
        if month not in history:
            return {"error": f"No data for team on month {month}"}

        engine = self.recommender.policy_engine
        if month not in engine.prediction_months():
            return {
                "error": "Month to predict must be a valid prediction month. We need at least 3 months of history to make predictions.",
                "details": f"Month {month} is not a valid prediction month.",
            }

        result = self.recommender.recommend(team_name, month)
        selected_policy_info = policy_summary(result.selected_policy)

        if result.insufficient_practices:
            baseline_for_profile = result.baseline_month if result.baseline_month is not None else month
            return {
                "team": team_name,
                "month": month,
                "recommendations": [],
                "validation": None,
                "practice_profile": self._get_practice_profile(team_name, baseline_for_profile),
                "selected_policy": selected_policy_info,
                "no_similar_teams_found": False,
                "message": f"Team '{team_name}' has fewer than two practices left to improve.",
            }

        prev_month = result.baseline_month
        months = sorted(history.keys())
        month_to_predict_idx = months.index(month)

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
        # Compare the baseline month to the predicted month, practice by practice.
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

            # Same comparison, one month further out.
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

            # Same comparison, two months further out.
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
        # Merge the 3 months' worth of improvements into one entry per practice,
        # keeping whichever month showed the biggest improvement.
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
        recommended_practices = list(result.practices)
        validated_count = sum(1 for imp in actual_improvements if imp["practice"] in recommended_practices)

        # Calculate accuracy only if there were actual improvements
        # If no improvements occurred, set accuracy to None - this isn't a model failure,
        # it just means the team didn't improve anything in the validation window
        if actual_improvements and recommended_practices:
            accuracy = validated_count / len(recommended_practices)
        else:
            accuracy = None  # No accuracy when no improvements occurred

        validation_summary = {
            "next_month": month_to_predict,  # The predicted month
            "month_after": month_after if month_to_predict_idx + 1 < len(months) else None,
            "month_after_2": month_after_2 if month_to_predict_idx + 2 < len(months) else None,
            "actual_improvements": actual_improvements,
            "validated_count": validated_count,
            "total_recommendations": len(recommended_practices),
            "accuracy": accuracy,
            "team_improved_anything": len(actual_improvements) > 0,
        }

        # Format recommendations
        formatted_recs = []
        # Build one detailed, API-shaped entry per recommendation.
        for practice in result.practices:
            score = result.scores[practice]
            current_level = result.current_levels[practice]
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
            explanation = self.recommender.get_recommendation_explanation(team_name, month, practice)
            similar_count = explanation.get("similar_teams_improved", 0)
            has_sequence_boost = explanation.get("has_sequence_boost", False)
            no_peers_for_practice = explanation.get("no_similar_teams_found", False)
            similar_teams_list = explanation.get("similar_teams_list", [])

            # Determine why based on similarity, sequence, and popularity contribution
            if similar_count > 0 and has_sequence_boost:
                why = f"{similar_count} similar team(s) improved this practice + sequence patterns"
            elif similar_count > 0:
                why = f"{similar_count} similar team(s) improved this practice"
            elif has_sequence_boost:
                why = "Recommended based on improvement sequences"
            elif no_peers_for_practice:
                why = "No comparable team was found; recommended based on organization-wide popularity and improvement sequences"
            else:
                why = "Recommended based on organization-wide popularity"

            # Check if validated and which month(s) it improved in
            validated = False
            improved_in_months = None
            # Look for this recommended practice among what actually improved.
            for imp in actual_improvements:
                if imp["practice"] == practice:
                    validated = True
                    improved_in_months = imp.get("improved_in", [])
                    break

            # Format similar teams list
            formatted_similar_teams = []
            # Reformat each similar team's info into the API response shape.
            for st in similar_teams_list:
                if st.get("month") is None:
                    continue
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
            "selected_policy": selected_policy_info,
            "no_similar_teams_found": result.no_similar_teams_found,
            "message": None,
        }

    def run_backtest(self) -> dict[str, Any]:
        """
        Run the global two-month adaptive blend backtest. No model parameters are
        accepted - the monthly policy is the only configuration authority.

        Returns:
            Dictionary matching BacktestResponse: per_month_results, primary, and
            sensitivity.
        """
        result = self.backtest_engine.run_backtest()

        if "error" in result:
            return result

        result.pop("status", None)
        return result

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
            # Add up how many months of data each team contributes.
            for team in teams:
                history = self.processor.get_team_history(team)
                total_observations += len(history)

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
            }

            # Add practice definitions if available
            if self.practice_definitions:
                # Only include definitions for practices that exist in the system
                practice_defs = {}
                practice_remarks_dict = {}
                # Only carry over definitions/remarks for practices actually in use.
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
        # Re-learn from the full history: the policy engine's monthly selection leaves
        # the shared mapper's state gated to whatever month it last scored, but this tab
        # always shows all-history transitions regardless of that.
        sequence_mapper.learn_sequences()

        # Get all sequences
        sequences = sequence_mapper.get_all_sequences(min_count=1)

        # Get stats
        stats = sequence_mapper.get_sequence_stats()

        # Format sequences for API
        formatted_sequences = []
        # Reformat each learned sequence into the API response shape.
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
        # Bucket every sequence under the practice it starts from.
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

        # Sort each practice's score into its maturity level bucket.
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
