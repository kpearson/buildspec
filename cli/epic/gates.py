"""Transition gate protocol and context for validation gates.

This module defines the TransitionGate protocol that all validation gates must
implement, and the EpicContext dataclass that provides gates with access to
epic state and operations.

The gate pattern is used throughout the state machine to enforce invariants
before state transitions. All validation gates implement the TransitionGate
protocol, which requires a check() method that validates whether a transition
is allowed.

How to implement a new gate:
-----------------------------
1. Create a class that implements the TransitionGate protocol
2. Implement the check(ticket, context) method
3. Return GateResult(passed=True) if validation succeeds
4. Return GateResult(passed=False, reason="...") if validation fails
5. Optionally include metadata in the GateResult for additional information

Example:
--------
    class MyCustomGate:
        def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
            if some_validation_logic(ticket, context):
                return GateResult(
                    passed=True,
                    metadata={"info": "validation details"}
                )
            return GateResult(
                passed=False,
                reason="Validation failed because..."
            )

The state machine calls gates via the _run_gate() method during state
transitions to enforce invariants and validate preconditions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from cli.epic.git_operations import GitOperations
from cli.epic.models import GateResult, Ticket


class TransitionGate(Protocol):
    """Protocol defining the interface for validation gates.

    All validation gates must implement this protocol to be used by the
    state machine. Gates are called during state transitions to validate
    that the transition is allowed and all preconditions are met.

    The check() method should be deterministic and idempotent - calling it
    multiple times with the same inputs should always produce the same result.
    """

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Validate whether a state transition is allowed.

        Args:
            ticket: The ticket being validated for transition
            context: Epic context providing access to state and operations

        Returns:
            GateResult with passed=True if validation succeeds, passed=False
            with a descriptive reason if validation fails. May include optional
            metadata for additional information.

        Note:
            This method should not modify ticket or context state. It should
            only perform validation and return results. State modifications
            are handled by the state machine after successful validation.
        """
        ...


@dataclass
class EpicContext:
    """Context object providing gates with access to epic state and operations.

    This dataclass contains all the state and operations that validation gates
    need to perform their checks. It is passed to every gate's check() method.

    Attributes:
        epic_id: Unique identifier for the epic (typically the epic name)
        epic_branch: Name of the epic branch (e.g., "epic/my-feature")
        baseline_commit: Git commit SHA from which the epic branch was created
            (typically main branch HEAD at epic initialization). First ticket
            branches from this commit; subsequent tickets stack on previous
            ticket's final_commit.
        tickets: Dictionary mapping ticket ID to Ticket object for all tickets
            in the epic. Gates use this to check dependencies and other tickets.
        git: GitOperations instance for performing git validation checks such
            as commit existence, branch validation, and ancestry checks.
        epic_config: Configuration dictionary from the epic YAML file containing
            settings like rollback_on_failure and other epic-level options.
    """

    epic_id: str
    epic_branch: str
    baseline_commit: str
    tickets: dict[str, Ticket]
    git: GitOperations
    epic_config: dict[str, Any]
