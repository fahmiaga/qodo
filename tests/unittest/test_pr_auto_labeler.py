"""
Unit tests for PR auto-labeler tool.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pr_agent.tools.pr_auto_labeler import PRAutoLabeler
from pr_agent.config_loader import global_settings


class TestPRAutoLabeler:
    """Test suite for PRAutoLabeler tool."""
    
    @pytest.mark.asyncio
    async def test_run_auto_labeler_disabled(self, monkeypatch):
        """Test that labeler returns None when feature is disabled."""
        monkeypatch.setattr(global_settings.config, 'get', lambda key, default=None: False if key == 'enable_auto_large_pr_label' else default)
        
        with patch('pr_agent.tools.pr_auto_labeler.get_git_provider_with_context') as mock_provider:
            mock_git_provider = AsyncMock()
            mock_git_provider.get_pr_id.return_value = "123"
            mock_provider.return_value = mock_git_provider
            
            labeler = PRAutoLabeler("https://github.com/test/repo/pull/123")
            result = await labeler.run()
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_run_auto_labeler_no_labels(self, monkeypatch):
        """Test when PR doesn't qualify for any labels."""
        def mock_get(key, default=None):
            if key == 'enable_auto_large_pr_label':
                return True
            if key == 'auto_label_large_pr_threshold':
                return 500
            return default
        
        monkeypatch.setattr(global_settings.config, 'get', mock_get)
        
        with patch('pr_agent.tools.pr_auto_labeler.get_git_provider_with_context') as mock_provider_factory:
            mock_git_provider = MagicMock()
            mock_git_provider.get_pr_id.return_value = "123"
            
            # Small PR (below threshold)
            mock_file = MagicMock()
            mock_file.num_plus_lines = 100
            mock_file.num_minus_lines = 50
            mock_git_provider.get_diff_files.return_value = [mock_file]
            
            mock_provider_factory.return_value = mock_git_provider
            
            labeler = PRAutoLabeler("https://github.com/test/repo/pull/123")
            result = await labeler.run()
            
            assert result == ""
            # Verify labels weren't published
            mock_git_provider.publish_labels.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_auto_labeler_applies_label(self, monkeypatch):
        """Test that label is applied to large PR."""
        def mock_get(key, default=None):
            if key == 'enable_auto_large_pr_label':
                return True
            if key == 'auto_label_large_pr_threshold':
                return 500
            if key == 'auto_label_large_pr_label_name':
                return 'needs-staging-test'
            return default
        
        monkeypatch.setattr(global_settings.config, 'get', mock_get)
        
        with patch('pr_agent.tools.pr_auto_labeler.get_git_provider_with_context') as mock_provider_factory:
            mock_git_provider = MagicMock()
            mock_git_provider.get_pr_id.return_value = "123"
            
            # Large PR (above threshold of 500)
            mock_file = MagicMock()
            mock_file.num_plus_lines = 300
            mock_file.num_minus_lines = 300
            mock_git_provider.get_diff_files.return_value = [mock_file]
            
            # No existing labels
            mock_git_provider.get_pr_labels.return_value = []
            
            mock_provider_factory.return_value = mock_git_provider
            
            labeler = PRAutoLabeler("https://github.com/test/repo/pull/123")
            result = await labeler.run()
            
            assert result == ""
            # Verify label was published
            mock_git_provider.publish_labels.assert_called_once()
            published_labels = mock_git_provider.publish_labels.call_args[0][0]
            assert 'needs-staging-test' in published_labels
    
    @pytest.mark.asyncio
    async def test_run_auto_labeler_preserves_existing_labels(self, monkeypatch):
        """Test that existing labels are preserved when adding new ones."""
        def mock_get(key, default=None):
            if key == 'enable_auto_large_pr_label':
                return True
            if key == 'auto_label_large_pr_threshold':
                return 500
            if key == 'auto_label_large_pr_label_name':
                return 'needs-staging-test'
            return default
        
        monkeypatch.setattr(global_settings.config, 'get', mock_get)
        
        with patch('pr_agent.tools.pr_auto_labeler.get_git_provider_with_context') as mock_provider_factory:
            mock_git_provider = MagicMock()
            mock_git_provider.get_pr_id.return_value = "123"
            
            # Large PR
            mock_file = MagicMock()
            mock_file.num_plus_lines = 400
            mock_file.num_minus_lines = 400
            mock_git_provider.get_diff_files.return_value = [mock_file]
            
            # Existing labels
            mock_git_provider.get_pr_labels.return_value = ['bug-fix', 'documentation']
            
            mock_provider_factory.return_value = mock_git_provider
            
            labeler = PRAutoLabeler("https://github.com/test/repo/pull/123")
            result = await labeler.run()
            
            assert result == ""
            # Verify all labels are present
            published_labels = mock_git_provider.publish_labels.call_args[0][0]
            assert 'bug-fix' in published_labels
            assert 'documentation' in published_labels
            assert 'needs-staging-test' in published_labels
    
    @pytest.mark.asyncio
    async def test_run_auto_labeler_handles_get_labels_error(self, monkeypatch):
        """Test graceful handling when getting existing labels fails."""
        def mock_get(key, default=None):
            if key == 'enable_auto_large_pr_label':
                return True
            if key == 'auto_label_large_pr_threshold':
                return 500
            if key == 'auto_label_large_pr_label_name':
                return 'needs-staging-test'
            return default
        
        monkeypatch.setattr(global_settings.config, 'get', mock_get)
        
        with patch('pr_agent.tools.pr_auto_labeler.get_git_provider_with_context') as mock_provider_factory:
            mock_git_provider = MagicMock()
            mock_git_provider.get_pr_id.return_value = "123"
            
            # Large PR
            mock_file = MagicMock()
            mock_file.num_plus_lines = 400
            mock_file.num_minus_lines = 400
            mock_git_provider.get_diff_files.return_value = [mock_file]
            
            # Simulate error when getting labels
            mock_git_provider.get_pr_labels.side_effect = Exception("API Error")
            
            mock_provider_factory.return_value = mock_git_provider
            
            labeler = PRAutoLabeler("https://github.com/test/repo/pull/123")
            result = await labeler.run()
            
            # Should still succeed and apply the label
            assert result == ""
            published_labels = mock_git_provider.publish_labels.call_args[0][0]
            assert 'needs-staging-test' in published_labels
    
    @pytest.mark.asyncio
    async def test_run_auto_labeler_no_duplicate_labels(self, monkeypatch):
        """Test that duplicate labels are not created."""
        def mock_get(key, default=None):
            if key == 'enable_auto_large_pr_label':
                return True
            if key == 'auto_label_large_pr_threshold':
                return 500
            if key == 'auto_label_large_pr_label_name':
                return 'needs-staging-test'
            return default
        
        monkeypatch.setattr(global_settings.config, 'get', mock_get)
        
        with patch('pr_agent.tools.pr_auto_labeler.get_git_provider_with_context') as mock_provider_factory:
            mock_git_provider = MagicMock()
            mock_git_provider.get_pr_id.return_value = "123"
            
            # Large PR
            mock_file = MagicMock()
            mock_file.num_plus_lines = 400
            mock_file.num_minus_lines = 400
            mock_git_provider.get_diff_files.return_value = [mock_file]
            
            # Label already exists
            mock_git_provider.get_pr_labels.return_value = ['needs-staging-test']
            
            mock_provider_factory.return_value = mock_git_provider
            
            labeler = PRAutoLabeler("https://github.com/test/repo/pull/123")
            result = await labeler.run()
            
            # Should still succeed
            assert result == ""
            # Should publish labels (even though they're the same)
            published_labels = mock_git_provider.publish_labels.call_args[0][0]
            # Check that 'needs-staging-test' appears only once
            assert published_labels.count('needs-staging-test') == 1
    
    @pytest.mark.asyncio
    async def test_run_auto_labeler_exception_handling(self, monkeypatch):
        """Test that exceptions are handled gracefully."""
        monkeypatch.setattr(global_settings.config, 'get', lambda key, default=None: True if key == 'enable_auto_large_pr_label' else default)
        
        with patch('pr_agent.tools.pr_auto_labeler.get_git_provider_with_context') as mock_provider_factory:
            mock_git_provider = MagicMock()
            mock_git_provider.get_pr_id.return_value = "123"
            mock_git_provider.get_diff_files.side_effect = Exception("Unexpected error")
            
            mock_provider_factory.return_value = mock_git_provider
            
            labeler = PRAutoLabeler("https://github.com/test/repo/pull/123")
            result = await labeler.run()
            
            # Should return None on exception
            assert result is None
