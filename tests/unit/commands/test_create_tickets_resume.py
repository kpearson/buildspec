"""Unit tests for create-tickets auto-resume functionality."""

import pytest
from pathlib import Path

from cli.commands.create_tickets import (
    _check_tickets_exist,
    _check_review_completed,
    _check_review_feedback_applied,
)


class TestCheckTicketsExist:
    """Test ticket existence detection."""

    def test_returns_true_when_tickets_exist(self, tmp_path):
        """Should return True when ticket markdown files exist."""
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "TICK-001.md").write_text("# Ticket 1")
        (tickets_dir / "TICK-002.md").write_text("# Ticket 2")

        result = _check_tickets_exist(tickets_dir)

        assert result is True

    def test_returns_false_when_no_tickets(self, tmp_path):
        """Should return False when tickets directory is empty."""
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()

        result = _check_tickets_exist(tickets_dir)

        assert result is False

    def test_returns_false_when_directory_missing(self, tmp_path):
        """Should return False when tickets directory doesn't exist."""
        tickets_dir = tmp_path / "tickets"

        result = _check_tickets_exist(tickets_dir)

        assert result is False

    def test_ignores_non_markdown_files(self, tmp_path):
        """Should only count .md files as tickets."""
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "notes.txt").write_text("notes")
        (tickets_dir / "data.json").write_text("{}")

        result = _check_tickets_exist(tickets_dir)

        assert result is False

    def test_counts_single_ticket_as_existing(self, tmp_path):
        """Should return True even with just one ticket file."""
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "TICK-001.md").write_text("# Ticket 1")

        result = _check_tickets_exist(tickets_dir)

        assert result is True


class TestCheckReviewCompleted:
    """Test review artifact detection."""

    def test_returns_true_when_review_exists(self, tmp_path):
        """Should return True when review artifact exists."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        review_file = artifacts_dir / "epic-review.md"
        review_file.write_text("# Epic Review")

        result = _check_review_completed(artifacts_dir, "epic-review.md")

        assert result is True

    def test_returns_false_when_review_missing(self, tmp_path):
        """Should return False when review artifact doesn't exist."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        result = _check_review_completed(artifacts_dir, "epic-review.md")

        assert result is False

    def test_returns_false_when_artifacts_dir_missing(self, tmp_path):
        """Should return False when artifacts directory doesn't exist."""
        artifacts_dir = tmp_path / "artifacts"

        result = _check_review_completed(artifacts_dir, "epic-review.md")

        assert result is False


class TestCheckReviewFeedbackApplied:
    """Test review feedback completion detection."""

    def test_returns_true_when_status_completed(self, tmp_path):
        """Should return True when status is 'completed' in frontmatter."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        updates_file = artifacts_dir / "epic-review-updates.md"
        updates_file.write_text("""---
date: 2025-01-01
status: completed
---

# Epic Review Updates
All changes applied.
""")

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-review-updates.md"
        )

        assert result is True

    def test_returns_false_when_status_in_progress(self, tmp_path):
        """Should return False when status is 'in_progress'."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        updates_file = artifacts_dir / "epic-review-updates.md"
        updates_file.write_text("""---
date: 2025-01-01
status: in_progress
---

# Updates
""")

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-review-updates.md"
        )

        assert result is False

    def test_returns_false_when_no_frontmatter(self, tmp_path):
        """Should return False when file has no frontmatter."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        updates_file = artifacts_dir / "epic-review-updates.md"
        updates_file.write_text("# Updates\nPlain markdown.")

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-review-updates.md"
        )

        assert result is False

    def test_returns_false_when_file_missing(self, tmp_path):
        """Should return False when updates file doesn't exist."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-review-updates.md"
        )

        assert result is False

    def test_handles_malformed_frontmatter(self, tmp_path):
        """Should return False gracefully when YAML is malformed."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        updates_file = artifacts_dir / "epic-review-updates.md"
        updates_file.write_text("""---
this is not: valid: yaml: format
---

# Updates
""")

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-review-updates.md"
        )

        assert result is False

    def test_handles_empty_frontmatter(self, tmp_path):
        """Should return False when frontmatter exists but is empty."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        updates_file = artifacts_dir / "epic-review-updates.md"
        updates_file.write_text("""---
---

# Updates
""")

        result = _check_review_feedback_applied(
            artifacts_dir, "epic-review-updates.md"
        )

        assert result is False
