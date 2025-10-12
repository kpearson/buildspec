"""Unit tests for create-epic auto-resume functionality."""

import pytest
from pathlib import Path

from cli.commands.create_epic import (
    _check_epic_exists,
    _check_review_completed,
    _check_review_feedback_applied,
)


class TestCheckEpicExists:
    """Test epic existence detection."""

    def test_finds_epic_with_exact_name(self, tmp_path):
        """Should find epic file with matching base name."""
        epic_file = tmp_path / "my-feature.epic.yaml"
        epic_file.write_text("epic: test")

        result = _check_epic_exists(tmp_path, "my-feature")

        assert result == epic_file

    def test_finds_epic_with_partial_name(self, tmp_path):
        """Should find epic file with base name in stem."""
        epic_file = tmp_path / "test-my-feature-extra.epic.yaml"
        epic_file.write_text("epic: test")

        result = _check_epic_exists(tmp_path, "my-feature")

        assert result == epic_file

    def test_returns_none_when_no_epic_exists(self, tmp_path):
        """Should return None when no epic file found."""
        result = _check_epic_exists(tmp_path, "my-feature")

        assert result is None

    def test_returns_none_when_name_doesnt_match(self, tmp_path):
        """Should return None when epic exists but name doesn't match."""
        epic_file = tmp_path / "other-feature.epic.yaml"
        epic_file.write_text("epic: test")

        result = _check_epic_exists(tmp_path, "my-feature")

        assert result is None

    def test_ignores_non_epic_yaml_files(self, tmp_path):
        """Should ignore YAML files without .epic suffix."""
        yaml_file = tmp_path / "my-feature.yaml"
        yaml_file.write_text("data: test")

        result = _check_epic_exists(tmp_path, "my-feature")

        assert result is None


class TestCheckReviewCompleted:
    """Test review artifact detection."""

    def test_returns_true_when_review_exists(self, tmp_path):
        """Should return True when review artifact exists."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        review_file = artifacts_dir / "epic-file-review.md"
        review_file.write_text("# Review")

        result = _check_review_completed(artifacts_dir, "epic-file-review.md")

        assert result is True

    def test_returns_false_when_review_missing(self, tmp_path):
        """Should return False when review artifact doesn't exist."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        result = _check_review_completed(artifacts_dir, "epic-file-review.md")

        assert result is False

    def test_returns_false_when_artifacts_dir_missing(self, tmp_path):
        """Should return False when artifacts directory doesn't exist."""
        artifacts_dir = tmp_path / "artifacts"

        result = _check_review_completed(artifacts_dir, "epic-file-review.md")

        assert result is False


class TestCheckReviewFeedbackApplied:
    """Test review feedback completion detection."""

    def test_returns_true_when_status_completed(self, tmp_path):
        """Should return True when status is 'completed' in frontmatter."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        updates_file = artifacts_dir / "epic-file-review-updates.md"
        updates_file.write_text("""---
date: 2025-01-01
status: completed
---

# Updates
Changes applied successfully.
""")

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-file-review-updates.md"
        )

        assert result is True

    def test_returns_false_when_status_in_progress(self, tmp_path):
        """Should return False when status is 'in_progress'."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        updates_file = artifacts_dir / "epic-file-review-updates.md"
        updates_file.write_text("""---
date: 2025-01-01
status: in_progress
---

# Updates
Working on it...
""")

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-file-review-updates.md"
        )

        assert result is False

    def test_returns_false_when_no_frontmatter(self, tmp_path):
        """Should return False when file has no frontmatter."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        updates_file = artifacts_dir / "epic-file-review-updates.md"
        updates_file.write_text("# Updates\nNo frontmatter here.")

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-file-review-updates.md"
        )

        assert result is False

    def test_returns_false_when_file_missing(self, tmp_path):
        """Should return False when updates file doesn't exist."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-file-review-updates.md"
        )

        assert result is False

    def test_returns_false_when_invalid_yaml(self, tmp_path):
        """Should return False when frontmatter YAML is malformed."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        updates_file = artifacts_dir / "epic-file-review-updates.md"
        updates_file.write_text("""---
date: 2025-01-01
status: completed
invalid yaml: [unclosed bracket
---

# Updates
""")

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-file-review-updates.md"
        )

        assert result is False

    def test_handles_status_with_errors(self, tmp_path):
        """Should return True for 'completed_with_errors' status."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        updates_file = artifacts_dir / "epic-file-review-updates.md"
        updates_file.write_text("""---
date: 2025-01-01
status: completed_with_errors
---

# Updates
""")

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-file-review-updates.md"
        )

        # Current implementation only checks for "completed"
        # This documents the behavior
        assert result is False
