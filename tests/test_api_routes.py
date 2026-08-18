"""
Tests for API routes.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from src.api.routes import create_routes
from src.api.service import APIService


class TestAPIRoutes:
    """Test API routes functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create mock APIService."""
        service = Mock(spec=APIService)
        service.get_all_teams = Mock(return_value=[
            {'name': 'Team1', 'num_months': 3, 'months': [202001, 202002, 202003],
             'first_month': 202001, 'last_month': 202003}
        ])
        service.get_teams_with_improvements = Mock(return_value=[])
        service.get_team_months = Mock(return_value=[202003])
        selected_policy = {
            'is_bootstrap': True,
            'peer_count': None,
            'min_similarity': None,
            'similarity_weight': 0.0,
            'sequence_weight': 0.0,
            'popularity_weight': 1.0,
            'popularity_recency_weight': 0.5,
            'completed_prior_months': [],
            'mean_prior_hit_rate': None,
        }
        service.get_recommendations = Mock(return_value={
            'team': 'Team1',
            'month': 202003,
            'recommendations': [],
            'validation': None,
            'practice_profile': None,
            'selected_policy': selected_policy,
            'no_similar_teams_found': False,
            'message': None,
        })
        service.run_backtest = Mock(return_value={
            'per_month_results': [],
            'primary': {
                'months_included': 0, 'total_predictions': 0, 'correct_predictions': 0,
                'overall_accuracy': None, 'random_baseline': None, 'improvement_gap': None,
                'improvement_factor': None, 'time_aware_popularity_accuracy': None,
                'blend_minus_popularity': None, 'overall_precision': None, 'overall_recall': None,
                'overall_mrr': None, 'random_precision': None, 'random_recall': None,
                'random_mrr': None, 'precision_gap': None, 'recall_gap': None, 'mrr_gap': None,
                'precision_improvement_factor': None, 'recall_improvement_factor': None,
                'mrr_improvement_factor': None, 'teams_tested': 0, 'avg_improvements_per_case': None,
            },
            'sensitivity': {
                'months_included': 0, 'total_predictions': 0, 'correct_predictions': 0,
                'overall_accuracy': None, 'random_baseline': None, 'improvement_gap': None,
                'improvement_factor': None, 'time_aware_popularity_accuracy': None,
                'blend_minus_popularity': None, 'overall_precision': None, 'overall_recall': None,
                'overall_mrr': None, 'random_precision': None, 'random_recall': None,
                'random_mrr': None, 'precision_gap': None, 'recall_gap': None, 'mrr_gap': None,
                'precision_improvement_factor': None, 'recall_improvement_factor': None,
                'mrr_improvement_factor': None, 'teams_tested': 0, 'avg_improvements_per_case': None,
            },
        })
        service.get_system_stats = Mock(return_value={
            'num_teams': 10,
            'num_practices': 30,
            'num_months': 5,
            'total_observations': 100,
            'months': [202001, 202002, 202003, 202004, 202005],
            'practices': ['Practice1', 'Practice2'],
        })
        service.get_improvement_sequences = Mock(return_value={
            'sequences': [],
            'stats': {}
        })
        return service

    @pytest.fixture
    def client(self, mock_service):
        """Create test client."""
        router = create_routes(mock_service)
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_get_teams(self, client, mock_service):
        """Test GET /api/teams endpoint."""
        response = client.get("/api/teams")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        mock_service.get_all_teams.assert_called_once()

    def test_get_teams_with_improvements(self, client, mock_service):
        """Test GET /api/teams/with-improvements endpoint."""
        response = client.get("/api/teams/with-improvements")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        mock_service.get_teams_with_improvements.assert_called_once()

    def test_get_team_months(self, client, mock_service):
        """Test GET /api/teams/{team_name}/months endpoint."""
        response = client.get("/api/teams/Team1/months")
        assert response.status_code == 200
        data = response.json()
        assert 'team' in data
        assert 'months' in data

    def test_get_team_months_not_found(self, client, mock_service):
        """Test GET /api/teams/{team_name}/months with unknown team."""
        mock_service.get_team_months = Mock(return_value=None)
        response = client.get("/api/teams/UnknownTeam/months")
        assert response.status_code == 404

    def test_post_recommendations(self, client, mock_service):
        """Test POST /api/recommendations endpoint."""
        request_data = {'team': 'Team1', 'month': 202003}
        response = client.post("/api/recommendations", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert 'team' in data
        assert 'recommendations' in data
        assert 'selected_policy' in data

    def test_post_recommendations_rejects_top_n_other_than_two(self, client, mock_service):
        """The primary flow always returns exactly two recommendations - a request for
        any other top_n must fail validation, not silently receive a different policy."""
        request_data = {'team': 'Team1', 'month': 202003, 'top_n': 3}
        response = client.post("/api/recommendations", json=request_data)
        assert response.status_code == 422

    def test_post_recommendations_rejects_unknown_fields(self, client, mock_service):
        """There is no k_similar (or any other tunable) on the request anymore."""
        request_data = {'team': 'Team1', 'month': 202003, 'k_similar': 10}
        response = client.post("/api/recommendations", json=request_data)
        assert response.status_code == 422

    def test_post_recommendations_error(self, client, mock_service):
        """Test POST /api/recommendations with error."""
        mock_service.get_recommendations = Mock(return_value={'error': 'Team not found'})
        request_data = {'team': 'UnknownTeam', 'month': 202003}
        response = client.post("/api/recommendations", json=request_data)
        assert response.status_code == 400

    def test_post_backtest(self, client, mock_service):
        """Test POST /api/backtest endpoint - takes no request body."""
        response = client.post("/api/backtest")
        assert response.status_code == 200
        data = response.json()
        assert 'primary' in data
        assert 'sensitivity' in data
        mock_service.run_backtest.assert_called_once_with()

    def test_get_system_stats(self, client, mock_service):
        """Test GET /api/stats endpoint."""
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert 'num_teams' in data

    def test_get_sequences(self, client, mock_service):
        """Test GET /api/sequences endpoint."""
        response = client.get("/api/sequences")
        assert response.status_code == 200
        data = response.json()
        assert 'sequences' in data

    def test_optimize_routes_removed(self, client):
        """The static all-history optimizer is removed entirely - none of its endpoints exist."""
        assert client.post("/api/optimize", json={}).status_code == 404
        assert client.post("/api/optimize/cancel").status_code == 404
        assert client.get("/api/optimize/latest").status_code == 404
        assert client.post("/api/backtest/cancel").status_code == 404
