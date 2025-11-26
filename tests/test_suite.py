"""
Comprehensive test suite for the Agile Prediction MVP.

Run tests with: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import pandas as pd
import numpy as np
from src.data import DataLoader, DataProcessor, DataValidator
from src.ml import SimilarityEngine, SequenceMapper, RecommendationEngine


class TestDataLoading:
    """Test data loading functionality."""
    
    def test_data_loader_initialization(self):
        """Test DataLoader can be initialized."""
        excel_path = 'data/raw/20250204_Cleaned_Dataset.xlsx'
        if os.path.exists(excel_path):
            loader = DataLoader(excel_path)
            assert loader.file_path == excel_path
            assert loader.df is None
    
    def test_data_loader_loads_file(self):
        """Test DataLoader can load Excel file."""
        excel_path = 'data/raw/20250204_Cleaned_Dataset.xlsx'
        if os.path.exists(excel_path):
            loader = DataLoader(excel_path)
            df = loader.load()
            assert df is not None
            assert len(df) > 0
            assert loader.teams is not None
            assert len(loader.teams) > 0


class TestDataProcessing:
    """Test data processing functionality."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        excel_path = 'data/raw/20250204_Cleaned_Dataset.xlsx'
        if os.path.exists(excel_path):
            loader = DataLoader(excel_path)
            df = loader.load()
            practices = loader.practices
            return df, practices
        return None, None
    
    def test_processor_normalizes_data(self, sample_data):
        """Test that processor normalizes values."""
        df, practices = sample_data
        if df is None:
            pytest.skip("Sample data not available")
        
        processor = DataProcessor(df, practices)
        processor.process()
        
        # Check that values are in 0-1 range
        for team_history in processor.team_histories.values():
            for vector in team_history.values():
                assert np.all(vector >= 0), "Values should be >= 0"
                assert np.all(vector <= 1), "Values should be <= 1"
    
    def test_processor_builds_histories(self, sample_data):
        """Test that processor builds team histories."""
        df, practices = sample_data
        if df is None:
            pytest.skip("Sample data not available")
        
        processor = DataProcessor(df, practices)
        processor.process()
        
        teams = processor.get_all_teams()
        assert len(teams) > 0
        
        for team in teams[:3]:
            history = processor.get_team_history(team)
            assert isinstance(history, dict)
            assert len(history) > 0


class TestSimilarityEngine:
    """Test similarity calculation."""
    
    @pytest.fixture
    def engine_with_data(self):
        """Create similarity engine with data."""
        excel_path = 'data/raw/20250204_Cleaned_Dataset.xlsx'
        if os.path.exists(excel_path):
            loader = DataLoader(excel_path)
            df = loader.load()
            practices = loader.practices
            processor = DataProcessor(df, practices)
            processor.process()
            engine = SimilarityEngine(processor)
            return engine, processor
        return None, None
    
    def test_similarity_engine_builds_matrix(self, engine_with_data):
        """Test similarity matrix building."""
        engine, processor = engine_with_data
        if engine is None:
            pytest.skip("Engine not available")
        
        months = processor.get_all_months()
        if len(months) == 0:
            pytest.skip("No months available")
        
        matrix = engine.build_similarity_matrix(months[0])
        assert matrix is not None
        assert len(matrix) > 0
        
        # Check that diagonal is 1.0 (self-similarity)
        np.testing.assert_array_almost_equal(
            np.diag(matrix), np.ones(len(matrix))
        )


class TestSequenceMapper:
    """Test sequence mapping."""
    
    @pytest.fixture
    def mapper_with_data(self):
        """Create sequence mapper with data."""
        excel_path = 'data/raw/20250204_Cleaned_Dataset.xlsx'
        if os.path.exists(excel_path):
            loader = DataLoader(excel_path)
            df = loader.load()
            practices = loader.practices
            processor = DataProcessor(df, practices)
            processor.process()
            mapper = SequenceMapper(processor, practices)
            return mapper, processor, practices
        return None, None, None
    
    def test_sequence_mapper_learns_patterns(self, mapper_with_data):
        """Test sequence learning."""
        mapper, processor, practices = mapper_with_data
        if mapper is None:
            pytest.skip("Mapper not available")
        
        mapper.learn_sequences()
        assert mapper.learned
        assert len(mapper.transition_matrix) > 0 or len(mapper.practice_improvement_freq) > 0


class TestRecommendations:
    """Test recommendation engine."""
    
    @pytest.fixture
    def recommender_with_data(self):
        """Create complete recommendation engine."""
        excel_path = 'data/raw/20250204_Cleaned_Dataset.xlsx'
        if os.path.exists(excel_path):
            loader = DataLoader(excel_path)
            df = loader.load()
            practices = loader.practices
            processor = DataProcessor(df, practices)
            processor.process()
            
            similarity_engine = SimilarityEngine(processor)
            sequence_mapper = SequenceMapper(processor, practices)
            sequence_mapper.learn_sequences()
            
            recommender = RecommendationEngine(similarity_engine, sequence_mapper, practices)
            return recommender, processor, practices
        return None, None, None
    
    def test_recommender_makes_recommendations(self, recommender_with_data):
        """Test that recommender can make recommendations."""
        recommender, processor, practices = recommender_with_data
        if recommender is None:
            pytest.skip("Recommender not available")
        
        teams = processor.get_all_teams()
        months = processor.get_all_months()
        
        if len(teams) == 0 or len(months) < 2:
            pytest.skip("Not enough data")
        
        team = teams[0]
        
        # Get a month that has data for this team
        history = processor.get_team_history(team)
        team_months = sorted(history.keys())
        
        if len(team_months) < 2:
            pytest.skip(f"Team {team} doesn't have enough months")
        
        current_month = team_months[0]
        
        recommendations = recommender.recommend(
            team, current_month, top_n=3, k_similar=5
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 3


def run_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("RUNNING MVP TEST SUITE")
    print("="*60)
    
    # Run with pytest if available
    try:
        pytest.main([__file__, '-v', '--tb=short'])
    except:
        print("Note: Install pytest for full test functionality")
        print("  pip install pytest")


if __name__ == '__main__':
    run_tests()
