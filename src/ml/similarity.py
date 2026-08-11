"""
SimilarityEngine: Calculate similarity between teams using cosine similarity.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class SimilarityEngine:
    """Calculate team similarities based on practice maturity vectors."""

    def __init__(self, processor):
        """
        Initialize SimilarityEngine.

        Args:
            processor: DataProcessor instance with processed team histories
        """
        # Gives access to every team's history, so similarity comparisons can
        # look up any team's scores at any month on demand.
        self.processor = processor

    def find_similar_teams(self, target_team: str, target_month: int, k: int = 5, min_similarity: float = 0.0) -> list:
        """
        Find K most similar teams to a target team at a specific month.

        Compares the target team's state at target_month against ALL teams'
        states at ALL past months (months < target_month). This leverages
        all available historical data for better recommendations.

        Args:
            target_team (str): Name of target team
            target_month (int): Month to compare (yyyymmdd format)
            k (int): Number of similar teams to return
            min_similarity (float): Minimum similarity threshold (0.0-1.0, default 0.0 = no filter)

        Returns:
            list: List of (team_name, similarity_score, historical_month) tuples,
                  sorted by similarity score (descending). historical_month is the
                  month when the similar team had a similar state.

        Raises:
            ValueError: If team or month not found
        """
        # Get target team's practice vector at target_month
        target_history = self.processor.get_team_history(target_team)
        if target_month not in target_history:
            raise ValueError(f"Team '{target_team}' has no data for month {target_month}")

        # target_vector: target team's practice maturity scores at target_month, one value
        # per practice. Reshaped to (1, n_practices) since cosine_similarity expects a matrix
        # of row vectors, even for a single team.
        target_vector = target_history[target_month]
        target_vector = np.array(target_vector).reshape(1, -1)

        # Get all past months (months < target_month)
        all_months = self.processor.get_all_months()
        past_months = [m for m in all_months if m < target_month]

        if not past_months:
            raise ValueError(f"No past months available before {target_month}")

        # Collect all similarity comparisons across all past months
        all_similarities = []

        for historical_month in past_months:
            # Get all teams that have data for this historical month
            all_teams = self.processor.get_all_teams()

            for team in all_teams:
                # Skip the target team itself
                if team == target_team:
                    continue

                team_history = self.processor.get_team_history(team)
                if historical_month not in team_history:
                    continue

                # Get team's practice vector at historical month
                team_vector = team_history[historical_month]
                team_vector = np.array(team_vector).reshape(1, -1)

                # Calculate cosine similarity
                similarity = cosine_similarity(target_vector, team_vector)[0][0]

                # Filter by minimum similarity threshold
                if similarity >= min_similarity:
                    # Store: (team_name, similarity_score, historical_month)
                    all_similarities.append((team, float(similarity), historical_month))

        if not all_similarities:
            raise ValueError(f"No similar teams found for '{target_team}' in past months")

        # Deduplicate by team name - keep only the entry with highest similarity for each team
        # This ensures we get K different teams, not the same team at different months
        team_best_similarity = {}
        for team, similarity, historical_month in all_similarities:
            if team not in team_best_similarity or similarity > team_best_similarity[team][1]:
                team_best_similarity[team] = (team, similarity, historical_month)

        # Convert to list and sort by similarity score (descending)
        unique_similarities = list(team_best_similarity.values())
        unique_similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top K different teams
        return unique_similarities[:k]
