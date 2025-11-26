"""
DataValidator: Validate data quality and integrity.
"""

import pandas as pd


class DataValidator:
    """Validate agile metrics data for quality and consistency."""

    def __init__(self, df: pd.DataFrame, practices: list):
        """
        Initialize DataValidator.

        Args:
            df (pd.DataFrame): Data frame to validate
            practices (list): List of practice column names
        """
        self.df = df
        self.practices = practices
        self.issues = []

    def validate(self) -> bool:
        """
        Run all validation checks.

        Returns:
            bool: True if data is valid, False otherwise
        """
        self.issues = []

        # Check required columns
        self._check_required_columns()

        # Check data types
        self._check_data_types()

        # Check value ranges
        self._check_value_ranges()

        # Check for missing values
        self._check_missing_values()

        # Check teams have multiple time periods
        self._check_temporal_coverage()

        if self.issues:
            print(f"Warning: Validation found {len(self.issues)} issues:")
            for issue in self.issues:
                print(f"   - {issue}")
            return False

        print("Data validation passed")
        return True

    def _check_required_columns(self) -> None:
        """Check that required columns exist."""
        required = {"Team Name", "Month"}
        missing = required - set(self.df.columns)
        if missing:
            self.issues.append(f"Missing required columns: {missing}")

    def _check_data_types(self) -> None:
        """Check that data types are correct."""
        if self.df["Team Name"].dtype != "object":
            self.issues.append("Team Name should be string type")

        if not pd.api.types.is_numeric_dtype(self.df["Month"]):
            self.issues.append("Month should be numeric type")

    def _check_value_ranges(self) -> None:
        """Check that practice values are in valid range (0-3)."""
        for practice in self.practices:
            min_val = self.df[practice].min()
            max_val = self.df[practice].max()

            if min_val < 0 or max_val > 3:
                self.issues.append(f"Practice '{practice}' has values outside 0-3 range: [{min_val}, {max_val}]")

    def _check_missing_values(self) -> None:
        """Check for missing values."""
        missing_count = self.df.isnull().sum().sum()
        if missing_count > 0:
            self.issues.append(f"Found {missing_count} missing values in data")

    def get_missing_values_details(self) -> dict:
        """
        Get detailed breakdown of missing values by practice and month.

        Returns:
            dict: Detailed missing values information
        """
        result = {
            "total_missing": int(self.df.isnull().sum().sum()),
            "by_practice": {},
            "by_month": {},
            "practices_with_missing": [],
            "months_with_missing": [],
        }

        # Check missing values by practice
        for practice in self.practices:
            if practice in self.df.columns:
                missing_count = int(self.df[practice].isna().sum())
                if missing_count > 0:
                    total_rows = len(self.df)
                    pct = (missing_count / total_rows) * 100
                    result["by_practice"][practice] = {
                        "count": missing_count,
                        "percentage": round(pct, 1),
                        "by_month": {},
                    }
                    result["practices_with_missing"].append(practice)

                    # Check missing values by month for this practice
                    for month in sorted(self.df["Month"].unique()):
                        month_data = self.df[self.df["Month"] == month]
                        month_missing = int(month_data[practice].isna().sum())
                        month_total = len(month_data)
                        if month_missing > 0:
                            month_pct = (month_missing / month_total) * 100 if month_total > 0 else 0
                            result["by_practice"][practice]["by_month"][int(month)] = {
                                "count": month_missing,
                                "total": month_total,
                                "percentage": round(month_pct, 1),
                            }

        # Check missing values by month (across all practices)
        for month in sorted(self.df["Month"].unique()):
            month_data = self.df[self.df["Month"] == month]
            month_missing = int(month_data[self.practices].isnull().sum().sum())
            if month_missing > 0:
                month_total = len(month_data) * len(self.practices)
                month_pct = (month_missing / month_total) * 100 if month_total > 0 else 0
                result["by_month"][int(month)] = {
                    "count": month_missing,
                    "total": month_total,
                    "percentage": round(month_pct, 1),
                }
                result["months_with_missing"].append(int(month))

        # Sort practices by missing count (descending)
        result["practices_with_missing"].sort(key=lambda p: result["by_practice"][p]["count"], reverse=True)

        return result

    def _check_temporal_coverage(self) -> None:
        """Check that teams have multiple time periods."""
        team_counts = self.df["Team Name"].value_counts()
        min_periods = team_counts.min()

        if min_periods < 2:
            teams_with_one = team_counts[team_counts == 1].index.tolist()
            self.issues.append(
                f"Some teams ({len(teams_with_one)}) have only 1 time period. Need at least 2 for analysis."
            )

    def get_data_quality_report(self) -> dict:
        """
        Generate data quality report.

        Returns:
            dict: Detailed quality metrics
        """
        return {
            "total_rows": len(self.df),
            "total_columns": len(self.df.columns),
            "unique_teams": self.df["Team Name"].nunique(),
            "unique_months": self.df["Month"].nunique(),
            "missing_values": self.df.isnull().sum().sum(),
            "validation_issues": len(self.issues),
            "is_valid": len(self.issues) == 0,
        }

    def filter_high_missing_practices(self, practices: list, threshold: float = 90.0) -> tuple:
        """
        Filter out practices with missing values above a threshold percentage.

        Args:
            practices (list): List of practice names to filter
            threshold (float): Maximum percentage of missing values allowed (default: 90.0)

        Returns:
            tuple: (filtered_practices, excluded_practices)
                - filtered_practices: List of practices with missing values <= threshold
                - excluded_practices: List of practices that were excluded
        """
        missing_details = self.get_missing_values_details()
        total_rows = len(self.df)

        filtered_practices = []
        excluded_practices = []

        for practice in practices:
            if practice not in self.df.columns:
                # Practice column doesn't exist, exclude it
                excluded_practices.append(practice)
                continue

            # Check missing values for this practice
            if practice in missing_details["by_practice"]:
                missing_pct = missing_details["by_practice"][practice]["percentage"]
                if missing_pct > threshold:
                    excluded_practices.append(practice)
                else:
                    filtered_practices.append(practice)
            else:
                # No missing values, include it
                filtered_practices.append(practice)

        return filtered_practices, excluded_practices

    def get_missing_values_details_for_practices(self, practices: list) -> dict:
        """
        Get missing values details for a specific set of practices.
        This is useful after filtering practices to show only missing values
        for practices that are actually being used.

        Args:
            practices (list): List of practice names to include in the analysis

        Returns:
            dict: Missing values information filtered to only the specified practices
        """
        result = {
            "total_missing": 0,
            "by_practice": {},
            "by_month": {},
            "practices_with_missing": [],
            "months_with_missing": [],
        }

        # Check missing values by practice (only for specified practices)
        for practice in practices:
            if practice not in self.df.columns:
                continue

            missing_count = int(self.df[practice].isna().sum())
            if missing_count > 0:
                total_rows = len(self.df)
                pct = (missing_count / total_rows) * 100
                result["by_practice"][practice] = {"count": missing_count, "percentage": round(pct, 1), "by_month": {}}
                result["practices_with_missing"].append(practice)
                result["total_missing"] += missing_count

                # Check missing values by month for this practice
                for month in sorted(self.df["Month"].unique()):
                    month_data = self.df[self.df["Month"] == month]
                    month_missing = int(month_data[practice].isna().sum())
                    month_total = len(month_data)
                    if month_missing > 0:
                        month_pct = (month_missing / month_total) * 100 if month_total > 0 else 0
                        result["by_practice"][practice]["by_month"][int(month)] = {
                            "count": month_missing,
                            "total": month_total,
                            "percentage": round(month_pct, 1),
                        }

        # Check missing values by month (across specified practices only)
        for month in sorted(self.df["Month"].unique()):
            month_data = self.df[self.df["Month"] == month]
            # Only count missing values for the specified practices
            month_missing = int(month_data[practices].isnull().sum().sum())
            if month_missing > 0:
                month_total = len(month_data) * len(practices)
                month_pct = (month_missing / month_total) * 100 if month_total > 0 else 0
                result["by_month"][int(month)] = {
                    "count": month_missing,
                    "total": month_total,
                    "percentage": round(month_pct, 1),
                }
                if int(month) not in result["months_with_missing"]:
                    result["months_with_missing"].append(int(month))

        # Sort practices by missing count (descending)
        result["practices_with_missing"].sort(key=lambda p: result["by_practice"][p]["count"], reverse=True)

        return result
