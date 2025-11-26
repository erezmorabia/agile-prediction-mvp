"""
PracticeDefinitions: Load practice level definitions from Excel file.
"""

import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)


class PracticeDefinitionsLoader:
    """Load practice level definitions from Excel file."""

    def __init__(self, file_path: str = "data/raw/practice_level_definitions.xlsx"):
        """
        Initialize PracticeDefinitionsLoader.

        Args:
            file_path (str): Path to Excel file containing practice definitions
        """
        self.file_path = file_path
        self.definitions: dict[str, dict[int, str]] | None = None
        self.remarks: dict[str, str] | None = None

    def load(self) -> dict[str, dict[int, str]]:
        """
        Load practice definitions from Excel file.

        Returns:
            Dictionary mapping practice name to level definitions:
            {practice_name: {0: "definition", 1: "definition", 2: "definition", 3: "definition"}}

        Returns empty dict if file not found or error occurs.
        """
        if not os.path.exists(self.file_path):
            logger.warning(f"Practice definitions file not found: {self.file_path}")
            return {}

        try:
            df = pd.read_excel(self.file_path)

            # Expected columns: 'Level', 0, 1, 2, 3, 'Remarks'
            if "Level" not in df.columns:
                logger.error("Missing 'Level' column in practice definitions file")
                return {}

            definitions = {}
            remarks = {}

            for _, row in df.iterrows():
                practice_name = str(row["Level"]).strip()
                if not practice_name or pd.isna(practice_name):
                    continue

                # Extract level definitions (handle NaN values)
                practice_defs = {}
                for level in [0, 1, 2, 3]:
                    level_col = level  # Column name is integer 0, 1, 2, 3
                    if level_col in df.columns:
                        value = row[level_col]
                        if pd.notna(value):
                            practice_defs[level] = str(value).strip()

                if practice_defs:  # Only add if at least one level is defined
                    definitions[practice_name] = practice_defs

                # Extract remarks if available
                if "Remarks" in df.columns and pd.notna(row.get("Remarks")):
                    remarks[practice_name] = str(row["Remarks"]).strip()

            self.definitions = definitions
            self.remarks = remarks

            logger.info(f"Loaded {len(definitions)} practice definitions from {self.file_path}")
            return definitions

        except Exception as e:
            logger.error(f"Error loading practice definitions: {e}", exc_info=True)
            return {}

    def get_definitions(self) -> dict[str, dict[int, str]]:
        """
        Get practice definitions (loads if not already loaded).

        Returns:
            Dictionary mapping practice name to level definitions
        """
        if self.definitions is None:
            self.load()
        return self.definitions or {}

    def get_remarks(self) -> dict[str, str]:
        """
        Get practice remarks (loads if not already loaded).

        Returns:
            Dictionary mapping practice name to remarks
        """
        if self.remarks is None:
            self.load()
        return self.remarks or {}

    def get_practice_definition(self, practice_name: str) -> dict[int, str] | None:
        """
        Get level definitions for a specific practice.

        Args:
            practice_name (str): Name of the practice

        Returns:
            Dictionary mapping level (0-3) to definition, or None if not found
        """
        definitions = self.get_definitions()
        return definitions.get(practice_name)

    def get_practice_remark(self, practice_name: str) -> str | None:
        """
        Get remarks for a specific practice.

        Args:
            practice_name (str): Name of the practice

        Returns:
            Remarks string, or None if not found
        """
        remarks = self.get_remarks()
        return remarks.get(practice_name)
