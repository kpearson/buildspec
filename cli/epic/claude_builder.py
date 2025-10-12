"""Claude Code ticket builder subprocess wrapper.

This module provides the ClaudeTicketBuilder class that spawns Claude Code
as a subprocess to implement individual tickets. The builder constructs
prompts, manages subprocess execution with timeouts, and parses structured
JSON output.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from cli.epic.models import AcceptanceCriterion, BuilderResult


class ClaudeTicketBuilder:
    """Spawns Claude Code as a subprocess for ticket implementation.

    The builder is responsible for:
    - Constructing instruction prompts with ticket context
    - Spawning Claude Code subprocess with proper arguments
    - Enforcing 1-hour timeout
    - Parsing structured JSON output
    - Returning BuilderResult with all execution details
    """

    def __init__(
        self,
        ticket_file: Path,
        branch_name: str,
        base_commit: str,
        epic_file: Path,
    ):
        """Initialize the builder with ticket context.

        Args:
            ticket_file: Path to the ticket markdown file
            branch_name: Git branch name for this ticket
            base_commit: Base commit SHA the branch was created from
            epic_file: Path to the epic YAML file
        """
        self.ticket_file = ticket_file
        self.branch_name = branch_name
        self.base_commit = base_commit
        self.epic_file = epic_file

    def execute(self) -> BuilderResult:
        """Execute the ticket builder subprocess.

        Spawns Claude Code subprocess with the constructed prompt, waits
        for completion (up to 3600 seconds), captures stdout/stderr,
        and parses the structured JSON output.

        Returns:
            BuilderResult with success status, commit info, test status,
            and acceptance criteria, or error information if failed.
        """
        prompt = self._build_prompt()

        try:
            # Spawn subprocess with 1-hour timeout
            result = subprocess.run(
                ["claude", "--prompt", prompt, "--mode", "execute-ticket", "--output-json"],
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )

            # Capture stdout/stderr
            stdout = result.stdout
            stderr = result.stderr

            # Check if subprocess failed (non-zero exit)
            if result.returncode != 0:
                return BuilderResult(
                    success=False,
                    error=f"Claude subprocess failed with exit code {result.returncode}",
                    stdout=stdout,
                    stderr=stderr,
                )

            # Parse JSON output
            try:
                output_data = self._parse_output(stdout)

                # Convert acceptance criteria dicts to AcceptanceCriterion objects
                acceptance_criteria = [
                    AcceptanceCriterion(
                        criterion=ac.get("criterion", ""),
                        met=ac.get("met", False),
                    )
                    for ac in output_data.get("acceptance_criteria", [])
                ]

                return BuilderResult(
                    success=True,
                    final_commit=output_data.get("final_commit"),
                    test_status=output_data.get("test_status"),
                    acceptance_criteria=acceptance_criteria,
                    stdout=stdout,
                    stderr=stderr,
                )
            except (ValueError, KeyError) as e:
                return BuilderResult(
                    success=False,
                    error=f"Failed to parse JSON output: {e}",
                    stdout=stdout,
                    stderr=stderr,
                )

        except subprocess.TimeoutExpired:
            return BuilderResult(
                success=False,
                error="Ticket builder timed out after 3600 seconds",
            )

    def _build_prompt(self) -> str:
        """Build the instruction prompt for Claude.

        Constructs a prompt that includes:
        - Ticket file path
        - Branch name
        - Base commit
        - Epic file path
        - Workflow steps
        - Output format requirements (JSON)

        Returns:
            Formatted prompt string for Claude Code.
        """
        prompt = f"""You are a ticket builder agent executing a single ticket from an epic.

**Ticket file:** {self.ticket_file}
**Branch name:** {self.branch_name}
**Epic file:** {self.epic_file}
**Base commit:** {self.base_commit} (latest)
**Session ID:** 0f75ba21-0a87-4f4f-a9bf-5459547fb556

## Your Task

Read the ticket file and implement all requirements. This includes:
1. Reading the ticket file to understand requirements
2. Implementing all necessary code changes
3. Writing comprehensive tests
4. Running tests to verify implementation
5. Committing your changes with a descriptive message including: session_id: 0f75ba21-0a87-4f4f-a9bf-5459547fb556

## Output Requirements

After completing the ticket, you MUST output a JSON object with the following structure:

```json
{{
  "final_commit": "abc123...",
  "test_status": "passing",
  "acceptance_criteria": [
    {{"criterion": "Subprocess spawned with correct CLI arguments", "met": true}},
    {{"criterion": "Timeout enforced at 3600 seconds", "met": true}},
    ...
  ]
}}
```

**Required fields:**
- `final_commit` (string): The final git commit SHA after all changes
- `test_status` (string): One of "passing", "failing", or "skipped"
- `acceptance_criteria` (array): List of acceptance criteria with met status

The JSON MUST be valid and parseable. You can include other text in your output,
but the JSON object must be clearly identifiable (enclosed in braces).
"""
        return prompt

    def _parse_output(self, stdout: str) -> dict[str, Any]:
        """Parse JSON output from stdout.

        Finds the JSON object in the stdout text (looking for {...} block),
        and parses it. Handles cases where JSON is embedded in other text.

        Args:
            stdout: The stdout text from the subprocess

        Returns:
            Parsed JSON data as a dictionary

        Raises:
            ValueError: If no valid JSON object found or parsing fails
        """
        # Try to find JSON object in stdout (look for {...})
        # Use regex to find the first complete JSON object
        match = re.search(r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}', stdout, re.DOTALL)

        if not match:
            raise ValueError("No JSON object found in output")

        json_str = match.group(0)

        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}") from e
