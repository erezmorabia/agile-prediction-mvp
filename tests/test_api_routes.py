"""
Tests for API routes.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock, patch
from src.api.routes import create_routes
from src.api.service import APIService


class TestAPIRoutes:
    """Test API routes functionality."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock APIService."""
        service = Mock(spec=APIService)
        service.get_all_teams = Mock(return_value=[
            {'name': 'Team1', 'num_months': 3, 'months': [202001, 202002, 202003]}
        ])
        service.get_teams_with_improvements = Mock(return_value=[])
        service.get_team_months = Mock(return_value=[202003])
        service.get_recommendations = Mock(return_value={
            'team': 'Team1',
            'month': 202003,
            'recommendations': []
        })
        service.run_backtest = Mock(return_value={
            'total_predictions': 100,
            'overall_accuracy': 0.7
        })
        service.get_system_stats = Mock(return_value={
            'num_teams': 10,
            'num_practices': 30
        })
        service.get_improvement_sequences = Mock(return_value={
            'sequences': [],
            'stats': {}
        })
        service.find_optimal_config = Mock(return_value={
            'optimal_config': {'top_n': 3},
            'model_accuracy': 0.75
        })
        service.optimizer_engine = Mock()
        service.optimizer_engine.cancel = Mock()
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
        request_data = {
            'team': 'Team1',
            'month': 202003,
            'top_n': 3,
            'k_similar': 10
        }
        response = client.post("/api/recommendations", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert 'team' in data
        assert 'recommendations' in data
    
    def test_post_recommendations_error(self, client, mock_service):
        """Test POST /api/recommendations with error."""
        mock_service.get_recommendations = Mock(return_value={'error': 'Team not found'})
        request_data = {'team': 'UnknownTeam', 'month': 202003}
        response = client.post("/api/recommendations", json=request_data)
        assert response.status_code == 400
    
    def test_post_backtest(self, client, mock_service):
        """Test POST /api/backtest endpoint."""
        request_data = {'train_ratio': 0.7}
        response = client.post("/api/backtest", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert 'total_predictions' in data
    
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
    
    def test_post_optimize(self, client, mock_service):
        """Test POST /api/optimize endpoint."""
        request_data = {'min_accuracy': 0.5}
        response = client.post("/api/optimize", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert 'optimal_config' in data
    
    def test_post_optimize_cancel(self, client, mock_service):
        """Test POST /api/optimize/cancel endpoint."""
        response = client.post("/api/optimize/cancel")
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        mock_service.optimizer_engine.cancel.assert_called_once()
    
    def test_get_latest_optimization(self, client):
        """Test GET /api/optimize/latest endpoint."""
        with patch('src.api.routes.OptimizationEngine') as mock_optimizer:
            mock_optimizer.load_latest_results = Mock(return_value={'test': 'data'})
            response = client.get("/api/optimize/latest")
            assert response.status_code == 200

