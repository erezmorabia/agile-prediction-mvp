"""
OutputFormatter: Format and display results to the user.
"""


class OutputFormatter:
    """Format recommendation results for display."""

    @staticmethod
    def format_recommendation(practice: str, score: float, current_level: float) -> str:
        """
        Format a single recommendation.

        Args:
            practice (str): Practice name
            score (float): Recommendation score
            current_level (float): Current maturity level (0-1)

        Returns:
            str: Formatted recommendation string
        """
        level_bar = "▓" * int(current_level * 10) + "░" * (10 - int(current_level * 10))
        return f"{practice:40s} | Score: {score:6.3f} | Level: [{level_bar}] {current_level:.2f}"

    @staticmethod
    def format_recommendations(recommendations: list) -> str:
        """
        Format multiple recommendations.

        Args:
            recommendations (list): List of (practice, score, level) tuples

        Returns:
            str: Formatted recommendations string
        """
        output = "TOP RECOMMENDATIONS:\n"
        output += "=" * 80 + "\n"

        for i, (practice, score, level) in enumerate(recommendations, 1):
            output += f"{i}. {OutputFormatter.format_recommendation(practice, score, level)}\n"

        output += "=" * 80
        return output

    @staticmethod
    def format_team_stats(team_name: str, month: int, stats: dict) -> str:
        """
        Format team statistics.

        Args:
            team_name (str): Team name
            month (int): Month (yyyymmdd format)
            stats (dict): Statistics dictionary

        Returns:
            str: Formatted stats string
        """
        output = f"\nTEAM: {team_name} | MONTH: {month}\n"
        output += "=" * 80 + "\n"

        for key, value in stats.items():
            output += f"{key:30s}: {value}\n"

        output += "=" * 80
        return output
