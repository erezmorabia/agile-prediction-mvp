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

    def test_expected_random_hit_rate_matches_hand_computed_value(self):
        """Independently verify the hypergeometric formula against a hand-checkable example.

        n=5 eligible practices, k=2 improvements, top_n=2 recommendations:
        P(hit) = 1 - C(3,2)/C(5,2) = 1 - 3/10 = 0.7.
        """
        baseline = BacktestEngine._expected_random_hit_rate(n=5, k=2, top_n=2)
        assert baseline == pytest.approx(0.7)

    def test_expected_random_hit_rate_uses_case_candidate_count(self):
        """Maxed-out practices excluded by the model must also be excluded by random."""
        candidate_aware = BacktestEngine._expected_random_hit_rate(n=5, k=1, top_n=2)
        all_practices = BacktestEngine._expected_random_hit_rate(n=30, k=1, top_n=2)

        assert candidate_aware == pytest.approx(0.4)
        assert all_practices == pytest.approx(1 / 15)

    def test_random_metrics_use_case_candidates_and_monthly_macro_average(
        self, sample_recommender, sample_processor
    ):
        """Every random comparator mirrors the model's per-month aggregation."""
        backtest = BacktestEngine(sample_recommender, sample_processor)
        rows = [
            {
                "month": 1, "predictions": 2, "correct": 0, "accuracy": 0.0,
                "time_aware_popularity_accuracy": 0.0, "precision": 0.0,
                "recall": 0.0, "mrr": 0.0,
            },
            {
                "month": 2, "predictions": 1, "correct": 0, "accuracy": 0.0,
                "time_aware_popularity_accuracy": 0.0, "precision": 0.0,
                "recall": 0.0, "mrr": 0.0,
            },
        ]
        # Month 1 has two cases; month 2 has one. A pooled case average would weight
        # month 1 twice, so these assertions also pin the required monthly macro-average.
        case_stats = {1: [(5, 1), (3, 1)], 2: [(10, 1)]}

        result = backtest._aggregate_scope(rows, case_stats)

        assert result["random_baseline"] == pytest.approx(((0.4 + 2 / 3) / 2 + 0.2) / 2)
        assert result["random_precision"] == pytest.approx(((1 / 5 + 1 / 3) / 2 + 1 / 10) / 2)
        assert result["random_recall"] == pytest.approx(((2 / 5 + 2 / 3) / 2 + 2 / 10) / 2)
        assert result["random_mrr"] == pytest.approx(((0.3 + 0.5) / 2 + 0.15) / 2)

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
    
    def test_run_backtest_accepts_no_parameters(self, sample_recommender, sample_processor):
        """run_backtest() takes no configuration parameters; the monthly policy is the
        only configuration authority."""
        import inspect

        signature = inspect.signature(BacktestEngine.run_backtest)
        assert list(signature.parameters) == ["self"]
    
    def test_aggregate_scope_empty_returns_none_fields(self, sample_recommender, sample_processor):
        """_aggregate_scope([]) returns None rate fields (not 0.0), so the caller can
        render 'not enough completed months'
        instead of a misleading 0%. Replaces the old _build_partial_results, which this
        refactor collapsed into one aggregation function used for every scope."""
        backtest = BacktestEngine(sample_recommender, sample_processor)

        result = backtest._aggregate_scope([], {})

        assert result['months_included'] == 0
        assert result['overall_accuracy'] is None
        assert result['random_baseline'] is None
        assert result['total_predictions'] == 0
        assert result['correct_predictions'] == 0
