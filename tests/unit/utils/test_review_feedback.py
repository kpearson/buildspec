"""Unit tests for review_feedback module."""

from dataclasses import asdict, fields
from pathlib import Path
from typing import List

from cli.utils.review_feedback import ReviewTargets


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
