"""
Tests for PracticeDefinitionsLoader class.
"""

import pytest
import pandas as pd
import os
from unittest.mock import patch, mock_open
from src.data.practice_definitions import PracticeDefinitionsLoader


class TestPracticeDefinitionsLoader:
    """Test PracticeDefinitionsLoader functionality."""
    
    def test_initialization_default_path(self):
        """Test PracticeDefinitionsLoader can be initialized with default path."""
        loader = PracticeDefinitionsLoader()
        assert loader.file_path == "data/raw/practice_level_definitions.xlsx"
        assert loader.definitions is None
        assert loader.remarks is None
    
    def test_initialization_custom_path(self):
        """Test PracticeDefinitionsLoader can be initialized with custom path."""
        custom_path = "custom/path.xlsx"
        loader = PracticeDefinitionsLoader(custom_path)
        assert loader.file_path == custom_path
    
    def test_load_file_not_found(self):
        """Test load returns empty dict when file not found."""
        loader = PracticeDefinitionsLoader("nonexistent_file.xlsx")
        result = loader.load()
        
        assert isinstance(result, dict)
        assert len(result) == 0
        assert loader.definitions is None
    
    @patch('pandas.read_excel')
    @patch('os.path.exists')
    def test_load_success(self, mock_exists, mock_read_excel):
        """Test load successfully loads definitions from Excel."""
        mock_exists.return_value = True
        
        # Create mock DataFrame
        mock_df = pd.DataFrame({
            'Level': ['Practice1', 'Practice2'],
            0: ['Level 0 def 1', 'Level 0 def 2'],
            1: ['Level 1 def 1', 'Level 1 def 2'],
            2: ['Level 2 def 1', 'Level 2 def 2'],
            3: ['Level 3 def 1', 'Level 3 def 2'],
            'Remarks': ['Remark 1', 'Remark 2']
        })
        mock_read_excel.return_value = mock_df
        
        loader = PracticeDefinitionsLoader("test.xlsx")
        result = loader.load()
        
        assert isinstance(result, dict)
        assert len(result) > 0
        assert loader.definitions is not None
        assert loader.remarks is not None
    
    @patch('pandas.read_excel')
    @patch('os.path.exists')
    def test_load_missing_level_column(self, mock_exists, mock_read_excel):
        """Test load handles missing Level column."""
        mock_exists.return_value = True
        
        # Create mock DataFrame without Level column
        mock_df = pd.DataFrame({
            'Practice': ['Practice1'],
            0: ['Level 0 def'],
            1: ['Level 1 def']
        })
        mock_read_excel.return_value = mock_df
        
        loader = PracticeDefinitionsLoader("test.xlsx")
        result = loader.load()
        
        # Should return empty dict when Level column missing
        assert isinstance(result, dict)
        assert len(result) == 0
    
    @patch('pandas.read_excel')
    @patch('os.path.exists')
    def test_get_definitions_loads_if_needed(self, mock_exists, mock_read_excel):
        """Test get_definitions loads data if not already loaded."""
        mock_exists.return_value = True
        
        mock_df = pd.DataFrame({
            'Level': ['Practice1'],
            0: ['Level 0 def'],
            1: ['Level 1 def']
        })
        mock_read_excel.return_value = mock_df
        
        loader = PracticeDefinitionsLoader("test.xlsx")
        # Don't call load() explicitly
        
        definitions = loader.get_definitions()
        
        # Should have loaded automatically
        assert isinstance(definitions, dict)
        mock_read_excel.assert_called()
    
    @patch('pandas.read_excel')
    @patch('os.path.exists')
    def test_get_definitions_returns_cached(self, mock_exists, mock_read_excel):
        """Test get_definitions returns cached data."""
        mock_exists.return_value = True
        
        mock_df = pd.DataFrame({
            'Level': ['Practice1'],
            0: ['Level 0 def'],
            1: ['Level 1 def']
        })
        mock_read_excel.return_value = mock_df
        
        loader = PracticeDefinitionsLoader("test.xlsx")
        loader.load()
        
        # Reset mock call count
        mock_read_excel.reset_mock()
        
        # Call get_definitions twice
        definitions1 = loader.get_definitions()
        definitions2 = loader.get_definitions()
        
        # Should use cached data (read_excel not called again)
        assert definitions1 == definitions2
        mock_read_excel.assert_not_called()
    
    @patch('pandas.read_excel')
    @patch('os.path.exists')
    def test_get_remarks_loads_if_needed(self, mock_exists, mock_read_excel):
        """Test get_remarks loads data if not already loaded."""
        mock_exists.return_value = True
        
        mock_df = pd.DataFrame({
            'Level': ['Practice1'],
            0: ['Level 0 def'],
            'Remarks': ['Test remark']
        })
        mock_read_excel.return_value = mock_df
        
        loader = PracticeDefinitionsLoader("test.xlsx")
        # Don't call load() explicitly
        
        remarks = loader.get_remarks()
        
        # Should have loaded automatically
        assert isinstance(remarks, dict)
        mock_read_excel.assert_called()
    
    @patch('pandas.read_excel')
    @patch('os.path.exists')
    def test_get_practice_definition(self, mock_exists, mock_read_excel):
        """Test get_practice_definition returns definition for specific practice."""
        mock_exists.return_value = True
        
        mock_df = pd.DataFrame({
            'Level': ['Practice1'],
            0: ['Level 0 def'],
            1: ['Level 1 def'],
            2: ['Level 2 def'],
            3: ['Level 3 def']
        })
        mock_read_excel.return_value = mock_df
        
        loader = PracticeDefinitionsLoader("test.xlsx")
        loader.load()
        
        definition = loader.get_practice_definition("Practice1")
        
        assert definition is not None
        assert isinstance(definition, dict)
        assert 0 in definition
        assert 1 in definition
        assert 2 in definition
        assert 3 in definition
    
    @patch('pandas.read_excel')
    @patch('os.path.exists')
    def test_get_practice_definition_not_found(self, mock_exists, mock_read_excel):
        """Test get_practice_definition returns None for unknown practice."""
        mock_exists.return_value = True
        
        mock_df = pd.DataFrame({
            'Level': ['Practice1'],
            0: ['Level 0 def']
        })
        mock_read_excel.return_value = mock_df
        
        loader = PracticeDefinitionsLoader("test.xlsx")
        loader.load()
        
        definition = loader.get_practice_definition("UnknownPractice")
        
        assert definition is None
    
    @patch('pandas.read_excel')
    @patch('os.path.exists')
    def test_get_practice_remark(self, mock_exists, mock_read_excel):
        """Test get_practice_remark returns remark for specific practice."""
        mock_exists.return_value = True
        
        mock_df = pd.DataFrame({
            'Level': ['Practice1'],
            0: ['Level 0 def'],
            'Remarks': ['Test remark']
        })
        mock_read_excel.return_value = mock_df
        
        loader = PracticeDefinitionsLoader("test.xlsx")
        loader.load()
        
        remark = loader.get_practice_remark("Practice1")
        
        assert remark == "Test remark"
    
    @patch('pandas.read_excel')
    @patch('os.path.exists')
    def test_get_practice_remark_not_found(self, mock_exists, mock_read_excel):
        """Test get_practice_remark returns None for unknown practice."""
        mock_exists.return_value = True
        
        mock_df = pd.DataFrame({
            'Level': ['Practice1'],
            0: ['Level 0 def'],
            'Remarks': ['Test remark']
        })
        mock_read_excel.return_value = mock_df
        
        loader = PracticeDefinitionsLoader("test.xlsx")
        loader.load()
        
        remark = loader.get_practice_remark("UnknownPractice")
        
        assert remark is None
    
    @patch('pandas.read_excel')
    @patch('os.path.exists')
    def test_load_handles_nan_values(self, mock_exists, mock_read_excel):
        """Test load handles NaN values in Excel."""
        mock_exists.return_value = True
        
        mock_df = pd.DataFrame({
            'Level': ['Practice1', 'Practice2'],
            0: ['Level 0 def 1', None],  # NaN value
            1: ['Level 1 def 1', 'Level 1 def 2'],
            'Remarks': ['Remark 1', None]  # NaN remark
        })
        mock_read_excel.return_value = mock_df
        
        loader = PracticeDefinitionsLoader("test.xlsx")
        result = loader.load()
        
        # Should handle NaN gracefully
        assert isinstance(result, dict)
        # Practice1 should have definitions
        assert 'Practice1' in result or len(result) > 0
    
    @patch('pandas.read_excel')
    @patch('os.path.exists')
    def test_load_handles_exception(self, mock_exists, mock_read_excel):
        """Test load handles exceptions gracefully."""
        mock_exists.return_value = True
        mock_read_excel.side_effect = Exception("Test error")
        
        loader = PracticeDefinitionsLoader("test.xlsx")
        result = loader.load()
        
        # Should return empty dict on error
        assert isinstance(result, dict)
        assert len(result) == 0

