"""Unit tests for ClaudeTicketBuilder with mocked subprocess."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.epic.claude_builder import ClaudeTicketBuilder
from cli.epic.models import BuilderResult


@pytest.fixture
def builder() -> ClaudeTicketBuilder:
    """Create a ClaudeTicketBuilder instance for testing."""
    return ClaudeTicketBuilder(
        ticket_file=Path("/path/to/ticket.md"),
        branch_name="ticket/test-ticket",
        base_commit="abc123",
        epic_file=Path("/path/to/epic.yaml"),
    )


class TestClaudeTicketBuilder:
    """Test suite for ClaudeTicketBuilder."""

    def test_init_stores_context(self):
        """Test that __init__ stores all ticket context."""
        ticket_file = Path("/path/to/ticket.md")
        branch_name = "ticket/test-ticket"
        base_commit = "abc123"
        epic_file = Path("/path/to/epic.yaml")

        builder = ClaudeTicketBuilder(
            ticket_file=ticket_file,
            branch_name=branch_name,
            base_commit=base_commit,
            epic_file=epic_file,
        )

        assert builder.ticket_file == ticket_file
        assert builder.branch_name == branch_name
        assert builder.base_commit == base_commit
        assert builder.epic_file == epic_file

    def test_build_prompt_includes_context(self, builder):
        """Test that _build_prompt includes all necessary context."""
        prompt = builder._build_prompt()

        assert str(builder.ticket_file) in prompt
        assert builder.branch_name in prompt
        assert builder.base_commit in prompt
        assert str(builder.epic_file) in prompt
        assert "final_commit" in prompt
        assert "test_status" in prompt
        assert "acceptance_criteria" in prompt

    def test_parse_output_valid_json(self, builder):
        """Test parsing valid JSON output."""
        stdout = """
        Some text before
        {
            "final_commit": "def456",
            "test_status": "passing",
            "acceptance_criteria": [
                {"criterion": "Test 1", "met": true},
                {"criterion": "Test 2", "met": false}
            ]
        }
        Some text after
        """

        result = builder._parse_output(stdout)

        assert result["final_commit"] == "def456"
        assert result["test_status"] == "passing"
        assert len(result["acceptance_criteria"]) == 2
        assert result["acceptance_criteria"][0]["criterion"] == "Test 1"
        assert result["acceptance_criteria"][0]["met"] is True

    def test_parse_output_nested_json(self, builder):
        """Test parsing JSON with nested objects."""
        stdout = """
        {
            "final_commit": "def456",
            "test_status": "passing",
            "acceptance_criteria": [
                {
                    "criterion": "Complex test",
                    "met": true,
                    "details": {"nested": "value"}
                }
            ]
        }
        """

        result = builder._parse_output(stdout)

        assert result["final_commit"] == "def456"
        assert len(result["acceptance_criteria"]) == 1

    def test_parse_output_no_json(self, builder):
        """Test parsing output with no JSON raises ValueError."""
        stdout = "Just some text without JSON"

        with pytest.raises(ValueError, match="No JSON object found"):
            builder._parse_output(stdout)

    def test_parse_output_invalid_json(self, builder):
        """Test parsing invalid JSON raises ValueError."""
        stdout = '{ "invalid": json, }'

        with pytest.raises(ValueError, match="Invalid JSON format"):
            builder._parse_output(stdout)

    @patch("subprocess.run")
    def test_execute_success_case(self, mock_run, builder):
        """Test successful execution with valid JSON output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """
        {
            "final_commit": "def456",
            "test_status": "passing",
            "acceptance_criteria": [
                {"criterion": "Test 1", "met": true}
            ]
        }
        """
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = builder.execute()

        # Verify subprocess called with correct arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0][0] == "claude"
        assert "--prompt" in call_args[0][0]
        assert "--mode" in call_args[0][0]
        assert "execute-ticket" in call_args[0][0]
        assert "--output-json" in call_args[0][0]
        assert call_args[1]["timeout"] == 3600

        # Verify result
        assert result.success is True
        assert result.final_commit == "def456"
        assert result.test_status == "passing"
        assert len(result.acceptance_criteria) == 1
        assert result.acceptance_criteria[0].criterion == "Test 1"
        assert result.acceptance_criteria[0].met is True
        assert result.error is None

    @patch("subprocess.run")
    def test_execute_non_zero_exit(self, mock_run, builder):
        """Test execution with non-zero exit code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Some output"
        mock_result.stderr = "Error message"
        mock_run.return_value = mock_result

        result = builder.execute()

        assert result.success is False
        assert "exit code 1" in result.error
        assert result.stdout == "Some output"
        assert result.stderr == "Error message"
        assert result.final_commit is None

    @patch("subprocess.run")
    def test_execute_timeout_case(self, mock_run, builder):
        """Test execution timeout after 3600 seconds."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["claude"], timeout=3600
        )

        result = builder.execute()

        assert result.success is False
        assert "timed out after 3600 seconds" in result.error
        assert result.final_commit is None

    @patch("subprocess.run")
    def test_execute_parsing_failure(self, mock_run, builder):
        """Test execution with invalid JSON in output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "No JSON here"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = builder.execute()

        assert result.success is False
        assert "Failed to parse JSON output" in result.error
        assert result.stdout == "No JSON here"

    @patch("subprocess.run")
    def test_execute_empty_acceptance_criteria(self, mock_run, builder):
        """Test execution with empty acceptance criteria list."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """
        {
            "final_commit": "def456",
            "test_status": "passing",
            "acceptance_criteria": []
        }
        """
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = builder.execute()

        assert result.success is True
        assert len(result.acceptance_criteria) == 0

    @patch("subprocess.run")
    def test_execute_optional_fields_missing(self, mock_run, builder):
        """Test execution with optional fields missing from JSON."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """
        {
            "final_commit": "def456",
            "test_status": "skipped"
        }
        """
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = builder.execute()

        assert result.success is True
        assert result.final_commit == "def456"
        assert result.test_status == "skipped"
        assert len(result.acceptance_criteria) == 0

    @patch("subprocess.run")
    def test_execute_captures_stdout_stderr(self, mock_run, builder):
        """Test that execute captures both stdout and stderr."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """
        Debug output
        {
            "final_commit": "def456",
            "test_status": "passing",
            "acceptance_criteria": []
        }
        """
        mock_result.stderr = "Warning: something"
        mock_run.return_value = mock_result

        result = builder.execute()

        assert result.success is True
        assert "Debug output" in result.stdout
        assert result.stderr == "Warning: something"

    def test_parse_output_multiple_json_objects(self, builder):
        """Test parsing when stdout contains multiple JSON-like text."""
        stdout = """
        First JSON mention: {"not": "the real one"}

        The actual result:
        {
            "final_commit": "def456",
            "test_status": "passing",
            "acceptance_criteria": []
        }
        """

        result = builder._parse_output(stdout)

        # Should find the first complete JSON object
        assert result["not"] == "the real one"

    @patch("subprocess.run")
    def test_execute_subprocess_uses_list_args(self, mock_run, builder):
        """Test that subprocess is called with list-form arguments (security)."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"final_commit": "abc", "test_status": "passing"}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        builder.execute()

        # Verify subprocess.run called with list, not string
        call_args = mock_run.call_args[0][0]
        assert isinstance(call_args, list)
        # Verify shell=True is not used (default is False)
        assert "shell" not in mock_run.call_args[1] or mock_run.call_args[1].get("shell") is False
