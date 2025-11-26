"""
MetricsCalculator: Calculate performance metrics for the recommendation system.
"""

import numpy as np


class MetricsCalculator:
    """Calculate various metrics for evaluating recommendation quality."""

    @staticmethod
    def calculate_hit_rate(recommendations: list, actual_improvements: set) -> float:
        """
        Calculate hit rate (how many recommendations were correct).

        Args:
            recommendations (list): List of recommended practice names
            actual_improvements (set): Set of practices that actually improved

        Returns:
            float: Hit rate (0-1)
        """
        if not recommendations:
            return 0.0

        hits = sum(1 for r in recommendations if r in actual_improvements)
        return hits / len(recommendations)

    @staticmethod
    def calculate_mrr(recommendations: list, actual_improvements: set) -> float:
        """
        Calculate Mean Reciprocal Rank (position of first correct recommendation).

        Args:
            recommendations (list): List of recommended practice names (in order)
            actual_improvements (set): Set of practices that actually improved

        Returns:
            float: MRR (0-1, where 1 is perfect)
        """
        for rank, rec in enumerate(recommendations, 1):
            if rec in actual_improvements:
                return 1.0 / rank
        return 0.0

    @staticmethod
    def calculate_coverage(all_recommendations: list, all_practices: set) -> float:
        """
        Calculate coverage (percentage of practices that were recommended).

        Args:
            all_recommendations (list): All recommendations made across predictions
            all_practices (set): Set of all available practices

        Returns:
            float: Coverage (0-1)
        """
        recommended_practices = set(all_recommendations)
        if not all_practices:
            return 0.0
        return len(recommended_practices & all_practices) / len(all_practices)

    @staticmethod
    def calculate_diversity(recommendations: list) -> float:
        """
        Calculate diversity of recommendations (higher = more varied).

        Args:
            recommendations (list): List of (practice, score, level) tuples

        Returns:
            float: Diversity score (0-1)
        """
        if len(recommendations) <= 1:
            return 0.0

        scores = [r[1] for r in recommendations]
        mean_score = np.mean(scores)
        std_score = np.std(scores)

        if mean_score == 0:
            return 0.0

        # Coefficient of variation
        cv = std_score / mean_score
        return min(cv, 1.0)  # Normalize to 0-1

    @staticmethod
    def calculate_confidence(recommendation_score: float, max_possible: float = 1.0) -> float:
        """
        Calculate confidence of a recommendation based on its score.

        Args:
            recommendation_score (float): Score of the recommendation
            max_possible (float): Maximum possible score

        Returns:
            float: Confidence (0-1)
        """
        if max_possible == 0:
            return 0.0
        return min(recommendation_score / max_possible, 1.0)
