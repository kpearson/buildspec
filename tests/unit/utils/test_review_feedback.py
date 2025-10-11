"""Unit tests for review_feedback module."""

import os
import re
import stat
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path
from typing import List
from unittest.mock import patch

import pytest
import yaml

from cli.utils.review_feedback import (
    ReviewTargets,
    _create_fallback_updates_doc,
    _create_template_doc,
)


class TestReviewTargets:
    """Test suite for ReviewTargets dataclass."""

    def test_review_targets_creation_with_all_fields(self):
        """Verify dataclass can be instantiated with all required fields."""
        targets = ReviewTargets(
            primary_file=Path(".epics/test/test.epic.yaml"),
            additional_files=[Path(".epics/test/tickets/TST-001.md")],
            editable_directories=[Path(".epics/test")],
            artifacts_dir=Path(".epics/test/artifacts"),
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="epic-file-review.log",
            error_file_name="epic-file-review-errors.log",
            epic_name="test-epic",
            reviewer_session_id="550e8400-e29b-41d4-a716-446655440000",
            review_type="epic-file",
        )

        assert targets.primary_file == Path(".epics/test/test.epic.yaml")
        assert targets.additional_files == [
            Path(".epics/test/tickets/TST-001.md")
        ]
        assert targets.editable_directories == [Path(".epics/test")]
        assert targets.artifacts_dir == Path(".epics/test/artifacts")
        assert targets.updates_doc_name == "epic-file-review-updates.md"
        assert targets.log_file_name == "epic-file-review.log"
        assert targets.error_file_name == "epic-file-review-errors.log"
        assert targets.epic_name == "test-epic"
        assert (
            targets.reviewer_session_id
            == "550e8400-e29b-41d4-a716-446655440000"
        )
        assert targets.review_type == "epic-file"

    def test_review_targets_type_hints_present(self):
        """Verify all fields have correct type annotations."""
        type_hints = {
            field.name: field.type for field in fields(ReviewTargets)
        }

        assert type_hints["primary_file"] == Path
        assert type_hints["additional_files"] == List[Path]
        assert type_hints["editable_directories"] == List[Path]
        assert type_hints["artifacts_dir"] == Path
        assert type_hints["updates_doc_name"] is str
        assert type_hints["log_file_name"] is str
        assert type_hints["error_file_name"] is str
        assert type_hints["epic_name"] is str
        assert type_hints["reviewer_session_id"] is str

        # Check that review_type has Literal type hint
        review_type_field = next(
            f for f in fields(ReviewTargets) if f.name == "review_type"
        )
        assert "Literal" in str(review_type_field.type)

    def test_review_targets_epic_file_review_type(self):
        """Verify review_type can be set to 'epic-file' literal."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test",
            reviewer_session_id="test-id",
            review_type="epic-file",
        )

        assert targets.review_type == "epic-file"

    def test_review_targets_epic_review_type(self):
        """Verify review_type can be set to 'epic' literal."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test",
            reviewer_session_id="test-id",
            review_type="epic",
        )

        assert targets.review_type == "epic"

    def test_review_targets_path_fields_accept_path_objects(self):
        """Verify Path fields accept pathlib.Path instances."""
        primary = Path("/absolute/path/to/epic.yaml")
        additional = [
            Path("/absolute/path/to/ticket1.md"),
            Path("/absolute/path/to/ticket2.md"),
        ]
        editable = [Path("/absolute/path/to/dir1"), Path("/absolute/dir2")]
        artifacts = Path("/absolute/path/to/artifacts")

        targets = ReviewTargets(
            primary_file=primary,
            additional_files=additional,
            editable_directories=editable,
            artifacts_dir=artifacts,
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test",
            reviewer_session_id="test-id",
            review_type="epic",
        )

        assert isinstance(targets.primary_file, Path)
        assert all(isinstance(p, Path) for p in targets.additional_files)
        assert all(isinstance(p, Path) for p in targets.editable_directories)
        assert isinstance(targets.artifacts_dir, Path)

    def test_review_targets_additional_files_empty_list(self):
        """Verify additional_files can be empty list."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[Path("dir")],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test",
            reviewer_session_id="test-id",
            review_type="epic-file",
        )

        assert targets.additional_files == []

    def test_review_targets_editable_directories_empty_list(self):
        """Verify editable_directories can be empty list."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test",
            reviewer_session_id="test-id",
            review_type="epic-file",
        )

        assert targets.editable_directories == []

    def test_review_targets_immutability(self):
        """Verify dataclass fields can be modified (not frozen)."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test",
            reviewer_session_id="test-id",
            review_type="epic-file",
        )

        # Dataclass is not frozen, so fields can be modified
        targets.epic_name = "modified"
        assert targets.epic_name == "modified"

    def test_review_targets_string_representation(self):
        """Verify __repr__ shows all fields clearly."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[Path("ticket.md")],
            editable_directories=[Path("dir")],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="test-session-id",
            review_type="epic",
        )

        repr_str = repr(targets)

        # Check that key fields appear in representation
        assert "ReviewTargets" in repr_str
        assert "primary_file" in repr_str
        assert "test.yaml" in repr_str
        assert "additional_files" in repr_str
        assert "ticket.md" in repr_str
        assert "epic_name" in repr_str
        assert "test-epic" in repr_str
        assert "review_type" in repr_str
        assert "epic" in repr_str


class TestReviewTargetsIntegration:
    """Integration tests for ReviewTargets."""

    def test_review_targets_with_real_paths(self, tmp_path):
        """Create ReviewTargets with real paths and verify resolution."""
        epic_file = tmp_path / "test.epic.yaml"
        ticket_file = tmp_path / "ticket.md"
        artifacts_dir = tmp_path / "artifacts"

        # Create files
        epic_file.touch()
        ticket_file.touch()
        artifacts_dir.mkdir()

        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[ticket_file],
            editable_directories=[tmp_path],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="550e8400-e29b-41d4-a716-446655440000",
            review_type="epic",
        )

        # Verify paths resolve correctly
        assert targets.primary_file.exists()
        assert targets.additional_files[0].exists()
        assert targets.artifacts_dir.exists()
        assert targets.editable_directories[0].exists()

        # Verify paths are absolute after resolution
        assert targets.primary_file.resolve().is_absolute()

    def test_review_targets_serialization(self):
        """Verify ReviewTargets can be converted to dict for logging."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[Path("ticket1.md"), Path("ticket2.md")],
            editable_directories=[Path("dir1"), Path("dir2")],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="550e8400-e29b-41d4-a716-446655440000",
            review_type="epic",
        )

        # Convert to dict
        targets_dict = asdict(targets)

        # Verify all fields present
        assert "primary_file" in targets_dict
        assert "additional_files" in targets_dict
        assert "editable_directories" in targets_dict
        assert "artifacts_dir" in targets_dict
        assert "updates_doc_name" in targets_dict
        assert "log_file_name" in targets_dict
        assert "error_file_name" in targets_dict
        assert "epic_name" in targets_dict
        assert "reviewer_session_id" in targets_dict
        assert "review_type" in targets_dict

        # Verify values
        assert targets_dict["epic_name"] == "test-epic"
        assert targets_dict["review_type"] == "epic"
        assert len(targets_dict["additional_files"]) == 2


class TestCreateTemplateDoc:
    """Test suite for _create_template_doc() function."""

    def test_create_template_doc_creates_file(self, tmp_path):
        """Verify file is created at correct path with temp directory."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        _create_template_doc(targets, "builder-session-id")

        template_path = tmp_path / "artifacts" / "updates.md"
        assert template_path.exists()
        assert template_path.is_file()

    def test_create_template_doc_includes_frontmatter(self, tmp_path):
        """Verify frontmatter YAML is present and parseable."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        _create_template_doc(targets, "builder-session-id")

        template_path = tmp_path / "artifacts" / "updates.md"
        content = template_path.read_text(encoding="utf-8")

        # Extract frontmatter
        assert content.startswith("---\n")
        frontmatter_end = content.find("\n---\n", 4)
        assert frontmatter_end > 0

        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        assert isinstance(frontmatter, dict)
        assert "date" in frontmatter
        assert "epic" in frontmatter
        assert "builder_session_id" in frontmatter
        assert "reviewer_session_id" in frontmatter
        assert "status" in frontmatter

    def test_create_template_doc_frontmatter_date_format(self, tmp_path):
        """Verify date field matches YYYY-MM-DD pattern."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        _create_template_doc(targets, "builder-session-id")

        template_path = tmp_path / "artifacts" / "updates.md"
        content = template_path.read_text(encoding="utf-8")

        # Extract frontmatter
        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        # Verify date format YYYY-MM-DD
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        # YAML parser may return a date object or string
        date_str = (
            frontmatter["date"]
            if isinstance(frontmatter["date"], str)
            else frontmatter["date"].strftime("%Y-%m-%d")
        )
        assert re.match(date_pattern, date_str)

        # Verify it's today's date
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert date_str == expected_date

    def test_create_template_doc_frontmatter_epic_name(self, tmp_path):
        """Verify epic field equals targets.epic_name."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="my-special-epic",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        _create_template_doc(targets, "builder-session-id")

        template_path = tmp_path / "artifacts" / "updates.md"
        content = template_path.read_text(encoding="utf-8")

        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        assert frontmatter["epic"] == "my-special-epic"

    def test_create_template_doc_frontmatter_builder_session_id(self, tmp_path):
        """Verify builder_session_id field is set correctly."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        _create_template_doc(targets, "my-builder-session-123")

        template_path = tmp_path / "artifacts" / "updates.md"
        content = template_path.read_text(encoding="utf-8")

        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        assert frontmatter["builder_session_id"] == "my-builder-session-123"

    def test_create_template_doc_frontmatter_reviewer_session_id(
        self, tmp_path
    ):
        """Verify reviewer_session_id equals targets.reviewer_session_id."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="my-reviewer-session-456",
            review_type="epic-file",
        )

        _create_template_doc(targets, "builder-session-id")

        template_path = tmp_path / "artifacts" / "updates.md"
        content = template_path.read_text(encoding="utf-8")

        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        assert frontmatter["reviewer_session_id"] == "my-reviewer-session-456"

    def test_create_template_doc_frontmatter_status_in_progress(self, tmp_path):
        """Verify status field is exactly 'in_progress'."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        _create_template_doc(targets, "builder-session-id")

        template_path = tmp_path / "artifacts" / "updates.md"
        content = template_path.read_text(encoding="utf-8")

        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        assert frontmatter["status"] == "in_progress"

    def test_create_template_doc_includes_placeholder_sections(self, tmp_path):
        """Verify body has required placeholder section headings."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        _create_template_doc(targets, "builder-session-id")

        template_path = tmp_path / "artifacts" / "updates.md"
        content = template_path.read_text(encoding="utf-8")

        # Verify required sections are present
        assert "## Changes Applied" in content
        assert "## Files Modified" in content
        assert "## Review Feedback Addressed" in content

        # Verify in-progress messaging
        assert "Review feedback is being applied..." in content
        assert (
            "This template will be replaced by Claude with documentation "
            "of changes made" in content
        )

    def test_create_template_doc_creates_parent_directories(self, tmp_path):
        """Verify function creates nested directories if they don't exist."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "nested" / "deep" / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        # Verify directories don't exist yet
        assert not (tmp_path / "nested").exists()

        _create_template_doc(targets, "builder-session-id")

        # Verify directories were created
        assert (tmp_path / "nested").exists()
        assert (tmp_path / "nested" / "deep").exists()
        assert (tmp_path / "nested" / "deep" / "artifacts").exists()

        template_path = (
            tmp_path / "nested" / "deep" / "artifacts" / "updates.md"
        )
        assert template_path.exists()

    def test_create_template_doc_overwrites_existing_file(self, tmp_path):
        """Verify function overwrites existing template if called again."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        # Create directory and file with different content
        (tmp_path / "artifacts").mkdir()
        template_path = tmp_path / "artifacts" / "updates.md"
        template_path.write_text("Old content", encoding="utf-8")

        original_mtime = template_path.stat().st_mtime

        # Call function to overwrite
        _create_template_doc(targets, "builder-session-id")

        # Verify file was overwritten
        content = template_path.read_text(encoding="utf-8")
        assert "Old content" not in content
        assert "status: in_progress" in content
        assert template_path.stat().st_mtime >= original_mtime

    def test_create_template_doc_utf8_encoding(self, tmp_path):
        """Verify file is written with UTF-8 encoding (test with unicode)."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic-with-émojis-🎉",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        _create_template_doc(targets, "builder-session-id")

        template_path = tmp_path / "artifacts" / "updates.md"

        # Read with UTF-8 encoding explicitly
        content = template_path.read_text(encoding="utf-8")

        # Verify unicode characters are preserved
        assert "test-epic-with-émojis-🎉" in content

        # Verify file can be read as UTF-8 without errors
        with open(template_path, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) > 0

    def test_create_template_doc_permission_error(self, tmp_path):
        """Verify function raises clear error if directory is not writable."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "readonly_artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        # Create directory and make it read-only
        readonly_dir = tmp_path / "readonly_artifacts"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, stat.S_IRUSR | stat.S_IXUSR)

        try:
            # Attempt to create template should raise OSError
            with pytest.raises(OSError):
                _create_template_doc(targets, "builder-session-id")
        finally:
            # Clean up: restore write permissions
            os.chmod(
                readonly_dir,
                stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR,
            )

    def test_create_template_doc_disk_full_error(self, tmp_path):
        """Verify function handles OSError when disk is full."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-session-id",
            review_type="epic-file",
        )

        # Mock write_text to raise OSError simulating disk full
        with patch.object(
            Path, "write_text", side_effect=OSError("No space left on device")
        ):
            with pytest.raises(OSError) as exc_info:
                _create_template_doc(targets, "builder-session-id")

            assert "No space left on device" in str(exc_info.value)


class TestCreateTemplateDocIntegration:
    """Integration tests for _create_template_doc() function."""

    def test_create_template_doc_roundtrip(self, tmp_path):
        """Create template, read it back, verify frontmatter can be parsed."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="review-updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="integration-test-epic",
            reviewer_session_id="550e8400-e29b-41d4-a716-446655440000",
            review_type="epic",
        )

        builder_session_id = "abcd1234-5678-90ef-ghij-klmnopqrstuv"

        # Create template
        _create_template_doc(targets, builder_session_id)

        # Read it back
        template_path = tmp_path / "artifacts" / "review-updates.md"
        content = template_path.read_text(encoding="utf-8")

        # Parse frontmatter
        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        # Verify all fields are correct
        # YAML parser may return a date object or string
        date_str = (
            frontmatter["date"]
            if isinstance(frontmatter["date"], str)
            else frontmatter["date"].strftime("%Y-%m-%d")
        )
        assert date_str == datetime.now().strftime("%Y-%m-%d")
        assert frontmatter["epic"] == "integration-test-epic"
        assert frontmatter["builder_session_id"] == builder_session_id
        assert (
            frontmatter["reviewer_session_id"]
            == "550e8400-e29b-41d4-a716-446655440000"
        )
        assert frontmatter["status"] == "in_progress"

        # Verify body content
        body = content[frontmatter_end + 5 :]
        assert "Review Feedback Application In Progress" in body
        assert "## Changes Applied" in body
        assert "## Files Modified" in body
        assert "## Review Feedback Addressed" in body

    def test_create_template_doc_with_real_targets(self, tmp_path):
        """Create ReviewTargets with real paths and verify template created."""
        # Set up realistic directory structure
        epic_dir = tmp_path / ".epics" / "test-epic"
        artifacts_dir = epic_dir / "artifacts"
        tickets_dir = epic_dir / "tickets"

        epic_dir.mkdir(parents=True)
        tickets_dir.mkdir()

        epic_file = epic_dir / "test-epic.epic.yaml"
        epic_file.write_text("name: test-epic\n", encoding="utf-8")

        ticket_file = tickets_dir / "TST-001.md"
        ticket_file.write_text("# TST-001\n", encoding="utf-8")

        # Create ReviewTargets
        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[ticket_file],
            editable_directories=[epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-review-updates.md",
            log_file_name="epic-review.log",
            error_file_name="epic-review-errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic",
        )

        # Create template
        _create_template_doc(targets, "builder-456")

        # Verify template was created
        template_path = artifacts_dir / "epic-review-updates.md"
        assert template_path.exists()

        # Verify content is valid
        content = template_path.read_text(encoding="utf-8")
        assert "status: in_progress" in content
        assert "epic: test-epic" in content
        assert "builder_session_id: builder-456" in content
        assert "reviewer_session_id: reviewer-123" in content


class TestBuildFeedbackPrompt:
    """Test suite for _build_feedback_prompt() function."""

    def test_build_feedback_prompt_epic_file_review_type(self):
        """Verify prompt for epic-file review includes only epic YAML in editable files."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path(".epics/test/test.epic.yaml"),
            additional_files=[],
            editable_directories=[Path(".epics/test")],
            artifacts_dir=Path(".epics/test/artifacts"),
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        prompt = _build_feedback_prompt(
            "Test review content", targets, "builder-456"
        )

        # Verify prompt mentions epic file
        assert str(targets.primary_file) in prompt
        # Verify prompt doesn't mention ticket files (empty list)
        assert "**Ticket files**:" not in prompt
        # Verify it's for epic-file review
        assert "Epic File Review Updates" in prompt

    def test_build_feedback_prompt_epic_review_type(self):
        """Verify prompt for epic review includes both epic YAML and ticket files."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path(".epics/test/test.epic.yaml"),
            additional_files=[
                Path(".epics/test/tickets/TST-001.md"),
                Path(".epics/test/tickets/TST-002.md"),
            ],
            editable_directories=[Path(".epics/test")],
            artifacts_dir=Path(".epics/test/artifacts"),
            updates_doc_name="epic-review-updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic",
        )

        prompt = _build_feedback_prompt(
            "Test review content", targets, "builder-456"
        )

        # Verify prompt mentions both epic and ticket files
        assert str(targets.primary_file) in prompt
        assert "**Ticket files**:" in prompt
        assert "TST-001.md" in prompt
        assert "TST-002.md" in prompt
        # Verify it's for epic review
        assert "Epic Review Updates" in prompt

    def test_build_feedback_prompt_includes_review_content(self):
        """Verify review_content parameter is included verbatim in prompt."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        review_content = "This is the review feedback with specific content."
        prompt = _build_feedback_prompt(review_content, targets, "builder-456")

        # Verify review content is included verbatim
        assert review_content in prompt

    def test_build_feedback_prompt_includes_builder_session_id(self):
        """Verify builder_session_id appears in frontmatter example."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        builder_session_id = "my-builder-session-789"
        prompt = _build_feedback_prompt(
            "Review content", targets, builder_session_id
        )

        # Verify builder_session_id appears in prompt
        assert builder_session_id in prompt
        assert "builder_session_id:" in prompt

    def test_build_feedback_prompt_includes_reviewer_session_id(self):
        """Verify targets.reviewer_session_id appears in frontmatter example."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="my-reviewer-session-999",
            review_type="epic-file",
        )

        prompt = _build_feedback_prompt(
            "Review content", targets, "builder-456"
        )

        # Verify reviewer_session_id appears in prompt
        assert "my-reviewer-session-999" in prompt
        assert "reviewer_session_id:" in prompt

    def test_build_feedback_prompt_includes_artifacts_path(self):
        """Verify prompt references targets.artifacts_dir/targets.updates_doc_name."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path(".epics/my-epic/artifacts"),
            updates_doc_name="my-updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        prompt = _build_feedback_prompt(
            "Review content", targets, "builder-456"
        )

        # Verify the full path is in the prompt
        expected_path = str(
            targets.artifacts_dir / targets.updates_doc_name
        )
        assert expected_path in prompt

    def test_build_feedback_prompt_includes_all_8_sections(self):
        """Verify all required sections present using regex pattern matching."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        prompt = _build_feedback_prompt(
            "Review content", targets, "builder-456"
        )

        # Section 1: Documentation requirement
        assert re.search(
            r"CRITICAL REQUIREMENT.*Document Your Work", prompt, re.DOTALL
        )

        # Section 2: Task description
        assert re.search(r"Your Task:.*Apply Review Feedback", prompt)

        # Section 3: Review content (embedded)
        assert "Review content" in prompt

        # Section 4: Workflow steps
        assert "### Workflow" in prompt
        assert re.search(r"\d+\.\s+\*\*Read\*\*", prompt)

        # Section 5: What to fix
        assert "### What to Fix" in prompt
        assert "Priority 1" in prompt
        assert "Priority 2" in prompt

        # Section 6: Important rules
        assert "### Important Rules" in prompt

        # Section 7: Example edits
        assert "### Example Surgical Edit" in prompt

        # Section 8: Final documentation step
        assert "### Final Step" in prompt

    def test_build_feedback_prompt_section_order(self):
        """Verify sections appear in correct order."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        prompt = _build_feedback_prompt(
            "Review content", targets, "builder-456"
        )

        # Find positions of each section
        doc_requirement_pos = prompt.find("CRITICAL REQUIREMENT")
        task_desc_pos = prompt.find("Your Task:")
        workflow_pos = prompt.find("### Workflow")
        what_to_fix_pos = prompt.find("### What to Fix")
        important_rules_pos = prompt.find("### Important Rules")
        example_edits_pos = prompt.find("### Example Surgical Edit")
        final_step_pos = prompt.find("### Final Step")

        # Verify order
        assert doc_requirement_pos < task_desc_pos
        assert task_desc_pos < workflow_pos
        assert workflow_pos < what_to_fix_pos
        assert what_to_fix_pos < important_rules_pos
        assert important_rules_pos < example_edits_pos
        assert example_edits_pos < final_step_pos

    def test_build_feedback_prompt_epic_file_rules(self):
        """Verify 'epic-file' review has epic-specific rules only."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        prompt = _build_feedback_prompt(
            "Review content", targets, "builder-456"
        )

        # Verify epic-specific rules are present
        assert "PRESERVE" in prompt
        assert "existing epic structure" in prompt
        assert "KEEP" in prompt
        assert "ticket IDs unchanged" in prompt

        # Verify ticket-specific rules are NOT present
        assert "For Ticket Markdown Files:" not in prompt

    def test_build_feedback_prompt_epic_rules(self):
        """Verify 'epic' review has both epic and ticket rules."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[Path("ticket.md")],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic",
        )

        prompt = _build_feedback_prompt(
            "Review content", targets, "builder-456"
        )

        # Verify both epic and ticket rules are present
        assert "For Epic YAML:" in prompt
        assert "PRESERVE" in prompt
        assert "existing epic structure" in prompt
        assert "For Ticket Markdown Files:" in prompt
        assert "PRESERVE" in prompt
        assert "ticket frontmatter" in prompt

    def test_build_feedback_prompt_special_characters_escaped(self):
        """Verify review_content with special chars doesn't break prompt formatting."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Review content with special characters
        review_content = """
        Review with "quotes" and 'apostrophes'
        Newlines\n\nAnd more newlines
        Backslashes \\ and forward slashes /
        Unicode: 🎉 émoji café
        """

        prompt = _build_feedback_prompt(review_content, targets, "builder-456")

        # Verify special characters are preserved in prompt
        assert '"quotes"' in prompt
        assert "'apostrophes'" in prompt
        assert "🎉" in prompt
        assert "émoji" in prompt
        assert "café" in prompt

    def test_build_feedback_prompt_empty_review_content(self):
        """Verify function handles empty review_content gracefully."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Empty review content
        prompt = _build_feedback_prompt("", targets, "builder-456")

        # Verify prompt is still well-formed
        assert "CRITICAL REQUIREMENT" in prompt
        assert "Your Task:" in prompt
        assert "### Workflow" in prompt
        # Empty review content should still appear in structure
        assert len(prompt) > 100  # Prompt should still have substantial content

    def test_build_feedback_prompt_long_review_content(self):
        """Verify function handles very long review_content (10000+ chars)."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Very long review content (>10000 chars)
        review_content = "This is a very long review. " * 500

        prompt = _build_feedback_prompt(review_content, targets, "builder-456")

        # Verify entire review content is included
        assert review_content in prompt
        # Verify prompt structure is still intact
        assert "CRITICAL REQUIREMENT" in prompt
        assert "### Final Step" in prompt

    def test_build_feedback_prompt_markdown_formatting(self):
        """Verify prompt has proper markdown headings (##, ###, etc.)."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        prompt = _build_feedback_prompt(
            "Review content", targets, "builder-456"
        )

        # Verify markdown heading levels
        assert re.search(r"^##\s+", prompt, re.MULTILINE)  # Level 2 headings
        assert re.search(r"^###\s+", prompt, re.MULTILINE)  # Level 3 headings

        # Verify code blocks
        assert "```markdown" in prompt
        assert "```" in prompt

        # Verify bold formatting
        assert "**" in prompt


class TestBuildFeedbackPromptIntegration:
    """Integration tests for _build_feedback_prompt() function."""

    def test_build_feedback_prompt_with_real_targets(self, tmp_path):
        """Create ReviewTargets with real paths and verify prompt references them correctly."""
        from cli.utils.review_feedback import _build_feedback_prompt

        # Create realistic directory structure
        epic_dir = tmp_path / ".epics" / "test-epic"
        artifacts_dir = epic_dir / "artifacts"
        tickets_dir = epic_dir / "tickets"

        epic_dir.mkdir(parents=True)
        tickets_dir.mkdir()
        artifacts_dir.mkdir()

        epic_file = epic_dir / "test-epic.epic.yaml"
        epic_file.write_text("name: test-epic\n", encoding="utf-8")

        ticket_file = tickets_dir / "TST-001.md"
        ticket_file.write_text("# TST-001\n", encoding="utf-8")

        # Create ReviewTargets with real paths
        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[ticket_file],
            editable_directories=[epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-review-updates.md",
            log_file_name="epic-review.log",
            error_file_name="epic-review-errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic",
        )

        # Build prompt
        prompt = _build_feedback_prompt(
            "Test review content", targets, "builder-456"
        )

        # Verify all paths are referenced correctly
        assert str(epic_file) in prompt
        assert str(ticket_file) in prompt
        assert str(artifacts_dir / "epic-review-updates.md") in prompt

    def test_build_feedback_prompt_roundtrip(self):
        """Verify generated prompt can be parsed and contains expected content."""
        from cli.utils.review_feedback import _build_feedback_prompt

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=Path("artifacts"),
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Build prompt
        prompt = _build_feedback_prompt(
            "Test review content", targets, "builder-456"
        )

        # Parse and verify key elements
        lines = prompt.split("\n")

        # Check that prompt is multi-line
        assert len(lines) > 10

        # Check for markdown structure
        heading_count = sum(1 for line in lines if line.startswith("#"))
        assert heading_count > 5

        # Check for code blocks
        code_block_count = prompt.count("```")
        assert code_block_count >= 2  # At least one code block (opening and closing)

        # Check for frontmatter example
        assert "date:" in prompt
        assert "epic:" in prompt
        assert "builder_session_id:" in prompt
        assert "reviewer_session_id:" in prompt
        assert "status: completed" in prompt


class TestCreateFallbackDoc:
    """Test suite for _create_fallback_updates_doc() function."""

    def test_create_fallback_doc_creates_file(self, tmp_path):
        """Verify file is created at correct path."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        _create_fallback_updates_doc(
            targets, "Some stdout", "Some stderr", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        assert fallback_path.exists()
        assert fallback_path.is_file()

    def test_create_fallback_doc_frontmatter_status_with_errors(self, tmp_path):
        """Verify status is 'completed_with_errors' when stderr is not empty."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        _create_fallback_updates_doc(
            targets, "Some stdout", "Error occurred", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        # Extract frontmatter
        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        assert frontmatter["status"] == "completed_with_errors"

    def test_create_fallback_doc_frontmatter_status_completed(self, tmp_path):
        """Verify status is 'completed' when stderr is empty."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        _create_fallback_updates_doc(
            targets, "Some stdout", "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        assert frontmatter["status"] == "completed"

    def test_create_fallback_doc_includes_stdout(self, tmp_path):
        """Verify stdout is included in code block."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        test_stdout = "Edited file: /path/to/file.py\nRead file: /path/to/another.py"
        _create_fallback_updates_doc(
            targets, test_stdout, "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        assert "## Standard Output" in content
        assert test_stdout in content

    def test_create_fallback_doc_includes_stderr(self, tmp_path):
        """Verify stderr is included when not empty."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        test_stderr = "Error: File not found\nWarning: Validation failed"
        _create_fallback_updates_doc(
            targets, "Some stdout", test_stderr, "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        assert "## Standard Error" in content
        assert test_stderr in content

    def test_create_fallback_doc_omits_stderr_section_when_empty(self, tmp_path):
        """Verify stderr section is omitted when stderr is empty string."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        _create_fallback_updates_doc(
            targets, "Some stdout", "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        assert "## Standard Error" not in content

    def test_create_fallback_doc_detects_edited_files(self, tmp_path):
        """Verify 'Edited file: /path' pattern is detected and listed."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        stdout = "Edited file: /Users/kit/Code/buildspec/.epics/my-epic/my-epic.epic.yaml\nSome other output"
        _create_fallback_updates_doc(
            targets, stdout, "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        assert "## Files Potentially Modified" in content
        assert "/Users/kit/Code/buildspec/.epics/my-epic/my-epic.epic.yaml" in content

    def test_create_fallback_doc_detects_written_files(self, tmp_path):
        """Verify 'Wrote file: /path' pattern is detected and listed."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        stdout = "Wrote file: /path/to/new/file.md\nCompleted successfully"
        _create_fallback_updates_doc(
            targets, stdout, "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        assert "/path/to/new/file.md" in content

    def test_create_fallback_doc_deduplicates_file_paths(self, tmp_path):
        """Verify same file path listed only once even if edited multiple times."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        stdout = """Edited file: /path/to/file.py
Read file: /path/to/file.py
Edited file: /path/to/file.py
Wrote file: /path/to/file.py"""
        _create_fallback_updates_doc(
            targets, stdout, "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        # Count occurrences of the file path - should only appear once in list
        file_path = "/path/to/file.py"
        list_section = content.split("## Files Potentially Modified")[1].split("##")[0]
        occurrences = list_section.count(f"`{file_path}`")
        assert occurrences == 1

    def test_create_fallback_doc_empty_stdout(self, tmp_path):
        """Verify 'No output' message when stdout is empty."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        _create_fallback_updates_doc(
            targets, "", "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        assert "No output" in content

    def test_create_fallback_doc_empty_stderr(self, tmp_path):
        """Verify stderr section handling when stderr is empty."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        _create_fallback_updates_doc(
            targets, "Some output", "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        # Empty stderr should result in "completed" status and no stderr section
        assert "## Standard Error" not in content
        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)
        assert frontmatter["status"] == "completed"

    def test_create_fallback_doc_includes_next_steps(self, tmp_path):
        """Verify 'Next Steps' section provides manual verification guidance."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        _create_fallback_updates_doc(
            targets, "Some output", "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        assert "## Next Steps" in content
        assert "Review the stdout and stderr logs" in content
        assert "Manually verify the changes" in content

    def test_create_fallback_doc_utf8_encoding(self, tmp_path):
        """Verify file is written with UTF-8 encoding."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic-émojis-🎉",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        stdout_with_unicode = "Edited file: /path/to/file-émoji-🎉.py"
        _create_fallback_updates_doc(
            targets, stdout_with_unicode, "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        assert "test-epic-émojis-🎉" in content
        assert "file-émoji-🎉.py" in content

    def test_create_fallback_doc_frontmatter_date(self, tmp_path):
        """Verify date field uses current date in YYYY-MM-DD format."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        _create_fallback_updates_doc(
            targets, "output", "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        # Verify date format YYYY-MM-DD
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        date_str = (
            frontmatter["date"]
            if isinstance(frontmatter["date"], str)
            else frontmatter["date"].strftime("%Y-%m-%d")
        )
        assert re.match(date_pattern, date_str)
        assert date_str == datetime.now().strftime("%Y-%m-%d")

    def test_create_fallback_doc_frontmatter_epic_name(self, tmp_path):
        """Verify epic field matches targets.epic_name."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="my-special-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        _create_fallback_updates_doc(
            targets, "output", "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        assert frontmatter["epic"] == "my-special-epic"

    def test_create_fallback_doc_frontmatter_session_ids(self, tmp_path):
        """Verify both builder and reviewer session IDs are included."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-session-789",
            review_type="epic-file",
        )

        _create_fallback_updates_doc(
            targets, "output", "", "builder-session-123"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        assert frontmatter["builder_session_id"] == "builder-session-123"
        assert frontmatter["reviewer_session_id"] == "reviewer-session-789"

    def test_create_fallback_doc_long_stdout(self, tmp_path):
        """Verify function handles very long stdout (100000+ chars)."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Create very long stdout
        long_stdout = "Line of output\n" * 10000  # ~150K chars
        _create_fallback_updates_doc(
            targets, long_stdout, "", "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        assert fallback_path.exists()
        content = fallback_path.read_text(encoding="utf-8")

        # Verify long content is included
        assert len(content) > 100000
        assert "Line of output" in content

    def test_create_fallback_doc_special_chars_in_output(self, tmp_path):
        """Verify special characters in stdout/stderr don't break markdown formatting."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        special_stdout = "```\n# Header\n**Bold** _italic_\n[link](url)\n<!-- comment -->"
        special_stderr = "Error: `code` **failed**"
        _create_fallback_updates_doc(
            targets, special_stdout, special_stderr, "builder-456"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        # Verify special chars are preserved in code blocks
        assert "```\n# Header" in content
        assert "**Bold**" in content
        assert "`code`" in content


class TestCreateFallbackDocIntegration:
    """Integration tests for _create_fallback_updates_doc()."""

    def test_create_fallback_doc_roundtrip(self, tmp_path):
        """Create fallback doc, read it back, verify frontmatter is parseable."""
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=tmp_path / "artifacts",
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="integration-test",
            reviewer_session_id="reviewer-abc",
            review_type="epic",
        )

        stdout = "Edited file: /path/to/file.py\nWrote file: /path/to/doc.md"
        stderr = "Warning: Something happened"

        _create_fallback_updates_doc(
            targets, stdout, stderr, "builder-xyz"
        )

        fallback_path = tmp_path / "artifacts" / "updates.md"
        content = fallback_path.read_text(encoding="utf-8")

        # Parse frontmatter
        frontmatter_end = content.find("\n---\n", 4)
        frontmatter_text = content[4:frontmatter_end]
        frontmatter = yaml.safe_load(frontmatter_text)

        # Verify all frontmatter fields
        assert "date" in frontmatter
        assert frontmatter["epic"] == "integration-test"
        assert frontmatter["builder_session_id"] == "builder-xyz"
        assert frontmatter["reviewer_session_id"] == "reviewer-abc"
        assert frontmatter["status"] == "completed_with_errors"

        # Verify body sections
        body = content[frontmatter_end + 5:]
        assert "## Status" in body
        assert "## What Happened" in body
        assert "## Standard Output" in body
        assert "## Standard Error" in body
        assert "## Files Potentially Modified" in body
        assert "## Next Steps" in body

        # Verify file detection worked
        assert "/path/to/file.py" in content
        assert "/path/to/doc.md" in content


class TestApplyReviewFeedback:
    """Test suite for apply_review_feedback() function."""

    def test_apply_review_feedback_success_epic_file(
        self, tmp_path, mocker
    ):
        """Verify full workflow for epic-file review with successful completion."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        epic_dir = tmp_path / ".epics" / "test-epic"
        artifacts_dir = epic_dir / "artifacts"
        epic_dir.mkdir(parents=True)

        epic_file = epic_dir / "test.epic.yaml"
        epic_file.write_text("name: test-epic\n", encoding="utf-8")

        review_artifact = artifacts_dir / "review.md"
        review_artifact.parent.mkdir(parents=True, exist_ok=True)
        review_artifact.write_text(
            "## Review Feedback\nFix Priority 1 issues", encoding="utf-8"
        )

        # Create ReviewTargets
        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[],
            editable_directories=[epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="review.log",
            error_file_name="review-errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Mock subprocess to simulate successful Claude execution
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Edited file: /path/to/test.epic.yaml"
        mock_result.stderr = ""

        mock_subprocess = mocker.patch("subprocess.run", return_value=mock_result)

        # Mock console with status context manager
        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()

        # Mock context
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Create completed documentation (simulating Claude's success)
        def create_completed_doc(*args, **kwargs):
            # After subprocess runs, create the completed doc
            updates_path = artifacts_dir / "updates.md"
            updates_path.write_text(
                f"""---
date: {datetime.now().strftime('%Y-%m-%d')}
epic: test-epic
builder_session_id: builder-456
reviewer_session_id: reviewer-123
status: completed
---

# Epic File Review Updates

## Changes Applied

### Priority 1 Fixes
- Fixed coordination requirements
""",
                encoding="utf-8",
            )
            return mock_result

        mock_subprocess.side_effect = create_completed_doc

        # Execute
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="builder-456",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Verify subprocess was called with correct parameters
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[1]["input"] is not None  # Prompt was passed
        assert "builder-456" in call_args[0][0]  # Session ID in command

        # Verify success console output
        assert any(
            "successfully" in str(call)
            for call in mock_console.print.call_args_list
        )

        # Verify documentation exists and has completed status
        updates_path = artifacts_dir / "updates.md"
        assert updates_path.exists()
        content = updates_path.read_text(encoding="utf-8")
        assert "status: completed" in content

    def test_apply_review_feedback_success_epic(self, tmp_path, mocker):
        """Verify full workflow for epic review including ticket files."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        epic_dir = tmp_path / ".epics" / "test-epic"
        tickets_dir = epic_dir / "tickets"
        artifacts_dir = epic_dir / "artifacts"
        epic_dir.mkdir(parents=True)
        tickets_dir.mkdir()

        epic_file = epic_dir / "test.epic.yaml"
        epic_file.write_text("name: test-epic\n", encoding="utf-8")

        ticket_file = tickets_dir / "TST-001.md"
        ticket_file.write_text("# TST-001\n", encoding="utf-8")

        review_artifact = artifacts_dir / "review.md"
        review_artifact.parent.mkdir(parents=True, exist_ok=True)
        review_artifact.write_text(
            "## Review\nImprove tickets", encoding="utf-8"
        )

        # Create ReviewTargets for epic review
        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[ticket_file],
            editable_directories=[epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-review-updates.md",
            log_file_name="epic-review.log",
            error_file_name="epic-review-errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-789",
            review_type="epic",
        )

        # Mock subprocess
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "Edited file: /path/to/test.epic.yaml\n"
            "Edited file: /path/to/TST-001.md"
        )
        mock_result.stderr = ""

        mock_subprocess = mocker.patch("subprocess.run", return_value=mock_result)

        # Mock console with status context manager
        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()

        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Create completed documentation
        def create_completed_doc(*args, **kwargs):
            updates_path = artifacts_dir / "epic-review-updates.md"
            updates_path.write_text(
                f"""---
date: {datetime.now().strftime('%Y-%m-%d')}
epic: test-epic
builder_session_id: builder-999
reviewer_session_id: reviewer-789
status: completed
---

# Epic Review Updates

## Changes Applied
- Updated epic and tickets
""",
                encoding="utf-8",
            )
            return mock_result

        mock_subprocess.side_effect = create_completed_doc

        # Execute
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="builder-999",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Verify both epic and ticket mentioned in prompt
        call_args = mock_subprocess.call_args
        prompt = call_args[1]["input"]
        assert str(epic_file) in prompt
        assert "TST-001.md" in prompt

        # Verify success
        updates_path = artifacts_dir / "epic-review-updates.md"
        assert updates_path.exists()

    def test_apply_review_feedback_missing_review_artifact(
        self, tmp_path, mocker
    ):
        """Verify FileNotFoundError raised when review artifact missing."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create targets without creating review artifact
        artifacts_dir = tmp_path / "artifacts"
        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()

        # Execute and expect FileNotFoundError
        with pytest.raises(FileNotFoundError):
            apply_review_feedback(
                review_artifact_path=tmp_path / "nonexistent.md",
                builder_session_id="builder-456",
                context=mock_context,
                targets=targets,
                console=mock_console,
            )

        # Verify error was logged to console
        assert any(
            "Error" in str(call) for call in mock_console.print.call_args_list
        )

    def test_apply_review_feedback_malformed_yaml(self, tmp_path, mocker):
        """Verify yaml.YAMLError handling when frontmatter is malformed."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        review_artifact = artifacts_dir / "review.md"
        review_artifact.write_text("Review content", encoding="utf-8")

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Mock subprocess to create doc with malformed YAML
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Output"
        mock_result.stderr = ""

        def create_malformed_doc(*args, **kwargs):
            updates_path = artifacts_dir / "updates.md"
            # Invalid YAML frontmatter (unclosed quote)
            updates_path.write_text(
                '---\nstatus: "incomplete\n---\ncontent',
                encoding="utf-8",
            )
            return mock_result

        mocker.patch("subprocess.run", side_effect=create_malformed_doc)

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Execute - should handle YAML error gracefully
        # The function logs the error but creates fallback doc
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="builder-456",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Verify fallback doc was created
        updates_path = artifacts_dir / "updates.md"
        assert updates_path.exists()

    def test_apply_review_feedback_claude_failure_creates_fallback(
        self, tmp_path, mocker
    ):
        """Verify fallback doc created when Claude session fails."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        review_artifact = artifacts_dir / "review.md"
        review_artifact.write_text("Review", encoding="utf-8")

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Mock subprocess to simulate Claude failure
        mocker.patch(
            "subprocess.run",
            side_effect=Exception("Claude crashed"),
        )

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Execute - should handle exception and create fallback
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="builder-456",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Verify fallback doc was created
        fallback_path = artifacts_dir / "updates.md"
        assert fallback_path.exists()
        content = fallback_path.read_text(encoding="utf-8")
        assert "status: completed" in content or "status: completed_with_errors" in content

        # Verify console showed warning
        assert any(
            "fallback" in str(call).lower()
            for call in mock_console.print.call_args_list
        )

    def test_apply_review_feedback_template_not_updated_creates_fallback(
        self, tmp_path, mocker
    ):
        """Verify fallback created when Claude doesn't update template (status=in_progress)."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        review_artifact = artifacts_dir / "review.md"
        review_artifact.write_text("Review", encoding="utf-8")

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Mock subprocess - succeeds but doesn't update template
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Some output"
        mock_result.stderr = ""

        # Template stays as "in_progress" (not updated by Claude)
        mocker.patch("subprocess.run", return_value=mock_result)

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Execute
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="builder-456",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Verify fallback was created (because template wasn't updated)
        updates_path = artifacts_dir / "updates.md"
        assert updates_path.exists()
        content = updates_path.read_text(encoding="utf-8")

        # Template should have been replaced with fallback
        assert "status: completed" in content or "status: completed_with_errors" in content
        assert "## Standard Output" in content

    def test_apply_review_feedback_logs_stdout_stderr(
        self, tmp_path, mocker
    ):
        """Verify stdout and stderr are logged to files."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        review_artifact = artifacts_dir / "review.md"
        review_artifact.write_text("Review", encoding="utf-8")

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="test.log",
            error_file_name="test-errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Mock subprocess with stdout and stderr
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "This is stdout output"
        mock_result.stderr = "This is stderr output"

        def create_completed_doc(*args, **kwargs):
            updates_path = artifacts_dir / "updates.md"
            updates_path.write_text(
                f"""---
status: completed
---
Done""",
                encoding="utf-8",
            )
            return mock_result

        mocker.patch("subprocess.run", side_effect=create_completed_doc)

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Execute
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="builder-456",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Verify stdout log file
        log_path = artifacts_dir / "test.log"
        assert log_path.exists()
        assert log_path.read_text(encoding="utf-8") == "This is stdout output"

        # Verify stderr log file
        error_path = artifacts_dir / "test-errors.log"
        assert error_path.exists()
        assert error_path.read_text(encoding="utf-8") == "This is stderr output"

    def test_apply_review_feedback_console_output_success(
        self, tmp_path, mocker
    ):
        """Verify success messages are displayed to console."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        review_artifact = artifacts_dir / "review.md"
        review_artifact.write_text("Review", encoding="utf-8")

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Mock subprocess success
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Edited file: /path/to/file.yaml"
        mock_result.stderr = ""

        def create_completed_doc(*args, **kwargs):
            updates_path = artifacts_dir / "updates.md"
            updates_path.write_text(
                "---\nstatus: completed\n---\nDone",
                encoding="utf-8",
            )
            return mock_result

        mocker.patch("subprocess.run", side_effect=create_completed_doc)

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Execute
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="builder-456",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Check console.print was called with success messages
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        # Should show "Applying review feedback..."
        assert any("Applying" in call for call in print_calls)

        # Should show success message
        assert any("successfully" in call for call in print_calls)

        # Should show documentation path
        assert any("Documentation" in call for call in print_calls)

    def test_apply_review_feedback_console_output_failure(
        self, tmp_path, mocker
    ):
        """Verify failure messages are displayed to console."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        review_artifact = artifacts_dir / "review.md"
        review_artifact.write_text("Review", encoding="utf-8")

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Mock subprocess failure
        mocker.patch(
            "subprocess.run",
            side_effect=Exception("Subprocess failed"),
        )

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Execute
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="builder-456",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Check console.print was called with warning/error messages
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        # Should show warning about failure
        assert any(
            "Warning" in call or "fallback" in call for call in print_calls
        )

    def test_apply_review_feedback_calls_helper_functions(
        self, tmp_path, mocker
    ):
        """Verify orchestration - all helper functions are called in order."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        review_artifact = artifacts_dir / "review.md"
        review_artifact.write_text("Review content", encoding="utf-8")

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Mock all helper functions
        mock_build_prompt = mocker.patch(
            "cli.utils.review_feedback._build_feedback_prompt",
            return_value="Test prompt",
        )
        mock_create_template = mocker.patch(
            "cli.utils.review_feedback._create_template_doc"
        )

        # Mock subprocess
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Output"
        mock_result.stderr = ""

        def create_completed_doc(*args, **kwargs):
            updates_path = artifacts_dir / "updates.md"
            updates_path.write_text(
                "---\nstatus: completed\n---",
                encoding="utf-8",
            )
            return mock_result

        mocker.patch("subprocess.run", side_effect=create_completed_doc)

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Execute
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="builder-456",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Verify helper functions were called
        mock_build_prompt.assert_called_once()
        mock_create_template.assert_called_once()

        # Verify they were called with correct parameters
        build_args = mock_build_prompt.call_args
        assert build_args[1]["review_content"] == "Review content"
        assert build_args[1]["targets"] == targets
        assert build_args[1]["builder_session_id"] == "builder-456"

        template_args = mock_create_template.call_args
        assert template_args[1]["targets"] == targets
        assert template_args[1]["builder_session_id"] == "builder-456"

    def test_apply_review_feedback_builds_prompt_with_correct_params(
        self, tmp_path, mocker
    ):
        """Verify prompt is built with correct review content and targets."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        review_artifact = artifacts_dir / "review.md"
        custom_review_content = "Custom review feedback content here"
        review_artifact.write_text(custom_review_content, encoding="utf-8")

        targets = ReviewTargets(
            primary_file=Path("custom.yaml"),
            additional_files=[Path("ticket1.md")],
            editable_directories=[Path("dir")],
            artifacts_dir=artifacts_dir,
            updates_doc_name="custom-updates.md",
            log_file_name="custom.log",
            error_file_name="custom-errors.log",
            epic_name="custom-epic",
            reviewer_session_id="custom-reviewer-id",
            review_type="epic",
        )

        # Spy on _build_feedback_prompt
        original_build = __import__(
            "cli.utils.review_feedback", fromlist=["_build_feedback_prompt"]
        )._build_feedback_prompt

        captured_params = {}

        def capture_params(*args, **kwargs):
            captured_params["args"] = args
            captured_params["kwargs"] = kwargs
            return original_build(*args, **kwargs)

        mocker.patch(
            "cli.utils.review_feedback._build_feedback_prompt",
            side_effect=capture_params,
        )

        # Mock subprocess
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        def create_completed_doc(*args, **kwargs):
            updates_path = artifacts_dir / "custom-updates.md"
            updates_path.write_text(
                "---\nstatus: completed\n---",
                encoding="utf-8",
            )
            return mock_result

        mocker.patch("subprocess.run", side_effect=create_completed_doc)

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Execute
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="custom-builder-id",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Verify _build_feedback_prompt was called with correct params
        # Function is called with keyword arguments, so check kwargs
        if captured_params.get("kwargs"):
            assert captured_params["kwargs"]["review_content"] == custom_review_content
            assert captured_params["kwargs"]["targets"] == targets
            assert captured_params["kwargs"]["builder_session_id"] == "custom-builder-id"
        else:
            # Or positional args
            assert captured_params["args"][0] == custom_review_content
            assert captured_params["args"][1] == targets
            assert captured_params["args"][2] == "custom-builder-id"

    def test_apply_review_feedback_creates_template_before_claude(
        self, tmp_path, mocker
    ):
        """Verify template is created BEFORE Claude runs."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        review_artifact = artifacts_dir / "review.md"
        review_artifact.write_text("Review", encoding="utf-8")

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Track call order
        call_order = []

        def track_template(*args, **kwargs):
            call_order.append("template")

        def track_subprocess(*args, **kwargs):
            call_order.append("subprocess")
            # Verify template exists before subprocess runs
            assert (artifacts_dir / "updates.md").exists()
            # Create completed doc
            updates_path = artifacts_dir / "updates.md"
            updates_path.write_text(
                "---\nstatus: completed\n---",
                encoding="utf-8",
            )
            mock_result = mocker.Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            return mock_result

        mocker.patch(
            "cli.utils.review_feedback._create_template_doc",
            side_effect=track_template,
        )
        mocker.patch("subprocess.run", side_effect=track_subprocess)

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Execute
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="builder-456",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Verify template was created before subprocess
        assert call_order == ["template", "subprocess"]

    def test_apply_review_feedback_validates_frontmatter_status(
        self, tmp_path, mocker
    ):
        """Verify validation logic checks frontmatter status field."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create test files
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)

        review_artifact = artifacts_dir / "review.md"
        review_artifact.write_text("Review", encoding="utf-8")

        targets = ReviewTargets(
            primary_file=Path("test.yaml"),
            additional_files=[],
            editable_directories=[],
            artifacts_dir=artifacts_dir,
            updates_doc_name="updates.md",
            log_file_name="log.log",
            error_file_name="errors.log",
            epic_name="test-epic",
            reviewer_session_id="reviewer-123",
            review_type="epic-file",
        )

        # Mock subprocess
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Output"
        mock_result.stderr = ""

        # Template will remain in_progress (Claude didn't update it)
        mocker.patch("subprocess.run", return_value=mock_result)

        # Spy on _create_fallback_updates_doc
        mock_fallback = mocker.patch(
            "cli.utils.review_feedback._create_fallback_updates_doc"
        )

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Execute
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="builder-456",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Verify fallback was called (because status stayed in_progress)
        mock_fallback.assert_called_once()

    def test_apply_review_feedback_end_to_end_with_real_files(
        self, tmp_path, mocker
    ):
        """Integration test with real file operations (no subprocess mock)."""
        from cli.utils.review_feedback import apply_review_feedback

        # Create realistic file structure
        epic_dir = tmp_path / ".epics" / "integration-epic"
        tickets_dir = epic_dir / "tickets"
        artifacts_dir = epic_dir / "artifacts"

        epic_dir.mkdir(parents=True)
        tickets_dir.mkdir()
        artifacts_dir.mkdir()

        # Create epic file
        epic_file = epic_dir / "integration-epic.epic.yaml"
        epic_file.write_text(
            "name: integration-epic\ndescription: Test epic\n",
            encoding="utf-8",
        )

        # Create ticket file
        ticket_file = tickets_dir / "INT-001.md"
        ticket_file.write_text("# INT-001\n## Task\nTest", encoding="utf-8")

        # Create review artifact
        review_artifact = artifacts_dir / "epic-review.md"
        review_artifact.write_text(
            """---
date: 2025-01-15
---

# Epic Review

## Priority 1 Issues
- Add missing acceptance criteria
- Define integration contracts

## Priority 2 Issues
- Improve test coverage""",
            encoding="utf-8",
        )

        # Create ReviewTargets
        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[ticket_file],
            editable_directories=[epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-review-updates.md",
            log_file_name="epic-review.log",
            error_file_name="epic-review-errors.log",
            epic_name="integration-epic",
            reviewer_session_id="int-reviewer-123",
            review_type="epic",
        )

        # Mock subprocess to simulate Claude success
        mock_result = mocker.Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            f"Edited file: {epic_file}\n"
            f"Edited file: {ticket_file}"
        )
        mock_result.stderr = ""

        def create_real_completed_doc(*args, **kwargs):
            # Simulate Claude actually creating the documentation
            updates_path = artifacts_dir / "epic-review-updates.md"
            updates_path.write_text(
                f"""---
date: {datetime.now().strftime('%Y-%m-%d')}
epic: integration-epic
builder_session_id: int-builder-456
reviewer_session_id: int-reviewer-123
status: completed
---

# Epic Review Updates

## Changes Applied

### Priority 1 Fixes
- Added missing acceptance criteria to INT-001
- Defined integration contracts in epic coordination_requirements

### Priority 2 Fixes
- Improved test coverage specifications

## Summary
Applied all Priority 1 and Priority 2 fixes from epic review.
""",
                encoding="utf-8",
            )
            return mock_result

        mocker.patch("subprocess.run", side_effect=create_real_completed_doc)

        mock_console = mocker.Mock()
        mock_console.status.return_value.__enter__ = mocker.Mock()
        mock_console.status.return_value.__exit__ = mocker.Mock()
        mock_context = mocker.Mock()
        mock_context.cwd = tmp_path

        # Execute end-to-end
        apply_review_feedback(
            review_artifact_path=review_artifact,
            builder_session_id="int-builder-456",
            context=mock_context,
            targets=targets,
            console=mock_console,
        )

        # Verify all expected artifacts exist
        updates_path = artifacts_dir / "epic-review-updates.md"
        assert updates_path.exists()

        log_path = artifacts_dir / "epic-review.log"
        assert log_path.exists()

        # Verify documentation content
        content = updates_path.read_text(encoding="utf-8")
        assert "status: completed" in content
        assert "integration-epic" in content
        assert "Priority 1 Fixes" in content

        # Verify success console output
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("successfully" in call for call in print_calls)
