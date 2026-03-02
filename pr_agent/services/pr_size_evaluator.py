"""
Service for evaluating PR size and determining if labels should be applied.
This module provides logic for calculating total PR changes and determining
if a PR exceeds configured thresholds.
"""

from typing import List, Tuple

from pr_agent.algo.types import FilePatchInfo
from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


class PRSizeEvaluator:
    """Evaluates PR size and determines automatic labels to apply."""

    @staticmethod
    def calculate_total_changes(diff_files: List[FilePatchInfo]) -> Tuple[int, int, int]:
        """
        Calculate total additions, deletions, and changes in a PR.

        Args:
            diff_files: List of FilePatchInfo objects from git provider

        Returns:
            Tuple of (total_additions, total_deletions, total_changes)
        """
        get_logger().info(f"[PRSizeEvaluator] calculate_total_changes called with {len(diff_files)} files")
        total_additions = 0
        total_deletions = 0

        for file_patch in diff_files:
            total_additions += file_patch.num_plus_lines
            total_deletions += file_patch.num_minus_lines

        total_changes = total_additions + total_deletions
        return total_additions, total_deletions, total_changes

    @staticmethod
    def should_add_large_pr_label(diff_files: List[FilePatchInfo]) -> bool:
        """
        Determine if PR should receive the large PR label based on changes.

        Args:
            diff_files: List of FilePatchInfo objects from git provider

        Returns:
            True if PR exceeds the configured threshold, False otherwise
        """
        try:
            if not get_settings().config.get("enable_auto_large_pr_label", False):
                return False

            threshold = get_settings().config.get("auto_label_large_pr_threshold", 500)

            _, _, total_changes = PRSizeEvaluator.calculate_total_changes(diff_files)

            is_large = total_changes >= threshold

            if is_large:
                get_logger().info(
                    f"PR size: {total_changes} changes (additions + deletions), "
                    f"exceeds threshold of {threshold}. Will apply large PR label."
                )
            else:
                get_logger().debug(
                    f"PR size: {total_changes} changes (additions + deletions), "
                    f"below threshold of {threshold}. No label needed."
                )

            return is_large

        except Exception as e:
            get_logger().warning(f"Error evaluating PR size for auto-label: {e}")
            return False

    @staticmethod
    def get_auto_labels(diff_files: List[FilePatchInfo]) -> List[str]:
        """
        Determine all automatic labels that should be applied to the PR.

        Args:
            diff_files: List of FilePatchInfo objects from git provider

        Returns:
            List of label names to apply
        """
        get_logger().info(f"[PRSizeEvaluator] get_auto_labels called")
        labels = []

        # Check for large PR label
        if PRSizeEvaluator.should_add_large_pr_label(diff_files):
            label_name = get_settings().config.get("auto_label_large_pr_label_name", "needs-staging-test")
            labels.append(label_name)

        # TODO: Add more automatic label logic here in the future
        # For example: auto-label based on files changed, author, etc.

        return labels
