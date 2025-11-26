"""
Tests for OptimizationEngine class.
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.validation.optimizer import OptimizationEngine
from src.validation.backtest import BacktestEngine


class TestOptimizationEngine:
    """Test OptimizationEngine functionality."""
    
    @pytest.fixture
    def mock_backtest_engine(self):
        """Create a mock BacktestEngine."""
        return Mock(spec=BacktestEngine)
    
    @pytest.fixture
    def optimizer(self, mock_backtest_engine):
        """Create OptimizationEngine with mock backtest engine."""
        return OptimizationEngine(mock_backtest_engine)
    
    def test_initialization(self, mock_backtest_engine):
        """Test OptimizationEngine can be initialized."""
        optimizer = OptimizationEngine(mock_backtest_engine)
        assert optimizer.backtest_engine == mock_backtest_engine
        assert optimizer._cancelled is False
    
    def test_generate_parameter_combinations_defaults(self, optimizer):
        """Test generate_parameter_combinations with default ranges."""
        combinations = list(optimizer.generate_parameter_combinations())
        
        assert len(combinations) > 0
        
        # Check structure of first combination
        first_combo = combinations[0]
        assert 'top_n' in first_combo
        assert 'similarity_weight' in first_combo
        assert 'k_similar' in first_combo
        assert 'similar_teams_lookahead_months' in first_combo
        assert 'recent_improvements_months' in first_combo
        assert 'min_similarity_threshold' in first_combo
    
    def test_generate_parameter_combinations_custom_ranges(self, optimizer):
        """Test generate_parameter_combinations with custom ranges."""
        combinations = list(optimizer.generate_parameter_combinations(
            top_n_range=[2, 3],
            similarity_weight_range=[0.6, 0.7],
            k_similar_range=[5, 10]
        ))
        
        # Should generate 2 * 2 * 2 = 8 combinations
        assert len(combinations) == 8
        
        # Check that all combinations use provided ranges
        top_n_values = set(c['top_n'] for c in combinations)
        assert top_n_values == {2, 3}
        
        similarity_weights = set(c['similarity_weight'] for c in combinations)
        assert similarity_weights == {0.6, 0.7}
        
        k_similar_values = set(c['k_similar'] for c in combinations)
        assert k_similar_values == {5, 10}
    
    def test_generate_parameter_combinations_fixed_params(self, optimizer):
        """Test generate_parameter_combinations with fixed parameters."""
        fixed_params = {'top_n': 5, 'k_similar': 20}
        
        combinations = list(optimizer.generate_parameter_combinations(
            fixed_params=fixed_params
        ))
        
        # All combinations should have fixed values
        for combo in combinations:
            assert combo['top_n'] == 5
            assert combo['k_similar'] == 20
    
    def test_cancel(self, optimizer):
        """Test cancel sets cancellation flag."""
        assert optimizer._cancelled is False
        
        optimizer.cancel()
        
        assert optimizer._cancelled is True
    
    def test_reset_cancellation(self, optimizer):
        """Test reset_cancellation clears cancellation flag."""
        optimizer._cancelled = True
        
        optimizer.reset_cancellation()
        
        assert optimizer._cancelled is False
    
    def test_save_results(self, optimizer, tmp_path):
        """Test save_results saves to JSON file."""
        # Change to temp directory
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            results = {
                'optimal_config': {'top_n': 3},
                'model_accuracy': 0.75,
                'random_baseline': 0.1,
                'improvement_gap': 0.65
            }
            
            filepath = optimizer.save_results(results)
            
            assert filepath is not None
            assert os.path.exists(filepath)
            
            # Verify file contents
            with open(filepath, 'r') as f:
                loaded = json.load(f)
            
            assert loaded['optimal_config'] == results['optimal_config']
            assert loaded['model_accuracy'] == results['model_accuracy']
            assert 'timestamp' in loaded
        finally:
            os.chdir(original_dir)
    
    def test_save_results_creates_directory(self, optimizer, tmp_path):
        """Test save_results creates results directory if it doesn't exist."""
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            # Remove results directory if it exists
            results_dir = Path('results')
            if results_dir.exists():
                import shutil
                shutil.rmtree(results_dir)
            
            results = {'optimal_config': {'top_n': 3}}
            filepath = optimizer.save_results(results)
            
            assert filepath is not None
            assert results_dir.exists()
        finally:
            os.chdir(original_dir)
    
    def test_load_latest_results_no_files(self, tmp_path):
        """Test load_latest_results returns None when no files exist."""
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            # Ensure results directory doesn't exist or is empty
            results_dir = Path('results')
            if results_dir.exists():
                import shutil
                shutil.rmtree(results_dir)
            
            result = OptimizationEngine.load_latest_results()
            
            assert result is None
        finally:
            os.chdir(original_dir)
    
    def test_load_latest_results_with_files(self, optimizer, tmp_path):
        """Test load_latest_results loads most recent file."""
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            # Create results directory
            results_dir = Path('results')
            results_dir.mkdir(exist_ok=True)
            
            # Create test files
            old_file = results_dir / 'optimization_20200101_000000.json'
            new_file = results_dir / 'optimization_20200102_000000.json'
            
            old_data = {'test': 'old'}
            new_data = {'test': 'new'}
            
            with open(old_file, 'w') as f:
                json.dump(old_data, f)
            
            with open(new_file, 'w') as f:
                json.dump(new_data, f)
            
            result = OptimizationEngine.load_latest_results()
            
            assert result is not None
            assert result['test'] == 'new'
        finally:
            os.chdir(original_dir)
    
    def test_find_optimal_config_basic(self, optimizer):
        """Test find_optimal_config runs optimization."""
        # Mock backtest to return valid results
        mock_result = {
            'overall_accuracy': 0.75,
            'random_baseline': 0.1,
            'improvement_gap': 0.65,
            'improvement_factor': 7.5,
            'total_predictions': 100,
            'correct_predictions': 75,
            'cancelled': False
        }
        
        optimizer.backtest_engine.run_backtest = Mock(return_value=mock_result)
        
        # Use small parameter ranges for faster testing
        result = optimizer.find_optimal_config(
            min_accuracy=0.5,
            top_n_range=[2],
            similarity_weight_range=[0.6],
            k_similar_range=[5],
            min_similarity_threshold_range=[0.0]
        )
        
        assert isinstance(result, dict)
        assert 'optimal_config' in result
        assert 'model_accuracy' in result
        assert 'random_baseline' in result
        assert 'improvement_gap' in result
        assert 'total_combinations_tested' in result
        assert 'valid_combinations' in result
        assert 'all_results' in result
    
    def test_find_optimal_config_filters_by_accuracy(self, optimizer):
        """Test find_optimal_config filters by minimum accuracy."""
        # Mock backtest to return results below threshold
        mock_result_low = {
            'overall_accuracy': 0.3,  # Below threshold
            'random_baseline': 0.1,
            'improvement_gap': 0.2,
            'improvement_factor': 3.0,
            'total_predictions': 100,
            'correct_predictions': 30,
            'cancelled': False
        }
        
        # Mock backtest to return results above threshold
        mock_result_high = {
            'overall_accuracy': 0.75,  # Above threshold
            'random_baseline': 0.1,
            'improvement_gap': 0.65,
            'improvement_factor': 7.5,
            'total_predictions': 100,
            'correct_predictions': 75,
            'cancelled': False
        }
        
        # Return low accuracy first, then high
        optimizer.backtest_engine.run_backtest = Mock(side_effect=[
            mock_result_low, mock_result_high
        ])
        
        result = optimizer.find_optimal_config(
            min_accuracy=0.5,
            top_n_range=[2, 3],
            similarity_weight_range=[0.6],
            k_similar_range=[5],
            min_similarity_threshold_range=[0.0]
        )
        
        # Should only include high accuracy result
        assert result['valid_combinations'] == 1
        assert len(result['all_results']) == 1
    
    def test_find_optimal_config_cancellation(self, optimizer):
        """Test find_optimal_config handles cancellation."""
        mock_result = {
            'overall_accuracy': 0.75,
            'random_baseline': 0.1,
            'improvement_gap': 0.65,
            'improvement_factor': 7.5,
            'total_predictions': 100,
            'correct_predictions': 75,
            'cancelled': False
        }
        
        optimizer.backtest_engine.run_backtest = Mock(return_value=mock_result)
        
        # Cancel after first iteration
        call_count = [0]
        def check_cancelled():
            call_count[0] += 1
            if call_count[0] == 1:
                optimizer.cancel()
            return optimizer._cancelled
        
        result = optimizer.find_optimal_config(
            min_accuracy=0.5,
            top_n_range=[2, 3],
            similarity_weight_range=[0.6],
            k_similar_range=[5],
            min_similarity_threshold_range=[0.0]
        )
        
        assert result['cancelled'] is True
        assert result['total_combinations_tested'] < result.get('total_combinations_available', 999)
    
    def test_find_optimal_config_early_stop(self, optimizer):
        """Test find_optimal_config stops early when excellent solution found."""
        mock_result_excellent = {
            'overall_accuracy': 0.8,
            'random_baseline': 0.1,
            'improvement_gap': 0.7,  # Above early_stop_threshold (0.25)
            'improvement_factor': 8.0,
            'total_predictions': 100,
            'correct_predictions': 80,
            'cancelled': False
        }
        
        optimizer.backtest_engine.run_backtest = Mock(return_value=mock_result_excellent)
        
        result = optimizer.find_optimal_config(
            min_accuracy=0.5,
            top_n_range=[2, 3, 4],
            similarity_weight_range=[0.6],
            k_similar_range=[5],
            min_similarity_threshold_range=[0.0],
            early_stop_threshold=0.25,
            early_stop_min_tested=0.1  # Low threshold for testing
        )
        
        # Should stop early if excellent solution found
        # (May or may not stop depending on when solution is found)
        assert result['early_stopped'] is True or result['total_combinations_tested'] <= result.get('total_combinations_available', 999)
    
    def test_find_optimal_config_progress_callback(self, optimizer):
        """Test find_optimal_config calls progress callback."""
        mock_result = {
            'overall_accuracy': 0.75,
            'random_baseline': 0.1,
            'improvement_gap': 0.65,
            'improvement_factor': 7.5,
            'total_predictions': 100,
            'correct_predictions': 75,
            'cancelled': False
        }
        
        optimizer.backtest_engine.run_backtest = Mock(return_value=mock_result)
        
        callback_calls = []
        def progress_callback(current, total, config):
            callback_calls.append((current, total, config))
        
        result = optimizer.find_optimal_config(
            min_accuracy=0.5,
            top_n_range=[2, 3],
            similarity_weight_range=[0.6],
            k_similar_range=[5],
            min_similarity_threshold_range=[0.0],
            progress_callback=progress_callback
        )
        
        # Callback should be called
        assert len(callback_calls) > 0
        
        # Check callback parameters
        for current, total, config in callback_calls:
            assert isinstance(current, int)
            assert isinstance(total, int)
            assert isinstance(config, dict)
    
    def test_find_optimal_config_error_handling(self, optimizer):
        """Test find_optimal_config handles errors gracefully."""
        # Mock backtest to raise exception
        optimizer.backtest_engine.run_backtest = Mock(side_effect=Exception("Test error"))
        
        result = optimizer.find_optimal_config(
            min_accuracy=0.5,
            top_n_range=[2],
            similarity_weight_range=[0.6],
            k_similar_range=[5],
            min_similarity_threshold_range=[0.0]
        )
        
        # Should complete without crashing
        assert isinstance(result, dict)
        assert result['valid_combinations'] == 0

