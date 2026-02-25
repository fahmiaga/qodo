"""
Unit tests for PR size evaluator service.
"""

import pytest

from pr_agent.algo.types import FilePatchInfo, EDIT_TYPE
from pr_agent.config_loader import global_settings
from pr_agent.services.pr_size_evaluator import PRSizeEvaluator


class MockFilePatchInfo:
    """Mock FilePatchInfo for testing."""
    
    def __init__(self, num_plus_lines: int, num_minus_lines: int):
        self.num_plus_lines = num_plus_lines
        self.num_minus_lines = num_minus_lines


class TestPRSizeEvaluator:
    """Test suite for PRSizeEvaluator service."""
    
    def test_calculate_total_changes_empty_pr(self):
        """Test calculation with no files changed."""
        diff_files = []
        additions, deletions, total = PRSizeEvaluator.calculate_total_changes(diff_files)
        
        assert additions == 0
        assert deletions == 0
        assert total == 0
    
    def test_calculate_total_changes_single_file(self):
        """Test calculation with a single file."""
        diff_files = [MockFilePatchInfo(10, 5)]
        additions, deletions, total = PRSizeEvaluator.calculate_total_changes(diff_files)
        
        assert additions == 10
        assert deletions == 5
        assert total == 15
    
    def test_calculate_total_changes_multiple_files(self):
        """Test calculation with multiple files."""
        diff_files = [
            MockFilePatchInfo(10, 5),
            MockFilePatchInfo(20, 15),
            MockFilePatchInfo(5, 10),
        ]
        additions, deletions, total = PRSizeEvaluator.calculate_total_changes(diff_files)
        
        assert additions == 35  # 10 + 20 + 5
        assert deletions == 30  # 5 + 15 + 10
        assert total == 65  # 35 + 30
    
    def test_should_add_large_pr_label_disabled(self, monkeypatch):
        """Test that label is not added when feature is disabled."""
        monkeypatch.setattr(global_settings.config, 'enable_auto_large_pr_label', False)
        
        diff_files = [MockFilePatchInfo(300, 300)]  # 600 total changes
        result = PRSizeEvaluator.should_add_large_pr_label(diff_files)
        
        assert result is False
    
    def test_should_add_large_pr_label_below_threshold(self, monkeypatch):
        """Test that label is not added when PR is below threshold."""
        monkeypatch.setattr(global_settings.config, 'enable_auto_large_pr_label', True)
        monkeypatch.setattr(global_settings.config, 'auto_label_large_pr_threshold', 500)
        
        diff_files = [MockFilePatchInfo(200, 200)]  # 400 total changes
        result = PRSizeEvaluator.should_add_large_pr_label(diff_files)
        
        assert result is False
    
    def test_should_add_large_pr_label_exactly_at_threshold(self, monkeypatch):
        """Test that label is added when PR is exactly at threshold."""
        monkeypatch.setattr(global_settings.config, 'enable_auto_large_pr_label', True)
        monkeypatch.setattr(global_settings.config, 'auto_label_large_pr_threshold', 500)
        
        diff_files = [MockFilePatchInfo(250, 250)]  # 500 total changes
        result = PRSizeEvaluator.should_add_large_pr_label(diff_files)
        
        assert result is True
    
    def test_should_add_large_pr_label_above_threshold(self, monkeypatch):
        """Test that label is added when PR exceeds threshold."""
        monkeypatch.setattr(global_settings.config, 'enable_auto_large_pr_label', True)
        monkeypatch.setattr(global_settings.config, 'auto_label_large_pr_threshold', 500)
        
        diff_files = [MockFilePatchInfo(300, 300)]  # 600 total changes
        result = PRSizeEvaluator.should_add_large_pr_label(diff_files)
        
        assert result is True
    
    def test_should_add_large_pr_label_custom_threshold(self, monkeypatch):
        """Test with custom threshold value."""
        monkeypatch.setattr(global_settings.config, 'enable_auto_large_pr_label', True)
        monkeypatch.setattr(global_settings.config, 'auto_label_large_pr_threshold', 1000)
        
        diff_files = [MockFilePatchInfo(400, 400)]  # 800 total changes
        result = PRSizeEvaluator.should_add_large_pr_label(diff_files)
        
        assert result is False
        
        # Now test above the threshold
        diff_files = [MockFilePatchInfo(600, 600)]  # 1200 total changes
        result = PRSizeEvaluator.should_add_large_pr_label(diff_files)
        
        assert result is True
    
    def test_get_auto_labels_empty(self, monkeypatch):
        """Test getting labels when feature is disabled."""
        monkeypatch.setattr(global_settings.config, 'enable_auto_large_pr_label', False)
        
        diff_files = [MockFilePatchInfo(300, 300)]
        labels = PRSizeEvaluator.get_auto_labels(diff_files)
        
        assert labels == []
    
    def test_get_auto_labels_large_pr(self, monkeypatch):
        """Test getting labels for a large PR."""
        monkeypatch.setattr(global_settings.config, 'enable_auto_large_pr_label', True)
        monkeypatch.setattr(global_settings.config, 'auto_label_large_pr_threshold', 500)
        monkeypatch.setattr(global_settings.config, 'auto_label_large_pr_label_name', 'needs-staging-test')
        
        diff_files = [MockFilePatchInfo(300, 300)]  # 600 total changes
        labels = PRSizeEvaluator.get_auto_labels(diff_files)
        
        assert 'needs-staging-test' in labels
        assert len(labels) == 1
    
    def test_get_auto_labels_custom_label_name(self, monkeypatch):
        """Test that custom label name is used."""
        monkeypatch.setattr(global_settings.config, 'enable_auto_large_pr_label', True)
        monkeypatch.setattr(global_settings.config, 'auto_label_large_pr_threshold', 400)
        monkeypatch.setattr(global_settings.config, 'auto_label_large_pr_label_name', 'large-pr-review-required')
        
        diff_files = [MockFilePatchInfo(200, 250)]  # 450 total changes
        labels = PRSizeEvaluator.get_auto_labels(diff_files)
        
        assert 'large-pr-review-required' in labels
        assert len(labels) == 1
    
    def test_should_add_large_pr_label_with_exception(self, monkeypatch):
        """Test graceful handling of exceptions."""
        # Simulate an exception when getting settings
        monkeypatch.setattr(global_settings.config, 'get', lambda key, default: (_ for _ in ()).throw(Exception("Test error")))
        
        diff_files = [MockFilePatchInfo(300, 300)]
        result = PRSizeEvaluator.should_add_large_pr_label(diff_files)
        
        # Should return False on exception
        assert result is False
