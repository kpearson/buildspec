"""Integration tests for review feedback application workflows.

These tests verify that review feedback is correctly applied to epic and ticket files
through the full create-epic and create-tickets workflows using real test fixtures.
"""

import shutil
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from rich.console import Console

from cli.utils.review_feedback import ReviewTargets, apply_review_feedback
from cli.core.context import ProjectContext


@pytest.fixture
def test_fixture_dir():
    """Return path to the simple epic test fixture."""
    return (
        Path(__file__).parent.parent.parent
        / ".epics"
        / "test-fixtures"
        / "simple-epic"
    )


@pytest.fixture
def temp_epic_dir(tmp_path):
    """Create a temporary copy of the test fixture for modification."""
    fixture_dir = (
        Path(__file__).parent.parent.parent
        / ".epics"
        / "test-fixtures"
        / "simple-epic"
    )
    temp_dir = tmp_path / "simple-epic"
    shutil.copytree(fixture_dir, temp_dir)
    return temp_dir


@pytest.fixture
def mock_console():
    """Create a mock Console for testing output."""
    return MagicMock(spec=Console)


@pytest.fixture
def mock_project_context():
    """Create a mock ProjectContext for testing."""
    context = MagicMock(spec=ProjectContext)
    context.cwd = Path(__file__).parent.parent.parent
    return context


class TestCreateEpicWithEpicFileReview:
    """Test suite for create-epic workflow with epic-file-review."""

    def test_create_epic_with_epic_file_review(
        self, temp_epic_dir, mock_console, mock_project_context
    ):
        """Test full create-epic workflow with epic-file-review feedback application."""
        epic_file = temp_epic_dir / "simple-epic.epic.yaml"
        review_artifact = (
            temp_epic_dir / "artifacts" / "epic-file-review-artifact.md"
        )
        artifacts_dir = temp_epic_dir / "artifacts"

        # Create ReviewTargets for epic-file-review
        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[],
            editable_directories=[temp_epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="epic-file-review.log",
            error_file_name="epic-file-review-errors.log",
            epic_name="simple-test-epic",
            reviewer_session_id="test-reviewer-session-id",
            review_type="epic-file",
        )

        # Mock subprocess to simulate Claude updating the template document
        with patch("subprocess.run") as mock_subprocess:
            def mock_run(*args, **kwargs):
                # Simulate Claude updating the template document
                updates_doc = artifacts_dir / targets.updates_doc_name
                content = updates_doc.read_text()
                # Change status from in_progress to completed
                content = content.replace(
                    "status: in_progress", "status: completed"
                )
                # Add some documentation
                content += "\n\n## Changes Applied\n\n- Updated epic description\n"
                updates_doc.write_text(content)

                # Return mock result
                result = MagicMock()
                result.returncode = 0
                result.stdout = "Applied feedback"
                result.stderr = ""
                return result

            mock_subprocess.side_effect = mock_run

            # Apply review feedback
            apply_review_feedback(
                review_artifact_path=review_artifact,
                builder_session_id="test-builder-session",
                context=mock_project_context,
                targets=targets,
                console=mock_console,
            )

        # Verify updates document was created
        updates_doc = artifacts_dir / "epic-file-review-updates.md"
        assert updates_doc.exists(), "Updates document should be created"

        # Verify updates document has completed status
        updates_content = updates_doc.read_text()
        assert "status: completed" in updates_content

        # Verify console output was provided
        assert mock_console.print.called

    def test_epic_yaml_updated_by_review_feedback(
        self, temp_epic_dir, mock_console, mock_project_context
    ):
        """Verify epic YAML file contains expected changes from review feedback."""
        epic_file = temp_epic_dir / "simple-epic.epic.yaml"
        review_artifact = (
            temp_epic_dir / "artifacts" / "epic-file-review-artifact.md"
        )
        artifacts_dir = temp_epic_dir / "artifacts"

        # Read original epic content
        original_content = epic_file.read_text()

        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[],
            editable_directories=[temp_epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="epic-file-review.log",
            error_file_name="epic-file-review-errors.log",
            epic_name="simple-test-epic",
            reviewer_session_id="test-reviewer-session-id",
            review_type="epic-file",
        )

        # Mock subprocess to simulate editing the epic file
        with patch("subprocess.run") as mock_subprocess:
            def mock_run(*args, **kwargs):
                # Simulate Claude editing the epic file
                content = epic_file.read_text()
                content += "\n\nnon_goals:\n  - Testing with production data\n"
                epic_file.write_text(content)

                # Update template document
                updates_doc = artifacts_dir / targets.updates_doc_name
                doc_content = updates_doc.read_text()
                doc_content = doc_content.replace(
                    "status: in_progress", "status: completed"
                )
                updates_doc.write_text(doc_content)

                result = MagicMock()
                result.returncode = 0
                result.stdout = "Edited epic file"
                result.stderr = ""
                return result

            mock_subprocess.side_effect = mock_run

            apply_review_feedback(
                review_artifact_path=review_artifact,
                builder_session_id="test-builder-session",
                context=mock_project_context,
                targets=targets,
                console=mock_console,
            )

        # Verify epic file was modified
        updated_content = epic_file.read_text()
        assert updated_content != original_content
        assert "non_goals" in updated_content

    def test_epic_file_review_documentation_created(
        self, temp_epic_dir, mock_console, mock_project_context
    ):
        """Verify epic-file-review-updates.md is created with correct structure."""
        epic_file = temp_epic_dir / "simple-epic.epic.yaml"
        review_artifact = (
            temp_epic_dir / "artifacts" / "epic-file-review-artifact.md"
        )
        artifacts_dir = temp_epic_dir / "artifacts"

        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[],
            editable_directories=[temp_epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="epic-file-review.log",
            error_file_name="epic-file-review-errors.log",
            epic_name="simple-test-epic",
            reviewer_session_id="test-reviewer-session-id",
            review_type="epic-file",
        )

        with patch("subprocess.run") as mock_subprocess:
            def mock_run(*args, **kwargs):
                updates_doc = artifacts_dir / targets.updates_doc_name
                content = updates_doc.read_text()
                content = content.replace(
                    "status: in_progress", "status: completed"
                )
                content += "\n\n## Summary\n\nApplied epic file review feedback.\n"
                updates_doc.write_text(content)

                result = MagicMock()
                result.returncode = 0
                result.stdout = "Created documentation"
                result.stderr = ""
                return result

            mock_subprocess.side_effect = mock_run

            apply_review_feedback(
                review_artifact_path=review_artifact,
                builder_session_id="test-builder-session",
                context=mock_project_context,
                targets=targets,
                console=mock_console,
            )

        updates_doc = artifacts_dir / "epic-file-review-updates.md"
        assert updates_doc.exists()

        content = updates_doc.read_text()

        # Verify frontmatter structure
        assert "---" in content
        assert "status: completed" in content
        assert "epic: simple-test-epic" in content
        assert "builder_session_id: test-builder-session" in content
        assert "reviewer_session_id: test-reviewer-session-id" in content


class TestCreateTicketsWithEpicReview:
    """Test suite for create-tickets workflow with epic-review."""

    def test_create_tickets_with_epic_review(
        self, temp_epic_dir, mock_console, mock_project_context
    ):
        """Test full create-tickets workflow with epic-review feedback application."""
        # Create ticket files first
        tickets_dir = temp_epic_dir / "tickets"
        tickets_dir.mkdir(exist_ok=True)

        for ticket_id in ["TEST-001", "TEST-002", "TEST-003"]:
            ticket_file = tickets_dir / f"{ticket_id}.md"
            ticket_file.write_text(f"# {ticket_id}\n\nInitial content\n")

        epic_file = temp_epic_dir / "simple-epic.epic.yaml"
        review_artifact = temp_epic_dir / "artifacts" / "epic-review-artifact.md"
        artifacts_dir = temp_epic_dir / "artifacts"
        ticket_files = list(tickets_dir.glob("*.md"))

        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=ticket_files,
            editable_directories=[temp_epic_dir, tickets_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-review-updates.md",
            log_file_name="epic-review.log",
            error_file_name="epic-review-errors.log",
            epic_name="simple-test-epic",
            reviewer_session_id="test-epic-reviewer-session-id",
            review_type="epic",
        )

        with patch("subprocess.run") as mock_subprocess:
            def mock_run(*args, **kwargs):
                # Simulate Claude updating both epic and ticket files
                updates_doc = artifacts_dir / targets.updates_doc_name
                content = updates_doc.read_text()
                content = content.replace(
                    "status: in_progress", "status: completed"
                )
                content += "\n\n## Changes Applied\n\n- Updated epic and tickets\n"
                updates_doc.write_text(content)

                result = MagicMock()
                result.returncode = 0
                result.stdout = "Applied epic review feedback"
                result.stderr = ""
                return result

            mock_subprocess.side_effect = mock_run

            apply_review_feedback(
                review_artifact_path=review_artifact,
                builder_session_id="test-builder-session",
                context=mock_project_context,
                targets=targets,
                console=mock_console,
            )

        # Verify updates document was created
        updates_doc = artifacts_dir / "epic-review-updates.md"
        assert updates_doc.exists()

        # Verify status is completed
        updates_content = updates_doc.read_text()
        assert "status: completed" in updates_content

    def test_epic_and_tickets_updated_by_review_feedback(
        self, temp_epic_dir, mock_console, mock_project_context
    ):
        """Verify both epic YAML and ticket markdown files are updated correctly."""
        # Create ticket files
        tickets_dir = temp_epic_dir / "tickets"
        tickets_dir.mkdir(exist_ok=True)

        ticket_files = []
        for ticket_id in ["TEST-001", "TEST-002", "TEST-003"]:
            ticket_file = tickets_dir / f"{ticket_id}.md"
            ticket_file.write_text(f"# {ticket_id}\n\nOriginal content\n")
            ticket_files.append(ticket_file)

        epic_file = temp_epic_dir / "simple-epic.epic.yaml"
        review_artifact = temp_epic_dir / "artifacts" / "epic-review-artifact.md"
        artifacts_dir = temp_epic_dir / "artifacts"

        # Read original contents
        original_epic = epic_file.read_text()
        original_tickets = {f: f.read_text() for f in ticket_files}

        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=ticket_files,
            editable_directories=[temp_epic_dir, tickets_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-review-updates.md",
            log_file_name="epic-review.log",
            error_file_name="epic-review-errors.log",
            epic_name="simple-test-epic",
            reviewer_session_id="test-epic-reviewer-session-id",
            review_type="epic",
        )

        with patch("subprocess.run") as mock_subprocess:
            def mock_run(*args, **kwargs):
                # Simulate Claude editing epic
                content = epic_file.read_text()
                content += "\n\ntesting_strategy: Unit and integration tests\n"
                epic_file.write_text(content)

                # Simulate Claude editing tickets
                for ticket_file in ticket_files:
                    content = ticket_file.read_text()
                    content += "\n\n## Implementation Details\n\nAdded by review.\n"
                    ticket_file.write_text(content)

                # Update documentation
                updates_doc = artifacts_dir / targets.updates_doc_name
                doc_content = updates_doc.read_text()
                doc_content = doc_content.replace(
                    "status: in_progress", "status: completed"
                )
                updates_doc.write_text(doc_content)

                result = MagicMock()
                result.returncode = 0
                result.stdout = "Edited all files"
                result.stderr = ""
                return result

            mock_subprocess.side_effect = mock_run

            apply_review_feedback(
                review_artifact_path=review_artifact,
                builder_session_id="test-builder-session",
                context=mock_project_context,
                targets=targets,
                console=mock_console,
            )

        # Verify epic was modified
        updated_epic = epic_file.read_text()
        assert updated_epic != original_epic
        assert "testing_strategy" in updated_epic

        # Verify all tickets were modified
        for ticket_file in ticket_files:
            updated_content = ticket_file.read_text()
            assert updated_content != original_tickets[ticket_file]
            assert "Implementation Details" in updated_content

    def test_epic_review_documentation_created(
        self, temp_epic_dir, mock_console, mock_project_context
    ):
        """Verify epic-review-updates.md is created with correct structure."""
        # Create ticket files
        tickets_dir = temp_epic_dir / "tickets"
        tickets_dir.mkdir(exist_ok=True)

        ticket_files = []
        for ticket_id in ["TEST-001", "TEST-002", "TEST-003"]:
            ticket_file = tickets_dir / f"{ticket_id}.md"
            ticket_file.write_text(f"# {ticket_id}\n\nContent\n")
            ticket_files.append(ticket_file)

        epic_file = temp_epic_dir / "simple-epic.epic.yaml"
        review_artifact = temp_epic_dir / "artifacts" / "epic-review-artifact.md"
        artifacts_dir = temp_epic_dir / "artifacts"

        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=ticket_files,
            editable_directories=[temp_epic_dir, tickets_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-review-updates.md",
            log_file_name="epic-review.log",
            error_file_name="epic-review-errors.log",
            epic_name="simple-test-epic",
            reviewer_session_id="test-epic-reviewer-session-id",
            review_type="epic",
        )

        with patch("subprocess.run") as mock_subprocess:
            def mock_run(*args, **kwargs):
                updates_doc = artifacts_dir / targets.updates_doc_name
                content = updates_doc.read_text()
                content = content.replace(
                    "status: in_progress", "status: completed"
                )
                content += "\n\n## Summary\n\nApplied epic review feedback.\n"
                content += "\n## Files Modified\n\n- Epic YAML\n- All ticket files\n"
                updates_doc.write_text(content)

                result = MagicMock()
                result.returncode = 0
                result.stdout = "Created documentation"
                result.stderr = ""
                return result

            mock_subprocess.side_effect = mock_run

            apply_review_feedback(
                review_artifact_path=review_artifact,
                builder_session_id="test-builder-session",
                context=mock_project_context,
                targets=targets,
                console=mock_console,
            )

        updates_doc = artifacts_dir / "epic-review-updates.md"
        assert updates_doc.exists()

        content = updates_doc.read_text()

        # Verify frontmatter
        assert "status: completed" in content
        assert "epic: simple-test-epic" in content
        assert "builder_session_id: test-builder-session" in content
        assert "reviewer_session_id: test-epic-reviewer-session-id" in content


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def test_fallback_documentation_on_claude_failure(
        self, temp_epic_dir, mock_console, mock_project_context
    ):
        """Verify fallback documentation is created when Claude fails."""
        epic_file = temp_epic_dir / "simple-epic.epic.yaml"
        review_artifact = (
            temp_epic_dir / "artifacts" / "epic-file-review-artifact.md"
        )
        artifacts_dir = temp_epic_dir / "artifacts"

        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[],
            editable_directories=[temp_epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="epic-file-review.log",
            error_file_name="epic-file-review-errors.log",
            epic_name="simple-test-epic",
            reviewer_session_id="test-reviewer-session-id",
            review_type="epic-file",
        )

        # Mock subprocess to fail (not update template)
        with patch("subprocess.run") as mock_subprocess:
            def mock_run(*args, **kwargs):
                # Don't update the template document - simulate failure
                result = MagicMock()
                result.returncode = 0
                result.stdout = "Failed to complete"
                result.stderr = "Error occurred during processing"
                return result

            mock_subprocess.side_effect = mock_run

            apply_review_feedback(
                review_artifact_path=review_artifact,
                builder_session_id="test-builder-session",
                context=mock_project_context,
                targets=targets,
                console=mock_console,
            )

        # Verify fallback documentation was created
        updates_doc = artifacts_dir / "epic-file-review-updates.md"
        assert updates_doc.exists()

        content = updates_doc.read_text()

        # Fallback doc should have error status
        assert (
            "status: completed_with_errors" in content
            or "status: in_progress" not in content
        )

    def test_error_message_when_review_artifact_missing(
        self, temp_epic_dir, mock_console, mock_project_context
    ):
        """Verify clear error message when review artifact is missing."""
        epic_file = temp_epic_dir / "simple-epic.epic.yaml"
        review_artifact = temp_epic_dir / "artifacts" / "nonexistent-review.md"
        artifacts_dir = temp_epic_dir / "artifacts"

        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[],
            editable_directories=[temp_epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="epic-file-review.log",
            error_file_name="epic-file-review-errors.log",
            epic_name="simple-test-epic",
            reviewer_session_id="test-reviewer-session-id",
            review_type="epic-file",
        )

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            apply_review_feedback(
                review_artifact_path=review_artifact,
                builder_session_id="test-builder-session",
                context=mock_project_context,
                targets=targets,
                console=mock_console,
            )


class TestPerformanceAndLogging:
    """Test suite for performance and logging verification."""

    def test_review_feedback_performance(
        self, temp_epic_dir, mock_console, mock_project_context
    ):
        """Verify review feedback completes in acceptable time (< 30 seconds)."""
        # Create ticket files
        tickets_dir = temp_epic_dir / "tickets"
        tickets_dir.mkdir(exist_ok=True)

        ticket_files = []
        for i in range(10):  # Create 10 tickets
            ticket_file = tickets_dir / f"TEST-{i:03d}.md"
            ticket_file.write_text(f"# TEST-{i:03d}\n\nContent\n")
            ticket_files.append(ticket_file)

        epic_file = temp_epic_dir / "simple-epic.epic.yaml"
        review_artifact = temp_epic_dir / "artifacts" / "epic-review-artifact.md"
        artifacts_dir = temp_epic_dir / "artifacts"

        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=ticket_files,
            editable_directories=[temp_epic_dir, tickets_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-review-updates.md",
            log_file_name="epic-review.log",
            error_file_name="epic-review-errors.log",
            epic_name="simple-test-epic",
            reviewer_session_id="test-reviewer-session-id",
            review_type="epic",
        )

        with patch("subprocess.run") as mock_subprocess:
            def mock_run(*args, **kwargs):
                updates_doc = artifacts_dir / targets.updates_doc_name
                content = updates_doc.read_text()
                content = content.replace(
                    "status: in_progress", "status: completed"
                )
                updates_doc.write_text(content)

                result = MagicMock()
                result.returncode = 0
                result.stdout = "Completed"
                result.stderr = ""
                return result

            mock_subprocess.side_effect = mock_run

            start_time = time.time()
            apply_review_feedback(
                review_artifact_path=review_artifact,
                builder_session_id="test-builder-session",
                context=mock_project_context,
                targets=targets,
                console=mock_console,
            )
            duration = time.time() - start_time

        # Should complete quickly with mocks (< 1 second)
        # Real performance should be < 30 seconds
        assert duration < 5.0, f"Performance test took {duration}s (should be < 5s)"

    def test_stdout_stderr_logged_separately(
        self, temp_epic_dir, mock_console, mock_project_context
    ):
        """Verify stdout and stderr are logged to separate files."""
        epic_file = temp_epic_dir / "simple-epic.epic.yaml"
        review_artifact = (
            temp_epic_dir / "artifacts" / "epic-file-review-artifact.md"
        )
        artifacts_dir = temp_epic_dir / "artifacts"

        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[],
            editable_directories=[temp_epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="epic-file-review.log",
            error_file_name="epic-file-review-errors.log",
            epic_name="simple-test-epic",
            reviewer_session_id="test-reviewer-session-id",
            review_type="epic-file",
        )

        with patch("subprocess.run") as mock_subprocess:
            def mock_run(*args, **kwargs):
                updates_doc = artifacts_dir / targets.updates_doc_name
                content = updates_doc.read_text()
                content = content.replace(
                    "status: in_progress", "status: completed"
                )
                updates_doc.write_text(content)

                result = MagicMock()
                result.returncode = 0
                result.stdout = "stdout content"
                result.stderr = "stderr content"
                return result

            mock_subprocess.side_effect = mock_run

            apply_review_feedback(
                review_artifact_path=review_artifact,
                builder_session_id="test-builder-session",
                context=mock_project_context,
                targets=targets,
                console=mock_console,
            )

        # Verify log files were created
        log_file = artifacts_dir / "epic-file-review.log"
        error_file = artifacts_dir / "epic-file-review-errors.log"

        assert log_file.exists()
        assert error_file.exists()
        assert log_file.read_text() == "stdout content"
        assert error_file.read_text() == "stderr content"

    def test_console_output_provides_feedback(
        self, temp_epic_dir, mock_console, mock_project_context
    ):
        """Verify console output provides clear user feedback."""
        epic_file = temp_epic_dir / "simple-epic.epic.yaml"
        review_artifact = (
            temp_epic_dir / "artifacts" / "epic-file-review-artifact.md"
        )
        artifacts_dir = temp_epic_dir / "artifacts"

        targets = ReviewTargets(
            primary_file=epic_file,
            additional_files=[],
            editable_directories=[temp_epic_dir],
            artifacts_dir=artifacts_dir,
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="epic-file-review.log",
            error_file_name="epic-file-review-errors.log",
            epic_name="simple-test-epic",
            reviewer_session_id="test-reviewer-session-id",
            review_type="epic-file",
        )

        with patch("subprocess.run") as mock_subprocess:
            def mock_run(*args, **kwargs):
                updates_doc = artifacts_dir / targets.updates_doc_name
                content = updates_doc.read_text()
                content = content.replace(
                    "status: in_progress", "status: completed"
                )
                updates_doc.write_text(content)

                result = MagicMock()
                result.returncode = 0
                result.stdout = "Applied feedback"
                result.stderr = ""
                return result

            mock_subprocess.side_effect = mock_run

            apply_review_feedback(
                review_artifact_path=review_artifact,
                builder_session_id="test-builder-session",
                context=mock_project_context,
                targets=targets,
                console=mock_console,
            )

        # Verify console.print was called with feedback messages
        assert mock_console.print.called

        # Check for informative messages
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert len(print_calls) > 0, "Console should provide feedback to user"
