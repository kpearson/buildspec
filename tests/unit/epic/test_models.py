"""Unit tests for epic state machine data models."""

import pytest
from cli.epic.models import (
    AcceptanceCriterion,
    BuilderResult,
    EpicState,
    GateResult,
    GitInfo,
    Ticket,
    TicketState,
)


class TestTicketState:
    """Test TicketState enum."""

    def test_enum_values(self):
        """Test all enum values are correctly defined."""
        assert TicketState.PENDING == "PENDING"
        assert TicketState.READY == "READY"
        assert TicketState.BRANCH_CREATED == "BRANCH_CREATED"
        assert TicketState.IN_PROGRESS == "IN_PROGRESS"
        assert TicketState.AWAITING_VALIDATION == "AWAITING_VALIDATION"
        assert TicketState.COMPLETED == "COMPLETED"
        assert TicketState.FAILED == "FAILED"
        assert TicketState.BLOCKED == "BLOCKED"

    def test_enum_count(self):
        """Test that all expected states are present."""
        assert len(TicketState) == 8

    def test_string_behavior(self):
        """Test that enum inherits from str."""
        assert isinstance(TicketState.PENDING, str)
        assert TicketState.PENDING == "PENDING"


class TestEpicState:
    """Test EpicState enum."""

    def test_enum_values(self):
        """Test all enum values are correctly defined."""
        assert EpicState.INITIALIZING == "INITIALIZING"
        assert EpicState.EXECUTING == "EXECUTING"
        assert EpicState.MERGING == "MERGING"
        assert EpicState.FINALIZED == "FINALIZED"
        assert EpicState.FAILED == "FAILED"
        assert EpicState.ROLLED_BACK == "ROLLED_BACK"

    def test_enum_count(self):
        """Test that all expected states are present."""
        assert len(EpicState) == 6

    def test_string_behavior(self):
        """Test that enum inherits from str."""
        assert isinstance(EpicState.INITIALIZING, str)
        assert EpicState.INITIALIZING == "INITIALIZING"


class TestGitInfo:
    """Test GitInfo dataclass."""

    def test_default_initialization(self):
        """Test initialization with default values."""
        git_info = GitInfo()
        assert git_info.branch_name is None
        assert git_info.base_commit is None
        assert git_info.final_commit is None

    def test_partial_initialization(self):
        """Test initialization with some values."""
        git_info = GitInfo(branch_name="feature-branch")
        assert git_info.branch_name == "feature-branch"
        assert git_info.base_commit is None
        assert git_info.final_commit is None

    def test_full_initialization(self):
        """Test initialization with all values."""
        git_info = GitInfo(
            branch_name="feature-branch",
            base_commit="abc123",
            final_commit="def456",
        )
        assert git_info.branch_name == "feature-branch"
        assert git_info.base_commit == "abc123"
        assert git_info.final_commit == "def456"

    def test_immutability(self):
        """Test that GitInfo is immutable (frozen)."""
        git_info = GitInfo(branch_name="feature-branch")
        with pytest.raises(AttributeError):
            git_info.branch_name = "new-branch"  # type: ignore


class TestAcceptanceCriterion:
    """Test AcceptanceCriterion dataclass."""

    def test_default_initialization(self):
        """Test initialization with default values."""
        criterion = AcceptanceCriterion(criterion="Test criterion")
        assert criterion.criterion == "Test criterion"
        assert criterion.met is False

    def test_full_initialization(self):
        """Test initialization with all values."""
        criterion = AcceptanceCriterion(criterion="Test criterion", met=True)
        assert criterion.criterion == "Test criterion"
        assert criterion.met is True

    def test_mutability(self):
        """Test that AcceptanceCriterion is mutable."""
        criterion = AcceptanceCriterion(criterion="Test criterion")
        criterion.met = True
        assert criterion.met is True


class TestGateResult:
    """Test GateResult dataclass."""

    def test_minimal_initialization(self):
        """Test initialization with minimal required fields."""
        result = GateResult(passed=True)
        assert result.passed is True
        assert result.reason is None
        assert result.metadata == {}

    def test_full_initialization(self):
        """Test initialization with all values."""
        metadata = {"key": "value", "count": 42}
        result = GateResult(passed=False, reason="Dependencies not met", metadata=metadata)
        assert result.passed is False
        assert result.reason == "Dependencies not met"
        assert result.metadata == metadata

    def test_immutability(self):
        """Test that GateResult is immutable (frozen)."""
        result = GateResult(passed=True)
        with pytest.raises(AttributeError):
            result.passed = False  # type: ignore

    def test_default_metadata(self):
        """Test that each instance gets its own metadata dict."""
        result1 = GateResult(passed=True)
        result2 = GateResult(passed=False)
        # Since it's frozen, we can't modify, but we can verify they're different instances
        assert result1.metadata is not result2.metadata


class TestBuilderResult:
    """Test BuilderResult dataclass."""

    def test_minimal_initialization(self):
        """Test initialization with minimal required fields."""
        result = BuilderResult(success=True)
        assert result.success is True
        assert result.final_commit is None
        assert result.test_status is None
        assert result.acceptance_criteria == []
        assert result.error is None
        assert result.stdout is None
        assert result.stderr is None

    def test_full_initialization(self):
        """Test initialization with all values."""
        criteria = [
            AcceptanceCriterion(criterion="Criterion 1", met=True),
            AcceptanceCriterion(criterion="Criterion 2", met=False),
        ]
        result = BuilderResult(
            success=False,
            final_commit="abc123",
            test_status="passing",
            acceptance_criteria=criteria,
            error="Build failed",
            stdout="Build output",
            stderr="Build errors",
        )
        assert result.success is False
        assert result.final_commit == "abc123"
        assert result.test_status == "passing"
        assert result.acceptance_criteria == criteria
        assert result.error == "Build failed"
        assert result.stdout == "Build output"
        assert result.stderr == "Build errors"

    def test_immutability(self):
        """Test that BuilderResult is immutable (frozen)."""
        result = BuilderResult(success=True)
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore

    def test_default_acceptance_criteria(self):
        """Test that each instance gets its own acceptance_criteria list."""
        result1 = BuilderResult(success=True)
        result2 = BuilderResult(success=False)
        # Since it's frozen, we can't modify, but we can verify they're different instances
        assert result1.acceptance_criteria is not result2.acceptance_criteria


class TestTicket:
    """Test Ticket dataclass."""

    def test_minimal_initialization(self):
        """Test initialization with minimal required fields."""
        ticket = Ticket(id="ticket-1", path="/path/to/ticket", title="Test Ticket")
        assert ticket.id == "ticket-1"
        assert ticket.path == "/path/to/ticket"
        assert ticket.title == "Test Ticket"
        assert ticket.depends_on == []
        assert ticket.critical is False
        assert ticket.state == TicketState.PENDING
        assert isinstance(ticket.git_info, GitInfo)
        assert ticket.test_suite_status is None
        assert ticket.acceptance_criteria == []
        assert ticket.failure_reason is None
        assert ticket.blocking_dependency is None
        assert ticket.started_at is None
        assert ticket.completed_at is None

    def test_full_initialization(self):
        """Test initialization with all values."""
        git_info = GitInfo(
            branch_name="ticket-branch",
            base_commit="base123",
            final_commit="final456",
        )
        criteria = [
            AcceptanceCriterion(criterion="Criterion 1", met=True),
            AcceptanceCriterion(criterion="Criterion 2", met=True),
        ]
        ticket = Ticket(
            id="ticket-1",
            path="/path/to/ticket",
            title="Test Ticket",
            depends_on=["ticket-0"],
            critical=True,
            state=TicketState.COMPLETED,
            git_info=git_info,
            test_suite_status="passing",
            acceptance_criteria=criteria,
            failure_reason=None,
            blocking_dependency=None,
            started_at="2024-01-01T00:00:00Z",
            completed_at="2024-01-01T01:00:00Z",
        )
        assert ticket.id == "ticket-1"
        assert ticket.path == "/path/to/ticket"
        assert ticket.title == "Test Ticket"
        assert ticket.depends_on == ["ticket-0"]
        assert ticket.critical is True
        assert ticket.state == TicketState.COMPLETED
        assert ticket.git_info == git_info
        assert ticket.test_suite_status == "passing"
        assert ticket.acceptance_criteria == criteria
        assert ticket.failure_reason is None
        assert ticket.blocking_dependency is None
        assert ticket.started_at == "2024-01-01T00:00:00Z"
        assert ticket.completed_at == "2024-01-01T01:00:00Z"

    def test_failed_ticket(self):
        """Test initialization of a failed ticket."""
        ticket = Ticket(
            id="ticket-1",
            path="/path/to/ticket",
            title="Failed Ticket",
            state=TicketState.FAILED,
            failure_reason="Tests failed",
        )
        assert ticket.state == TicketState.FAILED
        assert ticket.failure_reason == "Tests failed"

    def test_blocked_ticket(self):
        """Test initialization of a blocked ticket."""
        ticket = Ticket(
            id="ticket-2",
            path="/path/to/ticket",
            title="Blocked Ticket",
            depends_on=["ticket-1"],
            state=TicketState.BLOCKED,
            blocking_dependency="ticket-1",
        )
        assert ticket.state == TicketState.BLOCKED
        assert ticket.blocking_dependency == "ticket-1"
        assert "ticket-1" in ticket.depends_on

    def test_mutability(self):
        """Test that Ticket is mutable."""
        ticket = Ticket(id="ticket-1", path="/path/to/ticket", title="Test Ticket")
        ticket.state = TicketState.IN_PROGRESS
        ticket.started_at = "2024-01-01T00:00:00Z"
        assert ticket.state == TicketState.IN_PROGRESS
        assert ticket.started_at == "2024-01-01T00:00:00Z"

    def test_default_lists(self):
        """Test that each instance gets its own default lists."""
        ticket1 = Ticket(id="ticket-1", path="/path/1", title="Ticket 1")
        ticket2 = Ticket(id="ticket-2", path="/path/2", title="Ticket 2")
        ticket1.depends_on.append("ticket-0")
        assert "ticket-0" in ticket1.depends_on
        assert "ticket-0" not in ticket2.depends_on

    def test_state_transitions(self):
        """Test various state transitions."""
        ticket = Ticket(id="ticket-1", path="/path/to/ticket", title="Test Ticket")

        # PENDING -> READY
        assert ticket.state == TicketState.PENDING
        ticket.state = TicketState.READY
        assert ticket.state == TicketState.READY

        # READY -> BRANCH_CREATED
        ticket.state = TicketState.BRANCH_CREATED
        assert ticket.state == TicketState.BRANCH_CREATED

        # BRANCH_CREATED -> IN_PROGRESS
        ticket.state = TicketState.IN_PROGRESS
        assert ticket.state == TicketState.IN_PROGRESS

        # IN_PROGRESS -> AWAITING_VALIDATION
        ticket.state = TicketState.AWAITING_VALIDATION
        assert ticket.state == TicketState.AWAITING_VALIDATION

        # AWAITING_VALIDATION -> COMPLETED
        ticket.state = TicketState.COMPLETED
        assert ticket.state == TicketState.COMPLETED
