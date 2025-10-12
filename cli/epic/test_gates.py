"""Mock gate implementations for testing the state machine.

These are simple gate implementations used for testing. The actual gate
implementations will be created in separate tickets.
"""

from __future__ import annotations

from cli.epic.gates import EpicContext, TransitionGate
from cli.epic.git_operations import GitError
from cli.epic.models import GateResult, Ticket, TicketState


class DependenciesMetGate:
    """Mock gate that checks if all dependencies are completed."""

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Check if all dependencies are completed.

        Args:
            ticket: Ticket to check
            context: Epic context

        Returns:
            GateResult with passed=True if all deps completed
        """
        if not ticket.depends_on:
            return GateResult(passed=True, reason="No dependencies")

        for dep_id in ticket.depends_on:
            if dep_id not in context.tickets:
                return GateResult(
                    passed=False,
                    reason=f"Dependency {dep_id} not found in tickets",
                )

            dep_ticket = context.tickets[dep_id]
            if dep_ticket.state != TicketState.COMPLETED:
                return GateResult(
                    passed=False,
                    reason=f"Dependency {dep_id} not completed (state: {dep_ticket.state.value})",
                )

        return GateResult(passed=True, reason="All dependencies completed")


class CreateBranchGate:
    """Mock gate that creates stacked branches."""

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Create branch from correct base commit.

        Args:
            ticket: Ticket to create branch for
            context: Epic context

        Returns:
            GateResult with branch info in metadata
        """
        try:
            # Calculate base commit
            base_commit = self._calculate_base_commit(ticket, context)

            # Create branch
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

    def _calculate_base_commit(self, ticket: Ticket, context: EpicContext) -> str:
        """Calculate base commit for stacked branches.

        Args:
            ticket: Ticket to calculate base for
            context: Epic context

        Returns:
            Base commit SHA
        """
        if not ticket.depends_on:
            # First ticket branches from epic baseline
            return context.baseline_commit

        if len(ticket.depends_on) == 1:
            # Single dependency - branch from its final commit
            dep_id = ticket.depends_on[0]
            dep_ticket = context.tickets[dep_id]
            if not dep_ticket.git_info or not dep_ticket.git_info.final_commit:
                raise ValueError(f"Dependency {dep_id} missing final_commit")
            return dep_ticket.git_info.final_commit

        # Multiple dependencies - find most recent
        dep_commits = []
        for dep_id in ticket.depends_on:
            dep_ticket = context.tickets[dep_id]
            if not dep_ticket.git_info or not dep_ticket.git_info.final_commit:
                raise ValueError(f"Dependency {dep_id} missing final_commit")
            dep_commits.append(dep_ticket.git_info.final_commit)

        return context.git.find_most_recent_commit(dep_commits)


class LLMStartGate:
    """Gate that enforces synchronous execution.

    This gate ensures only one Claude builder runs at a time by checking
    if any other tickets are currently in IN_PROGRESS or AWAITING_VALIDATION
    state. This prevents concurrent state updates and git conflicts.
    """

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Check if no other tickets are active and branch exists.

        Args:
            ticket: Ticket to start
            context: Epic context

        Returns:
            GateResult with passed=True if no active tickets and branch exists,
            passed=False otherwise with descriptive reason
        """
        # Count active tickets (IN_PROGRESS or AWAITING_VALIDATION)
        active_states = {TicketState.IN_PROGRESS, TicketState.AWAITING_VALIDATION}
        active_count = 0

        for other_ticket in context.tickets.values():
            if other_ticket.id == ticket.id:
                continue

            if other_ticket.state in active_states:
                active_count += 1

        # Block if any tickets are active (enforcing synchronous execution)
        if active_count >= 1:
            return GateResult(
                passed=False,
                reason="Another ticket in progress (synchronous execution only)",
            )

        # Verify ticket branch exists on remote
        if ticket.git_info and ticket.git_info.branch_name:
            if not context.git.branch_exists_remote(ticket.git_info.branch_name):
                return GateResult(
                    passed=False,
                    reason=f"Ticket branch does not exist on remote: {ticket.git_info.branch_name}",
                )

        return GateResult(passed=True, reason="No active tickets")


class ValidationGate:
    """Mock gate that validates ticket completion."""

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Validate ticket work meets requirements.

        Args:
            ticket: Ticket to validate
            context: Epic context

        Returns:
            GateResult with passed=True if all checks pass
        """
        # Check branch has commits
        result = self._check_branch_has_commits(ticket, context)
        if not result.passed:
            return result

        # Check final commit exists
        result = self._check_final_commit_exists(ticket, context)
        if not result.passed:
            return result

        # Check tests pass
        result = self._check_tests_pass(ticket, context)
        if not result.passed:
            return result

        # Check acceptance criteria
        result = self._check_acceptance_criteria(ticket, context)
        if not result.passed:
            return result

        return GateResult(passed=True, reason="All validation checks passed")

    def _check_branch_has_commits(
        self, ticket: Ticket, context: EpicContext
    ) -> GateResult:
        """Check if branch has commits beyond base.

        Args:
            ticket: Ticket to check
            context: Epic context

        Returns:
            GateResult
        """
        if not ticket.git_info or not ticket.git_info.branch_name:
            return GateResult(passed=False, reason="Missing git info")

        try:
            commits = context.git.get_commits_between(
                ticket.git_info.base_commit,
                ticket.git_info.branch_name,
            )

            if len(commits) == 0:
                return GateResult(passed=False, reason="No commits on ticket branch")

            return GateResult(
                passed=True,
                metadata={"commit_count": len(commits)},
            )
        except GitError as e:
            return GateResult(passed=False, reason=f"Git error: {e}")

    def _check_final_commit_exists(
        self, ticket: Ticket, context: EpicContext
    ) -> GateResult:
        """Check if final commit exists and is on branch.

        Args:
            ticket: Ticket to check
            context: Epic context

        Returns:
            GateResult
        """
        if not ticket.git_info or not ticket.git_info.final_commit:
            return GateResult(passed=False, reason="Missing final_commit")

        # Check commit exists
        if not context.git.commit_exists(ticket.git_info.final_commit):
            return GateResult(
                passed=False,
                reason=f"Final commit does not exist: {ticket.git_info.final_commit}",
            )

        # Check commit is on branch
        if not context.git.commit_on_branch(
            ticket.git_info.final_commit,
            ticket.git_info.branch_name,
        ):
            return GateResult(
                passed=False,
                reason=f"Final commit not on branch: {ticket.git_info.final_commit}",
            )

        return GateResult(passed=True)

    def _check_tests_pass(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Check if tests pass.

        Args:
            ticket: Ticket to check
            context: Epic context

        Returns:
            GateResult
        """
        if ticket.test_suite_status == "passing":
            return GateResult(passed=True)

        if ticket.test_suite_status == "skipped" and not ticket.critical:
            return GateResult(
                passed=True,
                metadata={"skipped": True},
            )

        return GateResult(
            passed=False,
            reason=f"Tests not passing: {ticket.test_suite_status}",
        )

    def _check_acceptance_criteria(
        self, ticket: Ticket, context: EpicContext
    ) -> GateResult:
        """Check if acceptance criteria are met.

        Args:
            ticket: Ticket to check
            context: Epic context

        Returns:
            GateResult
        """
        if not ticket.acceptance_criteria:
            return GateResult(passed=True, reason="No acceptance criteria")

        unmet = [ac for ac in ticket.acceptance_criteria if not ac.met]

        if unmet:
            return GateResult(
                passed=False,
                reason=f"Unmet acceptance criteria: {', '.join(ac.criterion for ac in unmet)}",
            )

        return GateResult(passed=True)
