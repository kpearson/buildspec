"""Integration tests for ClaudeTicketBuilder with echo subprocess."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cli.epic.claude_builder import ClaudeTicketBuilder
from cli.epic.models import AcceptanceCriterion


@pytest.fixture
def builder() -> ClaudeTicketBuilder:
    """Create a ClaudeTicketBuilder instance for integration testing."""
    return ClaudeTicketBuilder(
        ticket_file=Path("/tmp/test-ticket.md"),
        branch_name="ticket/integration-test",
        base_commit="abc123def",
        epic_file=Path("/tmp/test-epic.yaml"),
    )


class TestClaudeBuilderIntegration:
    """Integration tests using echo subprocess instead of real Claude."""

    @patch("subprocess.run")
    def test_integration_with_mock_json_response(self, mock_run, builder):
        """Test full integration flow with mock subprocess returning JSON."""
        # Mock subprocess to return valid JSON (simulating Claude Code)
        mock_json_output = {
            "final_commit": "abc123def456",
            "test_status": "passing",
            "acceptance_criteria": [
                {"criterion": "Subprocess spawned with correct CLI arguments", "met": True},
                {"criterion": "Timeout enforced at 3600 seconds", "met": True},
                {"criterion": "Structured JSON output parsed correctly", "met": True},
            ],
        }

        class MockCompletedProcess:
            def __init__(self):
                self.returncode = 0
                self.stdout = f"Builder output:\n{json.dumps(mock_json_output, indent=2)}\nDone!"
                self.stderr = ""

        mock_run.return_value = MockCompletedProcess()

        # Execute the builder
        result = builder.execute()

        # Verify subprocess was called correctly
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "claude"
        assert "--prompt" in call_args
        assert "--mode" in call_args
        assert "execute-ticket" in call_args
        assert "--output-json" in call_args

        # Verify result parsing
        assert result.success is True
        assert result.final_commit == "abc123def456"
        assert result.test_status == "passing"
        assert len(result.acceptance_criteria) == 3
        assert all(isinstance(ac, AcceptanceCriterion) for ac in result.acceptance_criteria)
        assert result.acceptance_criteria[0].criterion == "Subprocess spawned with correct CLI arguments"
        assert result.acceptance_criteria[0].met is True

    @patch("subprocess.run")
    def test_integration_with_simple_echo(self, mock_run, builder):
        """Test integration with simple echo command returning minimal JSON."""
        mock_json = {"final_commit": "xyz789", "test_status": "skipped"}

        class MockCompletedProcess:
            def __init__(self):
                self.returncode = 0
                self.stdout = json.dumps(mock_json)
                self.stderr = ""

        mock_run.return_value = MockCompletedProcess()

        result = builder.execute()

        assert result.success is True
        assert result.final_commit == "xyz789"
        assert result.test_status == "skipped"
        assert len(result.acceptance_criteria) == 0

    @patch("subprocess.run")
    def test_integration_with_failing_subprocess(self, mock_run, builder):
        """Test integration when subprocess exits with error."""
        class MockCompletedProcess:
            def __init__(self):
                self.returncode = 1
                self.stdout = "Something went wrong"
                self.stderr = "Error: Failed to execute"

        mock_run.return_value = MockCompletedProcess()

        result = builder.execute()

        assert result.success is False
        assert "exit code 1" in result.error
        assert result.stdout == "Something went wrong"
        assert result.stderr == "Error: Failed to execute"

    @patch("subprocess.run")
    def test_integration_timeout_handling(self, mock_run, builder):
        """Test integration when subprocess times out."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["claude"], timeout=3600)

        result = builder.execute()

        assert result.success is False
        assert "timed out" in result.error

    @patch("subprocess.run")
    def test_integration_with_complex_output(self, mock_run, builder):
        """Test integration with complex output containing multiple sections."""
        mock_json = {
            "final_commit": "complex123",
            "test_status": "passing",
            "acceptance_criteria": [
                {"criterion": "Feature A implemented", "met": True},
                {"criterion": "Feature B implemented", "met": True},
                {"criterion": "All tests pass", "met": True},
                {"criterion": "Documentation updated", "met": False},
            ],
        }

        class MockCompletedProcess:
            def __init__(self):
                self.returncode = 0
                self.stdout = f"""
Starting ticket implementation...

Step 1: Reading requirements
Step 2: Implementing features
Step 3: Writing tests
Step 4: Running tests

Results:
{json.dumps(mock_json, indent=2)}

All done!
"""
                self.stderr = "Warning: Some deprecation warnings\nWarning: Old API usage"

        mock_run.return_value = MockCompletedProcess()

        result = builder.execute()

        assert result.success is True
        assert result.final_commit == "complex123"
        assert result.test_status == "passing"
        assert len(result.acceptance_criteria) == 4
        assert result.acceptance_criteria[0].met is True
        assert result.acceptance_criteria[3].met is False
        assert "Warning" in result.stderr

    @patch("subprocess.run")
    def test_integration_prompt_construction(self, mock_run, builder):
        """Test that the constructed prompt contains all required information."""
        mock_json = {"final_commit": "test", "test_status": "passing"}

        class MockCompletedProcess:
            def __init__(self):
                self.returncode = 0
                self.stdout = json.dumps(mock_json)
                self.stderr = ""

        mock_run.return_value = MockCompletedProcess()

        result = builder.execute()

        # Get the prompt that was passed
        prompt_arg_index = mock_run.call_args[0][0].index("--prompt") + 1
        prompt = mock_run.call_args[0][0][prompt_arg_index]

        # Verify prompt contains necessary context
        assert str(builder.ticket_file) in prompt
        assert builder.base_commit in prompt
        assert str(builder.epic_file) in prompt
        assert "final_commit" in prompt  # Output format example
        assert "test_status" in prompt  # Output format example
        assert "acceptance_criteria" in prompt  # Output format example

        assert result.success is True
