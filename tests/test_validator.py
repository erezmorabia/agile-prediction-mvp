"""
Tests for DataValidator class.
"""

import pytest
import pandas as pd
import numpy as np
from src.data.validator import DataValidator


class TestDataValidator:
    """Test DataValidator functionality."""
    
    def test_initialization(self, sample_dataframe, sample_practices):
        """Test DataValidator can be initialized."""
        validator = DataValidator(sample_dataframe, sample_practices)
        assert validator.df is not None
        assert validator.practices == sample_practices
        assert validator.issues == []
    
    def test_validate_success(self, sample_dataframe, sample_practices):
        """Test validation passes for valid data."""
        validator = DataValidator(sample_dataframe, sample_practices)
        result = validator.validate()
        assert result is True
        assert len(validator.issues) == 0
    
    def test_validate_missing_required_columns(self, sample_practices):
        """Test validation fails when required columns are missing."""
        df = pd.DataFrame({
            'Month': [202001, 202002],
            'Practice1': [1, 2]
        })
        validator = DataValidator(df, sample_practices)
        result = validator.validate()
        assert result is False
        assert len(validator.issues) > 0
        assert any('Team Name' in issue for issue in validator.issues)
    
    def test_validate_missing_month_column(self, sample_practices):
        """Test validation fails when Month column is missing."""
        df = pd.DataFrame({
            'Team Name': ['Team1', 'Team2'],
            'Practice1': [1, 2]
        })
        validator = DataValidator(df, sample_practices)
        result = validator.validate()
        assert result is False
        assert any('Month' in issue for issue in validator.issues)
    
    def test_validate_wrong_data_types(self, sample_practices):
        """Test validation fails with wrong data types."""
        df = pd.DataFrame({
            'Team Name': [1, 2],  # Should be string
            'Month': ['202001', '202002'],  # Should be numeric
            'Practice1': [1, 2]
        })
        validator = DataValidator(df, ['Practice1'])
        result = validator.validate()
        assert result is False
    
    def test_validate_value_ranges(self, sample_dataframe_invalid, sample_practices):
        """Test validation fails when values are out of range."""
        validator = DataValidator(sample_dataframe_invalid, sample_practices)
        result = validator.validate()
        assert result is False
        assert any('outside 0-3 range' in issue for issue in validator.issues)
    
    def test_validate_missing_values(self, sample_dataframe_with_missing, sample_practices):
        """Test validation detects missing values."""
        validator = DataValidator(sample_dataframe_with_missing, sample_practices)
        result = validator.validate()
        assert result is False
        assert any('missing values' in issue.lower() for issue in validator.issues)
    
    def test_validate_temporal_coverage(self, sample_practices):
        """Test validation fails when teams have insufficient temporal coverage."""
        df = pd.DataFrame({
            'Team Name': ['Team1', 'Team2', 'Team3'],
            'Month': [202001, 202001, 202001],  # All teams have only 1 month
            'Practice1': [1, 2, 0]
        })
        validator = DataValidator(df, ['Practice1'])
        result = validator.validate()
        assert result is False
        assert any('time period' in issue.lower() for issue in validator.issues)
    
    def test_get_missing_values_details(self, sample_dataframe_with_missing, sample_practices):
        """Test get_missing_values_details returns correct information."""
        validator = DataValidator(sample_dataframe_with_missing, sample_practices)
        details = validator.get_missing_values_details()
        
        assert 'total_missing' in details
        assert 'by_practice' in details
        assert 'by_month' in details
        assert 'practices_with_missing' in details
        assert 'months_with_missing' in details
        
        assert details['total_missing'] > 0
        assert len(details['practices_with_missing']) > 0
    
    def test_get_missing_values_details_no_missing(self, sample_dataframe, sample_practices):
        """Test get_missing_values_details with no missing values."""
        validator = DataValidator(sample_dataframe, sample_practices)
        details = validator.get_missing_values_details()
        
        assert details['total_missing'] == 0
        assert len(details['practices_with_missing']) == 0
        assert len(details['months_with_missing']) == 0
    
    def test_get_missing_values_details_by_practice(self, sample_dataframe_with_missing, sample_practices):
        """Test missing values breakdown by practice."""
        validator = DataValidator(sample_dataframe_with_missing, sample_practices)
        details = validator.get_missing_values_details()
        
        for practice in details['practices_with_missing']:
            assert practice in details['by_practice']
            practice_info = details['by_practice'][practice]
            assert 'count' in practice_info
            assert 'percentage' in practice_info
            assert 'by_month' in practice_info
            assert practice_info['count'] > 0
    
    def test_get_missing_values_details_by_month(self, sample_dataframe_with_missing, sample_practices):
        """Test missing values breakdown by month."""
        validator = DataValidator(sample_dataframe_with_missing, sample_practices)
        details = validator.get_missing_values_details()
        
        if details['months_with_missing']:
            for month in details['months_with_missing']:
                assert month in details['by_month']
                month_info = details['by_month'][month]
                assert 'count' in month_info
                assert 'total' in month_info
                assert 'percentage' in month_info
    
    def test_get_data_quality_report(self, sample_dataframe, sample_practices):
        """Test get_data_quality_report returns correct metrics."""
        validator = DataValidator(sample_dataframe, sample_practices)
        validator.validate()
        report = validator.get_data_quality_report()
        
        assert 'total_rows' in report
        assert 'total_columns' in report
        assert 'unique_teams' in report
        assert 'unique_months' in report
        assert 'missing_values' in report
        assert 'validation_issues' in report
        assert 'is_valid' in report
        
        assert report['total_rows'] == len(sample_dataframe)
        assert report['unique_teams'] == sample_dataframe['Team Name'].nunique()
        assert report['is_valid'] == (len(validator.issues) == 0)
    
    def test_filter_high_missing_practices(self, sample_dataframe_with_missing, sample_practices):
        """Test filter_high_missing_practices filters correctly."""
        validator = DataValidator(sample_dataframe_with_missing, sample_practices)
        
        # Test with default threshold (90%)
        filtered, excluded = validator.filter_high_missing_practices(sample_practices)
        
        assert isinstance(filtered, list)
        assert isinstance(excluded, list)
        assert len(filtered) + len(excluded) == len(sample_practices)
    
    def test_filter_high_missing_practices_custom_threshold(self, sample_dataframe_with_missing, sample_practices):
        """Test filter_high_missing_practices with custom threshold."""
        validator = DataValidator(sample_dataframe_with_missing, sample_practices)
        
        # Test with low threshold (should exclude more)
        filtered, excluded = validator.filter_high_missing_practices(sample_practices, threshold=10.0)
        
        # With 10% threshold, practices with any missing values might be excluded
        assert isinstance(filtered, list)
        assert isinstance(excluded, list)
    
    def test_filter_high_missing_practices_no_missing(self, sample_dataframe, sample_practices):
        """Test filter_high_missing_practices with no missing values."""
        validator = DataValidator(sample_dataframe, sample_practices)
        filtered, excluded = validator.filter_high_missing_practices(sample_practices)
        
        # All practices should be included if no missing values
        assert len(filtered) == len(sample_practices)
        assert len(excluded) == 0
    
    def test_filter_high_missing_practices_nonexistent_practice(self, sample_dataframe, sample_practices):
        """Test filter_high_missing_practices handles nonexistent practices."""
        validator = DataValidator(sample_dataframe, sample_practices)
        practices_with_fake = sample_practices + ['NonexistentPractice']
        
        filtered, excluded = validator.filter_high_missing_practices(practices_with_fake)
        
        # Nonexistent practice should be excluded
        assert 'NonexistentPractice' in excluded
        assert len(filtered) <= len(sample_practices)
    
    def test_get_missing_values_details_for_practices(self, sample_dataframe_with_missing, sample_practices):
        """Test get_missing_values_details_for_practices filters correctly."""
        validator = DataValidator(sample_dataframe_with_missing, sample_practices)
        
        # Test with subset of practices
        subset = sample_practices[:2]
        details = validator.get_missing_values_details_for_practices(subset)
        
        assert 'total_missing' in details
        assert 'by_practice' in details
        assert 'by_month' in details
        
        # Should only include practices in subset
        for practice in details['by_practice']:
            assert practice in subset
    
    def test_get_missing_values_details_for_practices_empty_subset(self, sample_dataframe_with_missing, sample_practices):
        """Test get_missing_values_details_for_practices with empty subset."""
        validator = DataValidator(sample_dataframe_with_missing, sample_practices)
        details = validator.get_missing_values_details_for_practices([])
        
        assert details['total_missing'] == 0
        assert len(details['by_practice']) == 0
    
    def test_check_required_columns_private(self, sample_dataframe, sample_practices):
        """Test _check_required_columns private method."""
        validator = DataValidator(sample_dataframe, sample_practices)
        validator._check_required_columns()
        
        # Should not add issues for valid data
        assert len(validator.issues) == 0
    
    def test_check_data_types_private(self, sample_dataframe, sample_practices):
        """Test _check_data_types private method."""
        validator = DataValidator(sample_dataframe, sample_practices)
        validator._check_data_types()
        
        # Should not add issues for valid data
        assert len(validator.issues) == 0
    
    def test_check_value_ranges_private(self, sample_dataframe, sample_practices):
        """Test _check_value_ranges private method."""
        validator = DataValidator(sample_dataframe, sample_practices)
        validator._check_value_ranges()
        
        # Should not add issues for valid data
        assert len(validator.issues) == 0
    
    def test_check_missing_values_private(self, sample_dataframe, sample_practices):
        """Test _check_missing_values private method."""
        validator = DataValidator(sample_dataframe, sample_practices)
        validator._check_missing_values()
        
        # Should not add issues for valid data
        assert len(validator.issues) == 0
    
    def test_check_temporal_coverage_private(self, sample_dataframe, sample_practices):
        """Test _check_temporal_coverage private method."""
        validator = DataValidator(sample_dataframe, sample_practices)
        validator._check_temporal_coverage()
        
        # Should not add issues for valid data (teams have multiple months)
        assert len(validator.issues) == 0
    
    def test_validate_empty_dataframe(self, sample_practices):
        """Test validation with empty DataFrame."""
        df = pd.DataFrame(columns=['Team Name', 'Month', 'Practice1'])
        validator = DataValidator(df, ['Practice1'])
        result = validator.validate()
        
        # Empty DataFrame should fail validation
        assert result is False
    
    def test_issues_list_cleared_on_validate(self, sample_dataframe, sample_practices):
        """Test that issues list is cleared on each validate call."""
        validator = DataValidator(sample_dataframe, sample_practices)
        
        # First validation
        validator.validate()
        initial_issues = len(validator.issues)
        
        # Second validation should clear and re-check
        validator.validate()
        
        # Issues should be reset (not accumulated)
        assert len(validator.issues) == initial_issues

