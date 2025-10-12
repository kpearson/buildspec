"""Integration tests for EpicStateMachine.

Tests the state machine with mocked ClaudeTicketBuilder to verify the complete
execution flow without actually running Claude Code.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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

        # Get current branch name (could be master or main)
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        branch_name = result.stdout.strip()

        # Set up fake remote (just a local path)
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
def simple_epic(temp_git_repo):
    """Create a simple 3-ticket epic for testing."""
    repo_path = temp_git_repo

    # Create epic directory
    epic_dir = repo_path / ".epics" / "simple-epic"
    epic_dir.mkdir(parents=True)

    # Create tickets directory
    tickets_dir = epic_dir / "tickets"
    tickets_dir.mkdir()

    # Create epic YAML
    epic_file = epic_dir / "simple-epic.epic.yaml"
    epic_data = {
        "epic": "Simple Epic",
        "description": "Test epic with 3 sequential tickets",
        "ticket_count": 3,
        "rollback_on_failure": False,
        "tickets": [
            {
                "id": "ticket-a",
                "description": "Ticket A: First ticket with no dependencies",
                "depends_on": [],
                "critical": True,
            },
            {
                "id": "ticket-b",
                "description": "Ticket B: Second ticket depends on A",
                "depends_on": ["ticket-a"],
                "critical": True,
            },
            {
                "id": "ticket-c",
                "description": "Ticket C: Third ticket depends on B",
                "depends_on": ["ticket-b"],
                "critical": False,
            },
        ],
    }

    with open(epic_file, "w") as f:
        yaml.dump(epic_data, f)

    # Create ticket markdown files
    for ticket_id in ["ticket-a", "ticket-b", "ticket-c"]:
        ticket_file = tickets_dir / f"{ticket_id}.md"
        ticket_file.write_text(
            f"# {ticket_id}\n\n"
            f"Description: Test ticket {ticket_id}\n\n"
            f"## Acceptance Criteria\n\n"
            f"- Criterion 1\n"
            f"- Criterion 2\n"
        )

    return epic_file, repo_path


class TestSimpleEpicExecution:
    """Test complete execution of a simple 3-ticket epic."""

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_execute_3_sequential_tickets(self, mock_builder_class, simple_epic):
        """Test execution of 3 sequential tickets with mocked builder."""
        epic_file, repo_path = simple_epic

        # Track which tickets were executed
        executed_tickets = []

        def mock_builder_init(ticket_file, branch_name, base_commit, epic_file):
            """Mock builder initialization."""
            builder = MagicMock()
            ticket_id = Path(ticket_file).stem

            def execute_ticket():
                """Simulate ticket execution by making a commit."""
                executed_tickets.append(ticket_id)

                # Checkout the branch and make a commit
                subprocess.run(
                    ["git", "checkout", branch_name],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )

                # Make a change
                test_file = repo_path / f"{ticket_id}.txt"
                test_file.write_text(f"Changes for {ticket_id}\n")

                # Commit
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

                # Get commit SHA
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                commit_sha = result.stdout.strip()

                return BuilderResult(
                    success=True,
                    final_commit=commit_sha,
                    test_status="passing",
                    acceptance_criteria=[
                        AcceptanceCriterion(criterion="Criterion 1", met=True),
                        AcceptanceCriterion(criterion="Criterion 2", met=True),
                    ],
                )

            builder.execute = execute_ticket
            return builder

        mock_builder_class.side_effect = mock_builder_init

        # Change to repo directory for git operations
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)

            # Execute epic
            state_machine = EpicStateMachine(epic_file)
            state_machine.execute()

            # Verify all tickets executed in order
            assert executed_tickets == ["ticket-a", "ticket-b", "ticket-c"]

            # Verify all tickets completed
            assert state_machine.tickets["ticket-a"].state == TicketState.COMPLETED
            assert state_machine.tickets["ticket-b"].state == TicketState.COMPLETED
            assert state_machine.tickets["ticket-c"].state == TicketState.COMPLETED

            # Verify git info set correctly
            for ticket_id in ["ticket-a", "ticket-b", "ticket-c"]:
                ticket = state_machine.tickets[ticket_id]
                assert ticket.git_info is not None
                assert ticket.git_info.branch_name == f"ticket/{ticket_id}"
                assert ticket.git_info.base_commit is not None
                assert ticket.git_info.final_commit is not None

            # Verify stacked branch structure
            # ticket-b should branch from ticket-a's final commit
            ticket_a = state_machine.tickets["ticket-a"]
            ticket_b = state_machine.tickets["ticket-b"]
            assert ticket_b.git_info.base_commit == ticket_a.git_info.final_commit

            # ticket-c should branch from ticket-b's final commit
            ticket_c = state_machine.tickets["ticket-c"]
            assert ticket_c.git_info.base_commit == ticket_b.git_info.final_commit

            # Verify epic state
            assert state_machine.epic_state == EpicState.FINALIZED

            # Verify state file saved
            state_file = epic_file.parent / "artifacts" / "epic-state.json"
            assert state_file.exists()

            with open(state_file, "r") as f:
                state = json.load(f)

            assert state["schema_version"] == 1
            assert state["epic_state"] == "FINALIZED"
            assert len(state["tickets"]) == 3
            assert state["tickets"]["ticket-a"]["state"] == "COMPLETED"
            assert state["tickets"]["ticket-b"]["state"] == "COMPLETED"
            assert state["tickets"]["ticket-c"]["state"] == "COMPLETED"

        finally:
            os.chdir(original_cwd)

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_builder_failure_fails_ticket(self, mock_builder_class, simple_epic):
        """Test that builder failure marks ticket as FAILED."""
        epic_file, repo_path = simple_epic

        def mock_builder_init(ticket_file, branch_name, base_commit, epic_file):
            """Mock builder that fails for ticket-b."""
            builder = MagicMock()
            ticket_id = Path(ticket_file).stem

            def execute_ticket():
                if ticket_id == "ticket-a":
                    # Success for ticket-a
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
                            AcceptanceCriterion(criterion="Criterion 1", met=True),
                        ],
                    )
                else:
                    # Fail for other tickets
                    return BuilderResult(
                        success=False,
                        error=f"Builder failed for {ticket_id}",
                    )

            builder.execute = execute_ticket
            return builder

        mock_builder_class.side_effect = mock_builder_init

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)

            # Execute epic
            state_machine = EpicStateMachine(epic_file)
            state_machine.execute()

            # Verify ticket-a completed
            assert state_machine.tickets["ticket-a"].state == TicketState.COMPLETED

            # Verify ticket-b failed
            assert state_machine.tickets["ticket-b"].state == TicketState.FAILED
            assert state_machine.tickets["ticket-b"].failure_reason is not None

            # Verify ticket-c remained pending (dependencies not met)
            assert state_machine.tickets["ticket-c"].state == TicketState.PENDING

            # Verify epic failed
            assert state_machine.epic_state == EpicState.FAILED

        finally:
            os.chdir(original_cwd)

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_validation_failure_fails_ticket(self, mock_builder_class, simple_epic):
        """Test that validation failure marks ticket as FAILED."""
        epic_file, repo_path = simple_epic

        def mock_builder_init(ticket_file, branch_name, base_commit, epic_file):
            """Mock builder that returns failing tests."""
            builder = MagicMock()
            ticket_id = Path(ticket_file).stem

            def execute_ticket():
                # Checkout and make commit
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

                # Return with failing test status
                return BuilderResult(
                    success=True,
                    final_commit=result.stdout.strip(),
                    test_status="failing",  # Tests failed!
                    acceptance_criteria=[
                        AcceptanceCriterion(criterion="Criterion 1", met=True),
                    ],
                )

            builder.execute = execute_ticket
            return builder

        mock_builder_class.side_effect = mock_builder_init

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)

            # Execute epic
            state_machine = EpicStateMachine(epic_file)
            state_machine.execute()

            # Verify ticket-a failed due to validation (critical with failing tests)
            assert state_machine.tickets["ticket-a"].state == TicketState.FAILED
            assert "Validation failed" in state_machine.tickets["ticket-a"].failure_reason

        finally:
            os.chdir(original_cwd)


class TestStateFilePersistence:
    """Test state file persistence during execution."""

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_state_file_updated_after_each_transition(
        self, mock_builder_class, simple_epic
    ):
        """Test that state file is updated after each state transition."""
        epic_file, repo_path = simple_epic

        # Track state transitions
        state_snapshots = []

        original_save_state = EpicStateMachine._save_state

        def capture_state(self):
            """Capture state after each save."""
            original_save_state(self)
            state_file = self.state_file
            if state_file.exists():
                with open(state_file, "r") as f:
                    state_snapshots.append(json.load(f))

        def mock_builder_init(ticket_file, branch_name, base_commit, epic_file):
            """Mock builder for ticket-a only."""
            builder = MagicMock()
            ticket_id = Path(ticket_file).stem

            def execute_ticket():
                if ticket_id == "ticket-a":
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
                            AcceptanceCriterion(criterion="Test", met=True),
                        ],
                    )
                else:
                    return BuilderResult(success=False, error="Stop after ticket-a")

            builder.execute = execute_ticket
            return builder

        mock_builder_class.side_effect = mock_builder_init

        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)

            with patch.object(EpicStateMachine, "_save_state", capture_state):
                # Execute epic
                state_machine = EpicStateMachine(epic_file)
                state_machine.execute()

            # Verify we have multiple state snapshots
            assert len(state_snapshots) > 3

            # Verify state transitions captured
            ticket_a_states = [
                s["tickets"]["ticket-a"]["state"]
                for s in state_snapshots
                if "tickets" in s and "ticket-a" in s["tickets"]
            ]

            # Should see progression: PENDING -> READY -> BRANCH_CREATED -> IN_PROGRESS -> AWAITING_VALIDATION -> COMPLETED
            assert "PENDING" in ticket_a_states
            assert "READY" in ticket_a_states
            assert "COMPLETED" in ticket_a_states

        finally:
            os.chdir(original_cwd)


class TestEpicFinalization:
    """Integration tests for epic finalization with branch collapse."""

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_finalization_collapses_branches(self, mock_builder_class, simple_epic):
        """Test that finalization collapses all ticket branches into epic branch."""
        epic_file, repo_path = simple_epic

        def mock_builder_init(ticket_file, branch_name, base_commit, epic_file):
            """Mock builder that creates real commits."""
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

            # Execute epic
            state_machine = EpicStateMachine(epic_file)
            state_machine.execute()

            # Verify epic finalized
            assert state_machine.epic_state == EpicState.FINALIZED

            # Verify ticket branches deleted locally
            result = subprocess.run(
                ["git", "branch", "--list"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            local_branches = result.stdout
            assert "ticket/ticket-a" not in local_branches
            assert "ticket/ticket-b" not in local_branches
            assert "ticket/ticket-c" not in local_branches

            # Verify epic branch exists
            assert "epic/simple-epic" in local_branches

            # Verify epic branch has all changes
            subprocess.run(
                ["git", "checkout", "epic/simple-epic"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # All ticket files should exist
            assert (repo_path / "ticket-a.txt").exists()
            assert (repo_path / "ticket-b.txt").exists()
            assert (repo_path / "ticket-c.txt").exists()

            # Verify commit messages in epic branch
            result = subprocess.run(
                ["git", "log", "--oneline", "epic/simple-epic"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            log = result.stdout

            # Should have commits for all tickets with "feat:" prefix
            assert "feat:" in log
            # Check that ticket content is present (titles or IDs)
            assert "ticket" in log.lower()

        finally:
            os.chdir(original_cwd)

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_finalization_orders_by_dependencies(self, mock_builder_class, simple_epic):
        """Test that finalization merges tickets in dependency order."""
        epic_file, repo_path = simple_epic

        # Track merge order by intercepting git merge commands
        merge_order = []

        from cli.epic.git_operations import GitOperations
        original_run_git = GitOperations._run_git_command

        def track_merge(self, args, check=True, capture_output=True):
            """Track merge order by intercepting git merge commands."""
            if len(args) >= 3 and args[1] == "merge" and args[2] == "--squash":
                # git merge --squash -X ours branch_name
                # Extract branch name (last argument)
                branch = args[-1]
                if not branch.startswith("-"):  # Make sure it's not a flag
                    merge_order.append(branch)
            return original_run_git(self, args, check, capture_output)

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

            with patch.object(GitOperations, "_run_git_command", track_merge):
                # Execute epic
                state_machine = EpicStateMachine(epic_file)
                state_machine.execute()

            # Verify merge order (A -> B -> C)
            assert merge_order == [
                "ticket/ticket-a",
                "ticket/ticket-b",
                "ticket/ticket-c",
            ]

        finally:
            os.chdir(original_cwd)

    @patch("cli.epic.state_machine.ClaudeTicketBuilder")
    def test_finalization_with_partial_failures(self, mock_builder_class, simple_epic):
        """Test finalization only merges completed tickets, skips failed ones."""
        epic_file, repo_path = simple_epic

        def mock_builder_init(ticket_file, branch_name, base_commit, epic_file):
            """Mock builder that fails ticket-b."""
            builder = MagicMock()
            ticket_id = Path(ticket_file).stem

            def execute_ticket():
                if ticket_id == "ticket-b":
                    # Fail ticket-b
                    return BuilderResult(
                        success=False,
                        error="Simulated failure",
                    )

                # Success for others
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

            # Execute epic
            state_machine = EpicStateMachine(epic_file)
            state_machine.execute()

            # Verify ticket states
            assert state_machine.tickets["ticket-a"].state == TicketState.COMPLETED
            assert state_machine.tickets["ticket-b"].state == TicketState.FAILED
            assert state_machine.tickets["ticket-c"].state == TicketState.BLOCKED

            # Epic should be finalized even with partial failure
            assert state_machine.epic_state == EpicState.FINALIZED

            # Verify only ticket-a merged to epic branch
            subprocess.run(
                ["git", "checkout", "epic/simple-epic"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Only ticket-a file should exist
            assert (repo_path / "ticket-a.txt").exists()
            assert not (repo_path / "ticket-b.txt").exists()
            assert not (repo_path / "ticket-c.txt").exists()

        finally:
            os.chdir(original_cwd)
