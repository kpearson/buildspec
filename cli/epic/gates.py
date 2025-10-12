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
from cli.epic.models import GateResult, Ticket, TicketState


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


class DependenciesMetGate:
    """Gate that validates all ticket dependencies are completed.

    This gate checks that all dependencies in a ticket's depends_on list have
    state=COMPLETED before allowing the ticket to proceed. It enforces strict
    dependency ordering and prevents tickets from starting prematurely.

    The gate is used by the state machine when checking if PENDING tickets can
    transition to READY in the _get_ready_tickets method.

    Acceptance criteria checked:
        - All dependencies in ticket.depends_on list are verified
        - Returns passed=True only if ALL dependencies have state=COMPLETED
        - Returns passed=False with clear reason identifying first unmet dependency
        - Handles empty depends_on list correctly (returns passed=True)
        - Does not allow dependencies in FAILED or BLOCKED state to pass
    """

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Check if all dependencies are completed.

        Args:
            ticket: Ticket to check dependencies for
            context: Epic context containing all tickets

        Returns:
            GateResult with passed=True if all dependencies completed,
            passed=False with reason identifying first unmet dependency
        """
        # Empty dependency list is valid - ticket has no dependencies
        if not ticket.depends_on:
            return GateResult(passed=True, reason="No dependencies")

        # Check each dependency
        for dep_id in ticket.depends_on:
            # Verify dependency exists in tickets
            if dep_id not in context.tickets:
                return GateResult(
                    passed=False,
                    reason=f"Dependency {dep_id} not found in tickets",
                )

            dep_ticket = context.tickets[dep_id]

            # Only COMPLETED state is acceptable for dependencies
            # FAILED, BLOCKED, or any incomplete state must fail
            if dep_ticket.state != TicketState.COMPLETED:
                return GateResult(
                    passed=False,
                    reason=f"Dependency {dep_id} not completed (state: {dep_ticket.state.value})",
                )

        # All dependencies are completed
        return GateResult(passed=True, reason="All dependencies completed")


class CreateBranchGate:
    """Gate that creates stacked git branches from deterministically calculated base commits.

    This gate implements the stacked branch strategy for the epic state machine:
    - First ticket (no dependencies) branches from epic baseline commit
    - Tickets with single dependency branch from that dependency's final commit (true stacking)
    - Tickets with multiple dependencies branch from most recent dependency final commit

    The gate creates the branch using GitOperations, pushes it to remote, and returns
    branch information in the GateResult metadata.

    Acceptance criteria checked:
        - First ticket (no dependencies) branches from epic baseline commit
        - Tickets with single dependency branch from that dependency's final commit
        - Tickets with multiple dependencies branch from most recent dependency final commit
        - Branch created with name format "ticket/{ticket-id}"
        - Branch pushed to remote
        - Returns branch info in GateResult metadata
        - Raises error if dependency missing final_commit
    """

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Create stacked branch from correct base commit.

        This method calculates the appropriate base commit using _calculate_base_commit,
        creates the branch with format "ticket/{ticket-id}", pushes it to remote,
        and returns success with branch metadata.

        Args:
            ticket: Ticket to create branch for
            context: Epic context with git operations and ticket dependencies

        Returns:
            GateResult with passed=True and branch info in metadata on success,
            or passed=False with error reason on failure
        """
        try:
            from cli.epic.git_operations import GitError

            # Calculate base commit using stacked branch strategy
            base_commit = self._calculate_base_commit(ticket, context)

            # Create branch with standard naming convention
            branch_name = f"ticket/{ticket.id}"
            context.git.create_branch(branch_name, base_commit)
            context.git.push_branch(branch_name)

            return GateResult(
                passed=True,
                reason="Branch created successfully",
                metadata={
                    "branch_name": branch_name,
                    "base_commit": base_commit,
                },
            )
        except GitError as e:
            return GateResult(
                passed=False,
                reason=f"Failed to create branch: {e}",
            )
        except ValueError as e:
            # Catch ValueError from missing dependency final_commit
            return GateResult(
                passed=False,
                reason=f"Failed to create branch: {e}",
            )

    def _calculate_base_commit(self, ticket: Ticket, context: EpicContext) -> str:
        """Calculate base commit for stacked branches using dependency graph.

        Implements the stacked branch strategy:
        - No dependencies: Branch from epic baseline (first ticket in epic)
        - Single dependency: Branch from dependency's final commit (true stacking)
        - Multiple dependencies: Branch from most recent dependency final commit (diamond case)

        Args:
            ticket: Ticket to calculate base for
            context: Epic context with baseline commit and dependency tickets

        Returns:
            Base commit SHA to branch from

        Raises:
            ValueError: If dependency is missing final_commit (not yet completed)
        """
        if not ticket.depends_on:
            # First ticket branches from epic baseline
            return context.baseline_commit

        if len(ticket.depends_on) == 1:
            # Single dependency - branch from its final commit (true stacking)
            dep_id = ticket.depends_on[0]
            dep_ticket = context.tickets[dep_id]
            if not dep_ticket.git_info or not dep_ticket.git_info.final_commit:
                raise ValueError(f"Dependency {dep_id} missing final_commit")
            return dep_ticket.git_info.final_commit

        # Multiple dependencies - find most recent final commit (diamond case)
        dep_commits = []
        for dep_id in ticket.depends_on:
            dep_ticket = context.tickets[dep_id]
            if not dep_ticket.git_info or not dep_ticket.git_info.final_commit:
                raise ValueError(f"Dependency {dep_id} missing final_commit")
            dep_commits.append(dep_ticket.git_info.final_commit)

        return context.git.find_most_recent_commit(dep_commits)
