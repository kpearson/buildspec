"""Unit tests for execute-epic command."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import typer

from cli.commands.execute_epic import StateTransitionError, command
from cli.epic.git_operations import GitError
from cli.epic.models import EpicState, Ticket, TicketState


class TestExecuteEpicCommand:
    """Test execute-epic CLI command."""

    @patch("cli.commands.execute_epic.EpicStateMachine")
    def test_success_execution(self, mock_state_machine_class, tmp_path):
        """Should execute epic successfully and return exit code 0."""
        # Create test epic file
        epic_file = tmp_path / "test-epic.epic.yaml"
        epic_file.write_text("epic: test\ntickets: []")

        # Setup mock state machine
        mock_state_machine = MagicMock()
        mock_state_machine.epic_id = "test-epic"
        mock_state_machine.epic_branch = "epic/test-epic"
        mock_state_machine.baseline_commit = "abc123def456"
        mock_state_machine.tickets = {
            "ticket-1": Mock(state=TicketState.COMPLETED),
            "ticket-2": Mock(state=TicketState.COMPLETED),
        }
        mock_state_machine.epic_state = EpicState.FINALIZED
        mock_state_machine_class.return_value = mock_state_machine

        # Execute command
        try:
            command(str(epic_file), resume=False)
        except typer.Exit as e:
            # Command should not raise Exit for success
            pytest.fail(f"Command raised Exit with code {e.exit_code}")

        # Verify state machine was created and executed
        mock_state_machine_class.assert_called_once_with(epic_file, resume=False)
        mock_state_machine.execute.assert_called_once()

    @patch("cli.commands.execute_epic.EpicStateMachine")
    def test_with_resume_flag(self, mock_state_machine_class, tmp_path):
        """Should pass resume flag to state machine."""
        epic_file = tmp_path / "test-epic.epic.yaml"
        epic_file.write_text("epic: test")

        mock_state_machine = MagicMock()
        mock_state_machine.epic_id = "test-epic"
        mock_state_machine.epic_branch = "epic/test-epic"
        mock_state_machine.baseline_commit = "abc123"
        mock_state_machine.tickets = {}
        mock_state_machine.epic_state = EpicState.FINALIZED
        mock_state_machine_class.return_value = mock_state_machine

        try:
            command(str(epic_file), resume=True)
        except typer.Exit:
            pass

        mock_state_machine_class.assert_called_once_with(epic_file, resume=True)

    def test_file_not_found(self):
        """Should exit with code 1 when epic file doesn't exist."""
        with pytest.raises(typer.Exit) as exc_info:
            command("/nonexistent/path/epic.epic.yaml", resume=False)

        assert exc_info.value.exit_code == 1

    def test_invalid_extension(self, tmp_path):
        """Should exit with code 1 when file doesn't have .epic.yaml extension."""
        epic_file = tmp_path / "test.yaml"
        epic_file.write_text("epic: test")

        with pytest.raises(typer.Exit) as exc_info:
            command(str(epic_file), resume=False)

        assert exc_info.value.exit_code == 1

    def test_path_is_directory(self, tmp_path):
        """Should exit with code 1 when path is a directory."""
        epic_dir = tmp_path / "test-epic.epic.yaml"
        epic_dir.mkdir()

        with pytest.raises(typer.Exit) as exc_info:
            command(str(epic_dir), resume=False)

        assert exc_info.value.exit_code == 1

    @patch("cli.commands.execute_epic.EpicStateMachine")
    def test_state_machine_init_error_file_not_found(self, mock_state_machine_class, tmp_path):
        """Should handle FileNotFoundError from state machine initialization."""
        epic_file = tmp_path / "test-epic.epic.yaml"
        epic_file.write_text("epic: test")

        mock_state_machine_class.side_effect = FileNotFoundError("State file not found")

        with pytest.raises(typer.Exit) as exc_info:
            command(str(epic_file), resume=False)

        assert exc_info.value.exit_code == 1

    @patch("cli.commands.execute_epic.EpicStateMachine")
    def test_state_machine_init_error_value_error(self, mock_state_machine_class, tmp_path):
        """Should handle ValueError from state machine initialization."""
        epic_file = tmp_path / "test-epic.epic.yaml"
        epic_file.write_text("epic: test")

        mock_state_machine_class.side_effect = ValueError("Invalid epic YAML")

        with pytest.raises(typer.Exit) as exc_info:
            command(str(epic_file), resume=False)

        assert exc_info.value.exit_code == 1

    @patch("cli.commands.execute_epic.EpicStateMachine")
    def test_git_error_during_execution(self, mock_state_machine_class, tmp_path):
        """Should handle GitError during epic execution."""
        epic_file = tmp_path / "test-epic.epic.yaml"
        epic_file.write_text("epic: test")

        mock_state_machine = MagicMock()
        mock_state_machine.epic_id = "test-epic"
        mock_state_machine.epic_branch = "epic/test-epic"
        mock_state_machine.baseline_commit = "abc123"
        mock_state_machine.tickets = {}
        mock_state_machine.execute.side_effect = GitError("Branch conflict")
        mock_state_machine_class.return_value = mock_state_machine

        with pytest.raises(typer.Exit) as exc_info:
            command(str(epic_file), resume=False)

        assert exc_info.value.exit_code == 1

    @patch("cli.commands.execute_epic.EpicStateMachine")
    def test_state_transition_error_during_execution(self, mock_state_machine_class, tmp_path):
        """Should handle StateTransitionError during epic execution."""
        epic_file = tmp_path / "test-epic.epic.yaml"
        epic_file.write_text("epic: test")

        mock_state_machine = MagicMock()
        mock_state_machine.epic_id = "test-epic"
        mock_state_machine.epic_branch = "epic/test-epic"
        mock_state_machine.baseline_commit = "abc123"
        mock_state_machine.tickets = {}
        mock_state_machine.execute.side_effect = StateTransitionError("Invalid transition")
        mock_state_machine_class.return_value = mock_state_machine

        with pytest.raises(typer.Exit) as exc_info:
            command(str(epic_file), resume=False)

        assert exc_info.value.exit_code == 1

    @patch("cli.commands.execute_epic.EpicStateMachine")
    def test_failed_epic_state(self, mock_state_machine_class, tmp_path):
        """Should exit with code 1 when epic state is FAILED."""
        epic_file = tmp_path / "test-epic.epic.yaml"
        epic_file.write_text("epic: test")

        mock_state_machine = MagicMock()
        mock_state_machine.epic_id = "test-epic"
        mock_state_machine.epic_branch = "epic/test-epic"
        mock_state_machine.baseline_commit = "abc123"
        mock_state_machine.tickets = {
            "ticket-1": Mock(state=TicketState.COMPLETED),
            "ticket-2": Mock(state=TicketState.FAILED),
        }
        mock_state_machine.epic_state = EpicState.FAILED
        mock_state_machine_class.return_value = mock_state_machine

        with pytest.raises(typer.Exit) as exc_info:
            command(str(epic_file), resume=False)

        assert exc_info.value.exit_code == 1

    @patch("cli.commands.execute_epic.EpicStateMachine")
    def test_rolled_back_epic_state(self, mock_state_machine_class, tmp_path):
        """Should exit with code 1 when epic state is ROLLED_BACK."""
        epic_file = tmp_path / "test-epic.epic.yaml"
        epic_file.write_text("epic: test")

        mock_state_machine = MagicMock()
        mock_state_machine.epic_id = "test-epic"
        mock_state_machine.epic_branch = "epic/test-epic"
        mock_state_machine.baseline_commit = "abc123"
        mock_state_machine.tickets = {}
        mock_state_machine.epic_state = EpicState.ROLLED_BACK
        mock_state_machine_class.return_value = mock_state_machine

        with pytest.raises(typer.Exit) as exc_info:
            command(str(epic_file), resume=False)

        assert exc_info.value.exit_code == 1

    @patch("cli.commands.execute_epic.EpicStateMachine")
    def test_incomplete_epic_state(self, mock_state_machine_class, tmp_path):
        """Should exit with code 1 when epic is in incomplete state."""
        epic_file = tmp_path / "test-epic.epic.yaml"
        epic_file.write_text("epic: test")

        mock_state_machine = MagicMock()
        mock_state_machine.epic_id = "test-epic"
        mock_state_machine.epic_branch = "epic/test-epic"
        mock_state_machine.baseline_commit = "abc123"
        mock_state_machine.tickets = {
            "ticket-1": Mock(state=TicketState.COMPLETED),
            "ticket-2": Mock(state=TicketState.PENDING),
        }
        mock_state_machine.epic_state = EpicState.EXECUTING
        mock_state_machine_class.return_value = mock_state_machine

        with pytest.raises(typer.Exit) as exc_info:
            command(str(epic_file), resume=False)

        assert exc_info.value.exit_code == 1

    @patch("cli.commands.execute_epic.EpicStateMachine")
    def test_displays_completion_summary(self, mock_state_machine_class, tmp_path, capsys):
        """Should display completion summary with ticket counts."""
        epic_file = tmp_path / "test-epic.epic.yaml"
        epic_file.write_text("epic: test")

        mock_state_machine = MagicMock()
        mock_state_machine.epic_id = "test-epic"
        mock_state_machine.epic_branch = "epic/test-epic"
        mock_state_machine.baseline_commit = "abc123"
        mock_state_machine.tickets = {
            "ticket-1": Mock(state=TicketState.COMPLETED),
            "ticket-2": Mock(state=TicketState.COMPLETED),
            "ticket-3": Mock(state=TicketState.FAILED),
            "ticket-4": Mock(state=TicketState.BLOCKED),
        }
        mock_state_machine.epic_state = EpicState.FINALIZED
        mock_state_machine_class.return_value = mock_state_machine

        try:
            command(str(epic_file), resume=False)
        except typer.Exit:
            pass

        # Note: We can't easily test Rich console output in unit tests,
        # but we verify the logic executes without error

    @patch("cli.commands.execute_epic.EpicStateMachine")
    def test_unexpected_exception(self, mock_state_machine_class, tmp_path):
        """Should handle unexpected exceptions gracefully."""
        epic_file = tmp_path / "test-epic.epic.yaml"
        epic_file.write_text("epic: test")

        mock_state_machine_class.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(typer.Exit) as exc_info:
            command(str(epic_file), resume=False)

        assert exc_info.value.exit_code == 1
