"""
Tests for BacktestEngine class.
"""

import pytest
from unittest.mock import Mock, patch
from src.validation.backtest import BacktestEngine


class TestBacktestEngine:
    """Test BacktestEngine functionality."""
    
    def test_initialization(self, sample_recommender, sample_processor):
        """Test BacktestEngine can be initialized."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        assert backtest.recommender == sample_recommender
        assert backtest.processor == sample_processor
    
    def test_run_backtest_insufficient_data(self, sample_recommender, sample_processor):
        """Test run_backtest returns error when insufficient data."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        
        # Create processor with less than 4 months
        months = sample_processor.get_all_months()
        if len(months) >= 4:
            # Skip if we have enough data
            pytest.skip("Have sufficient data for backtest")
        
        result = backtest.run_backtest()
        
        assert 'error' in result
        assert '4 time periods' in result['error'] or '4' in result['error']
    
    def test_run_backtest_basic(self, sample_recommender, sample_processor):
        """Test run_backtest runs successfully with sufficient data."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        months = sample_processor.get_all_months()
        
        if len(months) < 4:
            pytest.skip("Need at least 4 months for backtest")
        
        result = backtest.run_backtest()
        
        assert isinstance(result, dict)
        assert 'status' in result or 'error' in result
        
        if 'error' not in result:
            assert 'per_month_results' in result
            assert 'total_predictions' in result
            assert 'correct_predictions' in result
            assert 'overall_accuracy' in result
            assert 'random_baseline' in result
            assert 'improvement_gap' in result
            assert 'improvement_factor' in result
            assert 'teams_tested' in result
    
    def test_run_backtest_per_month_results(self, sample_recommender, sample_processor):
        """Test run_backtest returns per-month results."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        months = sample_processor.get_all_months()
        
        if len(months) < 4:
            pytest.skip("Need at least 4 months for backtest")
        
        result = backtest.run_backtest()
        
        if 'error' not in result:
            assert isinstance(result['per_month_results'], list)
            
            # Check structure of per-month results
            for month_result in result['per_month_results']:
                assert 'month' in month_result
                assert 'train_months' in month_result
                assert 'predictions' in month_result
                assert 'correct' in month_result
                assert 'accuracy' in month_result
                assert 'teams_tested' in month_result
                
                assert isinstance(month_result['month'], int)
                assert isinstance(month_result['train_months'], list)
                assert isinstance(month_result['predictions'], int)
                assert isinstance(month_result['correct'], int)
                assert isinstance(month_result['accuracy'], float)
                assert 0.0 <= month_result['accuracy'] <= 1.0
    
    def test_run_backtest_accuracy_calculation(self, sample_recommender, sample_processor):
        """Test run_backtest calculates accuracy correctly."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        months = sample_processor.get_all_months()
        
        if len(months) < 4:
            pytest.skip("Need at least 4 months for backtest")
        
        result = backtest.run_backtest()
        
        if 'error' not in result:
            overall_accuracy = result['overall_accuracy']
            assert 0.0 <= overall_accuracy <= 1.0
            
            # Overall accuracy should be average of per-month accuracies
            if result['per_month_results']:
                per_month_accuracies = [r['accuracy'] for r in result['per_month_results']]
                expected_accuracy = sum(per_month_accuracies) / len(per_month_accuracies)
                assert abs(overall_accuracy - expected_accuracy) < 0.01
    
    def test_run_backtest_random_baseline(self, sample_recommender, sample_processor):
        """Test run_backtest calculates random baseline."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        months = sample_processor.get_all_months()
        
        if len(months) < 4:
            pytest.skip("Need at least 4 months for backtest")
        
        result = backtest.run_backtest()
        
        if 'error' not in result:
            random_baseline = result['random_baseline']
            assert 0.0 <= random_baseline <= 1.0
    
    def test_run_backtest_improvement_gap(self, sample_recommender, sample_processor):
        """Test run_backtest calculates improvement gap."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        months = sample_processor.get_all_months()
        
        if len(months) < 4:
            pytest.skip("Need at least 4 months for backtest")
        
        result = backtest.run_backtest()
        
        if 'error' not in result:
            improvement_gap = result['improvement_gap']
            overall_accuracy = result['overall_accuracy']
            random_baseline = result['random_baseline']
            
            # Improvement gap should be accuracy - baseline
            expected_gap = overall_accuracy - random_baseline
            assert abs(improvement_gap - expected_gap) < 0.01
    
    def test_run_backtest_with_config(self, sample_recommender, sample_processor):
        """Test run_backtest accepts configuration parameters."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        months = sample_processor.get_all_months()
        
        if len(months) < 4:
            pytest.skip("Need at least 4 months for backtest")
        
        config = {
            'top_n': 3,
            'k_similar': 10,
            'similarity_weight': 0.7,
            'similar_teams_lookahead_months': 2,
            'recent_improvements_months': 2,
            'min_similarity_threshold': 0.5
        }
        
        result = backtest.run_backtest(config=config)
        
        if 'error' not in result:
            assert isinstance(result, dict)
    
    def test_run_backtest_cancellation(self, sample_recommender, sample_processor):
        """Test run_backtest handles cancellation."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        months = sample_processor.get_all_months()
        
        if len(months) < 4:
            pytest.skip("Need at least 4 months for backtest")
        
        # Create cancellation check that returns True after first iteration
        call_count = [0]
        def cancellation_check():
            call_count[0] += 1
            return call_count[0] > 1
        
        result = backtest.run_backtest(cancellation_check=cancellation_check)
        
        # Should return partial results with cancelled flag
        assert isinstance(result, dict)
        assert result.get('cancelled', False) is True
        assert 'per_month_results' in result
    
    def test_build_partial_results(self, sample_recommender, sample_processor):
        """Test _build_partial_results builds correct structure."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        
        per_month_results = [
            {
                'month': 202001,
                'train_months': [],
                'predictions': 10,
                'correct': 7,
                'accuracy': 0.7,
                'teams_tested': 5
            }
        ]
        total_predictions = 10
        total_correct = 7
        improvements_per_case = [2, 3, 2]
        all_teams_tested = {'Team1', 'Team2'}
        top_n = 2
        
        result = backtest._build_partial_results(
            per_month_results, total_predictions, total_correct,
            improvements_per_case, all_teams_tested, top_n
        )
        
        assert isinstance(result, dict)
        assert result['cancelled'] is True
        assert 'per_month_results' in result
        assert 'total_predictions' in result
        assert 'correct_predictions' in result
        assert 'overall_accuracy' in result
        assert 'random_baseline' in result
        assert 'improvement_gap' in result
    
    def test_get_accuracy_summary_error(self, sample_recommender, sample_processor):
        """Test get_accuracy_summary handles error results."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        
        error_result = {'error': 'Insufficient data'}
        summary = backtest.get_accuracy_summary(error_result)
        
        assert isinstance(summary, str)
        assert 'Error' in summary or 'error' in summary.lower()
    
    def test_get_accuracy_summary_success(self, sample_recommender, sample_processor):
        """Test get_accuracy_summary formats successful results."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        
        success_result = {
            'total_predictions': 100,
            'correct_predictions': 70,
            'overall_accuracy': 0.7,
            'random_baseline': 0.1,
            'improvement_factor': 7.0,
            'teams_tested': 10,
            'per_month_results': []
        }
        
        summary = backtest.get_accuracy_summary(success_result)
        
        assert isinstance(summary, str)
        assert '100' in summary or 'Total Predictions' in summary
        assert '70' in summary or 'Correct' in summary
        assert '70.0%' in summary or '70%' in summary or '0.7' in summary

