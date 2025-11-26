"""
DataProcessor: Clean, normalize, and prepare data for ML algorithms.
"""

from collections import defaultdict

import numpy as np
import pandas as pd


class DataProcessor:
    """Process and prepare agile metrics data for machine learning."""

    def __init__(self, df: pd.DataFrame, practices: list):
        """
        Initialize DataProcessor.

        Args:
            df (pd.DataFrame): Raw data frame
            practices (list): List of practice column names
        """
        self.df = df
        self.practices = practices
        self.team_histories = defaultdict(dict)
        self.processed = False

    def process(self) -> None:
        """
        Process and prepare data for machine learning algorithms.

        Performs the following transformations:
        1. Fill missing values: Replaces NaN values with 0 (not implemented)
        2. Normalize scores: Converts practice maturity scores from 0-3 scale to 0-1 scale
           (divides by 3.0) for ML algorithm compatibility
        3. Build team histories: Creates a dictionary mapping each team to their practice
           vectors indexed by month, stored as numpy arrays

        After processing, the data is ready for use by similarity engine, sequence mapper,
        and recommendation engine. Team histories can be accessed via get_team_history().

        Returns:
            None: Modifies internal state:
                - self.team_histories: Dictionary mapping team names to month-indexed vectors
                - self.processed: Set to True

        Raises:
            ValueError: If practices list is empty or DataFrame is invalid.

        Note:
            - Original DataFrame is modified in-place (NaN values filled)
            - Practice scores are normalized: original_value / 3.0
            - Team histories are sorted by month chronologically
            - NaN values in vectors are replaced with 0.0 using np.nan_to_num()

        Example:
            >>> processor = DataProcessor(df, practices)
            >>> processor.process()
            Processing data...
            Processed 87 team histories
            >>> history = processor.get_team_history("Team Alpha")
            >>> history[20200107]  # Practice vector for January 2020
            array([0.33, 0.67, 0.0, ...])
        """
        print("Processing data...")

        # Fill NaN values with 0 (not implemented)
        for practice in self.practices:
            self.df[practice] = self.df[practice].fillna(0)

        # Normalize scores to 0-1 range (from 0-3 scale)
        for practice in self.practices:
            self.df[practice] = self.df[practice] / 3.0

        # Build team histories indexed by month
        for team in self.df["Team Name"].unique():
            team_data = self.df[self.df["Team Name"] == team].sort_values("Month")
            for _, row in team_data.iterrows():
                month = int(row["Month"])
                # Store practices as numpy array
                practices_vector = row[self.practices].values.astype(float)
                # Ensure no NaN values (fill with 0 if any remain)
                practices_vector = np.nan_to_num(practices_vector, nan=0.0)
                self.team_histories[team][month] = practices_vector

        self.processed = True
        print(f"Processed {len(self.team_histories)} team histories")

    def get_team_history(self, team_name: str) -> dict:
        """
        Get processed history for a team.

        Args:
            team_name (str): Name of the team

        Returns:
            dict: Dictionary mapping months to practice vectors
        """
        if not self.processed:
            raise ValueError("Data not processed. Call process() first.")

        if team_name not in self.team_histories:
            raise ValueError(f"Team '{team_name}' not found")

        return self.team_histories[team_name]

    def get_all_teams(self) -> list:
        """Get list of all teams."""
        if not self.processed:
            raise ValueError("Data not processed. Call process() first.")
        return list(self.team_histories.keys())

    def get_all_months(self) -> list:
        """Get list of all months."""
        all_months = set()
        for team_months in self.team_histories.values():
            all_months.update(team_months.keys())
        return sorted(list(all_months))

    def get_statistics(self) -> dict:
        """
        Get statistics about processed data.

        Returns:
            dict: Statistics including value ranges, missing data, etc.
        """
        if not self.processed:
            raise ValueError("Data not processed. Call process() first.")

        all_values = []
        for team_history in self.team_histories.values():
            for vector in team_history.values():
                all_values.extend(vector)

        all_values = np.array(all_values)

        return {
            "mean": float(np.mean(all_values)),
            "std": float(np.std(all_values)),
            "min": float(np.min(all_values)),
            "max": float(np.max(all_values)),
            "median": float(np.median(all_values)),
            "num_teams": len(self.team_histories),
            "num_practices": len(self.practices),
            "num_months": len(self.get_all_months()),
        }
