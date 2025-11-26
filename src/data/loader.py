"""
DataLoader: Load agile metrics from Excel files.
"""

import os

import pandas as pd


class DataLoader:
    """Load and prepare agile metrics data from Excel files."""

    def __init__(self, file_path: str):
        """
        Initialize DataLoader.

        Args:
            file_path (str): Path to Excel file containing agile metrics
        """
        self.file_path = file_path
        self.df = None
        self.practices = None
        self.teams = None
        self.months = None

    def load(self) -> pd.DataFrame:
        """
        Load agile metrics data from Excel file.

        Reads the first sheet of the Excel file and identifies practice columns
        (all columns except 'Team Name' and 'Month'). Extracts unique teams,
        practices, and months for later use.

        Expected Excel Format:
        - First sheet contains the data
        - Required columns: 'Team Name', 'Month'
        - Practice columns: All other columns are treated as practices
        - Practice values: Should be 0-3 (maturity levels), but validation happens later
        - Month format: Numeric yyyymmdd format (e.g., 20200107)

        Returns:
            pd.DataFrame: Loaded data with columns:
                - 'Team Name' (str): Name of the team
                - 'Month' (int): Month in yyyymmdd format
                - Practice columns: One column per practice with maturity scores (0-3)
            Also sets instance attributes:
                - self.practices: List of practice column names
                - self.teams: Sorted list of unique team names
                - self.months: Sorted list of unique months

        Raises:
            FileNotFoundError: If the specified file path does not exist.
            ValueError: If the Excel file cannot be read (corrupted, wrong format, etc.)
                or if required columns ('Team Name', 'Month') are missing.

        Example:
            >>> loader = DataLoader('data/raw/20250204_Cleaned_Dataset.xlsx')
            >>> df = loader.load()
            Loaded data: 87 teams, 30 practices, 10 months
               Total rows: 870
            >>> print(loader.practices[:3])
            ['Practice A', 'Practice B', 'Practice C']
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")

        try:
            self.df = pd.read_excel(self.file_path, sheet_name=0)
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {str(e)}")

        # Identify practice columns (all except Team Name and Month)
        self.practices = [col for col in self.df.columns if col not in ["Team Name", "Month"]]

        # Get unique teams and months
        self.teams = sorted(self.df["Team Name"].unique())
        self.months = sorted(self.df["Month"].unique())

        print(f"Loaded data: {len(self.teams)} teams, {len(self.practices)} practices, {len(self.months)} months")
        print(f"   Total rows: {len(self.df)}")

        return self.df

    def get_team_data(self, team_name: str) -> pd.DataFrame:
        """
        Get data for a specific team across all time periods.

        Args:
            team_name (str): Name of the team

        Returns:
            pd.DataFrame: Data for the team
        """
        if self.df is None:
            raise ValueError("Data not loaded. Call load() first.")

        team_data = self.df[self.df["Team Name"] == team_name].sort_values("Month")

        if len(team_data) == 0:
            raise ValueError(f"Team '{team_name}' not found in data")

        return team_data

    def get_summary(self) -> dict:
        """
        Get summary statistics of loaded data.

        Returns:
            dict: Summary information
        """
        if self.df is None:
            raise ValueError("Data not loaded. Call load() first.")

        return {
            "total_rows": len(self.df),
            "num_teams": len(self.teams),
            "num_practices": len(self.practices),
            "num_months": len(self.months),
            "date_range": f"{self.months[0]} to {self.months[-1]}",
            "practice_names": self.practices[:5],  # First 5 practices
            "team_names": self.teams[:5],  # First 5 teams
        }
