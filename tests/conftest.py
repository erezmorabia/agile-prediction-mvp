"""
Shared pytest fixtures for test suite.
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data import DataLoader, DataProcessor, DataValidator
from src.ml import SimilarityEngine, SequenceMapper, RecommendationEngine


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for testing."""
    data = {
        'Team Name': ['Team1', 'Team1', 'Team2', 'Team2', 'Team3', 'Team3'],
        'Month': [202001, 202002, 202001, 202002, 202001, 202002],
        'Practice1': [1, 2, 1, 2, 0, 1],
        'Practice2': [0, 1, 0, 1, 1, 2],
        'Practice3': [2, 3, 1, 2, 2, 2]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_dataframe_with_missing():
    """Create sample DataFrame with missing values."""
    data = {
        'Team Name': ['Team1', 'Team1', 'Team2', 'Team2'],
        'Month': [202001, 202002, 202001, 202002],
        'Practice1': [1, 2, np.nan, 2],
        'Practice2': [0, np.nan, 0, 1],
        'Practice3': [2, 3, 1, np.nan]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_dataframe_invalid():
    """Create sample DataFrame with invalid data."""
    data = {
        'Team Name': ['Team1', 'Team1'],
        'Month': [202001, 202002],
        'Practice1': [1, 5],  # Invalid: > 3
        'Practice2': [-1, 1],  # Invalid: < 0
        'Practice3': [2, 3]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_practices():
    """Sample practice list."""
    return ['Practice1', 'Practice2', 'Practice3']


@pytest.fixture
def sample_processor(sample_dataframe, sample_practices):
    """Create a DataProcessor with sample data."""
    processor = DataProcessor(sample_dataframe, sample_practices)
    processor.process()
    return processor


@pytest.fixture
def sample_validator(sample_dataframe, sample_practices):
    """Create a DataValidator with sample data."""
    return DataValidator(sample_dataframe, sample_practices)


@pytest.fixture
def sample_similarity_engine(sample_processor):
    """Create a SimilarityEngine with processed data."""
    return SimilarityEngine(sample_processor)


@pytest.fixture
def sample_sequence_mapper(sample_processor, sample_practices):
    """Create a SequenceMapper with processed data."""
    mapper = SequenceMapper(sample_processor, sample_practices)
    mapper.learn_sequences()
    return mapper


@pytest.fixture
def sample_recommender(sample_similarity_engine, sample_sequence_mapper, sample_practices):
    """Create a RecommendationEngine with all dependencies."""
    return RecommendationEngine(sample_similarity_engine, sample_sequence_mapper, sample_practices)


@pytest.fixture
def empty_dataframe():
    """Create empty DataFrame."""
    return pd.DataFrame(columns=['Team Name', 'Month', 'Practice1'])


@pytest.fixture
def single_team_dataframe():
    """Create DataFrame with single team."""
    data = {
        'Team Name': ['Team1', 'Team1'],
        'Month': [202001, 202002],
        'Practice1': [1, 2],
        'Practice2': [0, 1]
    }
    return pd.DataFrame(data)


@pytest.fixture
def minimal_dataframe():
    """Create minimal valid DataFrame."""
    data = {
        'Team Name': ['Team1', 'Team1', 'Team2', 'Team2'],
        'Month': [202001, 202002, 202001, 202002],
        'Practice1': [1, 2, 1, 2]
    }
    return pd.DataFrame(data)

