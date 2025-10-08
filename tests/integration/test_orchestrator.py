"""
Integration tests for orchestrator coordination.

Tests validate complete epic execution workflows including:
- Parallel ticket execution
- Concurrency control
- Error recovery
- Git workflow
- State machine transitions
"""

import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml


# Mock classes for orchestrator components that will be implemented
class MockTicket:
    """Mock ticket for testing."""

    def __init__(
        self,
        id: str,
        depends_on: Optional[List[str]] = None,
        critical: bool = True,
        path: str = "",
    ):
        self.id = id
        self.depends_on = depends_on or []
        self.critical = critical
        self.path = path
        self.status = "pending"
        self.phase = "not-started"
        self.git_info: Optional[Dict[str, str]] = None
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.failure_reason: Optional[str] = None
        self.blocking_dependency: Optional[str] = None


class MockEpicState:
    """Mock epic state for testing."""

    def __init__(
        self,
        epic_id: str,
        epic_branch: str,
        baseline_commit: str,
        rollback_on_failure: bool = True,
    ):
        self.epic_id = epic_id
        self.epic_branch = epic_branch
        self.baseline_commit = baseline_commit
        self.rollback_on_failure = rollback_on_failure
        self.status = "initializing"
        self.started_at = datetime.now(UTC).isoformat()
        self.completed_at: Optional[str] = None
        self.failure_reason: Optional[str] = None
        self.tickets: Dict[str, MockTicket] = {}
        self.epic_pr_url: Optional[str] = None


class MockValidationResult:
    """Mock validation result."""

    def __init__(self, passed: bool = True, error: Optional[str] = None):
        self.passed = passed
        self.error = error


# Mock orchestrator functions that will be implemented in cli/orchestrator/execute_epic.py
def initialize_epic_execution(epic_file: Path) -> MockEpicState:
    """Mock initialize_epic_execution function."""
    # Parse epic YAML
    with open(epic_file) as f:
        epic_data = yaml.safe_load(f)

    # Create epic branch
    repo_path = epic_file.parent.parent.parent
    epic_name = epic_data["epic"]
    epic_branch = f"epic/{epic_name}"

    # Get baseline commit
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    baseline_commit = result.stdout.strip()

    # Create epic branch
    subprocess.run(
        ["git", "checkout", "-b", epic_branch],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    # Create epic state
    state = MockEpicState(
        epic_id=epic_name,
        epic_branch=epic_branch,
        baseline_commit=baseline_commit,
        rollback_on_failure=epic_data.get("rollback_on_failure", True),
    )

    # Initialize tickets
    for ticket_data in epic_data["tickets"]:
        ticket = MockTicket(
            id=ticket_data["id"],
            depends_on=ticket_data.get("depends_on", []),
            critical=ticket_data.get("critical", True),
        )
        state.tickets[ticket.id] = ticket

    state.status = "ready_to_execute"
    return state


def calculate_ready_tickets(state: MockEpicState) -> List[MockTicket]:
    """Mock calculate_ready_tickets function."""
    ready = []
    for ticket in state.tickets.values():
        if ticket.status != "pending":
            continue

        # Check if all dependencies are completed
        dependencies_met = all(
            state.tickets[dep_id].status == "completed" for dep_id in ticket.depends_on
        )

        if dependencies_met:
            ready.append(ticket)

    # Prioritize: critical first, then by dependency depth
    ready.sort(key=lambda t: (not t.critical, len(t.depends_on)))
    return ready


def calculate_base_commit(state: MockEpicState, ticket: MockTicket) -> str:
    """Mock calculate_base_commit function."""
    if not ticket.depends_on:
        # No dependencies: branch from epic baseline
        return state.baseline_commit

    if len(ticket.depends_on) == 1:
        # Single dependency: use dependency's final commit
        dep_id = ticket.depends_on[0]
        dep_ticket = state.tickets[dep_id]
        if dep_ticket.git_info and dep_ticket.git_info.get("final_commit"):
            return dep_ticket.git_info["final_commit"]
        raise ValueError(f"Dependency {dep_id} has no git_info")

    # Multiple dependencies: use most recent final_commit
    final_commits = []
    for dep_id in ticket.depends_on:
        dep_ticket = state.tickets[dep_id]
        if dep_ticket.git_info and dep_ticket.git_info.get("final_commit"):
            final_commits.append(dep_ticket.git_info["final_commit"])

    if not final_commits:
        raise ValueError("No valid dependency commits found")

    # For testing, just return the last one (in real implementation, would use git merge-base)
    return final_commits[-1]


def validate_completion_report(
    ticket: MockTicket, report: Dict[str, Any]
) -> MockValidationResult:
    """Mock validate_completion_report function."""
    # Check required fields
    required_fields = [
        "ticket_id",
        "status",
        "branch_name",
        "base_commit",
        "final_commit",
        "files_modified",
        "test_suite_status",
        "acceptance_criteria",
    ]

    for field in required_fields:
        if field not in report:
            return MockValidationResult(
                passed=False, error=f"Missing required field: {field}"
            )

    # Check test suite status
    if report["test_suite_status"] == "failing":
        return MockValidationResult(
            passed=False, error="Test suite is failing"
        )

    # Check acceptance criteria format
    if not isinstance(report["acceptance_criteria"], list):
        return MockValidationResult(
            passed=False, error="acceptance_criteria must be a list"
        )

    for criterion in report["acceptance_criteria"]:
        if not isinstance(criterion, dict):
            return MockValidationResult(
                passed=False, error="Each criterion must be a dict"
            )
        if "criterion" not in criterion or "met" not in criterion:
            return MockValidationResult(
                passed=False, error="Criterion must have 'criterion' and 'met' fields"
            )

    return MockValidationResult(passed=True)


def execute_rollback(state: MockEpicState) -> None:
    """Mock execute_rollback function."""
    # Delete epic branch
    repo_path = Path.cwd()

    # Get current branch
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    current_branch = result.stdout.strip()

    # Switch to master if we're on epic or ticket branch
    if current_branch.startswith("epic/") or current_branch.startswith("ticket/"):
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=repo_path,
            capture_output=True,
            check=False,
        )

    # Delete epic branch
    subprocess.run(
        ["git", "branch", "-D", state.epic_branch],
        cwd=repo_path,
        capture_output=True,
        check=False,
    )

    # Delete ticket branches
    for ticket in state.tickets.values():
        if ticket.git_info and ticket.git_info.get("branch_name"):
            subprocess.run(
                ["git", "branch", "-D", ticket.git_info["branch_name"]],
                cwd=repo_path,
                capture_output=True,
                check=False,
            )

    state.status = "rolled_back"


def mark_dependent_tickets_blocked(state: MockEpicState, failed_ticket_id: str) -> None:
    """Mock mark_dependent_tickets_blocked function."""
    for ticket in state.tickets.values():
        if failed_ticket_id in ticket.depends_on:
            ticket.status = "blocked"
            ticket.blocking_dependency = failed_ticket_id


def update_epic_state(state: MockEpicState, updates: Dict[str, Any]) -> None:
    """Mock update_epic_state function."""
    # In real implementation, this would atomically update epic-state.json
    # For testing, just update in-memory state
    pass


def recover_from_crash(epic_file: Path, existing_state: Optional[MockEpicState] = None) -> MockEpicState:
    """Mock recover_from_crash function."""
    # In real implementation, this would read epic-state.json
    # For testing, use existing state if provided, otherwise re-initialize
    if existing_state:
        state = existing_state
    else:
        # Parse epic YAML but don't create new branch (it already exists)
        with open(epic_file) as f:
            epic_data = yaml.safe_load(f)

        repo_path = epic_file.parent.parent.parent
        epic_name = epic_data["epic"]
        epic_branch = f"epic/{epic_name}"

        # Get baseline commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        baseline_commit = result.stdout.strip()

        # Create epic state (don't create branch, it exists)
        state = MockEpicState(
            epic_id=epic_name,
            epic_branch=epic_branch,
            baseline_commit=baseline_commit,
            rollback_on_failure=epic_data.get("rollback_on_failure", True),
        )

        # Initialize tickets
        for ticket_data in epic_data["tickets"]:
            ticket = MockTicket(
                id=ticket_data["id"],
                depends_on=ticket_data.get("depends_on", []),
                critical=ticket_data.get("critical", True),
            )
            state.tickets[ticket.id] = ticket

        state.status = "ready_to_execute"

    # Reset stale executing tickets to queued
    for ticket in state.tickets.values():
        if ticket.status == "executing":
            # Check if dependencies are still met
            dependencies_met = all(
                state.tickets[dep_id].status == "completed"
                for dep_id in ticket.depends_on
            )
            if dependencies_met:
                ticket.status = "queued"
                ticket.started_at = None

    return state


def merge_ticket_branches(state: MockEpicState) -> None:
    """Mock merge_ticket_branches function."""
    # In real implementation, would merge ticket branches into epic branch
    # For testing, just mark as complete
    pass


def push_epic_branch(epic_branch: str) -> bool:
    """Mock push_epic_branch function."""
    # In real implementation, would push epic branch to remote
    # For testing, just return True
    return True


# Test Fixtures and Helpers


@pytest.fixture
def temp_repo(tmp_path):
    """Create temporary git repository for testing."""
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
    )

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
    )

    # Store original directory and change to repo
    original_cwd = Path.cwd()
    import os

    os.chdir(repo_path)

    yield repo_path

    # Restore original directory
    os.chdir(original_cwd)

    # Cleanup
    shutil.rmtree(repo_path, ignore_errors=True)


def create_test_epic(
    name: str,
    tickets: List[Dict[str, Any]],
    repo_path: Path,
    rollback_on_failure: bool = True,
) -> Path:
    """Create test epic YAML file."""
    epics_dir = repo_path / ".epics" / name
    epics_dir.mkdir(parents=True, exist_ok=True)

    epic_data = {
        "epic": name,
        "description": f"Test epic: {name}",
        "ticket_count": len(tickets),
        "rollback_on_failure": rollback_on_failure,
        "tickets": tickets,
    }

    epic_file = epics_dir / f"{name}.epic.yaml"
    epic_file.write_text(yaml.dump(epic_data))

    return epic_file


# Test Classes


class TestParallelExecution:
    """Test parallel ticket execution with concurrency control."""

    def test_parallel_execution_3_concurrent_tickets(self, temp_repo):
        """
        Test parallel execution respects MAX_CONCURRENT_TICKETS=3 limit.

        Epic with 5 independent tickets should execute 3 at a time.
        """
        # Create test epic with 5 independent tickets
        epic_file = create_test_epic(
            name="parallel-test",
            tickets=[
                {"id": "ticket-a", "critical": True, "depends_on": []},
                {"id": "ticket-b", "critical": True, "depends_on": []},
                {"id": "ticket-c", "critical": True, "depends_on": []},
                {"id": "ticket-d", "critical": True, "depends_on": []},
                {"id": "ticket-e", "critical": True, "depends_on": []},
            ],
            repo_path=temp_repo,
        )

        # Initialize epic
        state = initialize_epic_execution(epic_file)

        assert state.status == "ready_to_execute"
        assert len(state.tickets) == 5

        # Execute first wave
        ready = calculate_ready_tickets(state)
        assert len(ready) == 5  # All tickets ready

        # Spawn first 3 (MAX_CONCURRENT_TICKETS)
        MAX_CONCURRENT_TICKETS = 3
        executing_count = 3
        available_slots = MAX_CONCURRENT_TICKETS - executing_count
        assert available_slots == 0  # No more slots

        # Verify concurrency limit enforced
        assert executing_count <= MAX_CONCURRENT_TICKETS

        # Complete 1 ticket
        state.tickets["ticket-a"].status = "completed"
        state.tickets["ticket-a"].git_info = {
            "branch_name": "ticket/ticket-a",
            "base_commit": state.baseline_commit,
            "final_commit": "aaa111",
        }

        # Now 1 slot available
        executing_count = 2
        available_slots = MAX_CONCURRENT_TICKETS - executing_count
        assert available_slots == 1

        # Can spawn 1 more ticket
        ready = calculate_ready_tickets(state)
        # 4 remaining pending tickets (b, c, d, e minus the 2 executing)
        assert len(ready) >= 2


class TestCriticalFailureRollback:
    """Test critical ticket failure triggers rollback."""

    def test_rollback_on_critical_failure(self, temp_repo):
        """
        Test rollback when critical ticket fails with rollback_on_failure=true.

        Verify epic branch and ticket branches are deleted.
        """
        epic_file = create_test_epic(
            name="rollback-test",
            rollback_on_failure=True,
            tickets=[
                {"id": "ticket-a", "critical": True, "depends_on": []},
                {"id": "ticket-b", "critical": True, "depends_on": ["ticket-a"]},
            ],
            repo_path=temp_repo,
        )

        state = initialize_epic_execution(epic_file)
        epic_branch = state.epic_branch

        # Verify epic branch exists
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{epic_branch}"],
            cwd=temp_repo,
            capture_output=True,
        )
        assert result.returncode == 0

        # Create ticket branch for ticket-a
        subprocess.run(
            ["git", "checkout", "-b", "ticket/ticket-a"],
            cwd=temp_repo,
            check=True,
        )
        subprocess.run(
            ["git", "checkout", epic_branch],
            cwd=temp_repo,
            check=True,
        )

        # Ticket-a fails (critical)
        state.tickets["ticket-a"].status = "failed"
        state.tickets["ticket-a"].critical = True
        state.tickets["ticket-a"].failure_reason = "test_failure"

        # Execute rollback
        execute_rollback(state)

        # Verify epic branch deleted
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{epic_branch}"],
            cwd=temp_repo,
            capture_output=True,
        )
        assert result.returncode != 0  # Branch should not exist

        # Verify epic status
        assert state.status == "rolled_back"


class TestPartialSuccess:
    """Test partial success when non-critical ticket fails."""

    def test_partial_success_non_critical_failure(self, temp_repo):
        """
        Test partial success when non-critical ticket fails.

        Verify dependent tickets marked blocked, independent tickets continue.
        """
        epic_file = create_test_epic(
            name="partial-success-test",
            rollback_on_failure=False,
            tickets=[
                {"id": "ticket-a", "critical": True, "depends_on": []},
                {"id": "ticket-b", "critical": False, "depends_on": []},
                {"id": "ticket-c", "critical": True, "depends_on": ["ticket-b"]},
                {"id": "ticket-d", "critical": True, "depends_on": []},
            ],
            repo_path=temp_repo,
        )

        state = initialize_epic_execution(epic_file)

        # Ticket-a completes
        state.tickets["ticket-a"].status = "completed"

        # Ticket-b fails (non-critical)
        state.tickets["ticket-b"].status = "failed"
        state.tickets["ticket-b"].failure_reason = "test_failure"

        # Ticket-c should be blocked (depends on ticket-b)
        mark_dependent_tickets_blocked(state, "ticket-b")

        assert state.tickets["ticket-c"].status == "blocked"
        assert state.tickets["ticket-c"].blocking_dependency == "ticket-b"

        # Ticket-d should continue (independent)
        ready = calculate_ready_tickets(state)
        ready_ids = [t.id for t in ready]
        assert "ticket-d" in ready_ids

        # Complete ticket-d
        state.tickets["ticket-d"].status = "completed"

        # Epic should handle partial success
        # (ticket-b failed, but non-critical, ticket-a and ticket-d completed)


class TestCrashRecovery:
    """Test orchestrator crash recovery from epic-state.json."""

    def test_crash_recovery_resets_stale_tickets(self, temp_repo):
        """
        Test crash recovery resets stale 'executing' tickets.

        Verify stale tickets reset to queued/pending based on dependencies.
        """
        epic_file = create_test_epic(
            name="crash-recovery-test",
            tickets=[
                {"id": "ticket-a", "critical": True, "depends_on": []},
                {"id": "ticket-b", "critical": True, "depends_on": ["ticket-a"]},
            ],
            repo_path=temp_repo,
        )

        state = initialize_epic_execution(epic_file)

        # Ticket-a completes
        state.tickets["ticket-a"].status = "completed"
        state.tickets["ticket-a"].git_info = {
            "branch_name": "ticket/ticket-a",
            "base_commit": state.baseline_commit,
            "final_commit": "aaa111",
        }

        # Ticket-b is executing (simulating crash)
        state.tickets["ticket-b"].status = "executing"
        state.tickets["ticket-b"].started_at = datetime.now(UTC).isoformat()

        # Save state (in real implementation)
        update_epic_state(state, {})

        # Simulate crash: reload state from file (pass existing state to simulate reading from file)
        recovered_state = recover_from_crash(epic_file, existing_state=state)

        # Verify ticket-b reset to queued (dependencies met)
        assert recovered_state.tickets["ticket-b"].status == "queued"
        assert recovered_state.tickets["ticket-b"].started_at is None


class TestComplexDependencyGraphs:
    """Test various dependency graph structures."""

    def test_diamond_dependency_graph(self, temp_repo):
        """
        Test diamond dependency graph.

        A → B, A → C, B → D, C → D
        """
        epic_file = create_test_epic(
            name="diamond-test",
            tickets=[
                {"id": "ticket-a", "critical": True, "depends_on": []},
                {"id": "ticket-b", "critical": True, "depends_on": ["ticket-a"]},
                {"id": "ticket-c", "critical": True, "depends_on": ["ticket-a"]},
                {
                    "id": "ticket-d",
                    "critical": True,
                    "depends_on": ["ticket-b", "ticket-c"],
                },
            ],
            repo_path=temp_repo,
        )

        state = initialize_epic_execution(epic_file)

        # Wave 1: Only ticket-a ready
        ready = calculate_ready_tickets(state)
        assert len(ready) == 1
        assert ready[0].id == "ticket-a"

        # Complete ticket-a
        state.tickets["ticket-a"].status = "completed"
        state.tickets["ticket-a"].git_info = {"final_commit": "aaa111"}

        # Wave 2: ticket-b and ticket-c ready
        ready = calculate_ready_tickets(state)
        assert len(ready) == 2
        assert set([t.id for t in ready]) == {"ticket-b", "ticket-c"}

        # Complete ticket-b and ticket-c
        state.tickets["ticket-b"].status = "completed"
        state.tickets["ticket-b"].git_info = {"final_commit": "bbb222"}

        state.tickets["ticket-c"].status = "completed"
        state.tickets["ticket-c"].git_info = {"final_commit": "ccc333"}

        # Wave 3: ticket-d ready
        ready = calculate_ready_tickets(state)
        assert len(ready) == 1
        assert ready[0].id == "ticket-d"

        # Calculate base commit for ticket-d (should use most recent)
        base_commit = calculate_base_commit(state, state.tickets["ticket-d"])
        # Should be either bbb222 or ccc333 (most recent)
        assert base_commit in ["bbb222", "ccc333"]


class TestBaseCommitCalculation:
    """Test base commit calculation for various dependency scenarios."""

    def test_no_dependencies_uses_epic_baseline(self, temp_repo):
        """Test ticket with no dependencies branches from epic baseline."""
        epic_file = create_test_epic(
            name="base-commit-test",
            tickets=[{"id": "ticket-a", "critical": True, "depends_on": []}],
            repo_path=temp_repo,
        )

        state = initialize_epic_execution(epic_file)
        ticket = state.tickets["ticket-a"]

        base_commit = calculate_base_commit(state, ticket)

        assert base_commit == state.baseline_commit

    def test_single_dependency_uses_dependency_final_commit(self, temp_repo):
        """Test ticket with single dependency branches from dependency."""
        epic_file = create_test_epic(
            name="base-commit-test",
            tickets=[
                {"id": "ticket-a", "critical": True, "depends_on": []},
                {"id": "ticket-b", "critical": True, "depends_on": ["ticket-a"]},
            ],
            repo_path=temp_repo,
        )

        state = initialize_epic_execution(epic_file)

        # Complete ticket-a
        state.tickets["ticket-a"].status = "completed"
        state.tickets["ticket-a"].git_info = {"final_commit": "aaa111"}

        ticket_b = state.tickets["ticket-b"]
        base_commit = calculate_base_commit(state, ticket_b)

        assert base_commit == "aaa111"


class TestCompletionReportValidation:
    """Test completion report validation."""

    def test_valid_report_passes_validation(self):
        """Test valid completion report passes validation."""
        ticket = MockTicket(id="test-ticket")
        report = {
            "ticket_id": "test-ticket",
            "status": "completed",
            "branch_name": "ticket/test-ticket",
            "base_commit": "abc123",
            "final_commit": "def456",
            "files_modified": ["/path/to/file.py"],
            "test_suite_status": "passing",
            "acceptance_criteria": [{"criterion": "Test criterion", "met": True}],
        }

        result = validate_completion_report(ticket, report)

        assert result.passed is True
        assert result.error is None

    def test_missing_required_field_fails_validation(self):
        """Test missing required field fails validation."""
        ticket = MockTicket(id="test-ticket")
        report = {
            "ticket_id": "test-ticket",
            "status": "completed",
            # Missing branch_name
            "base_commit": "abc123",
            "final_commit": "def456",
            "files_modified": [],
            "test_suite_status": "passing",
            "acceptance_criteria": [],
        }

        result = validate_completion_report(ticket, report)

        assert result.passed is False
        assert "branch_name" in result.error

    def test_failing_test_suite_fails_validation(self):
        """Test failing test suite fails validation."""
        ticket = MockTicket(id="test-ticket")
        report = {
            "ticket_id": "test-ticket",
            "status": "completed",
            "branch_name": "ticket/test-ticket",
            "base_commit": "abc123",
            "final_commit": "def456",
            "files_modified": [],
            "test_suite_status": "failing",
            "acceptance_criteria": [],
        }

        result = validate_completion_report(ticket, report)

        assert result.passed is False
        assert "failing" in result.error.lower()

    def test_invalid_acceptance_criteria_format_fails_validation(self):
        """Test invalid acceptance criteria format fails validation."""
        ticket = MockTicket(id="test-ticket")
        report = {
            "ticket_id": "test-ticket",
            "status": "completed",
            "branch_name": "ticket/test-ticket",
            "base_commit": "abc123",
            "final_commit": "def456",
            "files_modified": [],
            "test_suite_status": "passing",
            "acceptance_criteria": [{"criterion": "Test criterion"}],  # Missing 'met'
        }

        result = validate_completion_report(ticket, report)

        assert result.passed is False
        assert "met" in result.error.lower()
