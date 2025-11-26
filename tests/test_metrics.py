"""
Tests for MetricsCalculator class.
"""

import pytest
from src.validation.metrics import MetricsCalculator


class TestMetricsCalculator:
    """Test MetricsCalculator functionality."""
    
    def test_calculate_hit_rate_basic(self):
        """Test calculate_hit_rate with basic inputs."""
        recommendations = ['Practice1', 'Practice2', 'Practice3']
        actual_improvements = {'Practice1', 'Practice3'}
        
        hit_rate = MetricsCalculator.calculate_hit_rate(recommendations, actual_improvements)
        
        assert hit_rate == pytest.approx(2/3, rel=1e-6)
    
    def test_calculate_hit_rate_perfect(self):
        """Test calculate_hit_rate with perfect match."""
        recommendations = ['Practice1', 'Practice2']
        actual_improvements = {'Practice1', 'Practice2'}
        
        hit_rate = MetricsCalculator.calculate_hit_rate(recommendations, actual_improvements)
        
        assert hit_rate == 1.0
    
    def test_calculate_hit_rate_zero(self):
        """Test calculate_hit_rate with no matches."""
        recommendations = ['Practice1', 'Practice2']
        actual_improvements = {'Practice3', 'Practice4'}
        
        hit_rate = MetricsCalculator.calculate_hit_rate(recommendations, actual_improvements)
        
        assert hit_rate == 0.0
    
    def test_calculate_hit_rate_empty_recommendations(self):
        """Test calculate_hit_rate with empty recommendations."""
        recommendations = []
        actual_improvements = {'Practice1', 'Practice2'}
        
        hit_rate = MetricsCalculator.calculate_hit_rate(recommendations, actual_improvements)
        
        assert hit_rate == 0.0
    
    def test_calculate_hit_rate_empty_actual(self):
        """Test calculate_hit_rate with empty actual improvements."""
        recommendations = ['Practice1', 'Practice2']
        actual_improvements = set()
        
        hit_rate = MetricsCalculator.calculate_hit_rate(recommendations, actual_improvements)
        
        assert hit_rate == 0.0
    
    def test_calculate_mrr_first_position(self):
        """Test calculate_mrr when first recommendation is correct."""
        recommendations = ['Practice1', 'Practice2', 'Practice3']
        actual_improvements = {'Practice1'}
        
        mrr = MetricsCalculator.calculate_mrr(recommendations, actual_improvements)
        
        assert mrr == 1.0
    
    def test_calculate_mrr_second_position(self):
        """Test calculate_mrr when second recommendation is correct."""
        recommendations = ['Practice1', 'Practice2', 'Practice3']
        actual_improvements = {'Practice2'}
        
        mrr = MetricsCalculator.calculate_mrr(recommendations, actual_improvements)
        
        assert mrr == pytest.approx(1/2, rel=1e-6)
    
    def test_calculate_mrr_third_position(self):
        """Test calculate_mrr when third recommendation is correct."""
        recommendations = ['Practice1', 'Practice2', 'Practice3']
        actual_improvements = {'Practice3'}
        
        mrr = MetricsCalculator.calculate_mrr(recommendations, actual_improvements)
        
        assert mrr == pytest.approx(1/3, rel=1e-6)
    
    def test_calculate_mrr_no_match(self):
        """Test calculate_mrr with no matches."""
        recommendations = ['Practice1', 'Practice2', 'Practice3']
        actual_improvements = {'Practice4'}
        
        mrr = MetricsCalculator.calculate_mrr(recommendations, actual_improvements)
        
        assert mrr == 0.0
    
    def test_calculate_mrr_empty_recommendations(self):
        """Test calculate_mrr with empty recommendations."""
        recommendations = []
        actual_improvements = {'Practice1'}
        
        mrr = MetricsCalculator.calculate_mrr(recommendations, actual_improvements)
        
        assert mrr == 0.0
    
    def test_calculate_coverage_basic(self):
        """Test calculate_coverage with basic inputs."""
        all_recommendations = ['Practice1', 'Practice2', 'Practice3', 'Practice1']
        all_practices = {'Practice1', 'Practice2', 'Practice3', 'Practice4', 'Practice5'}
        
        coverage = MetricsCalculator.calculate_coverage(all_recommendations, all_practices)
        
        # 3 unique practices recommended out of 5 total
        assert coverage == pytest.approx(3/5, rel=1e-6)
    
    def test_calculate_coverage_perfect(self):
        """Test calculate_coverage with perfect coverage."""
        all_recommendations = ['Practice1', 'Practice2', 'Practice3']
        all_practices = {'Practice1', 'Practice2', 'Practice3'}
        
        coverage = MetricsCalculator.calculate_coverage(all_recommendations, all_practices)
        
        assert coverage == 1.0
    
    def test_calculate_coverage_zero(self):
        """Test calculate_coverage with no overlap."""
        all_recommendations = ['Practice1', 'Practice2']
        all_practices = {'Practice3', 'Practice4'}
        
        coverage = MetricsCalculator.calculate_coverage(all_recommendations, all_practices)
        
        assert coverage == 0.0
    
    def test_calculate_coverage_empty_recommendations(self):
        """Test calculate_coverage with empty recommendations."""
        all_recommendations = []
        all_practices = {'Practice1', 'Practice2'}
        
        coverage = MetricsCalculator.calculate_coverage(all_recommendations, all_practices)
        
        assert coverage == 0.0
    
    def test_calculate_coverage_empty_practices(self):
        """Test calculate_coverage with empty practices set."""
        all_recommendations = ['Practice1', 'Practice2']
        all_practices = set()
        
        coverage = MetricsCalculator.calculate_coverage(all_recommendations, all_practices)
        
        assert coverage == 0.0
    
    def test_calculate_diversity_basic(self):
        """Test calculate_diversity with varied scores."""
        recommendations = [
            ('Practice1', 0.9, 0.5),
            ('Practice2', 0.7, 0.3),
            ('Practice3', 0.5, 0.2)
        ]
        
        diversity = MetricsCalculator.calculate_diversity(recommendations)
        
        # Should be between 0 and 1
        assert 0.0 <= diversity <= 1.0
    
    def test_calculate_diversity_single_recommendation(self):
        """Test calculate_diversity with single recommendation."""
        recommendations = [('Practice1', 0.8, 0.5)]
        
        diversity = MetricsCalculator.calculate_diversity(recommendations)
        
        assert diversity == 0.0
    
    def test_calculate_diversity_empty(self):
        """Test calculate_diversity with empty list."""
        recommendations = []
        
        diversity = MetricsCalculator.calculate_diversity(recommendations)
        
        assert diversity == 0.0
    
    def test_calculate_diversity_identical_scores(self):
        """Test calculate_diversity with identical scores."""
        recommendations = [
            ('Practice1', 0.8, 0.5),
            ('Practice2', 0.8, 0.5),
            ('Practice3', 0.8, 0.5)
        ]
        
        diversity = MetricsCalculator.calculate_diversity(recommendations)
        
        # Zero variance should give low diversity
        assert diversity == 0.0
    
    def test_calculate_diversity_zero_mean(self):
        """Test calculate_diversity with zero mean score."""
        recommendations = [
            ('Practice1', 0.0, 0.0),
            ('Practice2', 0.0, 0.0)
        ]
        
        diversity = MetricsCalculator.calculate_diversity(recommendations)
        
        assert diversity == 0.0
    
    def test_calculate_confidence_basic(self):
        """Test calculate_confidence with basic input."""
        score = 0.75
        max_possible = 1.0
        
        confidence = MetricsCalculator.calculate_confidence(score, max_possible)
        
        assert confidence == pytest.approx(0.75, rel=1e-6)
    
    def test_calculate_confidence_perfect(self):
        """Test calculate_confidence with perfect score."""
        score = 1.0
        max_possible = 1.0
        
        confidence = MetricsCalculator.calculate_confidence(score, max_possible)
        
        assert confidence == 1.0
    
    def test_calculate_confidence_zero(self):
        """Test calculate_confidence with zero score."""
        score = 0.0
        max_possible = 1.0
        
        confidence = MetricsCalculator.calculate_confidence(score, max_possible)
        
        assert confidence == 0.0
    
    def test_calculate_confidence_above_max(self):
        """Test calculate_confidence with score above max."""
        score = 1.5
        max_possible = 1.0
        
        confidence = MetricsCalculator.calculate_confidence(score, max_possible)
        
        # Should be capped at 1.0
        assert confidence == 1.0
    
    def test_calculate_confidence_custom_max(self):
        """Test calculate_confidence with custom max."""
        score = 50.0
        max_possible = 100.0
        
        confidence = MetricsCalculator.calculate_confidence(score, max_possible)
        
        assert confidence == pytest.approx(0.5, rel=1e-6)
    
    def test_calculate_confidence_zero_max(self):
        """Test calculate_confidence with zero max."""
        score = 0.5
        max_possible = 0.0
        
        confidence = MetricsCalculator.calculate_confidence(score, max_possible)
        
        assert confidence == 0.0
    
    def test_calculate_confidence_negative_score(self):
        """Test calculate_confidence with negative score."""
        score = -0.5
        max_possible = 1.0
        
        confidence = MetricsCalculator.calculate_confidence(score, max_possible)
        
        # Should handle negative gracefully (will be negative, but capped at 1.0)
        assert confidence <= 1.0

