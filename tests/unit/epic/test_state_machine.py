"""Unit tests for EpicStateMachine."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

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

        # Create epic YAML
        epic_file = epic_dir / "test-epic.epic.yaml"
        epic_data = {
            "epic": "Test Epic",
            "description": "Test epic description",
            "ticket_count": 3,
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
                    "critical": True,
                },
                {
                    "id": "ticket-c",
                    "description": "Ticket C description",
                    "depends_on": ["ticket-b"],
                    "critical": False,
                },
            ],
        }

        import yaml
        with open(epic_file, "w") as f:
            yaml.dump(epic_data, f)

        # Create ticket markdown files
        for ticket_id in ["ticket-a", "ticket-b", "ticket-c"]:
            ticket_file = tickets_dir / f"{ticket_id}.md"
            ticket_file.write_text(f"# {ticket_id}\n\nTest ticket")

        yield epic_file, epic_dir


class TestEpicStateMachineInitialization:
    """Tests for state machine initialization."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_init_loads_epic_config(self, mock_git_class, temp_epic_dir):
        """Test that __init__ loads epic configuration correctly."""
        epic_file, epic_dir = temp_epic_dir

        # Mock git operations
        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        assert state_machine.epic_id == "test-epic"
        assert state_machine.epic_branch == "epic/test-epic"
        assert state_machine.baseline_commit == "abc123"
        assert len(state_machine.tickets) == 3

    @patch("cli.epic.state_machine.GitOperations")
    def test_init_creates_tickets(self, mock_git_class, temp_epic_dir):
        """Test that __init__ creates ticket objects."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Check tickets created
        assert "ticket-a" in state_machine.tickets
        assert "ticket-b" in state_machine.tickets
        assert "ticket-c" in state_machine.tickets

        # Check ticket properties
        ticket_a = state_machine.tickets["ticket-a"]
        assert ticket_a.id == "ticket-a"
        assert ticket_a.state == TicketState.PENDING
        assert ticket_a.depends_on == []
        assert ticket_a.critical is True

        ticket_b = state_machine.tickets["ticket-b"]
        assert ticket_b.depends_on == ["ticket-a"]

    @patch("cli.epic.state_machine.GitOperations")
    def test_init_saves_initial_state(self, mock_git_class, temp_epic_dir):
        """Test that __init__ saves initial state to JSON."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Check state file exists
        state_file = epic_dir / "artifacts" / "epic-state.json"
        assert state_file.exists()

        # Check state file contents
        with open(state_file, "r") as f:
            state = json.load(f)

        assert state["schema_version"] == 1
        assert state["epic_id"] == "test-epic"
        assert state["baseline_commit"] == "abc123"
        assert len(state["tickets"]) == 3


class TestGetReadyTickets:
    """Tests for _get_ready_tickets method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_get_ready_tickets_returns_pending_with_met_deps(
        self, mock_git_class, temp_epic_dir
    ):
        """Test that _get_ready_tickets returns PENDING tickets with met dependencies."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Get ready tickets
        ready = state_machine._get_ready_tickets()

        # Should return ticket-a (no dependencies)
        assert len(ready) == 1
        assert ready[0].id == "ticket-a"

    @patch("cli.epic.state_machine.GitOperations")
    def test_get_ready_tickets_sorts_by_dependency_depth(
        self, mock_git_class, temp_epic_dir
    ):
        """Test that ready tickets are sorted by dependency depth."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Mark all tickets as PENDING (simulate after deps met)
        for ticket in state_machine.tickets.values():
            ticket.state = TicketState.PENDING

        # Mark ticket-a as COMPLETED
        state_machine.tickets["ticket-a"].state = TicketState.COMPLETED

        ready = state_machine._get_ready_tickets()

        # Should return ticket-b (depends on completed ticket-a)
        assert len(ready) == 1
        assert ready[0].id == "ticket-b"


class TestCalculateDependencyDepth:
    """Tests for _calculate_dependency_depth method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_calculate_depth_no_deps(self, mock_git_class, temp_epic_dir):
        """Test depth calculation for ticket with no dependencies."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)
        ticket_a = state_machine.tickets["ticket-a"]

        depth = state_machine._calculate_dependency_depth(ticket_a)
        assert depth == 0

    @patch("cli.epic.state_machine.GitOperations")
    def test_calculate_depth_with_deps(self, mock_git_class, temp_epic_dir):
        """Test depth calculation for ticket with dependencies."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Calculate depths
        depth_a = state_machine._calculate_dependency_depth(
            state_machine.tickets["ticket-a"]
        )
        depth_b = state_machine._calculate_dependency_depth(
            state_machine.tickets["ticket-b"]
        )
        depth_c = state_machine._calculate_dependency_depth(
            state_machine.tickets["ticket-c"]
        )

        assert depth_a == 0
        assert depth_b == 1
        assert depth_c == 2


class TestTransitionTicket:
    """Tests for _transition_ticket method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_transition_updates_state(self, mock_git_class, temp_epic_dir):
        """Test that transition updates ticket state."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        ticket_a = state_machine.tickets["ticket-a"]
        assert ticket_a.state == TicketState.PENDING

        state_machine._transition_ticket("ticket-a", TicketState.READY)

        assert ticket_a.state == TicketState.READY

    @patch("cli.epic.state_machine.GitOperations")
    def test_transition_saves_state(self, mock_git_class, temp_epic_dir):
        """Test that transition saves state to file."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Transition ticket
        state_machine._transition_ticket("ticket-a", TicketState.READY)

        # Check state file updated
        state_file = epic_dir / "artifacts" / "epic-state.json"
        with open(state_file, "r") as f:
            state = json.load(f)

        assert state["tickets"]["ticket-a"]["state"] == "READY"


class TestRunGate:
    """Tests for _run_gate method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_run_gate_returns_result(self, mock_git_class, temp_epic_dir):
        """Test that _run_gate returns gate result."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Mock gate
        mock_gate = MagicMock()
        mock_gate.check.return_value = GateResult(passed=True, reason="Test passed")

        ticket = state_machine.tickets["ticket-a"]
        result = state_machine._run_gate(ticket, mock_gate)

        assert result.passed is True
        assert result.reason == "Test passed"
        mock_gate.check.assert_called_once()


class TestSaveState:
    """Tests for _save_state method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_save_state_creates_valid_json(self, mock_git_class, temp_epic_dir):
        """Test that _save_state creates valid JSON."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Update some state
        state_machine.tickets["ticket-a"].state = TicketState.COMPLETED
        state_machine._save_state()

        # Load and verify JSON
        state_file = epic_dir / "artifacts" / "epic-state.json"
        with open(state_file, "r") as f:
            state = json.load(f)

        assert state["schema_version"] == 1
        assert state["tickets"]["ticket-a"]["state"] == "COMPLETED"

    @patch("cli.epic.state_machine.GitOperations")
    def test_save_state_atomic_write(self, mock_git_class, temp_epic_dir):
        """Test that _save_state uses atomic write (temp + rename)."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Save state
        state_machine._save_state()

        # State file should exist
        state_file = epic_dir / "artifacts" / "epic-state.json"
        assert state_file.exists()

        # No temp files should remain
        temp_files = list((epic_dir / "artifacts").glob("*.tmp"))
        assert len(temp_files) == 0


class TestSerializeTicket:
    """Tests for _serialize_ticket method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_serialize_ticket_basic_fields(self, mock_git_class, temp_epic_dir):
        """Test ticket serialization with basic fields."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        ticket = state_machine.tickets["ticket-a"]
        serialized = state_machine._serialize_ticket(ticket)

        assert serialized["id"] == "ticket-a"
        assert serialized["state"] == "PENDING"
        assert serialized["depends_on"] == []
        assert serialized["critical"] is True

    @patch("cli.epic.state_machine.GitOperations")
    def test_serialize_ticket_with_git_info(self, mock_git_class, temp_epic_dir):
        """Test ticket serialization with git info."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        ticket = state_machine.tickets["ticket-a"]
        ticket.git_info = GitInfo(
            branch_name="ticket/ticket-a",
            base_commit="abc123",
            final_commit="def456",
        )

        serialized = state_machine._serialize_ticket(ticket)

        assert serialized["git_info"]["branch_name"] == "ticket/ticket-a"
        assert serialized["git_info"]["base_commit"] == "abc123"
        assert serialized["git_info"]["final_commit"] == "def456"


class TestAllTicketsCompleted:
    """Tests for _all_tickets_completed method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_all_completed_returns_true(self, mock_git_class, temp_epic_dir):
        """Test returns True when all tickets in terminal states."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Mark all tickets as completed
        for ticket in state_machine.tickets.values():
            ticket.state = TicketState.COMPLETED

        assert state_machine._all_tickets_completed() is True

    @patch("cli.epic.state_machine.GitOperations")
    def test_all_completed_with_mixed_terminal_states(
        self, mock_git_class, temp_epic_dir
    ):
        """Test returns True with mix of COMPLETED, FAILED, BLOCKED."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Mix of terminal states
        state_machine.tickets["ticket-a"].state = TicketState.COMPLETED
        state_machine.tickets["ticket-b"].state = TicketState.FAILED
        state_machine.tickets["ticket-c"].state = TicketState.BLOCKED

        assert state_machine._all_tickets_completed() is True

    @patch("cli.epic.state_machine.GitOperations")
    def test_all_completed_returns_false_with_active(
        self, mock_git_class, temp_epic_dir
    ):
        """Test returns False when some tickets are active."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        state_machine.tickets["ticket-a"].state = TicketState.COMPLETED
        state_machine.tickets["ticket-b"].state = TicketState.IN_PROGRESS
        state_machine.tickets["ticket-c"].state = TicketState.PENDING

        assert state_machine._all_tickets_completed() is False


class TestHasActiveTickets:
    """Tests for _has_active_tickets method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_has_active_with_in_progress(self, mock_git_class, temp_epic_dir):
        """Test returns True when ticket is IN_PROGRESS."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        state_machine.tickets["ticket-a"].state = TicketState.IN_PROGRESS

        assert state_machine._has_active_tickets() is True

    @patch("cli.epic.state_machine.GitOperations")
    def test_has_active_with_awaiting_validation(self, mock_git_class, temp_epic_dir):
        """Test returns True when ticket is AWAITING_VALIDATION."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        state_machine.tickets["ticket-a"].state = TicketState.AWAITING_VALIDATION

        assert state_machine._has_active_tickets() is True

    @patch("cli.epic.state_machine.GitOperations")
    def test_has_active_returns_false(self, mock_git_class, temp_epic_dir):
        """Test returns False when no active tickets."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # All tickets in non-active states
        state_machine.tickets["ticket-a"].state = TicketState.COMPLETED
        state_machine.tickets["ticket-b"].state = TicketState.PENDING
        state_machine.tickets["ticket-c"].state = TicketState.READY

        assert state_machine._has_active_tickets() is False


class TestCompleteTicket:
    """Tests for _complete_ticket method."""

    @patch("cli.epic.state_machine.GitOperations")
    @patch("cli.epic.test_gates.ValidationGate")
    def test_complete_ticket_success(
        self, mock_validation_gate_class, mock_git_class, temp_epic_dir
    ):
        """Test successful ticket completion."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Set up ticket
        ticket = state_machine.tickets["ticket-a"]
        ticket.state = TicketState.IN_PROGRESS
        ticket.git_info = GitInfo(
            branch_name="ticket/ticket-a",
            base_commit="abc123",
        )

        # Mock validation gate to pass
        mock_gate = MagicMock()
        mock_gate.check.return_value = GateResult(passed=True)
        mock_validation_gate_class.return_value = mock_gate

        # Complete ticket
        acceptance_criteria = [
            AcceptanceCriterion(criterion="Test 1", met=True),
        ]
        result = state_machine._complete_ticket(
            "ticket-a",
            "def456",
            "passing",
            acceptance_criteria,
        )

        assert result is True
        assert ticket.state == TicketState.COMPLETED
        assert ticket.git_info.final_commit == "def456"
        assert ticket.test_suite_status == "passing"

    @patch("cli.epic.state_machine.GitOperations")
    @patch("cli.epic.test_gates.ValidationGate")
    def test_complete_ticket_validation_failure(
        self, mock_validation_gate_class, mock_git_class, temp_epic_dir
    ):
        """Test ticket completion with validation failure."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Set up ticket
        ticket = state_machine.tickets["ticket-a"]
        ticket.state = TicketState.IN_PROGRESS
        ticket.git_info = GitInfo(
            branch_name="ticket/ticket-a",
            base_commit="abc123",
        )

        # Mock validation gate to fail
        mock_gate = MagicMock()
        mock_gate.check.return_value = GateResult(
            passed=False, reason="Tests failed"
        )
        mock_validation_gate_class.return_value = mock_gate

        # Complete ticket
        result = state_machine._complete_ticket(
            "ticket-a",
            "def456",
            "failing",
            [],
        )

        assert result is False
        assert ticket.state == TicketState.FAILED
        assert "Validation failed" in ticket.failure_reason


class TestFailTicket:
    """Tests for _fail_ticket method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_fail_ticket_sets_reason(self, mock_git_class, temp_epic_dir):
        """Test that _fail_ticket sets failure reason."""
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
