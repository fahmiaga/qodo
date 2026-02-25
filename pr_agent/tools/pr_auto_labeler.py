"""
Automatic label assignment tool for PRs based on PR size.

This tool automatically assigns labels to pull requests when they exceed
a configurable size threshold (additions + deletions).
"""

import traceback
from typing import List, Optional

from pr_agent.config_loader import get_settings
from pr_agent.git_providers import get_git_provider_with_context
from pr_agent.log import get_logger
from pr_agent.services.pr_size_evaluator import PRSizeEvaluator


class PRAutoLabeler:
    """Automatically assigns labels to PRs based on size and other criteria."""

    def __init__(self, pr_url: str):
        """
        Initialize the PR auto-labeler.

        Args:
            pr_url (str): The URL of the pull request
        """
        self.git_provider = get_git_provider_with_context(pr_url)
        self.pr_id = self.git_provider.get_pr_id()

    async def run(self) -> Optional[str]:
        """
        Execute the auto-labeling logic for the PR.

        Returns:
            Empty string on success, or None on failure
        """
        try:
            # Check if auto-labeling is enabled
            if not get_settings().config.get("enable_auto_large_pr_label", False):
                get_logger().debug(f"Auto-labeling disabled for PR: {self.pr_id}")
                return None

            get_logger().info(f"Running auto-labeler for PR: {self.pr_id}")

            # Get diff files
            diff_files = self.git_provider.get_diff_files()

            # Determine labels to apply
            auto_labels = PRSizeEvaluator.get_auto_labels(diff_files)

            if not auto_labels:
                get_logger().debug(f"No auto-labels to apply for PR: {self.pr_id}")
                return ""

            # Get existing labels
            try:
                existing_labels = self.git_provider.get_pr_labels(update=True)
            except Exception as e:
                get_logger().warning(f"Failed to get existing PR labels: {e}")
                existing_labels = []

            # Merge with existing labels (avoid duplicates)
            combined_labels = list(set(existing_labels + auto_labels))

            # Publish labels if they changed
            if sorted(combined_labels) != sorted(existing_labels):
                get_logger().info(
                    f"Publishing auto-labels for PR: {self.pr_id}. "
                    f"New labels: {auto_labels}. Combined labels: {combined_labels}"
                )
                self.git_provider.publish_labels(combined_labels)
            else:
                get_logger().debug(f"Labels unchanged for PR: {self.pr_id}")

            return ""

        except Exception as e:
            get_logger().error(
                f"Error running auto-labeler for PR: {self.pr_id}. Error: {e}",
                artifact={"traceback": traceback.format_exc()}
            )
            return None
