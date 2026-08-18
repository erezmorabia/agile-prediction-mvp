"""
Tests for BacktestEngine class.
"""

import warnings

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
            assert 'primary' in result
            assert 'sensitivity' in result
            for scope in (result['primary'], result['sensitivity']):
                assert 'total_predictions' in scope
                assert 'correct_predictions' in scope
                assert 'overall_accuracy' in scope
                assert 'random_baseline' in scope
                assert 'improvement_gap' in scope
                assert 'improvement_factor' in scope
                assert 'teams_tested' in scope
    
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
                assert 'full_outcome_window' in month_result
                assert 'evaluable_cases' in month_result
                assert 'predictions' in month_result
                assert 'correct' in month_result
                assert 'accuracy' in month_result
                assert 'teams_tested' in month_result
                assert 'selected_policy' in month_result

                assert isinstance(month_result['month'], int)
                assert isinstance(month_result['full_outcome_window'], bool)
                assert isinstance(month_result['predictions'], int)
                assert isinstance(month_result['correct'], int)
                assert isinstance(month_result['accuracy'], float)
                assert 0.0 <= month_result['accuracy'] <= 1.0
    
    def test_run_backtest_accuracy_calculation(self, sample_recommender, sample_processor):
        """Test run_backtest calculates accuracy correctly for each scope."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        months = sample_processor.get_all_months()

        if len(months) < 4:
            pytest.skip("Need at least 4 months for backtest")

        result = backtest.run_backtest()

        if 'error' not in result:
            sensitivity_rows = result['per_month_results']
            scope = result['sensitivity']
            overall_accuracy = scope['overall_accuracy']
            if scope['months_included'] > 0:
                assert 0.0 <= overall_accuracy <= 1.0
                # Sensitivity accuracy should be the average of every month's accuracy
                per_month_accuracies = [r['accuracy'] for r in sensitivity_rows]
                expected_accuracy = sum(per_month_accuracies) / len(per_month_accuracies)
                assert abs(overall_accuracy - expected_accuracy) < 0.01
            else:
                assert overall_accuracy is None

    def test_run_backtest_random_baseline(self, sample_recommender, sample_processor):
        """Test run_backtest calculates random baseline for each scope."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        months = sample_processor.get_all_months()

        if len(months) < 4:
            pytest.skip("Need at least 4 months for backtest")

        result = backtest.run_backtest()

        if 'error' not in result:
            for scope in (result['primary'], result['sensitivity']):
                if scope['months_included'] > 0:
                    assert 0.0 <= scope['random_baseline'] <= 1.0
                else:
                    assert scope['random_baseline'] is None

    def test_baseline_from_k_avg_matches_hand_computed_value(self):
        """Independently verify the hypergeometric formula against a hand-checkable example.

        n=3 practices, 1 improves on average, 1 recommendation drawn at random:
        P(hit) = 1 - C(2,1)/C(3,1) = 1 - 2/3 = 1/3.
        """
        baseline = BacktestEngine._baseline_from_k_avg(k_avg=1, total_practices=3, top_n=1)
        assert baseline == pytest.approx(1 / 3)

    def test_baseline_from_k_avg_handles_fractional_k_avg(self):
        """comb(..., exact=False) must accept a non-integer k_avg without raising or warning.

        n=5, k_avg=1.5 (average improvements per case), top_n=1:
        P(hit) = 1 - C(3.5,1)/C(5,1) = 1 - 3.5/5 = 0.3.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            baseline = BacktestEngine._baseline_from_k_avg(k_avg=1.5, total_practices=5, top_n=1)
        assert baseline == pytest.approx(0.3)

    def test_run_backtest_improvement_gap(self, sample_recommender, sample_processor):
        """Test run_backtest calculates improvement gap per scope."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        months = sample_processor.get_all_months()

        if len(months) < 4:
            pytest.skip("Need at least 4 months for backtest")

        result = backtest.run_backtest()

        if 'error' not in result:
            for scope in (result['primary'], result['sensitivity']):
                if scope['months_included'] == 0:
                    assert scope['improvement_gap'] is None
                    continue
                # Improvement gap should be accuracy - baseline
                expected_gap = scope['overall_accuracy'] - scope['random_baseline']
                assert abs(scope['improvement_gap'] - expected_gap) < 0.01
    
    def test_run_backtest_accepts_no_model_parameters(self, sample_recommender, sample_processor):
        """run_backtest() takes only an optional cancellation_check - no config dict,
        no train_ratio. The monthly policy is the only configuration authority."""
        import inspect

        signature = inspect.signature(BacktestEngine.run_backtest)
        assert list(signature.parameters) == ["self", "cancellation_check"]

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
    
    def test_aggregate_scope_empty_returns_none_fields(self, sample_recommender, sample_processor):
        """_aggregate_scope([]) - e.g. a cancelled run with zero qualifying months - returns
        None rate fields (not 0.0), so the caller can render 'not enough completed months'
        instead of a misleading 0%. Replaces the old _build_partial_results, which this
        refactor collapsed into one aggregation function used for every scope."""
        backtest = BacktestEngine(sample_recommender, sample_processor)

        result = backtest._aggregate_scope([], {}, {}, total_practices=3)

        assert result['months_included'] == 0
        assert result['overall_accuracy'] is None
        assert result['random_baseline'] is None
        assert result['total_predictions'] == 0
        assert result['correct_predictions'] == 0
