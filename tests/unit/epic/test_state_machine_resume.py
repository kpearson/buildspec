"""Unit tests for EpicStateMachine resume functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cli.epic.models import (
    AcceptanceCriterion,
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


class TestInitializeNewEpic:
    """Tests for _initialize_new_epic method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_initialize_new_epic_creates_tickets(self, mock_git_class, temp_epic_dir):
        """Test that _initialize_new_epic creates tickets."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        assert len(state_machine.tickets) == 3
        assert "ticket-a" in state_machine.tickets
        assert state_machine.tickets["ticket-a"].state == TicketState.PENDING

    @patch("cli.epic.state_machine.GitOperations")
    def test_initialize_new_epic_saves_state(self, mock_git_class, temp_epic_dir):
        """Test that _initialize_new_epic saves initial state."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file)

        # Check state file created
        state_file = epic_dir / "artifacts" / "epic-state.json"
        assert state_file.exists()

        with open(state_file, "r") as f:
            state = json.load(f)

        assert state["schema_version"] == 1
        assert state["epic_id"] == "test-epic"


class TestLoadState:
    """Tests for _load_state method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_load_state_valid_json(self, mock_git_class, temp_epic_dir):
        """Test loading valid state from JSON."""
        epic_file, epic_dir = temp_epic_dir
        state_file = epic_dir / "artifacts" / "epic-state.json"

        # Create valid state file
        state_data = {
            "schema_version": 1,
            "epic_id": "test-epic",
            "epic_branch": "epic/test-epic",
            "baseline_commit": "abc123",
            "epic_state": "EXECUTING",
            "tickets": {
                "ticket-a": {
                    "id": "ticket-a",
                    "path": str(epic_dir / "tickets" / "ticket-a.md"),
                    "title": "Ticket A description",
                    "depends_on": [],
                    "critical": True,
                    "state": "COMPLETED",
                    "git_info": {
                        "branch_name": "ticket/ticket-a",
                        "base_commit": "abc123",
                        "final_commit": "def456",
                    },
                    "test_suite_status": "passing",
                    "acceptance_criteria": [
                        {"criterion": "Test 1", "met": True}
                    ],
                    "failure_reason": None,
                    "blocking_dependency": None,
                    "started_at": "2024-01-01T00:00:00",
                    "completed_at": "2024-01-01T01:00:00",
                },
                "ticket-b": {
                    "id": "ticket-b",
                    "path": str(epic_dir / "tickets" / "ticket-b.md"),
                    "title": "Ticket B description",
                    "depends_on": ["ticket-a"],
                    "critical": True,
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

        # Load state with resume=True
        state_machine = EpicStateMachine(epic_file, resume=True)

        # Verify tickets loaded correctly
        assert len(state_machine.tickets) == 2
        assert "ticket-a" in state_machine.tickets
        assert "ticket-b" in state_machine.tickets

        ticket_a = state_machine.tickets["ticket-a"]
        assert ticket_a.state == TicketState.COMPLETED
        assert ticket_a.git_info.branch_name == "ticket/ticket-a"
        assert ticket_a.git_info.final_commit == "def456"
        assert ticket_a.test_suite_status == "passing"
        assert len(ticket_a.acceptance_criteria) == 1
        assert ticket_a.acceptance_criteria[0].criterion == "Test 1"
        assert ticket_a.acceptance_criteria[0].met is True

        ticket_b = state_machine.tickets["ticket-b"]
        assert ticket_b.state == TicketState.PENDING
        assert ticket_b.git_info is None

    @patch("cli.epic.state_machine.GitOperations")
    def test_load_state_invalid_json(self, mock_git_class, temp_epic_dir):
        """Test loading state with invalid JSON."""
        epic_file, epic_dir = temp_epic_dir
        state_file = epic_dir / "artifacts" / "epic-state.json"

        # Create invalid JSON
        with open(state_file, "w") as f:
            f.write("{invalid json")

        mock_git = MagicMock()
        mock_git_class.return_value = mock_git

        with pytest.raises(ValueError, match="Invalid JSON"):
            EpicStateMachine(epic_file, resume=True)

    @patch("cli.epic.state_machine.GitOperations")
    def test_load_state_epic_id_mismatch(self, mock_git_class, temp_epic_dir):
        """Test loading state with mismatched epic ID."""
        epic_file, epic_dir = temp_epic_dir
        state_file = epic_dir / "artifacts" / "epic-state.json"

        # Create state with wrong epic ID
        state_data = {
            "schema_version": 1,
            "epic_id": "wrong-epic",
            "epic_branch": "epic/wrong-epic",
            "baseline_commit": "abc123",
            "epic_state": "EXECUTING",
            "tickets": {},
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        mock_git = MagicMock()
        mock_git_class.return_value = mock_git

        with pytest.raises(ValueError, match="Epic ID mismatch"):
            EpicStateMachine(epic_file, resume=True)

    @patch("cli.epic.state_machine.GitOperations")
    def test_load_state_missing_file(self, mock_git_class, temp_epic_dir):
        """Test loading state when state file doesn't exist."""
        epic_file, epic_dir = temp_epic_dir

        mock_git = MagicMock()
        mock_git_class.return_value = mock_git

        with pytest.raises(FileNotFoundError, match="Cannot resume"):
            EpicStateMachine(epic_file, resume=True)


class TestValidateLoadedState:
    """Tests for _validate_loaded_state method."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_validate_state_schema_version_mismatch(self, mock_git_class, temp_epic_dir):
        """Test validation fails with wrong schema version."""
        epic_file, epic_dir = temp_epic_dir
        state_file = epic_dir / "artifacts" / "epic-state.json"

        # Create state with wrong schema version
        state_data = {
            "schema_version": 999,
            "epic_id": "test-epic",
            "epic_branch": "epic/test-epic",
            "baseline_commit": "abc123",
            "epic_state": "EXECUTING",
            "tickets": {},
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        mock_git = MagicMock()
        mock_git_class.return_value = mock_git

        with pytest.raises(ValueError, match="schema version mismatch"):
            EpicStateMachine(epic_file, resume=True)

    @patch("cli.epic.state_machine.GitOperations")
    def test_validate_state_missing_epic_branch(self, mock_git_class, temp_epic_dir):
        """Test validation fails when epic branch doesn't exist."""
        epic_file, epic_dir = temp_epic_dir
        state_file = epic_dir / "artifacts" / "epic-state.json"

        state_data = {
            "schema_version": 1,
            "epic_id": "test-epic",
            "epic_branch": "epic/test-epic",
            "baseline_commit": "abc123",
            "epic_state": "EXECUTING",
            "tickets": {},
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        # Mock git to return False for epic branch
        mock_git = MagicMock()
        mock_git.branch_exists_remote.return_value = False
        mock_git_class.return_value = mock_git

        with pytest.raises(ValueError, match="Epic branch .* does not exist"):
            EpicStateMachine(epic_file, resume=True)

    @patch("cli.epic.state_machine.GitOperations")
    def test_validate_state_missing_ticket_branch(self, mock_git_class, temp_epic_dir):
        """Test validation fails when ticket branch doesn't exist."""
        epic_file, epic_dir = temp_epic_dir
        state_file = epic_dir / "artifacts" / "epic-state.json"

        state_data = {
            "schema_version": 1,
            "epic_id": "test-epic",
            "epic_branch": "epic/test-epic",
            "baseline_commit": "abc123",
            "epic_state": "EXECUTING",
            "tickets": {
                "ticket-a": {
                    "id": "ticket-a",
                    "path": str(epic_dir / "tickets" / "ticket-a.md"),
                    "title": "Ticket A",
                    "depends_on": [],
                    "critical": True,
                    "state": "IN_PROGRESS",
                    "git_info": {
                        "branch_name": "ticket/ticket-a",
                        "base_commit": "abc123",
                        "final_commit": None,
                    },
                    "test_suite_status": None,
                    "acceptance_criteria": [],
                    "failure_reason": None,
                    "blocking_dependency": None,
                    "started_at": "2024-01-01T00:00:00",
                    "completed_at": None,
                },
            },
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        # Mock git: epic branch exists but ticket branch doesn't
        mock_git = MagicMock()
        def branch_exists_side_effect(branch_name):
            if branch_name == "epic/test-epic":
                return True
            return False
        mock_git.branch_exists_remote.side_effect = branch_exists_side_effect
        mock_git_class.return_value = mock_git

        with pytest.raises(ValueError, match="branch .* does not exist on remote"):
            EpicStateMachine(epic_file, resume=True)

    @patch("cli.epic.state_machine.GitOperations")
    def test_validate_state_completed_without_final_commit(self, mock_git_class, temp_epic_dir):
        """Test validation fails when completed ticket has no final_commit."""
        epic_file, epic_dir = temp_epic_dir
        state_file = epic_dir / "artifacts" / "epic-state.json"

        state_data = {
            "schema_version": 1,
            "epic_id": "test-epic",
            "epic_branch": "epic/test-epic",
            "baseline_commit": "abc123",
            "epic_state": "EXECUTING",
            "tickets": {
                "ticket-a": {
                    "id": "ticket-a",
                    "path": str(epic_dir / "tickets" / "ticket-a.md"),
                    "title": "Ticket A",
                    "depends_on": [],
                    "critical": True,
                    "state": "COMPLETED",
                    "git_info": {
                        "branch_name": "ticket/ticket-a",
                        "base_commit": "abc123",
                        "final_commit": None,  # Missing!
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

        mock_git = MagicMock()
        mock_git.branch_exists_remote.return_value = True
        mock_git_class.return_value = mock_git

        with pytest.raises(ValueError, match="is COMPLETED but has no final_commit"):
            EpicStateMachine(epic_file, resume=True)

    @patch("cli.epic.state_machine.GitOperations")
    def test_validate_state_in_progress_without_git_info(self, mock_git_class, temp_epic_dir):
        """Test validation fails when IN_PROGRESS ticket has no git_info."""
        epic_file, epic_dir = temp_epic_dir
        state_file = epic_dir / "artifacts" / "epic-state.json"

        state_data = {
            "schema_version": 1,
            "epic_id": "test-epic",
            "epic_branch": "epic/test-epic",
            "baseline_commit": "abc123",
            "epic_state": "EXECUTING",
            "tickets": {
                "ticket-a": {
                    "id": "ticket-a",
                    "path": str(epic_dir / "tickets" / "ticket-a.md"),
                    "title": "Ticket A",
                    "depends_on": [],
                    "critical": True,
                    "state": "IN_PROGRESS",
                    "git_info": None,  # Missing!
                    "test_suite_status": None,
                    "acceptance_criteria": [],
                    "failure_reason": None,
                    "blocking_dependency": None,
                    "started_at": "2024-01-01T00:00:00",
                    "completed_at": None,
                },
            },
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        mock_git = MagicMock()
        mock_git.branch_exists_remote.return_value = True
        mock_git_class.return_value = mock_git

        with pytest.raises(ValueError, match="but has no git_info.branch_name"):
            EpicStateMachine(epic_file, resume=True)


class TestResumeIntegration:
    """Integration tests for resume flag."""

    @patch("cli.epic.state_machine.GitOperations")
    def test_resume_false_creates_new_state(self, mock_git_class, temp_epic_dir):
        """Test that resume=False creates new state even if state file exists."""
        epic_file, epic_dir = temp_epic_dir
        state_file = epic_dir / "artifacts" / "epic-state.json"

        mock_git = MagicMock()
        mock_git._run_git_command.return_value = Mock(stdout="abc123\n")
        mock_git_class.return_value = mock_git

        # Create first state machine (creates state file)
        state_machine1 = EpicStateMachine(epic_file)
        assert state_file.exists()

        # Create second state machine without resume (should overwrite)
        state_machine2 = EpicStateMachine(epic_file, resume=False)

        # Should have created fresh state
        assert all(t.state == TicketState.PENDING for t in state_machine2.tickets.values())

    @patch("cli.epic.state_machine.GitOperations")
    def test_resume_preserves_epic_state(self, mock_git_class, temp_epic_dir):
        """Test that resume preserves epic_state."""
        epic_file, epic_dir = temp_epic_dir
        state_file = epic_dir / "artifacts" / "epic-state.json"

        # Create state with MERGING epic state
        state_data = {
            "schema_version": 1,
            "epic_id": "test-epic",
            "epic_branch": "epic/test-epic",
            "baseline_commit": "abc123",
            "epic_state": "MERGING",
            "tickets": {},
        }

        with open(state_file, "w") as f:
            json.dump(state_data, f)

        mock_git = MagicMock()
        mock_git.branch_exists_remote.return_value = True
        mock_git_class.return_value = mock_git

        state_machine = EpicStateMachine(epic_file, resume=True)

        assert state_machine.epic_state == EpicState.MERGING
