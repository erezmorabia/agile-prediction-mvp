"""
DataProcessor: Clean, normalize, and prepare data for ML algorithms.
"""

import logging
from collections import defaultdict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataProcessor:
    """Process and prepare agile metrics data for machine learning."""

    def __init__(self, df: pd.DataFrame, practices: list):
        """
        Initialize DataProcessor.

        Args:
            df (pd.DataFrame): Raw data frame
            practices (list): List of practice column names
        """
        # The raw data frame to be cleaned and normalized by process().
        self.df = df

        # The list of practice column names present in df.
        self.practices = practices

        # Starts empty. Once process() runs, holds each team's month-by-month
        # scores as: team name -> {month: score vector}.
        self.team_histories = defaultdict(dict)

        # Source-to-analysis observation audit. Duplicate team-month rows are
        # resolved explicitly during process(), without changing the source file.
        self.raw_observation_count = len(df)
        self.unique_observation_count = 0
        self.duplicate_rows_ignored = 0
        self.duplicate_team_month_keys = []

        # On/off flag. False until process() finishes running once;
        # other methods rely on this before trusting team_histories.
        self.processed = False

    def process(self) -> None:
        """
        Process and prepare data for machine learning algorithms.

        Performs the following transformations:
        1. Fill missing values: Replaces NaN practice values with 0 in an internal working copy
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
            - Processing uses an internal copy; the caller's DataFrame is not modified
            - Duplicate (Team Name, Month) rows retain their final source occurrence
              and earlier occurrences are recorded in the observation audit attributes
            - Practice scores are normalized: original_value / 3.0
            - Team histories are sorted by month chronologically
            - NaN values in vectors are replaced with 0.0 using np.nan_to_num()

        Example:
            >>> processor = DataProcessor(df, practices)
            >>> processor.process()
            >>> processor.processed
            True
            >>> history = processor.get_team_history("Team Alpha")
            >>> history[20200107]  # Practice vector for January 2020
            array([0.33, 0.67, 0.0, ...])
        """
        # Resolve duplicate observation keys before sorting so "final occurrence"
        # refers deterministically to source-row order. This formalizes the prior
        # dictionary-overwrite behavior while making the excluded rows auditable.
        working_df = self.df.copy()
        required_keys = ["Team Name", "Month"]
        if all(column in working_df.columns for column in required_keys):
            duplicate_key_mask = working_df.duplicated(subset=required_keys, keep=False)
            ignored_mask = working_df.duplicated(subset=required_keys, keep="last")
            duplicate_keys = working_df.loc[duplicate_key_mask, required_keys].drop_duplicates()

            self.duplicate_rows_ignored = int(ignored_mask.sum())
            self.duplicate_team_month_keys = [
                (str(row["Team Name"]), int(row["Month"])) for _, row in duplicate_keys.iterrows()
            ]

            if self.duplicate_rows_ignored:
                formatted_keys = ", ".join(f"{team}/{month}" for team, month in self.duplicate_team_month_keys)
                logger.warning(
                    "Ignoring %d earlier duplicate team-month row(s); retaining the final source occurrence for: %s",
                    self.duplicate_rows_ignored,
                    formatted_keys,
                )
                working_df = working_df.loc[~ignored_mask].copy()

        self.unique_observation_count = len(working_df)

        # Fill NaN values with 0
        for practice in self.practices:
            working_df[practice] = working_df[practice].fillna(0)

        # Normalize scores to 0-1 range (from 0-3 scale)
        for practice in self.practices:
            working_df[practice] = working_df[practice] / 3.0

        self.df = working_df

        # Build team histories indexed by month
        for team in self.df["Team Name"].unique():
            team_data = self.df[self.df["Team Name"] == team].sort_values("Month")
            # Walk through this one team's rows, oldest month first
            for _, row in team_data.iterrows():
                month = int(row["Month"])
                # Store practices as numpy array
                practices_vector = row[self.practices].values.astype(float)
                # Ensure no NaN values (fill with 0 if any remain)
                practices_vector = np.nan_to_num(practices_vector, nan=0.0)
                self.team_histories[team][month] = practices_vector

        self.processed = True

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
        """Get sorted list of all months present across all teams.

        Collects month keys from every team's history and returns them in
        chronological order (yyyymmdd strings sort correctly lexicographically).

        Returns:
            list: Sorted list of month strings in yyyymmdd format.

        Raises:
            ValueError: If process() has not been called yet.
        """
        all_months = set()
        # Go through every team's history and collect the months it has data for
        for team_months in self.team_histories.values():
            all_months.update(team_months.keys())
        return sorted(all_months)

    def get_statistics(self) -> dict:
        """
        Get statistics about processed data.

        Returns:
            dict: Statistics including value ranges, missing data, etc.
        """
        if not self.processed:
            raise ValueError("Data not processed. Call process() first.")

        all_values = []
        # Go through every team's history...
        for team_history in self.team_histories.values():
            # ...and every month within it, pooling every score ever recorded
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
