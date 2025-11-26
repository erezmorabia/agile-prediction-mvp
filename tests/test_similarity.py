"""
Extended tests for SimilarityEngine class.
"""

import pytest
import numpy as np
from src.ml.similarity import SimilarityEngine


class TestSimilarityEngineExtended:
    """Extended tests for SimilarityEngine functionality."""
    
    def test_find_similar_teams_basic(self, sample_similarity_engine, sample_processor):
        """Test find_similar_teams returns similar teams."""
        engine = sample_similarity_engine
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) < 2 or len(months) < 2:
            pytest.skip("Need at least 2 teams and 2 months")
        
        target_team = teams[0]
        target_month = months[-1]  # Use last month
        
        # Check if target team has data for target month
        history = sample_processor.get_team_history(target_team)
        if target_month not in history:
            pytest.skip(f"Team {target_team} has no data for month {target_month}")
        
        # Check if there are past months
        past_months = [m for m in months if m < target_month]
        if not past_months:
            pytest.skip(f"No past months available before {target_month}")
        
        similar_teams = engine.find_similar_teams(target_team, target_month, k=3)
        
        assert isinstance(similar_teams, list)
        assert len(similar_teams) <= 3
        assert len(similar_teams) > 0
        
        # Check format: (team_name, similarity_score, historical_month)
        for team_info in similar_teams:
            assert len(team_info) == 3
            team_name, similarity_score, historical_month = team_info
            assert isinstance(team_name, str)
            assert isinstance(similarity_score, float)
            assert isinstance(historical_month, int)
            assert 0.0 <= similarity_score <= 1.0
            assert historical_month < target_month
    
    def test_find_similar_teams_k_parameter(self, sample_similarity_engine, sample_processor):
        """Test find_similar_teams respects k parameter."""
        engine = sample_similarity_engine
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) < 5 or len(months) < 2:
            pytest.skip("Need at least 5 teams and 2 months")
        
        target_team = teams[0]
        target_month = months[-1]
        
        history = sample_processor.get_team_history(target_team)
        if target_month not in history:
            pytest.skip(f"Team {target_team} has no data for month {target_month}")
        
        # Test with different k values
        for k in [1, 2, 5]:
            similar_teams = engine.find_similar_teams(target_team, target_month, k=k)
            assert len(similar_teams) <= k
    
    def test_find_similar_teams_min_similarity_threshold(self, sample_similarity_engine, sample_processor):
        """Test find_similar_teams filters by min_similarity threshold."""
        engine = sample_similarity_engine
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) < 2 or len(months) < 2:
            pytest.skip("Need at least 2 teams and 2 months")
        
        target_team = teams[0]
        target_month = months[-1]
        
        history = sample_processor.get_team_history(target_team)
        if target_month not in history:
            pytest.skip(f"Team {target_team} has no data for month {target_month}")
        
        # Test with high threshold
        similar_teams = engine.find_similar_teams(
            target_team, target_month, k=10, min_similarity=0.9
        )
        
        # All returned teams should have similarity >= 0.9
        for team_name, similarity_score, historical_month in similar_teams:
            assert similarity_score >= 0.9
    
    def test_find_similar_teams_excludes_target(self, sample_similarity_engine, sample_processor):
        """Test find_similar_teams excludes target team."""
        engine = sample_similarity_engine
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) < 2 or len(months) < 2:
            pytest.skip("Need at least 2 teams and 2 months")
        
        target_team = teams[0]
        target_month = months[-1]
        
        history = sample_processor.get_team_history(target_team)
        if target_month not in history:
            pytest.skip(f"Team {target_team} has no data for month {target_month}")
        
        similar_teams = engine.find_similar_teams(target_team, target_month, k=10)
        
        # Target team should not be in results
        for team_name, similarity_score, historical_month in similar_teams:
            assert team_name != target_team
    
    def test_find_similar_teams_deduplicates(self, sample_similarity_engine, sample_processor):
        """Test find_similar_teams deduplicates teams (one entry per team)."""
        engine = sample_similarity_engine
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) < 2 or len(months) < 2:
            pytest.skip("Need at least 2 teams and 2 months")
        
        target_team = teams[0]
        target_month = months[-1]
        
        history = sample_processor.get_team_history(target_team)
        if target_month not in history:
            pytest.skip(f"Team {target_team} has no data for month {target_month}")
        
        similar_teams = engine.find_similar_teams(target_team, target_month, k=10)
        
        # Check that each team appears only once
        team_names = [team_info[0] for team_info in similar_teams]
        assert len(team_names) == len(set(team_names))
    
    def test_find_similar_teams_sorted_by_similarity(self, sample_similarity_engine, sample_processor):
        """Test find_similar_teams returns teams sorted by similarity (descending)."""
        engine = sample_similarity_engine
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) < 3 or len(months) < 2:
            pytest.skip("Need at least 3 teams and 2 months")
        
        target_team = teams[0]
        target_month = months[-1]
        
        history = sample_processor.get_team_history(target_team)
        if target_month not in history:
            pytest.skip(f"Team {target_team} has no data for month {target_month}")
        
        similar_teams = engine.find_similar_teams(target_team, target_month, k=5)
        
        if len(similar_teams) > 1:
            # Check that similarities are in descending order
            similarities = [team_info[1] for team_info in similar_teams]
            assert similarities == sorted(similarities, reverse=True)
    
    def test_find_similar_teams_team_not_found(self, sample_similarity_engine, sample_processor):
        """Test find_similar_teams raises error for unknown team."""
        engine = sample_similarity_engine
        months = sample_processor.get_all_months()
        
        if len(months) == 0:
            pytest.skip("No months available")
        
        target_month = months[0]
        
        with pytest.raises(ValueError):
            engine.find_similar_teams("UnknownTeam", target_month, k=5)
    
    def test_find_similar_teams_month_not_found(self, sample_similarity_engine, sample_processor):
        """Test find_similar_teams raises error when team has no data for month."""
        engine = sample_similarity_engine
        teams = sample_processor.get_all_teams()
        
        if len(teams) == 0:
            pytest.skip("No teams available")
        
        target_team = teams[0]
        invalid_month = 99999999  # Non-existent month
        
        with pytest.raises(ValueError):
            engine.find_similar_teams(target_team, invalid_month, k=5)
    
    def test_find_similar_teams_no_past_months(self, sample_similarity_engine, sample_processor):
        """Test find_similar_teams raises error when no past months available."""
        engine = sample_similarity_engine
        teams = sample_processor.get_all_teams()
        months = sample_processor.get_all_months()
        
        if len(teams) == 0 or len(months) == 0:
            pytest.skip("Need teams and months")
        
        target_team = teams[0]
        first_month = min(months)  # First month has no past months
        
        history = sample_processor.get_team_history(target_team)
        if first_month not in history:
            pytest.skip(f"Team {target_team} has no data for first month")
        
        with pytest.raises(ValueError, match="No past months"):
            engine.find_similar_teams(target_team, first_month, k=5)
    
    def test_get_similarity_stats_not_built(self, sample_similarity_engine):
        """Test get_similarity_stats returns status when matrix not built."""
        engine = sample_similarity_engine
        stats = engine.get_similarity_stats()
        
        assert isinstance(stats, dict)
        assert stats.get('status') == 'not_built'
    
    def test_get_similarity_stats_after_build(self, sample_similarity_engine, sample_processor):
        """Test get_similarity_stats after building matrix."""
        engine = sample_similarity_engine
        months = sample_processor.get_all_months()
        
        if len(months) == 0:
            pytest.skip("No months available")
        
        target_month = months[0]
        engine.build_similarity_matrix(target_month)
        
        stats = engine.get_similarity_stats()
        
        assert isinstance(stats, dict)
        assert 'status' not in stats or stats.get('status') != 'not_built'
        assert 'num_teams' in stats
        assert 'mean_similarity' in stats
        assert 'std_similarity' in stats
        assert 'min_similarity' in stats
        assert 'max_similarity' in stats
        
        # Check that stats are valid
        assert stats['num_teams'] > 0
        assert 0.0 <= stats['mean_similarity'] <= 1.0
        assert stats['min_similarity'] >= 0.0
        assert stats['max_similarity'] <= 1.0
    
    def test_build_similarity_matrix_no_data(self, sample_similarity_engine):
        """Test build_similarity_matrix raises error when no data available."""
        engine = sample_similarity_engine
        invalid_month = 99999999
        
        with pytest.raises(ValueError, match="No data available"):
            engine.build_similarity_matrix(invalid_month)
    
    def test_build_similarity_matrix_diagonal_ones(self, sample_similarity_engine, sample_processor):
        """Test similarity matrix has ones on diagonal (self-similarity)."""
        engine = sample_similarity_engine
        months = sample_processor.get_all_months()
        
        if len(months) == 0:
            pytest.skip("No months available")
        
        target_month = months[0]
        matrix = engine.build_similarity_matrix(target_month)
        
        # Diagonal should be 1.0 (self-similarity)
        diagonal = np.diag(matrix)
        np.testing.assert_array_almost_equal(diagonal, np.ones(len(diagonal)))
    
    def test_build_similarity_matrix_symmetric(self, sample_similarity_engine, sample_processor):
        """Test similarity matrix is symmetric."""
        engine = sample_similarity_engine
        months = sample_processor.get_all_months()
        
        if len(months) == 0:
            pytest.skip("No months available")
        
        target_month = months[0]
        matrix = engine.build_similarity_matrix(target_month)
        
        # Matrix should be symmetric (cosine similarity is symmetric)
        np.testing.assert_array_almost_equal(matrix, matrix.T)
    
    def test_build_similarity_matrix_valid_range(self, sample_similarity_engine, sample_processor):
        """Test similarity matrix values are in valid range [0, 1]."""
        engine = sample_similarity_engine
        months = sample_processor.get_all_months()
        
        if len(months) == 0:
            pytest.skip("No months available")
        
        target_month = months[0]
        matrix = engine.build_similarity_matrix(target_month)
        
        # All values should be between 0 and 1
        assert np.all(matrix >= 0)
        assert np.all(matrix <= 1)

