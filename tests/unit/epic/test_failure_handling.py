"""Unit tests for failure handling methods in EpicStateMachine."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from cli.epic.models import (
    EpicState,
    GitInfo,
    Ticket,
    TicketState,
)
from cli.epic.state_machine import EpicStateMachine


@pytest.fixture
def temp_epic_dir():
    """Create a temporary epic directory with YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        epic_dir = Path(tmpdir) / "test-epic"
        epic_dir.mkdir()

        # Create artifacts directory
        artifacts_dir = epic_dir / "artifacts"
        artifacts_dir.mkdir()

        # Create tickets directory
        tickets_dir = epic_dir / "tickets"
        tickets_dir.mkdir()

        # Create epic YAML with rollback_on_failure
        epic_file = epic_dir / "test-epic.epic.yaml"
        epic_data = {
            "epic": "Test Epic",
            "description": "Test epic description",
            "ticket_count": 4,
            "rollback_on_failure": True,
            "tickets": [
                {
                    "id": "ticket-a",
                    "description": "Ticket A description",
                    "depends_on": [],
                    "critical": True,
                },
                {
                    "id": "ticket-b",
                    "description": "Ticket B description",
                    "depends_on": ["ticket-a"],
                    "critical": False,
                },
                {
                    "id": "ticket-c",
                    "description": "Ticket C description",
                    "depends_on": ["ticket-b"],
                    "critical": False,
                },
                {
                    "id": "ticket-d",
                    "description": "Ticket D description (independent)",
                    "depends_on": [],
                    "critical": False,
                },
            ],
        }

        with open(epic_file, "w") as f:
            yaml.dump(epic_data, f)

        # Create ticket markdown files
        for ticket_id in ["ticket-a", "ticket-b", "ticket-c", "ticket-d"]:
            ticket_file = tickets_dir / f"{ticket_id}.md"
            ticket_file.write_text(f"# {ticket_id}\n\nTest ticket")

        yield epic_file, epic_dir


@pytest.fixture
def temp_epic_dir_no_rollback():
    """Create a temporary epic directory without rollback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        epic_dir = Path(tmpdir) / "test-epic"
        epic_dir.mkdir()

        # Create artifacts directory
        artifacts_dir = epic_dir / "artifacts"
        artifacts_dir.mkdir()

        # Create tickets directory
        tickets_dir = epic_dir / "tickets"
        tickets_dir.mkdir()

        # Create epic YAML without rollback_on_failure
        epic_file = epic_dir / "test-epic.epic.yaml"
        epic_data = {
            "epic": "Test Epic",
            "description": "Test epic description",
            "ticket_count": 2,
            "rollback_on_failure": False,
            "tickets": [
                {
                    "id": "ticket-a",
                    "description": "Ticket A description",
                    "depends_on": [],
                    "critical": True,
                },
                {
                    "id": "ticket-b",
                    "description": "Ticket B description",
                    "depends_on": ["ticket-a"],
                    "critical": False,
                },
            ],
        }

        with open(epic_file, "w") as f:
            yaml.dump(epic_data, f)

        # Create ticket markdown files
        for ticket_id in ["ticket-a", "ticket-b"]:
            ticket_file = tickets_dir / f"{ticket_id}.md"
            ticket_file.write_text(f"# {ticket_id}\n\nTest ticket")

        yield epic_file, epic_dir


class TestFindDependents:
    """Tests for _find_dependents method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_find_dependents_no_dependents(self, mock_git_class, temp_epic_dir):
        """Test finding dependents when ticket has no dependents."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # ticket-c has no dependents
        dependents = state_machine._find_dependents("ticket-c")

        assert dependents == []

    @patch("cli.epic.state_machine.GitOperations")
    def test_find_dependents_single_dependent(self, mock_git_class, temp_epic_dir):
        """Test finding dependents when ticket has one dependent."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # ticket-b depends on ticket-a
        dependents = state_machine._find_dependents("ticket-a")

        assert len(dependents) == 1
        assert "ticket-b" in dependents

    @patch("cli.epic.state_machine.GitOperations")
    def test_find_dependents_multiple_dependents(self, mock_git_class, temp_epic_dir):
        """Test finding dependents when ticket has multiple dependents."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Add another ticket that depends on ticket-a
        state_machine.tickets["ticket-e"] = Ticket(
            id="ticket-e",
            path="/fake/path",
            title="Ticket E",
            depends_on=["ticket-a"],
            critical=False,
            state=TicketState.PENDING,
        )

        dependents = state_machine._find_dependents("ticket-a")

        assert len(dependents) == 2
        assert "ticket-b" in dependents
        assert "ticket-e" in dependents

    @patch("cli.epic.state_machine.GitOperations")
    def test_find_dependents_chain(self, mock_git_class, temp_epic_dir):
        """Test finding dependents in a dependency chain."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # ticket-b depends on ticket-a
        dependents_a = state_machine._find_dependents("ticket-a")
        assert "ticket-b" in dependents_a

        # ticket-c depends on ticket-b
        dependents_b = state_machine._find_dependents("ticket-b")
        assert "ticket-c" in dependents_b


class TestHandleTicketFailure:
    """Tests for _handle_ticket_failure method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_handle_failure_blocks_dependents(self, mock_git_class, temp_epic_dir):
        """Test that failure blocks dependent tickets."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Set up tickets
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_a.state = TicketState.FAILED
        ticket_a.failure_reason = "Test failure"

        ticket_b = state_machine.tickets["ticket-b"]
        ticket_b.state = TicketState.PENDING

        # Handle failure
        state_machine._handle_ticket_failure(ticket_a)

        # Verify ticket-b is blocked
        assert ticket_b.state == TicketState.BLOCKED
        assert ticket_b.blocking_dependency == "ticket-a"

    @patch("cli.epic.state_machine.GitOperations")
    def test_handle_failure_cascades_to_all_dependents(self, mock_git_class, temp_epic_dir):
        """Test that failure cascades to all dependent tickets."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Set up tickets
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_a.state = TicketState.FAILED
        ticket_a.failure_reason = "Test failure"

        ticket_b = state_machine.tickets["ticket-b"]
        ticket_b.state = TicketState.PENDING

        ticket_c = state_machine.tickets["ticket-c"]
        ticket_c.state = TicketState.PENDING

        # Handle failure
        state_machine._handle_ticket_failure(ticket_a)

        # Verify ticket-b is blocked (direct dependent)
        assert ticket_b.state == TicketState.BLOCKED
        assert ticket_b.blocking_dependency == "ticket-a"

        # Note: ticket-c should NOT be blocked yet since ticket-b hasn't failed
        # It will be blocked when ticket-b fails
        assert ticket_c.state == TicketState.PENDING

    @patch("cli.epic.state_machine.GitOperations")
    def test_handle_failure_does_not_block_completed_tickets(
        self, mock_git_class, temp_epic_dir
    ):
        """Test that failure doesn't block already completed tickets."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Set up tickets
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_a.state = TicketState.FAILED
        ticket_a.failure_reason = "Test failure"

        ticket_b = state_machine.tickets["ticket-b"]
        ticket_b.state = TicketState.COMPLETED

        # Handle failure
        state_machine._handle_ticket_failure(ticket_a)

        # Verify ticket-b remains completed
        assert ticket_b.state == TicketState.COMPLETED
        assert ticket_b.blocking_dependency is None

    @patch("cli.epic.state_machine.GitOperations")
    def test_handle_failure_does_not_block_failed_tickets(
        self, mock_git_class, temp_epic_dir
    ):
        """Test that failure doesn't block already failed tickets."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Set up tickets
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_a.state = TicketState.FAILED
        ticket_a.failure_reason = "Test failure"

        ticket_b = state_machine.tickets["ticket-b"]
        ticket_b.state = TicketState.FAILED

        # Handle failure
        state_machine._handle_ticket_failure(ticket_a)

        # Verify ticket-b remains failed
        assert ticket_b.state == TicketState.FAILED

    @patch("cli.epic.state_machine.GitOperations")
    def test_handle_failure_critical_with_rollback(self, mock_git_class, temp_epic_dir):
        """Test that critical failure with rollback triggers rollback."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Set up critical ticket
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_a.state = TicketState.FAILED
        ticket_a.failure_reason = "Test failure"
        ticket_a.critical = True

        # Handle failure
        state_machine._handle_ticket_failure(ticket_a)

        # Verify epic state is FAILED (rollback placeholder sets this)
        assert state_machine.epic_state == EpicState.FAILED

    @patch("cli.epic.state_machine.GitOperations")
    def test_handle_failure_critical_without_rollback(
        self, mock_git_class, temp_epic_dir_no_rollback
    ):
        """Test that critical failure without rollback fails epic."""
        epic_file, epic_dir = temp_epic_dir_no_rollback

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Set up critical ticket
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_a.state = TicketState.FAILED
        ticket_a.failure_reason = "Test failure"
        ticket_a.critical = True

        # Handle failure
        state_machine._handle_ticket_failure(ticket_a)

        # Verify epic state is FAILED
        assert state_machine.epic_state == EpicState.FAILED

    @patch("cli.epic.state_machine.GitOperations")
    def test_handle_failure_non_critical_allows_independent_tickets(
        self, mock_git_class, temp_epic_dir
    ):
        """Test that non-critical failure allows independent tickets to continue."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Set up non-critical ticket failure
        ticket_b = state_machine.tickets["ticket-b"]
        ticket_b.state = TicketState.FAILED
        ticket_b.failure_reason = "Test failure"
        ticket_b.critical = False

        ticket_d = state_machine.tickets["ticket-d"]
        ticket_d.state = TicketState.PENDING

        # Handle failure
        state_machine._handle_ticket_failure(ticket_b)

        # Verify epic remains EXECUTING
        assert state_machine.epic_state == EpicState.EXECUTING

        # Verify independent ticket remains unaffected
        assert ticket_d.state == TicketState.PENDING
        assert ticket_d.blocking_dependency is None


class TestFailTicket:
    """Tests for _fail_ticket method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_fail_ticket_sets_failure_reason(self, mock_git_class, temp_epic_dir):
        """Test that _fail_ticket sets failure_reason."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        ticket = state_machine.tickets["ticket-a"]
        ticket.state = TicketState.IN_PROGRESS

        state_machine._fail_ticket("ticket-a", "Test failure reason")

        assert ticket.state == TicketState.FAILED
        assert ticket.failure_reason == "Test failure reason"

    @patch("cli.epic.state_machine.GitOperations")
    def test_fail_ticket_triggers_cascading(self, mock_git_class, temp_epic_dir):
        """Test that _fail_ticket triggers cascading to dependents."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Set up tickets
        ticket_a = state_machine.tickets["ticket-a"]
        ticket_a.state = TicketState.IN_PROGRESS

        ticket_b = state_machine.tickets["ticket-b"]
        ticket_b.state = TicketState.PENDING

        # Fail ticket
        state_machine._fail_ticket("ticket-a", "Test failure")

        # Verify cascading happened
        assert ticket_a.state == TicketState.FAILED
        assert ticket_b.state == TicketState.BLOCKED
        assert ticket_b.blocking_dependency == "ticket-a"

    @patch("cli.epic.state_machine.GitOperations")
    def test_fail_ticket_saves_state(self, mock_git_class, temp_epic_dir):
        """Test that _fail_ticket saves state to file."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        ticket = state_machine.tickets["ticket-a"]
        ticket.state = TicketState.IN_PROGRESS

        # Fail ticket
        state_machine._fail_ticket("ticket-a", "Test failure")

        # Check state file updated
        state_file = epic_dir / "artifacts" / "epic-state.json"
        with open(state_file, "r") as f:
            state = json.load(f)

        assert state["tickets"]["ticket-a"]["state"] == "FAILED"
        assert state["tickets"]["ticket-a"]["failure_reason"] == "Test failure"
        assert state["tickets"]["ticket-b"]["state"] == "BLOCKED"
        assert state["tickets"]["ticket-b"]["blocking_dependency"] == "ticket-a"


class TestBlockedTicketsCannotTransitionToReady:
    """Tests to verify BLOCKED tickets cannot transition to READY."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_blocked_tickets_not_in_ready_tickets(self, mock_git_class, temp_epic_dir):
        """Test that BLOCKED tickets are not returned by _get_ready_tickets."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Block a ticket
        ticket_b = state_machine.tickets["ticket-b"]
        ticket_b.state = TicketState.BLOCKED
        ticket_b.blocking_dependency = "ticket-a"

        # Get ready tickets
        ready = state_machine._get_ready_tickets()

        # Verify blocked ticket is not in ready tickets
        ready_ids = [t.id for t in ready]
        assert "ticket-b" not in ready_ids

    @patch("cli.epic.state_machine.GitOperations")
    def test_pending_tickets_can_transition_to_ready(
        self, mock_git_class, temp_epic_dir
    ):
        """Test that PENDING tickets with met dependencies can transition to READY."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Get ready tickets (should return ticket-a and ticket-d which have no deps)
        ready = state_machine._get_ready_tickets()

        ready_ids = [t.id for t in ready]
        assert "ticket-a" in ready_ids
        assert "ticket-d" in ready_ids
        assert len(ready_ids) == 2
