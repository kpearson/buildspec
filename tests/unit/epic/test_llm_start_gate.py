"""Unit tests for LLMStartGate.

This module provides comprehensive test coverage for the LLMStartGate class,
which enforces synchronous execution by ensuring only one ticket is active
at a time (IN_PROGRESS or AWAITING_VALIDATION state).

Test coverage includes:
- No active tickets (should pass)
- One ticket IN_PROGRESS (should fail)
- One ticket AWAITING_VALIDATION (should fail)
- Multiple active tickets (should fail)
- Branch existence check with mocked git operations
- Edge cases: ticket without git_info, missing branch_name
"""

from unittest.mock import Mock

import pytest
from cli.epic.gates import EpicContext
from cli.epic.git_operations import GitOperations
from cli.epic.models import GitInfo, Ticket, TicketState
from cli.epic.test_gates import LLMStartGate


class TestLLMStartGate:
    """Test LLMStartGate implementation."""

    def test_passes_with_no_active_tickets(self):
        """Should pass when no other tickets are active."""
        gate = LLMStartGate()

        # Create context with tickets in non-active states
        tickets = {
            "ticket-1": Ticket(
                id="ticket-1",
                path="/path/1",
                title="Ticket 1",
                state=TicketState.COMPLETED,
            ),
            "ticket-2": Ticket(
                id="ticket-2",
                path="/path/2",
                title="Ticket 2",
                state=TicketState.PENDING,
            ),
            "ticket-3": Ticket(
                id="ticket-3",
                path="/path/3",
                title="Ticket 3",
                state=TicketState.FAILED,
            ),
        }

        # Ticket to start
        ticket_to_start = Ticket(
            id="ticket-4",
            path="/path/4",
            title="Ticket 4",
            git_info=GitInfo(branch_name="ticket/ticket-4"),
        )

        # Mock git operations
        mock_git = Mock(spec=GitOperations)
        mock_git.branch_exists_remote.return_value = True

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is True
        assert result.reason == "No active tickets"
        mock_git.branch_exists_remote.assert_called_once_with("ticket/ticket-4")

    def test_fails_with_one_ticket_in_progress(self):
        """Should fail when one ticket is IN_PROGRESS."""
        gate = LLMStartGate()

        # Create context with one IN_PROGRESS ticket
        tickets = {
            "ticket-1": Ticket(
                id="ticket-1",
                path="/path/1",
                title="Ticket 1",
                state=TicketState.IN_PROGRESS,
            ),
            "ticket-2": Ticket(
                id="ticket-2",
                path="/path/2",
                title="Ticket 2",
                state=TicketState.COMPLETED,
            ),
        }

        ticket_to_start = Ticket(
            id="ticket-3",
            path="/path/3",
            title="Ticket 3",
            git_info=GitInfo(branch_name="ticket/ticket-3"),
        )

        mock_git = Mock(spec=GitOperations)
        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is False
        assert result.reason == "Another ticket in progress (synchronous execution only)"
        # Should not check branch existence if already blocked
        mock_git.branch_exists_remote.assert_not_called()

    def test_fails_with_one_ticket_awaiting_validation(self):
        """Should fail when one ticket is AWAITING_VALIDATION."""
        gate = LLMStartGate()

        # Create context with one AWAITING_VALIDATION ticket
        tickets = {
            "ticket-1": Ticket(
                id="ticket-1",
                path="/path/1",
                title="Ticket 1",
                state=TicketState.AWAITING_VALIDATION,
            ),
            "ticket-2": Ticket(
                id="ticket-2",
                path="/path/2",
                title="Ticket 2",
                state=TicketState.COMPLETED,
            ),
        }

        ticket_to_start = Ticket(
            id="ticket-3",
            path="/path/3",
            title="Ticket 3",
            git_info=GitInfo(branch_name="ticket/ticket-3"),
        )

        mock_git = Mock(spec=GitOperations)
        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is False
        assert result.reason == "Another ticket in progress (synchronous execution only)"
        mock_git.branch_exists_remote.assert_not_called()

    def test_fails_with_multiple_active_tickets(self):
        """Should fail when multiple tickets are active."""
        gate = LLMStartGate()

        # Create context with multiple active tickets
        tickets = {
            "ticket-1": Ticket(
                id="ticket-1",
                path="/path/1",
                title="Ticket 1",
                state=TicketState.IN_PROGRESS,
            ),
            "ticket-2": Ticket(
                id="ticket-2",
                path="/path/2",
                title="Ticket 2",
                state=TicketState.AWAITING_VALIDATION,
            ),
            "ticket-3": Ticket(
                id="ticket-3",
                path="/path/3",
                title="Ticket 3",
                state=TicketState.COMPLETED,
            ),
        }

        ticket_to_start = Ticket(
            id="ticket-4",
            path="/path/4",
            title="Ticket 4",
            git_info=GitInfo(branch_name="ticket/ticket-4"),
        )

        mock_git = Mock(spec=GitOperations)
        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is False
        assert result.reason == "Another ticket in progress (synchronous execution only)"
        mock_git.branch_exists_remote.assert_not_called()

    def test_ignores_self_when_checking_active_tickets(self):
        """Should not count the ticket being checked as active."""
        gate = LLMStartGate()

        # Create context where the ticket being checked is already in tickets dict
        # and is IN_PROGRESS (simulating resumption or re-check)
        ticket_to_start = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Ticket 1",
            state=TicketState.IN_PROGRESS,
            git_info=GitInfo(branch_name="ticket/ticket-1"),
        )

        tickets = {
            "ticket-1": ticket_to_start,  # Same ticket
            "ticket-2": Ticket(
                id="ticket-2",
                path="/path/2",
                title="Ticket 2",
                state=TicketState.COMPLETED,
            ),
        }

        mock_git = Mock(spec=GitOperations)
        mock_git.branch_exists_remote.return_value = True

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        # Should pass because it ignores itself
        assert result.passed is True
        assert result.reason == "No active tickets"

    def test_fails_when_branch_does_not_exist_on_remote(self):
        """Should fail when ticket branch does not exist on remote."""
        gate = LLMStartGate()

        tickets = {
            "ticket-1": Ticket(
                id="ticket-1",
                path="/path/1",
                title="Ticket 1",
                state=TicketState.COMPLETED,
            ),
        }

        ticket_to_start = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Ticket 2",
            git_info=GitInfo(branch_name="ticket/ticket-2"),
        )

        # Mock git to return False for branch existence
        mock_git = Mock(spec=GitOperations)
        mock_git.branch_exists_remote.return_value = False

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is False
        assert "does not exist on remote" in result.reason
        assert "ticket/ticket-2" in result.reason
        mock_git.branch_exists_remote.assert_called_once_with("ticket/ticket-2")

    def test_passes_when_branch_exists_on_remote(self):
        """Should pass when branch exists on remote and no active tickets."""
        gate = LLMStartGate()

        tickets = {
            "ticket-1": Ticket(
                id="ticket-1",
                path="/path/1",
                title="Ticket 1",
                state=TicketState.COMPLETED,
            ),
        }

        ticket_to_start = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Ticket 2",
            git_info=GitInfo(branch_name="ticket/ticket-2"),
        )

        # Mock git to return True for branch existence
        mock_git = Mock(spec=GitOperations)
        mock_git.branch_exists_remote.return_value = True

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is True
        assert result.reason == "No active tickets"
        mock_git.branch_exists_remote.assert_called_once_with("ticket/ticket-2")

    def test_passes_when_ticket_has_no_git_info(self):
        """Should pass when ticket has no git_info (branch check skipped)."""
        gate = LLMStartGate()

        tickets = {
            "ticket-1": Ticket(
                id="ticket-1",
                path="/path/1",
                title="Ticket 1",
                state=TicketState.COMPLETED,
            ),
        }

        # Ticket without git_info
        ticket_to_start = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Ticket 2",
            git_info=None,
        )

        mock_git = Mock(spec=GitOperations)

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is True
        assert result.reason == "No active tickets"
        # Branch check should be skipped
        mock_git.branch_exists_remote.assert_not_called()

    def test_passes_when_ticket_has_no_branch_name(self):
        """Should pass when ticket has git_info but no branch_name."""
        gate = LLMStartGate()

        tickets = {
            "ticket-1": Ticket(
                id="ticket-1",
                path="/path/1",
                title="Ticket 1",
                state=TicketState.COMPLETED,
            ),
        }

        # Ticket with git_info but no branch_name
        ticket_to_start = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Ticket 2",
            git_info=GitInfo(branch_name=None, base_commit="abc123"),
        )

        mock_git = Mock(spec=GitOperations)

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is True
        assert result.reason == "No active tickets"
        # Branch check should be skipped
        mock_git.branch_exists_remote.assert_not_called()

    def test_empty_tickets_dict(self):
        """Should pass when tickets dictionary is empty."""
        gate = LLMStartGate()

        tickets = {}

        ticket_to_start = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Ticket 1",
            git_info=GitInfo(branch_name="ticket/ticket-1"),
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.branch_exists_remote.return_value = True

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is True
        assert result.reason == "No active tickets"

    def test_all_ticket_states_except_active_pass(self):
        """Should pass when tickets are in any state except IN_PROGRESS or AWAITING_VALIDATION."""
        gate = LLMStartGate()

        # Test all non-active states
        tickets = {
            "ticket-1": Ticket(
                id="ticket-1",
                path="/path/1",
                title="Ticket 1",
                state=TicketState.PENDING,
            ),
            "ticket-2": Ticket(
                id="ticket-2",
                path="/path/2",
                title="Ticket 2",
                state=TicketState.READY,
            ),
            "ticket-3": Ticket(
                id="ticket-3",
                path="/path/3",
                title="Ticket 3",
                state=TicketState.BRANCH_CREATED,
            ),
            "ticket-4": Ticket(
                id="ticket-4",
                path="/path/4",
                title="Ticket 4",
                state=TicketState.COMPLETED,
            ),
            "ticket-5": Ticket(
                id="ticket-5",
                path="/path/5",
                title="Ticket 5",
                state=TicketState.FAILED,
            ),
            "ticket-6": Ticket(
                id="ticket-6",
                path="/path/6",
                title="Ticket 6",
                state=TicketState.BLOCKED,
            ),
        }

        ticket_to_start = Ticket(
            id="ticket-7",
            path="/path/7",
            title="Ticket 7",
            git_info=GitInfo(branch_name="ticket/ticket-7"),
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.branch_exists_remote.return_value = True

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is True
        assert result.reason == "No active tickets"

    def test_active_count_check_is_greater_than_or_equal_to_one(self):
        """Verify the gate blocks when active_count >= 1."""
        gate = LLMStartGate()

        # Test with exactly 1 active ticket
        tickets = {
            "ticket-1": Ticket(
                id="ticket-1",
                path="/path/1",
                title="Ticket 1",
                state=TicketState.IN_PROGRESS,
            ),
        }

        ticket_to_start = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Ticket 2",
            git_info=GitInfo(branch_name="ticket/ticket-2"),
        )

        mock_git = Mock(spec=GitOperations)
        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is False
        assert result.reason == "Another ticket in progress (synchronous execution only)"

    def test_mixed_active_and_inactive_tickets(self):
        """Should fail even when there are many inactive tickets and one active."""
        gate = LLMStartGate()

        tickets = {
            "ticket-1": Ticket(
                id="ticket-1",
                path="/path/1",
                title="Ticket 1",
                state=TicketState.COMPLETED,
            ),
            "ticket-2": Ticket(
                id="ticket-2",
                path="/path/2",
                title="Ticket 2",
                state=TicketState.COMPLETED,
            ),
            "ticket-3": Ticket(
                id="ticket-3",
                path="/path/3",
                title="Ticket 3",
                state=TicketState.COMPLETED,
            ),
            "ticket-4": Ticket(
                id="ticket-4",
                path="/path/4",
                title="Ticket 4",
                state=TicketState.IN_PROGRESS,  # One active ticket
            ),
            "ticket-5": Ticket(
                id="ticket-5",
                path="/path/5",
                title="Ticket 5",
                state=TicketState.PENDING,
            ),
        }

        ticket_to_start = Ticket(
            id="ticket-6",
            path="/path/6",
            title="Ticket 6",
            git_info=GitInfo(branch_name="ticket/ticket-6"),
        )

        mock_git = Mock(spec=GitOperations)
        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket_to_start, context)

        assert result.passed is False
        assert result.reason == "Another ticket in progress (synchronous execution only)"
