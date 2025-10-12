"""Integration tests for epic state machine resume functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from cli.epic.models import (
    AcceptanceCriterion,
    BuilderResult,
    EpicState,
    GitInfo,
    TicketState,
)
from cli.epic.state_machine import EpicStateMachine


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = Path(tmpdir)

        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir, check=True, capture_output=True
        )

        # Create initial commit
        readme = repo_dir / "README.md"
        readme.write_text("# Test Repo")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir, check=True, capture_output=True
        )

        yield repo_dir


@pytest.fixture
def epic_with_tickets(temp_git_repo):
    """Create an epic with 3 sequential tickets."""
    epic_dir = temp_git_repo / ".epics" / "test-resume-epic"
    epic_dir.mkdir(parents=True)

    # Create tickets directory
    tickets_dir = epic_dir / "tickets"
    tickets_dir.mkdir()

    # Create artifacts directory
    artifacts_dir = epic_dir / "artifacts"
    artifacts_dir.mkdir()

    # Create epic YAML
    epic_file = epic_dir / "test-resume-epic.epic.yaml"
    epic_data = {
        "epic": "Test Resume Epic",
        "description": "Test epic for resume functionality",
        "ticket_count": 3,
        "rollback_on_failure": False,
        "tickets": [
            {
                "id": "ticket-a",
                "description": "First ticket",
                "depends_on": [],
                "critical": False,
            },
            {
                "id": "ticket-b",
                "description": "Second ticket depends on A",
                "depends_on": ["ticket-a"],
                "critical": False,
            },
            {
                "id": "ticket-c",
                "description": "Third ticket depends on B",
                "depends_on": ["ticket-b"],
                "critical": False,
            },
        ],
    }

    with open(epic_file, "w") as f:
        yaml.dump(epic_data, f)

    # Create ticket files
    for ticket_id in ["ticket-a", "ticket-b", "ticket-c"]:
        ticket_file = tickets_dir / f"{ticket_id}.md"
        ticket_file.write_text(f"# {ticket_id}\n\nTest ticket content")

    # Commit epic files
    import subprocess
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add epic files"],
        cwd=temp_git_repo, check=True, capture_output=True
    )

    yield epic_file, epic_dir, temp_git_repo


class TestResumeAfterPartialExecution:
    """Test resuming epic execution after interruption."""

    @patch("cli.epic.state_machine.GitOperations")
    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_resume_after_one_ticket_completed(
        self, mock_builder_class, mock_git_class, epic_with_tickets
    ):
        """Test resuming after completing one ticket."""
        epic_file, epic_dir, repo_dir = epic_with_tickets
        state_file = epic_dir / "artifacts" / "epic-state.json"

        # Mock git operations
        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="baseline123\n")
        mock_git.branch_exists_remote.return_value = True
        mock_git_class.return_value = mock_git

        # Mock builder to succeed
        mock_builder = MagicMock()
        mock_builder.execute.return_value = BuilderResult(
            success=True,
            final_commit="commit456",
            test_status="passing",
            acceptance_criteria=[AcceptanceCriterion(criterion="Works", met=True)],
        )
        mock_builder_class.return_value = mock_builder

        # First session: Initialize and complete ticket-a
        state_machine1 = EpicStateMachine(epic_file, resume=False)

        # Manually complete ticket-a to simulate partial execution
        state_machine1.tickets["ticket-a"].state = TicketState.COMPLETED
        state_machine1.tickets["ticket-a"].git_info = GitInfo(
            branch_name="ticket/ticket-a",
            base_commit="baseline123",
            final_commit="commit456",
        )
        state_machine1.tickets["ticket-a"].test_suite_status = "passing"
        state_machine1.tickets["ticket-a"].started_at = "2024-01-01T00:00:00"
        state_machine1.tickets["ticket-a"].completed_at = "2024-01-01T01:00:00"
        state_machine1._save_state()

        # Verify state file saved with ticket-a completed
        assert state_file.exists()
        with open(state_file, "r") as f:
            state = json.load(f)
        assert state["tickets"]["ticket-a"]["state"] == "COMPLETED"
        assert state["tickets"]["ticket-b"]["state"] == "PENDING"

        # Second session: Resume from state
        state_machine2 = EpicStateMachine(epic_file, resume=True)

        # Verify state loaded correctly
        assert state_machine2.tickets["ticket-a"].state == TicketState.COMPLETED
        assert state_machine2.tickets["ticket-a"].git_info.final_commit == "commit456"
        assert state_machine2.tickets["ticket-b"].state == TicketState.PENDING
        assert state_machine2.tickets["ticket-c"].state == TicketState.PENDING

        # Verify baseline commit preserved
        assert state_machine2.baseline_commit == "baseline123"

    @patch("cli.epic.state_machine.GitOperations")
    def test_resume_skips_completed_tickets(
        self, mock_git_class, epic_with_tickets
    ):
        """Test that resume skips tickets already in COMPLETED state."""
        epic_file, epic_dir, repo_dir = epic_with_tickets
        state_file = epic_dir / "artifacts" / "epic-state.json"

        # Create state with ticket-a completed
        state_data = {
            "schema_version": 1,
            "epic_id": "test-resume-epic",
            "epic_branch": "epic/test-resume-epic",
            "baseline_commit": "baseline123",
            "epic_state": "EXECUTING",
            "tickets": {
                "ticket-a": {
                    "id": "ticket-a",
                    "path": str(epic_dir / "tickets" / "ticket-a.md"),
                    "title": "First ticket",
                    "depends_on": [],
                    "critical": False,
                    "state": "COMPLETED",
                    "git_info": {
                        "branch_name": "ticket/ticket-a",
                        "base_commit": "baseline123",
                        "final_commit": "commit456",
                    },
                    "test_suite_status": "passing",
                    "acceptance_criteria": [],
                    "failure_reason": None,
                    "blocking_dependency": None,
                    "started_at": "2024-01-01T00:00:00",
                    "completed_at": "2024-01-01T01:00:00",
                },
                "ticket-b": {
                    "id": "ticket-b",
                    "path": str(epic_dir / "tickets" / "ticket-b.md"),
                    "title": "Second ticket",
                    "depends_on": ["ticket-a"],
                    "critical": False,
                    "state": "PENDING",
                    "git_info": None,
                    "test_suite_status": None,
                    "acceptance_criteria": [],
                    "failure_reason": None,
                    "blocking_dependency": None,
                    "started_at": None,
                    "completed_at": None,
                },
                "ticket-c": {
                    "id": "ticket-c",
                    "path": str(epic_dir / "tickets" / "ticket-c.md"),
                    "title": "Third ticket",
                    "depends_on": ["ticket-b"],
                    "critical": False,
                    "state": "PENDING",
                    "git_info": None,
                    "test_suite_status": None,
                    "acceptance_criteria": [],
                    "failure_reason": None,
                    "blocking_dependency": None,
                    "started_at": None,
                    "completed_at": None,
                },
            },
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        # Mock git operations
        mock_git = MagicMock()
        mock_git.branch_exists_remote.return_value = True
        mock_git_class.return_value = mock_git

        # Resume state machine
        state_machine = EpicStateMachine(epic_file, resume=True)

        # Get ready tickets - should return ticket-b (ticket-a already completed)
        ready_tickets = state_machine._get_ready_tickets()

        assert len(ready_tickets) == 1
        assert ready_tickets[0].id == "ticket-b"

    @patch("cli.epic.state_machine.GitOperations")
    def test_resume_with_failed_ticket(
        self, mock_git_class, epic_with_tickets
    ):
        """Test resuming with a failed ticket blocks dependents."""
        epic_file, epic_dir, repo_dir = epic_with_tickets
        state_file = epic_dir / "artifacts" / "epic-state.json"

        # Create state with ticket-a failed and ticket-b blocked
        state_data = {
            "schema_version": 1,
            "epic_id": "test-resume-epic",
            "epic_branch": "epic/test-resume-epic",
            "baseline_commit": "baseline123",
            "epic_state": "EXECUTING",
            "tickets": {
                "ticket-a": {
                    "id": "ticket-a",
                    "path": str(epic_dir / "tickets" / "ticket-a.md"),
                    "title": "First ticket",
                    "depends_on": [],
                    "critical": False,
                    "state": "FAILED",
                    "git_info": {
                        "branch_name": "ticket/ticket-a",
                        "base_commit": "baseline123",
                        "final_commit": None,
                    },
                    "test_suite_status": "failing",
                    "acceptance_criteria": [],
                    "failure_reason": "Tests failed",
                    "blocking_dependency": None,
                    "started_at": "2024-01-01T00:00:00",
                    "completed_at": None,
                },
                "ticket-b": {
                    "id": "ticket-b",
                    "path": str(epic_dir / "tickets" / "ticket-b.md"),
                    "title": "Second ticket",
                    "depends_on": ["ticket-a"],
                    "critical": False,
                    "state": "BLOCKED",
                    "git_info": None,
                    "test_suite_status": None,
                    "acceptance_criteria": [],
                    "failure_reason": None,
                    "blocking_dependency": "ticket-a",
                    "started_at": None,
                    "completed_at": None,
                },
                "ticket-c": {
                    "id": "ticket-c",
                    "path": str(epic_dir / "tickets" / "ticket-c.md"),
                    "title": "Third ticket",
                    "depends_on": ["ticket-b"],
                    "critical": False,
                    "state": "BLOCKED",
                    "git_info": None,
                    "test_suite_status": None,
                    "acceptance_criteria": [],
                    "failure_reason": None,
                    "blocking_dependency": "ticket-b",
                    "started_at": None,
                    "completed_at": None,
                },
            },
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        # Mock git operations
        mock_git = MagicMock()
        mock_git.branch_exists_remote.return_value = True
        mock_git_class.return_value = mock_git

        # Resume state machine
        state_machine = EpicStateMachine(epic_file, resume=True)

        # Verify failed and blocked states preserved
        assert state_machine.tickets["ticket-a"].state == TicketState.FAILED
        assert state_machine.tickets["ticket-a"].failure_reason == "Tests failed"
        assert state_machine.tickets["ticket-b"].state == TicketState.BLOCKED
        assert state_machine.tickets["ticket-b"].blocking_dependency == "ticket-a"
        assert state_machine.tickets["ticket-c"].state == TicketState.BLOCKED

        # No ready tickets (all blocked or failed)
        ready_tickets = state_machine._get_ready_tickets()
        assert len(ready_tickets) == 0

    @patch("cli.epic.state_machine.GitOperations")
    def test_resume_validates_branches_exist(
        self, mock_git_class, epic_with_tickets
    ):
        """Test that resume validates branches exist on remote."""
        epic_file, epic_dir, repo_dir = epic_with_tickets
        state_file = epic_dir / "artifacts" / "epic-state.json"

        # Create state with completed ticket
        state_data = {
            "schema_version": 1,
            "epic_id": "test-resume-epic",
            "epic_branch": "epic/test-resume-epic",
            "baseline_commit": "baseline123",
            "epic_state": "EXECUTING",
            "tickets": {
                "ticket-a": {
                    "id": "ticket-a",
                    "path": str(epic_dir / "tickets" / "ticket-a.md"),
                    "title": "First ticket",
                    "depends_on": [],
                    "critical": False,
                    "state": "COMPLETED",
                    "git_info": {
                        "branch_name": "ticket/ticket-a",
                        "base_commit": "baseline123",
                        "final_commit": "commit456",
                    },
                    "test_suite_status": "passing",
                    "acceptance_criteria": [],
                    "failure_reason": None,
                    "blocking_dependency": None,
                    "started_at": "2024-01-01T00:00:00",
                    "completed_at": "2024-01-01T01:00:00",
                },
            },
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        # Mock git: epic branch exists but ticket branch doesn't
        mock_git = MagicMock()
        def branch_exists_side_effect(branch_name):
            if branch_name == "epic/test-resume-epic":
                return True
            return False
        mock_git.branch_exists_remote.side_effect = branch_exists_side_effect
        mock_git_class.return_value = mock_git

        # Should raise error about missing ticket branch
        with pytest.raises(ValueError, match="does not exist on remote"):
            EpicStateMachine(epic_file, resume=True)

    @patch("cli.epic.state_machine.GitOperations")
    def test_resume_preserves_timestamps(
        self, mock_git_class, epic_with_tickets
    ):
        """Test that resume preserves started_at and completed_at timestamps."""
        epic_file, epic_dir, repo_dir = epic_with_tickets
        state_file = epic_dir / "artifacts" / "epic-state.json"

        started_time = "2024-01-01T10:00:00"
        completed_time = "2024-01-01T11:30:00"

        # Create state with timestamps
        state_data = {
            "schema_version": 1,
            "epic_id": "test-resume-epic",
            "epic_branch": "epic/test-resume-epic",
            "baseline_commit": "baseline123",
            "epic_state": "EXECUTING",
            "tickets": {
                "ticket-a": {
                    "id": "ticket-a",
                    "path": str(epic_dir / "tickets" / "ticket-a.md"),
                    "title": "First ticket",
                    "depends_on": [],
                    "critical": False,
                    "state": "COMPLETED",
                    "git_info": {
                        "branch_name": "ticket/ticket-a",
                        "base_commit": "baseline123",
                        "final_commit": "commit456",
                    },
                    "test_suite_status": "passing",
                    "acceptance_criteria": [],
                    "failure_reason": None,
                    "blocking_dependency": None,
                    "started_at": started_time,
                    "completed_at": completed_time,
                },
            },
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        # Mock git operations
        mock_git = MagicMock()
        mock_git.branch_exists_remote.return_value = True
        mock_git_class.return_value = mock_git

        # Resume state machine
        state_machine = EpicStateMachine(epic_file, resume=True)

        # Verify timestamps preserved
        ticket_a = state_machine.tickets["ticket-a"]
        assert ticket_a.started_at == started_time
        assert ticket_a.completed_at == completed_time
