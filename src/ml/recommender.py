"""
RecommendationEngine: thin compatibility wrapper over PolicyEngine.

The recommendation logic itself - the global two-month adaptive blend of similarity,
sequence, and time-aware popularity evidence - lives in PolicyEngine (src/ml/policy.py),
which is shared by the web API, the CLI, and the backtest so all three produce identical
recommendations for the same team and month. This class keeps the existing constructor
shape (similarity_engine, sequence_mapper, practices) so callers that already hold one
don't need to change, while exposing `policy_engine` for callers (BacktestEngine, the CLI,
APIService) that need cohort/selection operations PolicyEngine provides directly.
"""

from .policy import PolicyEngine


class RecommendationEngine:
    """Generate practice recommendations via the global two-month adaptive blend."""

    def __init__(self, similarity_engine, sequence_mapper, practices):
        """
        Initialize RecommendationEngine.

        Args:
            similarity_engine: SimilarityEngine instance
            sequence_mapper: SequenceMapper instance
            practices (list): List of practice names
        """
        self.similarity_engine = similarity_engine
        self.sequence_mapper = sequence_mapper
        self.practices = practices
        self.processor = similarity_engine.processor

        # Owns the grid, the cohort logic, and the monthly policy selection.
        self.policy_engine = PolicyEngine(similarity_engine, sequence_mapper, practices)

    def recommend(self, target_team: str, prediction_month: int):
        """
        Generate the top-2 practice recommendations for a team at a prediction month,
        using that month's globally selected policy (similarity / sequence / time-aware
        popularity blend).

        Args:
            target_team (str): Name of the team to generate recommendations for.
            prediction_month (int): Month to predict (yyyymmdd format). Recommendations
                are based on the team's own most recent observed snapshot strictly
                before this month.

        Returns:
            policy.RecommendationResult: `.practices` holds 0 or 2 practice names;
                empty with `.insufficient_practices=True` when the team has fewer than
                two non-maxed candidate practices at its baseline.
        """
        return self.policy_engine.recommend(target_team, prediction_month)

    def get_recommendation_explanation(self, target_team: str, prediction_month: int, practice: str) -> dict:
        """
        Explain why a practice was (or would be) recommended, using the prediction
        month's selected global policy.

        Args:
            target_team (str): Team name
            prediction_month (int): Month to predict (yyyymmdd format)
            practice (str): Practice name

        Returns:
            dict: Explanation details - see PolicyEngine.explain_practice.
        """
        return self.policy_engine.explain_practice(target_team, prediction_month, practice)
