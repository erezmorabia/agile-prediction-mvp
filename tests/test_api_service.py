"""
Tests for APIService class.
"""

import pytest
from unittest.mock import Mock, patch
from src.api.service import APIService
from src.ml.policy import BOOTSTRAP_POLICY, RecommendationResult, SelectedPolicy


class TestAPIService:
    """Test APIService functionality."""

    @pytest.fixture
    def mock_recommender(self):
        """Create mock RecommendationEngine, including its policy_engine."""
        recommender = Mock()
        recommender.practices = ['Practice1', 'Practice2', 'Practice3']
        recommender.policy_engine = Mock()
        recommender.policy_engine.prediction_months.return_value = [202003]
        recommender.policy_engine.baseline_month_for = Mock(
            side_effect=lambda team, month: 202002 if team == 'Team1' else None
        )
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
             patch('src.api.service.PracticeDefinitionsLoader'):
            service = APIService(mock_recommender, mock_processor)
            service.backtest_engine = Mock()
            service.practice_definitions = {}
            service.practice_remarks = {}
            service.missing_values_details = None
            return service

    def _recommend_result(self, practices=('Practice1', 'Practice2'), insufficient=False):
        selected_policy = SelectedPolicy(
            policy=BOOTSTRAP_POLICY, is_bootstrap=True, completed_prior_months=(), mean_prior_hit_rate=None
        )
        scores = {p: 0.8 - 0.1 * i for i, p in enumerate(practices)}
        levels = {p: 0.33 for p in practices}
        return RecommendationResult(
            team='Team1',
            prediction_month=202003,
            baseline_month=202002,
            practices=practices if not insufficient else (),
            scores=scores if not insufficient else {},
            current_levels=levels if not insufficient else {},
            selected_policy=selected_policy,
            no_similar_teams_found=False,
            insufficient_practices=insufficient,
        )

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

    def test_get_teams_with_improvements(self, api_service, mock_processor, mock_recommender):
        """Test get_teams_with_improvements returns teams with improvements."""
        teams_with_improvements = api_service.get_teams_with_improvements()

        assert isinstance(teams_with_improvements, list)

        # Check structure
        for team_info in teams_with_improvements:
            assert 'team' in team_info
            assert 'month' in team_info
            assert 'num_improvements' in team_info
            assert 'improvements' in team_info

    def test_get_team_months(self, api_service, mock_processor, mock_recommender):
        """Test get_team_months returns available months for team."""
        months = api_service.get_team_months('Team1')

        assert isinstance(months, list)
        # Team1's only valid prediction month (per the mocked policy_engine) is 202003.
        assert months == [202003]

    def test_get_team_months_team_not_found(self, api_service, mock_processor):
        """Test get_team_months returns None for unknown team."""
        mock_processor.get_all_teams = Mock(return_value=['Team1'])

        months = api_service.get_team_months('UnknownTeam')

        assert months is None

    def test_get_recommendations_basic(self, api_service, mock_recommender, mock_processor):
        """Test get_recommendations returns recommendations."""
        mock_recommender.recommend = Mock(return_value=self._recommend_result())
        mock_recommender.get_recommendation_explanation = Mock(return_value={
            'similar_teams_improved': 2,
            'total_similar_teams_checked': 5,
            'has_sequence_boost': True,
            'similar_teams_list': [],
            'no_similar_teams_found': False,
        })

        result = api_service.get_recommendations('Team1', 202003)

        assert isinstance(result, dict)
        assert 'team' in result
        assert 'month' in result
        assert 'recommendations' in result
        assert 'validation' in result
        assert 'practice_profile' in result
        assert 'selected_policy' in result
        assert 'no_similar_teams_found' in result
        assert 'message' in result

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

    def test_get_recommendations_insufficient_practices(self, api_service, mock_recommender, mock_processor):
        """Test get_recommendations surfaces the message when the team has fewer than
        two candidate practices - a valid outcome, not an error."""
        mock_recommender.recommend = Mock(return_value=self._recommend_result(insufficient=True))

        result = api_service.get_recommendations('Team1', 202003)

        assert result['recommendations'] == []
        assert result['message'] is not None
        assert 'fewer than two practices' in result['message']

    def test_run_backtest(self, api_service):
        """Test run_backtest runs backtest and returns results."""
        mock_result = {
            'status': 'success',
            'per_month_results': [],
            'primary': {'months_included': 0, 'overall_accuracy': None},
            'sensitivity': {'months_included': 0, 'overall_accuracy': None},
        }

        api_service.backtest_engine.run_backtest = Mock(return_value=mock_result)

        result = api_service.run_backtest()

        assert isinstance(result, dict)
        assert 'status' not in result  # stripped before returning
        assert 'primary' in result
        assert 'sensitivity' in result
        api_service.backtest_engine.run_backtest.assert_called_once_with()

    def test_run_backtest_takes_no_parameters(self):
        """run_backtest() accepts no model parameters - the monthly policy is the sole
        configuration authority."""
        import inspect

        signature = inspect.signature(APIService.run_backtest)
        assert list(signature.parameters) == ["self"]

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
        mock_recommender.sequence_mapper.learn_sequences = Mock()
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
        mock_recommender.sequence_mapper.learn_sequences.assert_called_once()

    def test_get_recommendations_formats_correctly(self, api_service, mock_recommender, mock_processor):
        """Test get_recommendations formats recommendations correctly."""
        mock_recommender.recommend = Mock(return_value=self._recommend_result())
        mock_recommender.get_recommendation_explanation = Mock(return_value={
            'similar_teams_improved': 2,
            'total_similar_teams_checked': 5,
            'has_sequence_boost': True,
            'similar_teams_list': [],
            'no_similar_teams_found': False,
        })

        result = api_service.get_recommendations('Team1', 202003)

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
            assert 'improved_in_months' in rec

    def test_get_recommendations_validation_summary(self, api_service, mock_recommender, mock_processor):
        """Test get_recommendations includes validation summary."""
        mock_recommender.recommend = Mock(return_value=self._recommend_result(practices=('Practice1',)))
        mock_recommender.get_recommendation_explanation = Mock(return_value={
            'similar_teams_improved': 2,
            'total_similar_teams_checked': 5,
            'has_sequence_boost': True,
            'similar_teams_list': [],
            'no_similar_teams_found': False,
        })

        result = api_service.get_recommendations('Team1', 202003)

        assert 'validation' in result
        validation = result['validation']
        assert 'next_month' in validation
        assert 'actual_improvements' in validation
        assert 'validated_count' in validation
        assert 'total_recommendations' in validation
        assert 'accuracy' in validation
