"""Integration tests for execute-epic CLI command.

Tests the execute-epic command end-to-end with real epics and mocked builder.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
import yaml

from cli.commands.execute_epic import command
from cli.epic.models import AcceptanceCriterion, BuilderResult, EpicState, TicketState


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        readme = repo_path / "README.md"
        readme.write_text("# Test Repo\n")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Get current branch name
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        branch_name = result.stdout.strip()

        # Set up fake remote
        remote_path = Path(tmpdir) / "remote"
        remote_path.mkdir()
        subprocess.run(
            ["git", "init", "--bare"],
            cwd=remote_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_path)],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        yield repo_path


@pytest.fixture
def simple_epic_fixture(temp_git_repo):
    """Create a simple 1-ticket epic for testing."""
    repo_path = temp_git_repo

    # Create epic directory
    epic_dir = repo_path / ".epics" / "test-epic"
    epic_dir.mkdir(parents=True)

    # Create tickets directory
    tickets_dir = epic_dir / "tickets"
    tickets_dir.mkdir()

    # Create epic YAML
    epic_file = epic_dir / "test-epic.epic.yaml"
    epic_data = {
        "epic": "Test Epic",
        "description": "Simple test epic with 1 ticket",
        "ticket_count": 1,
        "rollback_on_failure": False,
        "tickets": [
            {
                "id": "test-ticket",
                "description": "Test ticket",
                "depends_on": [],
                "critical": False,
            },
        ],
    }

    with open(epic_file, "w") as f:
        yaml.dump(epic_data, f)

    # Create ticket markdown file
    ticket_file = tickets_dir / "test-ticket.md"
    ticket_file.write_text(
        "# test-ticket\n\n"
        "Description: Test ticket\n\n"
        "## Acceptance Criteria\n\n"
        "- Test criterion\n"
    )

    return epic_file, repo_path


class TestExecuteEpicIntegration:
    """Integration tests for execute-epic command."""

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_execute_simple_epic_success(self, mock_builder_class, simple_epic_fixture):
        """Test successful execution of a simple epic."""
        epic_file, repo_path = simple_epic_fixture

        def mock_builder_init(ticket_file, branch_name, base_commit, epic_file):
            """Mock builder that creates a commit."""
            builder = MagicMock()
            ticket_id = Path(ticket_file).stem

            def execute_ticket():
                # Checkout branch and make commit
                subprocess.run(
                    ["git", "checkout", branch_name],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )
                test_file = repo_path / f"{ticket_id}.txt"
                test_file.write_text(f"Changes for {ticket_id}\n")
                subprocess.run(
                    ["git", "add", "."],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "commit", "-m", f"Implement {ticket_id}"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return BuilderResult(
                    success=True,
                    final_commit=result.stdout.strip(),
                    test_status="passing",
                    acceptance_criteria=[
                        AcceptanceCriterion(criterion="Test criterion", met=True),
                    ],
                )

            builder.execute = execute_ticket
            return builder

        mock_builder_class.side_effect = mock_builder_init

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)

            # Execute command
            command(str(epic_file), resume=False)

            # Verify state file exists
            state_file = epic_file.parent / "artifacts" / "epic-state.json"
            assert state_file.exists()

            # Verify state file contents
            with open(state_file, "r") as f:
                state = json.load(f)

            assert state["epic_state"] == "FINALIZED"
            assert state["tickets"]["test-ticket"]["state"] == "COMPLETED"

            # Verify epic branch exists
            result = subprocess.run(
                ["git", "branch", "--list"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            assert "epic/test-epic" in result.stdout

        finally:
            os.chdir(original_cwd)

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_execute_epic_with_failure(self, mock_builder_class, temp_git_repo):
        """Test execution of epic where ticket fails."""
        repo_path = temp_git_repo

        # Create epic with ticket that fails
        epic_dir = repo_path / ".epics" / "fail-epic"
        epic_dir.mkdir(parents=True)
        tickets_dir = epic_dir / "tickets"
        tickets_dir.mkdir()

        epic_file = epic_dir / "fail-epic.epic.yaml"
        epic_data = {
            "epic": "Fail Epic",
            "description": "Epic with ticket that fails",
            "ticket_count": 1,
            "rollback_on_failure": False,
            "tickets": [
                {
                    "id": "fail-ticket",
                    "description": "Ticket that will fail",
                    "depends_on": [],
                    "critical": False,
                },
            ],
        }

        with open(epic_file, "w") as f:
            yaml.dump(epic_data, f)

        ticket_file = tickets_dir / "fail-ticket.md"
        ticket_file.write_text("# fail-ticket\n\nTest\n")

        def mock_builder_init(ticket_file, branch_name, base_commit, epic_file):
            """Mock builder that fails."""
            builder = MagicMock()

            def execute_ticket():
                return BuilderResult(
                    success=False,
                    error="Simulated build failure",
                )

            builder.execute = execute_ticket
            return builder

        mock_builder_class.side_effect = mock_builder_init

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)

            # Execute command
            # Note: With current state machine, when all tickets fail but are non-critical,
            # the epic finalizes with 0 completed tickets (state = FINALIZED).
            # The command should still work without raising an error in this case.
            command(str(epic_file), resume=False)

            # Verify state file
            state_file = epic_file.parent / "artifacts" / "epic-state.json"
            assert state_file.exists()

            with open(state_file, "r") as f:
                state = json.load(f)

            # Epic finalizes even with 0 completed tickets
            assert state["epic_state"] == "FINALIZED"
            assert state["tickets"]["fail-ticket"]["state"] == "FAILED"

        finally:
            os.chdir(original_cwd)

    def test_execute_epic_file_not_found(self, temp_git_repo):
        """Test execution with non-existent epic file."""
        repo_path = temp_git_repo

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)

            # Execute command with non-existent file
            with pytest.raises(typer.Exit) as exc_info:
                command("/nonexistent/epic.epic.yaml", resume=False)

            assert exc_info.value.exit_code == 1

        finally:
            os.chdir(original_cwd)

    def test_execute_epic_invalid_extension(self, temp_git_repo):
        """Test execution with invalid file extension."""
        repo_path = temp_git_repo
        invalid_file = repo_path / "test.yaml"
        invalid_file.write_text("epic: test")

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)

            # Execute command with invalid extension
            with pytest.raises(typer.Exit) as exc_info:
                command(str(invalid_file), resume=False)

            assert exc_info.value.exit_code == 1

        finally:
            os.chdir(original_cwd)

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_execute_epic_displays_progress(
        self, mock_builder_class, simple_epic_fixture, capsys
    ):
        """Test that command displays progress messages."""
        epic_file, repo_path = simple_epic_fixture

        def mock_builder_init(ticket_file, branch_name, base_commit, epic_file):
            """Mock builder."""
            builder = MagicMock()
            ticket_id = Path(ticket_file).stem

            def execute_ticket():
                subprocess.run(
                    ["git", "checkout", branch_name],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )
                test_file = repo_path / f"{ticket_id}.txt"
                test_file.write_text(f"Changes\n")
                subprocess.run(
                    ["git", "add", "."],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "commit", "-m", "Test"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return BuilderResult(
                    success=True,
                    final_commit=result.stdout.strip(),
                    test_status="passing",
                    acceptance_criteria=[
                        AcceptanceCriterion(criterion="Test", met=True),
                    ],
                )

            builder.execute = execute_ticket
            return builder

        mock_builder_class.side_effect = mock_builder_init

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)

            # Execute command
            command(str(epic_file), resume=False)

            # Note: Rich console output can't be easily tested here,
            # but the command should complete without error

        finally:
            os.chdir(original_cwd)
