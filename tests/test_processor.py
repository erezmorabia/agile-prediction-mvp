"""Tests for deterministic source-to-analysis data processing."""

import logging

import pandas as pd

from src.data import DataProcessor


def test_processor_retains_final_duplicate_occurrence_without_mutating_source(caplog):
    """Earlier duplicate keys are ignored explicitly and the raw frame stays intact."""
    source = pd.DataFrame(
        {
            "Team Name": ["Team1", "Team1", "Team1"],
            "Month": [202001, 202001, 202002],
            "Practice1": [0, 3, 2],
        }
    )
    original = source.copy(deep=True)
    processor = DataProcessor(source, ["Practice1"])

    with caplog.at_level(logging.WARNING, logger="src.data.processor"):
        processor.process()

    pd.testing.assert_frame_equal(source, original)
    assert processor.raw_observation_count == 3
    assert processor.unique_observation_count == 2
    assert processor.duplicate_rows_ignored == 1
    assert processor.duplicate_team_month_keys == [("Team1", 202001)]
    assert processor.get_team_history("Team1")[202001].tolist() == [1.0]
    assert "retaining the final source occurrence" in caplog.text
