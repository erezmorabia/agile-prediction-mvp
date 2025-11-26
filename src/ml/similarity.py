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
        self.processor = processor
        self.similarity_matrix = None
        self.teams = None

    def build_similarity_matrix(self, target_month: int) -> np.ndarray:
        """
        Build cosine similarity matrix for all teams at a specific month.

        Calculates pairwise cosine similarities between all teams' practice maturity
        vectors at the specified month. The similarity matrix is symmetric with
        diagonal values of 1.0 (teams are perfectly similar to themselves).

        The similarity matrix is cached in self.similarity_matrix for reuse.
        Only teams with data for the target_month are included.

        Args:
            target_month (int): Month in yyyymmdd format (e.g., 20200107) to calculate
                similarities for. All teams must have data for this month.

        Returns:
            np.ndarray: 2D similarity matrix of shape (n_teams, n_teams) where:
                - matrix[i][j] = cosine similarity between team i and team j
                - Values range from -1.0 to 1.0 (typically 0.0 to 1.0 for practice vectors)
                - Diagonal values are 1.0 (perfect self-similarity)
                - Matrix is symmetric: matrix[i][j] == matrix[j][i]
            Also sets instance attributes:
                - self.similarity_matrix: Cached matrix
                - self.teams: List of team names (in same order as matrix rows/columns)

        Raises:
            ValueError: If no teams have data for the specified target_month.

        Example:
            >>> engine = SimilarityEngine(processor)
            >>> matrix = engine.build_similarity_matrix(20200107)
            >>> similarity = matrix[0][1]  # Similarity between first two teams
            >>> print(f"Similarity: {similarity:.3f}")
            Similarity: 0.856

        Note:
            - Uses cosine similarity: cos(θ) = (A·B) / (||A|| ||B||)
            - Only includes teams with data for target_month
            - Matrix is cached for performance (reuse for multiple queries)
        """
        teams = self.processor.get_all_teams()
        self.teams = teams

        # Get practice vectors for all teams at target month
        vectors = []
        valid_teams = []

        for team in teams:
            history = self.processor.get_team_history(team)
            if target_month in history:
                vectors.append(history[target_month])
                valid_teams.append(team)

        if not vectors:
            raise ValueError(f"No data available for month {target_month}")

        # Calculate cosine similarity
        vectors = np.array(vectors)
        self.similarity_matrix = cosine_similarity(vectors)
        self.teams = valid_teams

        return self.similarity_matrix

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

    def get_similarity_stats(self) -> dict:
        """
        Get statistics about the similarity matrix.

        Returns:
            dict: Statistics including mean, std, min, max similarities
        """
        if self.similarity_matrix is None:
            return {"status": "not_built"}

        # Exclude diagonal (self-similarities = 1.0)
        upper_triangle = self.similarity_matrix[np.triu_indices_from(self.similarity_matrix, k=1)]

        return {
            "num_teams": len(self.teams),
            "mean_similarity": float(np.mean(upper_triangle)),
            "std_similarity": float(np.std(upper_triangle)),
            "min_similarity": float(np.min(upper_triangle)),
            "max_similarity": float(np.max(upper_triangle)),
        }
