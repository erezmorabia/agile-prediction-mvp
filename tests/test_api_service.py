"""
Tests for APIService class.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.api.service import APIService


class TestAPIService:
    """Test APIService functionality."""
    
    @pytest.fixture
    def mock_recommender(self):
        """Create mock RecommendationEngine."""
        recommender = Mock()
        recommender.practices = ['Practice1', 'Practice2', 'Practice3']
        return recommender
    
    @pytest.fixture
    def mock_processor(self):
        """Create mock DataProcessor."""
        processor = Mock()
        processor.get_all_teams = Mock(return_value=['Team1', 'Team2'])
        processor.get_all_months = Mock(return_value=[202001, 202002, 202003])
        processor.get_team_history = Mock(return_value={
            202001: [0.33, 0.33, 0.33],
            202002: [0.67, 0.33, 0.33],
            202003: [0.67, 0.67, 0.33]
        })
        return processor
    
    @pytest.fixture
    def api_service(self, mock_recommender, mock_processor):
        """Create APIService with mocked dependencies."""
        with patch('src.api.service.BacktestEngine'), \
             patch('src.api.service.OptimizationEngine'), \
             patch('src.api.service.PracticeDefinitionsLoader'):
            service = APIService(mock_recommender, mock_processor)
            service.backtest_engine = Mock()
            service.optimizer_engine = Mock()
            service.practice_definitions = {}
            service.practice_remarks = {}
            service.missing_values_details = None
            return service
    
    def test_get_all_teams(self, api_service, mock_processor):
        """Test get_all_teams returns team information."""
        teams = api_service.get_all_teams()
        
        assert isinstance(teams, list)
        assert len(teams) > 0
        
        # Check structure
        for team_info in teams:
            assert 'name' in team_info
            assert 'num_months' in team_info
            assert 'months' in team_info
            assert 'first_month' in team_info
            assert 'last_month' in team_info
    
    def test_get_teams_with_improvements(self, api_service, mock_processor):
        """Test get_teams_with_improvements returns teams with improvements."""
        teams_with_improvements = api_service.get_teams_with_improvements()
        
        assert isinstance(teams_with_improvements, list)
        
        # Check structure
        for team_info in teams_with_improvements:
            assert 'team' in team_info
            assert 'month' in team_info
            assert 'num_improvements' in team_info
            assert 'improvements' in team_info
    
    def test_get_team_months(self, api_service, mock_processor):
        """Test get_team_months returns available months for team."""
        months = api_service.get_team_months('Team1')
        
        assert isinstance(months, list)
        # Should only include months 3+ (filtering first 2 months)
        # Since we have 3 months, should return at least month 3
    
    def test_get_team_months_team_not_found(self, api_service, mock_processor):
        """Test get_team_months returns None for unknown team."""
        mock_processor.get_all_teams = Mock(return_value=['Team1'])
        
        months = api_service.get_team_months('UnknownTeam')
        
        assert months is None
    
    def test_get_recommendations_basic(self, api_service, mock_recommender, mock_processor):
        """Test get_recommendations returns recommendations."""
        mock_recommender.recommend = Mock(return_value=[
            ('Practice1', 0.8, 0.33),
            ('Practice2', 0.7, 0.33)
        ])
        mock_recommender.get_recommendation_explanation = Mock(return_value={
            'similar_teams_improved': 2,
            'total_similar_teams_checked': 5,
            'has_sequence_boost': True,
            'similar_teams_list': []
        })
        
        result = api_service.get_recommendations('Team1', 202003, top_n=2)
        
        assert isinstance(result, dict)
        assert 'team' in result
        assert 'month' in result
        assert 'recommendations' in result
        assert 'validation' in result
        assert 'practice_profile' in result
        
        assert len(result['recommendations']) == 2
    
    def test_get_recommendations_team_not_found(self, api_service, mock_processor):
        """Test get_recommendations returns error for unknown team."""
        mock_processor.get_all_teams = Mock(return_value=['Team1'])
        
        result = api_service.get_recommendations('UnknownTeam', 202003)
        
        assert 'error' in result
        assert 'not found' in result['error'].lower()
    
    def test_get_recommendations_month_not_found(self, api_service, mock_processor):
        """Test get_recommendations returns error when team has no data for month."""
        result = api_service.get_recommendations('Team1', 99999999)
        
        assert 'error' in result
        assert 'no data' in result['error'].lower() or 'not found' in result['error'].lower()
    
    def test_run_backtest(self, api_service):
        """Test run_backtest runs backtest and returns results."""
        mock_result = {
            'total_predictions': 100,
            'correct_predictions': 70,
            'overall_accuracy': 0.7,
            'random_baseline': 0.1,
            'improvement_gap': 0.6,
            'improvement_factor': 7.0,
            'per_month_results': [],
            'teams_tested': 10,
            'avg_improvements_per_case': 2.5
        }
        
        api_service.backtest_engine.run_backtest = Mock(return_value=mock_result)
        
        result = api_service.run_backtest()
        
        assert isinstance(result, dict)
        assert 'total_predictions' in result
        assert 'overall_accuracy' in result
        assert 'random_baseline' in result
    
    def test_run_backtest_with_config(self, api_service):
        """Test run_backtest accepts configuration."""
        mock_result = {
            'total_predictions': 100,
            'correct_predictions': 70,
            'overall_accuracy': 0.7,
            'random_baseline': 0.1,
            'improvement_gap': 0.6,
            'improvement_factor': 7.0,
            'per_month_results': [],
            'teams_tested': 10,
            'avg_improvements_per_case': 2.5
        }
        
        api_service.backtest_engine.run_backtest = Mock(return_value=mock_result)
        
        config = {
            'top_n': 3,
            'k_similar': 10,
            'similarity_weight': 0.7
        }
        
        result = api_service.run_backtest(config=config)
        
        assert isinstance(result, dict)
        api_service.backtest_engine.run_backtest.assert_called_once()
    
    def test_find_optimal_config(self, api_service):
        """Test find_optimal_config runs optimization."""
        mock_result = {
            'optimal_config': {'top_n': 3},
            'model_accuracy': 0.75,
            'random_baseline': 0.1,
            'improvement_gap': 0.65,
            'improvement_factor': 7.5,
            'total_predictions': 100,
            'correct_predictions': 75,
            'total_combinations_tested': 10,
            'total_combinations_available': 20,
            'valid_combinations': 5,
            'all_results': [],
            'early_stopped': False,
            'cancelled': False
        }
        
        api_service.optimizer_engine.find_optimal_config = Mock(return_value=mock_result)
        
        result = api_service.find_optimal_config(min_accuracy=0.5)
        
        assert isinstance(result, dict)
        assert 'optimal_config' in result
        assert 'model_accuracy' in result
    
    def test_cancel_optimization(self, api_service):
        """Test cancel_optimization cancels optimization."""
        api_service.optimizer_engine.cancel = Mock()
        
        api_service.cancel_optimization()
        
        api_service.optimizer_engine.cancel.assert_called_once()
    
    def test_get_system_stats(self, api_service, mock_recommender, mock_processor):
        """Test get_system_stats returns system statistics."""
        stats = api_service.get_system_stats()
        
        assert isinstance(stats, dict)
        assert 'num_teams' in stats
        assert 'num_practices' in stats
        assert 'num_months' in stats
        assert 'total_observations' in stats
        assert 'months' in stats
        assert 'practices' in stats
    
    def test_get_improvement_sequences(self, api_service, mock_recommender):
        """Test get_improvement_sequences returns sequences."""
        mock_recommender.sequence_mapper = Mock()
        mock_recommender.sequence_mapper.get_all_sequences = Mock(return_value=[
            ('Practice1', 'Practice2', 5, 0.5),
            ('Practice2', 'Practice3', 3, 0.3)
        ])
        mock_recommender.sequence_mapper.get_sequence_stats = Mock(return_value={
            'num_transition_types': 2,
            'total_transitions': 8,
            'practices_that_improved': 3
        })
        
        result = api_service.get_improvement_sequences()
        
        assert isinstance(result, dict)
        assert 'sequences' in result
        assert 'grouped_sequences' in result
        assert 'stats' in result
        assert 'total_sequences' in result
    
    def test_get_recommendations_formats_correctly(self, api_service, mock_recommender, mock_processor):
        """Test get_recommendations formats recommendations correctly."""
        mock_recommender.recommend = Mock(return_value=[
            ('Practice1', 0.8, 0.33),
            ('Practice2', 0.7, 0.67)
        ])
        mock_recommender.get_recommendation_explanation = Mock(return_value={
            'similar_teams_improved': 2,
            'total_similar_teams_checked': 5,
            'has_sequence_boost': True,
            'similar_teams_list': []
        })
        
        result = api_service.get_recommendations('Team1', 202003, top_n=2)
        
        # Check recommendation format
        for rec in result['recommendations']:
            assert 'practice' in rec
            assert 'score' in rec
            assert 'current_level' in rec
            assert 'original_level' in rec
            assert 'level_num' in rec
            assert 'level_description' in rec
            assert 'level_display' in rec
            assert 'why' in rec
            assert 'similar_teams' in rec
            assert 'validated' in rec
    
    def test_get_recommendations_validation_summary(self, api_service, mock_recommender, mock_processor):
        """Test get_recommendations includes validation summary."""
        mock_recommender.recommend = Mock(return_value=[
            ('Practice1', 0.8, 0.33)
        ])
        mock_recommender.get_recommendation_explanation = Mock(return_value={
            'similar_teams_improved': 2,
            'total_similar_teams_checked': 5,
            'has_sequence_boost': True,
            'similar_teams_list': []
        })
        
        result = api_service.get_recommendations('Team1', 202003, top_n=1)
        
        assert 'validation' in result
        validation = result['validation']
        assert 'next_month' in validation
        assert 'actual_improvements' in validation
        assert 'validated_count' in validation
        assert 'total_recommendations' in validation
        assert 'accuracy' in validation

