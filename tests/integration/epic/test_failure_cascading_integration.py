"""Integration tests for failure cascading scenarios."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from cli.epic.models import (
    AcceptanceCriterion,
    BuilderResult,
    EpicState,
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

        subprocess.run(
            ["git", "init"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        test_file = repo_dir / "README.md"
        test_file.write_text("# Test Repo")
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        yield repo_dir


def create_epic_with_dependencies(repo_dir: Path, epic_name: str, tickets: list):
    """Create an epic directory with ticket dependencies."""
    epic_dir = repo_dir / ".epics" / epic_name
    epic_dir.mkdir(parents=True)

    # Create artifacts directory
    artifacts_dir = epic_dir / "artifacts"
    artifacts_dir.mkdir()

    # Create tickets directory
    tickets_dir = epic_dir / "tickets"
    tickets_dir.mkdir()

    # Create epic YAML
    epic_file = epic_dir / f"{epic_name}.epic.yaml"
    epic_data = {
        "epic": epic_name,
        "description": "Test epic for failure cascading",
        "ticket_count": len(tickets),
        "rollback_on_failure": False,
        "tickets": tickets,
    }

    with open(epic_file, "w") as f:
        yaml.dump(epic_data, f)

    # Create ticket markdown files
    for ticket in tickets:
        ticket_file = tickets_dir / f"{ticket['id']}.md"
        ticket_file.write_text(f"# {ticket['id']}\n\nTest ticket")

    return epic_file


class TestNonCriticalFailureBlocksDependents:
    """Test that non-critical ticket failure blocks dependents but allows independent tickets."""

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_noncritical_failure_blocks_dependents(
        self, mock_builder_class, temp_git_repo
    ):
        """Test ticket B (non-critical) fails, ticket D (depends on B) blocked, ticket C (independent) continues."""
        repo_dir = temp_git_repo

        # Create epic: A, B (depends on A), C (independent), D (depends on B)
        tickets = [
            {
                "id": "ticket-a",
                "description": "Ticket A",
                "depends_on": [],
                "critical": False,
            },
            {
                "id": "ticket-b",
                "description": "Ticket B",
                "depends_on": ["ticket-a"],
                "critical": False,
            },
            {
                "id": "ticket-c",
                "description": "Ticket C (independent)",
                "depends_on": [],
                "critical": False,
            },
            {
                "id": "ticket-d",
                "description": "Ticket D",
                "depends_on": ["ticket-b"],
                "critical": False,
            },
        ]

        epic_file = create_epic_with_dependencies(repo_dir, "test-epic", tickets)

        # Mock builder to succeed for A and C, fail for B
        def create_mock_builder(ticket_file, *args, **kwargs):
            mock_builder = MagicMock()

            if "ticket-a" in str(ticket_file):
                mock_builder.execute.return_value = BuilderResult(
                    success=True,
                    final_commit="commit-a",
                    test_status="passing",
                    acceptance_criteria=[
                        AcceptanceCriterion(criterion="Test", met=True)
                    ],
                )
            elif "ticket-b" in str(ticket_file):
                mock_builder.execute.return_value = BuilderResult(
                    success=False,
                    error="Builder failed for ticket B",
                )
            elif "ticket-c" in str(ticket_file):
                mock_builder.execute.return_value = BuilderResult(
                    success=True,
                    final_commit="commit-c",
                    test_status="passing",
                    acceptance_criteria=[
                        AcceptanceCriterion(criterion="Test", met=True)
                    ],
                )
            else:
                mock_builder.execute.return_value = BuilderResult(success=False, error="Unexpected ticket")

            return mock_builder

        mock_builder_class.side_effect = create_mock_builder

        # Create and execute state machine
        state_machine = EpicStateMachine(epic_file)

        # Mock git operations for simplicity
        with patch.object(state_machine.git, "create_branch"):
            with patch.object(state_machine.git, "push_branch"):
                with patch.object(state_machine.git, "branch_exists_remote", return_value=True):
                    with patch.object(state_machine.git, "get_commits_between", return_value=["commit1"]):
                        with patch.object(state_machine.git, "commit_exists", return_value=True):
                            with patch.object(state_machine.git, "commit_on_branch", return_value=True):
                                state_machine.execute()

        # Verify results
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_b = state_machine.tickets["ticket-b"]
        ticket_c = state_machine.tickets["ticket-c"]
        ticket_d = state_machine.tickets["ticket-d"]

        # ticket-a should be completed
        assert ticket_a.state == TicketState.COMPLETED

        # ticket-b should be failed
        assert ticket_b.state == TicketState.FAILED
        assert "Builder failed" in ticket_b.failure_reason

        # ticket-c should be completed (independent)
        assert ticket_c.state == TicketState.COMPLETED

        # ticket-d should be blocked
        assert ticket_d.state == TicketState.BLOCKED
        assert ticket_d.blocking_dependency == "ticket-b"

        # Epic should still be EXECUTING or FAILED (depending on final state)
        assert state_machine.epic_state in [EpicState.EXECUTING, EpicState.FAILED]


class TestCriticalFailureTransitionsEpicToFailed:
    """Test that critical ticket failure transitions epic to FAILED."""

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_critical_failure_transitions_epic_to_failed(
        self, mock_builder_class, temp_git_repo
    ):
        """Test critical ticket A fails, epic transitions to FAILED, dependents blocked."""
        repo_dir = temp_git_repo

        # Create epic: A (critical), B (depends on A), C (independent)
        tickets = [
            {
                "id": "ticket-a",
                "description": "Ticket A (critical)",
                "depends_on": [],
                "critical": True,
            },
            {
                "id": "ticket-b",
                "description": "Ticket B",
                "depends_on": ["ticket-a"],
                "critical": False,
            },
            {
                "id": "ticket-c",
                "description": "Ticket C (independent)",
                "depends_on": [],
                "critical": False,
            },
        ]

        epic_file = create_epic_with_dependencies(repo_dir, "test-epic", tickets)

        # Mock builder to fail for A
        def create_mock_builder(ticket_file, *args, **kwargs):
            mock_builder = MagicMock()

            if "ticket-a" in str(ticket_file):
                mock_builder.execute.return_value = BuilderResult(
                    success=False,
                    error="Critical failure in ticket A",
                )
            else:
                mock_builder.execute.return_value = BuilderResult(success=False, error="Unexpected ticket")

            return mock_builder

        mock_builder_class.side_effect = create_mock_builder

        # Create and execute state machine
        state_machine = EpicStateMachine(epic_file)

        # Mock git operations
        with patch.object(state_machine.git, "create_branch"):
            with patch.object(state_machine.git, "push_branch"):
                with patch.object(state_machine.git, "branch_exists_remote", return_value=True):
                    state_machine.execute()

        # Verify results
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_b = state_machine.tickets["ticket-b"]

        # ticket-a should be failed
        assert ticket_a.state == TicketState.FAILED
        assert "Critical failure" in ticket_a.failure_reason

        # ticket-b should be blocked
        assert ticket_b.state == TicketState.BLOCKED
        assert ticket_b.blocking_dependency == "ticket-a"

        # Epic should be FAILED
        assert state_machine.epic_state == EpicState.FAILED


class TestDiamondDependencyPartialExecution:
    """Test diamond dependency with partial execution (one path fails)."""

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_diamond_dependency_one_path_fails(
        self, mock_builder_class, temp_git_repo
    ):
        """Test diamond (A → B, A → C, B+C → D), B fails, verify C completes, D blocked."""
        repo_dir = temp_git_repo

        # Create diamond dependency: A → B, A → C, (B,C) → D
        tickets = [
            {
                "id": "ticket-a",
                "description": "Ticket A",
                "depends_on": [],
                "critical": False,
            },
            {
                "id": "ticket-b",
                "description": "Ticket B",
                "depends_on": ["ticket-a"],
                "critical": False,
            },
            {
                "id": "ticket-c",
                "description": "Ticket C",
                "depends_on": ["ticket-a"],
                "critical": False,
            },
            {
                "id": "ticket-d",
                "description": "Ticket D",
                "depends_on": ["ticket-b", "ticket-c"],
                "critical": False,
            },
        ]

        epic_file = create_epic_with_dependencies(repo_dir, "test-epic", tickets)

        # Mock builder to succeed for A and C, fail for B
        def create_mock_builder(ticket_file, *args, **kwargs):
            mock_builder = MagicMock()

            if "ticket-a" in str(ticket_file):
                mock_builder.execute.return_value = BuilderResult(
                    success=True,
                    final_commit="commit-a",
                    test_status="passing",
                    acceptance_criteria=[
                        AcceptanceCriterion(criterion="Test", met=True)
                    ],
                )
            elif "ticket-b" in str(ticket_file):
                mock_builder.execute.return_value = BuilderResult(
                    success=False,
                    error="Ticket B failed",
                )
            elif "ticket-c" in str(ticket_file):
                mock_builder.execute.return_value = BuilderResult(
                    success=True,
                    final_commit="commit-c",
                    test_status="passing",
                    acceptance_criteria=[
                        AcceptanceCriterion(criterion="Test", met=True)
                    ],
                )
            else:
                mock_builder.execute.return_value = BuilderResult(success=False, error="Unexpected ticket")

            return mock_builder

        mock_builder_class.side_effect = create_mock_builder

        # Create and execute state machine
        state_machine = EpicStateMachine(epic_file)

        # Mock git operations
        with patch.object(state_machine.git, "create_branch"):
            with patch.object(state_machine.git, "push_branch"):
                with patch.object(state_machine.git, "branch_exists_remote", return_value=True):
                    with patch.object(state_machine.git, "get_commits_between", return_value=["commit1"]):
                        with patch.object(state_machine.git, "commit_exists", return_value=True):
                            with patch.object(state_machine.git, "commit_on_branch", return_value=True):
                                with patch.object(
                                    state_machine.git,
                                    "find_most_recent_commit",
                                    return_value="commit-c",
                                ):
                                    state_machine.execute()

        # Verify results
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_b = state_machine.tickets["ticket-b"]
        ticket_c = state_machine.tickets["ticket-c"]
        ticket_d = state_machine.tickets["ticket-d"]

        # ticket-a should be completed
        assert ticket_a.state == TicketState.COMPLETED

        # ticket-b should be failed
        assert ticket_b.state == TicketState.FAILED

        # ticket-c should be completed (parallel path)
        assert ticket_c.state == TicketState.COMPLETED

        # ticket-d should be blocked (one dependency failed)
        assert ticket_d.state == TicketState.BLOCKED
        assert ticket_d.blocking_dependency == "ticket-b"


class TestValidationGateFailure:
    """Test validation gate failure triggers cascading."""

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_validation_gate_failure_blocks_dependents(
        self, mock_builder_class, temp_git_repo
    ):
        """Test builder succeeds but validation fails, verify dependent blocked."""
        repo_dir = temp_git_repo

        # Create epic: A, B (depends on A)
        tickets = [
            {
                "id": "ticket-a",
                "description": "Ticket A",
                "depends_on": [],
                "critical": False,
            },
            {
                "id": "ticket-b",
                "description": "Ticket B",
                "depends_on": ["ticket-a"],
                "critical": False,
            },
        ]

        epic_file = create_epic_with_dependencies(repo_dir, "test-epic", tickets)

        # Mock builder to succeed but with failing tests
        def create_mock_builder(ticket_file, *args, **kwargs):
            mock_builder = MagicMock()

            if "ticket-a" in str(ticket_file):
                mock_builder.execute.return_value = BuilderResult(
                    success=True,
                    final_commit="commit-a",
                    test_status="failing",  # Tests fail
                    acceptance_criteria=[
                        AcceptanceCriterion(criterion="Test", met=True)
                    ],
                )
            else:
                mock_builder.execute.return_value = BuilderResult(success=False, error="Unexpected ticket")

            return mock_builder

        mock_builder_class.side_effect = create_mock_builder

        # Create and execute state machine
        state_machine = EpicStateMachine(epic_file)

        # Make ticket-a critical so failing tests will fail validation
        state_machine.tickets["ticket-a"].critical = True

        # Mock git operations
        with patch.object(state_machine.git, "create_branch"):
            with patch.object(state_machine.git, "push_branch"):
                with patch.object(state_machine.git, "branch_exists_remote", return_value=True):
                    with patch.object(state_machine.git, "get_commits_between", return_value=["commit1"]):
                        with patch.object(state_machine.git, "commit_exists", return_value=True):
                            with patch.object(state_machine.git, "commit_on_branch", return_value=True):
                                state_machine.execute()

        # Verify results
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_b = state_machine.tickets["ticket-b"]

        # ticket-a should be failed (validation failed)
        assert ticket_a.state == TicketState.FAILED
        assert "Validation failed" in ticket_a.failure_reason

        # ticket-b should be blocked
        assert ticket_b.state == TicketState.BLOCKED
        assert ticket_b.blocking_dependency == "ticket-a"


class TestMultipleIndependentWithFailure:
    """Test multiple independent tickets with one failure."""

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_multiple_independent_one_fails(
        self, mock_builder_class, temp_git_repo
    ):
        """Test 3 independent tickets, middle one fails, verify other two complete."""
        repo_dir = temp_git_repo

        # Create epic: A, B, C (all independent)
        tickets = [
            {
                "id": "ticket-a",
                "description": "Ticket A",
                "depends_on": [],
                "critical": False,
            },
            {
                "id": "ticket-b",
                "description": "Ticket B",
                "depends_on": [],
                "critical": False,
            },
            {
                "id": "ticket-c",
                "description": "Ticket C",
                "depends_on": [],
                "critical": False,
            },
        ]

        epic_file = create_epic_with_dependencies(repo_dir, "test-epic", tickets)

        # Mock builder to succeed for A and C, fail for B
        def create_mock_builder(ticket_file, *args, **kwargs):
            mock_builder = MagicMock()

            if "ticket-a" in str(ticket_file):
                mock_builder.execute.return_value = BuilderResult(
                    success=True,
                    final_commit="commit-a",
                    test_status="passing",
                    acceptance_criteria=[
                        AcceptanceCriterion(criterion="Test", met=True)
                    ],
                )
            elif "ticket-b" in str(ticket_file):
                mock_builder.execute.return_value = BuilderResult(
                    success=False,
                    error="Ticket B failed",
                )
            elif "ticket-c" in str(ticket_file):
                mock_builder.execute.return_value = BuilderResult(
                    success=True,
                    final_commit="commit-c",
                    test_status="passing",
                    acceptance_criteria=[
                        AcceptanceCriterion(criterion="Test", met=True)
                    ],
                )
            else:
                mock_builder.execute.return_value = BuilderResult(success=False, error="Unexpected ticket")

            return mock_builder

        mock_builder_class.side_effect = create_mock_builder

        # Create and execute state machine
        state_machine = EpicStateMachine(epic_file)

        # Mock git operations
        with patch.object(state_machine.git, "create_branch"):
            with patch.object(state_machine.git, "push_branch"):
                with patch.object(state_machine.git, "branch_exists_remote", return_value=True):
                    with patch.object(state_machine.git, "get_commits_between", return_value=["commit1"]):
                        with patch.object(state_machine.git, "commit_exists", return_value=True):
                            with patch.object(state_machine.git, "commit_on_branch", return_value=True):
                                with patch.object(state_machine.git, "merge_branch", return_value="merge-commit"):
                                    with patch.object(state_machine.git, "delete_branch"):
                                        state_machine.execute()

        # Verify results
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_b = state_machine.tickets["ticket-b"]
        ticket_c = state_machine.tickets["ticket-c"]

        # ticket-a should be completed
        assert ticket_a.state == TicketState.COMPLETED

        # ticket-b should be failed
        assert ticket_b.state == TicketState.FAILED

        # ticket-c should be completed
        assert ticket_c.state == TicketState.COMPLETED

        # Epic should be finalized (2 out of 3 succeeded)
        assert state_machine.epic_state == EpicState.FINALIZED
