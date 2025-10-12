"""Self-driving epic state machine for autonomous ticket execution.

This module provides the EpicStateMachine class that orchestrates epic execution
from start to finish. The state machine drives the entire execution loop,
manages state transitions, validates preconditions via gates, and persists
state atomically to epic-state.json.

The execution has two phases:
- Phase 1: Execute tickets synchronously in dependency order
- Phase 2: Finalize epic (collapse branches - placeholder for now)
"""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from cli.epic.claude_builder import ClaudeTicketBuilder
from cli.epic.gates import EpicContext, TransitionGate
from cli.epic.git_operations import GitError, GitOperations
from cli.epic.models import (
    AcceptanceCriterion,
    BuilderResult,
    EpicState,
    GateResult,
    GitInfo,
    Ticket,
    TicketState,
)

logger = logging.getLogger(__name__)


class EpicStateMachine:
    """Self-driving state machine for autonomous epic execution.

    The state machine orchestrates ticket execution, state transitions, and
    validation gates. It uses GitOperations for branch management, spawns
    ClaudeTicketBuilder for ticket implementation, runs TransitionGate
    implementations for validation, and persists state to epic-state.json.

    Execution is synchronous (one ticket at a time) and follows dependency
    ordering using the stacked branch strategy.
    """

    def __init__(self, epic_file: Path, resume: bool = False):
        """Initialize the state machine.

        Args:
            epic_file: Path to the epic YAML file
            resume: If True, resume from existing state file (not implemented yet)

        Raises:
            FileNotFoundError: If epic file doesn't exist
            ValueError: If epic YAML is invalid
        """
        self.epic_file = epic_file
        self.epic_dir = epic_file.parent
        self.state_file = self.epic_dir / "artifacts" / "epic-state.json"

        # Load epic configuration
        with open(epic_file, "r") as f:
            self.epic_config = yaml.safe_load(f)

        # Extract epic metadata
        self.epic_id = self.epic_dir.name
        self.epic_branch = f"epic/{self.epic_id}"

        # Initialize git operations
        self.git = GitOperations()

        # Initialize tickets from epic config
        self.tickets: dict[str, Ticket] = {}
        self._initialize_tickets()

        # Get baseline commit (current HEAD for now)
        result = self.git._run_git_command(["git", "rev-parse", "HEAD"])
        self.baseline_commit = result.stdout.strip()

        # Create epic context
        self.context = EpicContext(
            epic_id=self.epic_id,
            epic_branch=self.epic_branch,
            baseline_commit=self.baseline_commit,
            tickets=self.tickets,
            git=self.git,
            epic_config=self.epic_config,
        )

        # Initialize epic state
        self.epic_state = EpicState.EXECUTING

        # Ensure artifacts directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Save initial state
        self._save_state()

        logger.info(f"Initialized epic state machine: {self.epic_id}")
        logger.info(f"Baseline commit: {self.baseline_commit}")
        logger.info(f"Epic branch: {self.epic_branch}")
        logger.info(f"Total tickets: {len(self.tickets)}")

    def _initialize_tickets(self) -> None:
        """Initialize ticket objects from epic YAML configuration."""
        tickets_data = self.epic_config.get("tickets", [])

        for ticket_data in tickets_data:
            ticket_id = ticket_data["id"]
            ticket_path = self.epic_dir / "tickets" / f"{ticket_id}.md"

            ticket = Ticket(
                id=ticket_id,
                path=str(ticket_path),
                title=ticket_data.get("description", "").split("\n")[0][:100],
                depends_on=ticket_data.get("depends_on", []),
                critical=ticket_data.get("critical", False),
                state=TicketState.PENDING,
            )

            self.tickets[ticket_id] = ticket

        logger.info(f"Initialized {len(self.tickets)} tickets from epic config")

    def execute(self) -> None:
        """Main execution loop - drives epic to completion autonomously.

        Phase 1: Execute tickets synchronously in dependency order until all
                 tickets are in terminal states (COMPLETED, FAILED, BLOCKED).
        Phase 2: Finalize epic by collapsing branches (placeholder for now).
        """
        logger.info("Starting epic execution")

        # Ensure epic branch exists
        self._ensure_epic_branch_exists()

        # Phase 1: Execute tickets
        while not self._all_tickets_completed():
            # Get ready tickets
            ready_tickets = self._get_ready_tickets()

            if not ready_tickets and self._has_active_tickets():
                # Wait for active ticket to complete
                logger.warning("No ready tickets but has active tickets - waiting")
                break
            elif not ready_tickets:
                # No ready tickets and no active tickets - check if blocked
                logger.warning("No ready tickets and no active tickets")
                break

            # Execute the first ready ticket
            ticket = ready_tickets[0]
            logger.info(f"Executing ticket: {ticket.id}")
            self._execute_ticket(ticket)

        # Phase 2: Finalize epic (placeholder)
        if self._all_tickets_completed():
            logger.info("All tickets completed - finalizing epic")
            self._finalize_epic()
        else:
            logger.warning("Not all tickets completed - epic incomplete")
            # Check for failures
            failed_count = sum(
                1 for t in self.tickets.values() if t.state == TicketState.FAILED
            )
            blocked_count = sum(
                1 for t in self.tickets.values() if t.state == TicketState.BLOCKED
            )
            if failed_count > 0 or blocked_count > 0:
                logger.error(
                    f"Epic failed: {failed_count} failed tickets, "
                    f"{blocked_count} blocked tickets"
                )
                self.epic_state = EpicState.FAILED
                self._save_state()

        logger.info("Epic execution complete")

    def _ensure_epic_branch_exists(self) -> None:
        """Ensure the epic branch exists, create if needed."""
        if not self.git.branch_exists_remote(self.epic_branch):
            logger.info(f"Creating epic branch: {self.epic_branch}")
            try:
                self.git.create_branch(self.epic_branch, self.baseline_commit)
                self.git.push_branch(self.epic_branch)
                logger.info(f"Epic branch created: {self.epic_branch}")
            except GitError as e:
                logger.error(f"Failed to create epic branch: {e}")
                raise

    def _get_ready_tickets(self) -> list[Ticket]:
        """Get tickets ready to execute.

        Filters PENDING tickets, runs DependenciesMetGate, transitions to READY,
        and returns sorted by priority (dependency depth).

        Returns:
            List of tickets ready to execute, sorted by priority
        """
        from cli.epic.gates import DependenciesMetGate

        ready_tickets = []

        for ticket in self.tickets.values():
            if ticket.state != TicketState.PENDING:
                continue

            # Run dependencies gate
            gate = DependenciesMetGate()
            result = self._run_gate(ticket, gate)

            if result.passed:
                # Transition to READY
                self._transition_ticket(ticket.id, TicketState.READY)
                ready_tickets.append(self.tickets[ticket.id])

        # Sort by dependency depth (tickets with no deps first)
        ready_tickets.sort(key=lambda t: self._calculate_dependency_depth(t))

        return ready_tickets

    def _calculate_dependency_depth(self, ticket: Ticket) -> int:
        """Calculate dependency depth for ticket ordering.

        Args:
            ticket: Ticket to calculate depth for

        Returns:
            Dependency depth (0 for no deps, 1 + max(dep_depth) for deps)
        """
        if not ticket.depends_on:
            return 0

        max_depth = 0
        for dep_id in ticket.depends_on:
            if dep_id in self.tickets:
                dep_depth = self._calculate_dependency_depth(self.tickets[dep_id])
                max_depth = max(max_depth, dep_depth)

        return 1 + max_depth

    def _execute_ticket(self, ticket: Ticket) -> None:
        """Execute a single ticket.

        Calls _start_ticket to create branch and transition to IN_PROGRESS,
        spawns ClaudeTicketBuilder, processes BuilderResult, and calls
        _complete_ticket or _fail_ticket.

        Args:
            ticket: Ticket to execute
        """
        logger.info(f"Starting ticket execution: {ticket.id}")

        try:
            # Start ticket (create branch, transition to IN_PROGRESS)
            branch_info = self._start_ticket(ticket.id)

            # Get updated ticket
            ticket = self.tickets[ticket.id]

            # Spawn builder
            logger.info(f"Spawning builder for ticket: {ticket.id}")
            builder = ClaudeTicketBuilder(
                ticket_file=Path(ticket.path),
                branch_name=branch_info["branch_name"],
                base_commit=branch_info["base_commit"],
                epic_file=self.epic_file,
            )

            result = builder.execute()

            # Process builder result
            if result.success:
                logger.info(f"Builder succeeded for ticket: {ticket.id}")
                success = self._complete_ticket(
                    ticket.id,
                    result.final_commit,
                    result.test_status,
                    result.acceptance_criteria,
                )
                if not success:
                    logger.error(f"Ticket failed validation: {ticket.id}")
            else:
                logger.error(f"Builder failed for ticket: {ticket.id}")
                self._fail_ticket(ticket.id, result.error or "Builder execution failed")

        except Exception as e:
            logger.error(f"Exception executing ticket {ticket.id}: {e}")
            self._fail_ticket(ticket.id, str(e))

    def _start_ticket(self, ticket_id: str) -> dict[str, Any]:
        """Start ticket execution.

        Runs CreateBranchGate (creates branch), transitions to BRANCH_CREATED,
        runs LLMStartGate, transitions to IN_PROGRESS.

        Args:
            ticket_id: ID of ticket to start

        Returns:
            Branch info dict with branch_name and base_commit

        Raises:
            Exception: If gate checks fail
        """
        from cli.epic.test_gates import CreateBranchGate, LLMStartGate

        ticket = self.tickets[ticket_id]
        logger.info(f"Starting ticket: {ticket_id}")

        # Run create branch gate
        create_gate = CreateBranchGate()
        result = self._run_gate(ticket, create_gate)

        if not result.passed:
            raise Exception(f"CreateBranchGate failed: {result.reason}")

        # Update ticket git info
        branch_name = result.metadata["branch_name"]
        base_commit = result.metadata["base_commit"]

        ticket = self.tickets[ticket_id]
        ticket.git_info = GitInfo(
            branch_name=branch_name,
            base_commit=base_commit,
        )

        # Transition to BRANCH_CREATED
        self._transition_ticket(ticket_id, TicketState.BRANCH_CREATED)

        # Run LLM start gate
        llm_gate = LLMStartGate()
        result = self._run_gate(self.tickets[ticket_id], llm_gate)

        if not result.passed:
            raise Exception(f"LLMStartGate failed: {result.reason}")

        # Transition to IN_PROGRESS
        ticket = self.tickets[ticket_id]
        ticket.started_at = datetime.utcnow().isoformat()
        self._transition_ticket(ticket_id, TicketState.IN_PROGRESS)

        logger.info(f"Ticket started: {ticket_id} on branch {branch_name}")

        return {
            "branch_name": branch_name,
            "base_commit": base_commit,
        }

    def _complete_ticket(
        self,
        ticket_id: str,
        final_commit: Optional[str],
        test_status: Optional[str],
        acceptance_criteria: list[AcceptanceCriterion],
    ) -> bool:
        """Complete ticket execution.

        Updates ticket with completion info, transitions to AWAITING_VALIDATION,
        runs ValidationGate, transitions to COMPLETED or FAILED.

        Args:
            ticket_id: ID of ticket to complete
            final_commit: Final commit SHA
            test_status: Test status (passing/failing/skipped)
            acceptance_criteria: List of acceptance criteria

        Returns:
            True if validation passes and ticket marked COMPLETED, False otherwise
        """
        from cli.epic.test_gates import ValidationGate

        ticket = self.tickets[ticket_id]
        logger.info(f"Completing ticket: {ticket_id}")

        # Update ticket with completion info
        ticket.git_info = GitInfo(
            branch_name=ticket.git_info.branch_name,
            base_commit=ticket.git_info.base_commit,
            final_commit=final_commit,
        )
        ticket.test_suite_status = test_status
        ticket.acceptance_criteria = acceptance_criteria
        ticket.completed_at = datetime.utcnow().isoformat()

        # Transition to AWAITING_VALIDATION
        self._transition_ticket(ticket_id, TicketState.AWAITING_VALIDATION)

        # Run validation gate
        validation_gate = ValidationGate()
        result = self._run_gate(self.tickets[ticket_id], validation_gate)

        if result.passed:
            # Transition to COMPLETED
            self._transition_ticket(ticket_id, TicketState.COMPLETED)
            logger.info(f"Ticket completed: {ticket_id}")
            return True
        else:
            # Transition to FAILED
            self._fail_ticket(ticket_id, f"Validation failed: {result.reason}")
            return False

    def _fail_ticket(self, ticket_id: str, reason: str) -> None:
        """Fail a ticket with cascading effects.

        Sets failure_reason, transitions to FAILED, and handles cascading
        effects (blocking dependents, epic failure for critical tickets).

        Args:
            ticket_id: ID of ticket to fail
            reason: Failure reason
        """
        ticket = self.tickets[ticket_id]
        ticket.failure_reason = reason
        self._transition_ticket(ticket_id, TicketState.FAILED)
        logger.error(f"Ticket failed: {ticket_id} - {reason}")

        # Handle cascading effects
        self._handle_ticket_failure(ticket)

    def _handle_ticket_failure(self, ticket: Ticket) -> None:
        """Handle ticket failure with cascading effects.

        Blocks dependent tickets and handles critical failures.

        Args:
            ticket: The ticket that failed
        """
        logger.info(f"Handling failure cascading for ticket: {ticket.id}")

        # Find and block all dependent tickets
        dependent_ids = self._find_dependents(ticket.id)

        for dep_id in dependent_ids:
            dependent = self.tickets[dep_id]

            # Only block tickets that are not already in terminal states
            if dependent.state not in [TicketState.COMPLETED, TicketState.FAILED]:
                logger.info(f"Blocking ticket {dep_id} due to failed dependency {ticket.id}")
                dependent.blocking_dependency = ticket.id
                self._transition_ticket(dep_id, TicketState.BLOCKED)

        # Handle critical ticket failure
        if ticket.critical:
            rollback_on_failure = self.epic_config.get("rollback_on_failure", False)

            if rollback_on_failure:
                logger.info(f"Critical ticket {ticket.id} failed - executing rollback")
                self._execute_rollback()
            else:
                logger.error(f"Critical ticket {ticket.id} failed - transitioning epic to FAILED")
                self.epic_state = EpicState.FAILED
                self._save_state()

    def _find_dependents(self, ticket_id: str) -> list[str]:
        """Find all tickets that depend on the given ticket.

        Args:
            ticket_id: ID of ticket to find dependents for

        Returns:
            List of ticket IDs that depend on the given ticket
        """
        dependents = []

        for tid, ticket in self.tickets.items():
            if ticket_id in ticket.depends_on:
                dependents.append(tid)

        logger.debug(f"Found {len(dependents)} dependents for ticket {ticket_id}: {dependents}")
        return dependents

    def _execute_rollback(self) -> None:
        """Execute rollback by cleaning up branches and resetting state.

        Placeholder for now - will be implemented in ticket: implement-rollback-logic.
        """
        logger.warning("Rollback requested but not yet implemented")
        self.epic_state = EpicState.FAILED
        self._save_state()

    def _topological_sort(self, tickets: list[Ticket]) -> list[Ticket]:
        """Sort tickets in dependency order (dependencies before dependents).

        Uses Kahn's algorithm for topological sorting.

        Args:
            tickets: List of tickets to sort

        Returns:
            Sorted list with dependencies before dependents

        Raises:
            ValueError: If circular dependency detected
        """
        # Build adjacency list and in-degree count
        ticket_map = {t.id: t for t in tickets}
        in_degree = {t.id: 0 for t in tickets}
        adjacency = {t.id: [] for t in tickets}

        for ticket in tickets:
            for dep_id in ticket.depends_on:
                if dep_id in ticket_map:
                    adjacency[dep_id].append(ticket.id)
                    in_degree[ticket.id] += 1

        # Queue tickets with no dependencies
        queue = [tid for tid in in_degree if in_degree[tid] == 0]
        sorted_ids = []

        while queue:
            # Sort queue to ensure deterministic ordering
            queue.sort()
            current_id = queue.pop(0)
            sorted_ids.append(current_id)

            # Reduce in-degree for dependents
            for dependent_id in adjacency[current_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        # Check for cycles
        if len(sorted_ids) != len(tickets):
            raise ValueError("Circular dependency detected in tickets")

        # Return tickets in sorted order
        return [ticket_map[tid] for tid in sorted_ids]

    def _finalize_epic(self) -> dict[str, Any]:
        """Finalize epic by collapsing branches.

        This method implements the collapse phase that runs after all tickets
        complete. It performs topological sort of tickets, squash-merges each
        into epic branch in dependency order, deletes ticket branches, and
        pushes epic branch to remote.

        Returns:
            Dict with success status, epic_branch, merge_commits, and pushed flag

        Raises:
            GitError: If merge conflicts occur or git operations fail
        """
        logger.info("Starting epic finalization")

        # Verify all tickets in terminal states
        terminal_states = {TicketState.COMPLETED, TicketState.BLOCKED, TicketState.FAILED}
        non_terminal = [
            t for t in self.tickets.values() if t.state not in terminal_states
        ]
        if non_terminal:
            error_msg = f"Cannot finalize: {len(non_terminal)} tickets not in terminal state"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Transition epic to MERGING
        self.epic_state = EpicState.MERGING
        self._save_state()

        # Get only COMPLETED tickets for merging
        completed_tickets = [
            t for t in self.tickets.values() if t.state == TicketState.COMPLETED
        ]

        if not completed_tickets:
            logger.warning("No completed tickets to merge")
            self.epic_state = EpicState.FINALIZED
            self._save_state()
            return {
                "success": True,
                "epic_branch": self.epic_branch,
                "merge_commits": [],
                "pushed": False,
            }

        # Topologically sort tickets
        try:
            sorted_tickets = self._topological_sort(completed_tickets)
            logger.info(
                f"Sorted {len(sorted_tickets)} tickets for merging: "
                f"{[t.id for t in sorted_tickets]}"
            )
        except ValueError as e:
            logger.error(f"Failed to sort tickets: {e}")
            self.epic_state = EpicState.FAILED
            self._save_state()
            raise

        # Stash any changes to state file before switching branches
        try:
            self.git._run_git_command(["git", "add", str(self.state_file)], check=False)
            self.git._run_git_command(["git", "stash", "push", "-m", "Stash state before finalization"], check=False)
        except GitError:
            pass  # OK if stash fails

        # Merge each ticket into epic branch
        merge_commits = []
        try:
            for ticket in sorted_tickets:
                logger.info(f"Merging ticket {ticket.id} into {self.epic_branch}")
                logger.debug(f"Ticket branch: {ticket.git_info.branch_name}, base: {ticket.git_info.base_commit}, final: {ticket.git_info.final_commit}")

                # Checkout epic branch
                self.git._run_git_command(["git", "checkout", self.epic_branch])

                # Perform squash merge with automatic conflict resolution for state file
                # Use -X ours strategy to prefer our version in conflicts
                merge_result = self.git._run_git_command(
                    ["git", "merge", "--squash", "-X", "ours", ticket.git_info.branch_name],
                    check=False
                )

                # If merge still failed (not just state file conflict), abort
                if merge_result.returncode != 0:
                    if "CONFLICT" in merge_result.stdout:
                        raise GitError(
                            f"Merge conflict for {ticket.id}: {merge_result.stdout}\n{merge_result.stderr}"
                        )

                # Remove state file from staging if it was included in the merge
                self.git._run_git_command(["git", "reset", "HEAD", str(self.state_file)], check=False)
                if self.state_file.exists():
                    self.state_file.unlink()

                # Construct commit message
                commit_message = f"feat: {ticket.title}\n\nTicket: {ticket.id}"

                # Commit the squash merge
                self.git._run_git_command(["git", "commit", "-m", commit_message])

                # Get the merge commit SHA
                result = self.git._run_git_command(["git", "rev-parse", "HEAD"])
                merge_commit = result.stdout.strip()

                merge_commits.append(merge_commit)
                logger.info(
                    f"Merged ticket {ticket.id}: commit {merge_commit[:8]}"
                )

        except GitError as e:
            logger.error(f"Merge conflict or error during finalization: {e}")
            self.epic_state = EpicState.FAILED
            self._save_state()
            raise

        # Delete ticket branches (both local and remote)
        for ticket in sorted_tickets:
            try:
                logger.info(f"Deleting branch {ticket.git_info.branch_name}")
                self.git.delete_branch(ticket.git_info.branch_name, remote=False)
                self.git.delete_branch(ticket.git_info.branch_name, remote=True)
            except GitError as e:
                # Log warning but continue - branch deletion is not critical
                logger.warning(
                    f"Failed to delete branch {ticket.git_info.branch_name}: {e}"
                )

        # Push epic branch to remote
        try:
            logger.info(f"Pushing epic branch {self.epic_branch} to remote")
            self.git.push_branch(self.epic_branch)
            pushed = True
        except GitError as e:
            logger.error(f"Failed to push epic branch: {e}")
            self.epic_state = EpicState.FAILED
            self._save_state()
            raise

        # Transition epic to FINALIZED
        self.epic_state = EpicState.FINALIZED
        self._save_state()

        logger.info(
            f"Epic finalization complete: {len(merge_commits)} commits, "
            f"{len(sorted_tickets)} branches deleted"
        )

        return {
            "success": True,
            "epic_branch": self.epic_branch,
            "merge_commits": merge_commits,
            "pushed": pushed,
        }

    def _transition_ticket(self, ticket_id: str, new_state: TicketState) -> None:
        """Transition ticket to new state.

        Validates transition, updates ticket.state, logs transition, saves state.

        Args:
            ticket_id: ID of ticket to transition
            new_state: New state to transition to
        """
        ticket = self.tickets[ticket_id]
        old_state = ticket.state

        # Update state
        ticket.state = new_state

        # Log transition
        self._log_transition(ticket_id, old_state, new_state)

        # Save state
        self._save_state()

    def _log_transition(
        self, ticket_id: str, old_state: TicketState, new_state: TicketState
    ) -> None:
        """Log state transition.

        Args:
            ticket_id: ID of ticket
            old_state: Previous state
            new_state: New state
        """
        logger.info(f"Ticket {ticket_id}: {old_state.value} -> {new_state.value}")

    def _run_gate(self, ticket: Ticket, gate: TransitionGate) -> GateResult:
        """Run a validation gate.

        Calls gate.check(), logs result, returns GateResult.

        Args:
            ticket: Ticket being validated
            gate: Gate to run

        Returns:
            GateResult from gate check
        """
        gate_name = gate.__class__.__name__
        logger.info(f"Running gate {gate_name} for ticket {ticket.id}")

        result = gate.check(ticket, self.context)

        if result.passed:
            logger.info(f"Gate {gate_name} passed for ticket {ticket.id}")
        else:
            logger.warning(
                f"Gate {gate_name} failed for ticket {ticket.id}: {result.reason}"
            )

        return result

    def _save_state(self) -> None:
        """Save state to JSON atomically.

        Serializes epic and ticket state to JSON, atomic write via temp file + rename.
        """
        # Build state dict
        state = {
            "schema_version": 1,
            "epic_id": self.epic_id,
            "epic_branch": self.epic_branch,
            "baseline_commit": self.baseline_commit,
            "epic_state": self.epic_state.value,
            "tickets": {
                ticket_id: self._serialize_ticket(ticket)
                for ticket_id, ticket in self.tickets.items()
            },
        }

        # Write atomically via temp file + rename
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=self.state_file.parent,
            delete=False,
            suffix=".json.tmp",
        ) as f:
            json.dump(state, f, indent=2)
            temp_path = f.name

        # Rename to final location (atomic on POSIX)
        Path(temp_path).rename(self.state_file)

        logger.debug(f"State saved to {self.state_file}")

    def _serialize_ticket(self, ticket: Ticket) -> dict[str, Any]:
        """Serialize ticket to JSON-compatible dict.

        Args:
            ticket: Ticket to serialize

        Returns:
            Dictionary representation of ticket
        """
        return {
            "id": ticket.id,
            "path": ticket.path,
            "title": ticket.title,
            "depends_on": ticket.depends_on,
            "critical": ticket.critical,
            "state": ticket.state.value,
            "git_info": {
                "branch_name": ticket.git_info.branch_name,
                "base_commit": ticket.git_info.base_commit,
                "final_commit": ticket.git_info.final_commit,
            } if ticket.git_info else None,
            "test_suite_status": ticket.test_suite_status,
            "acceptance_criteria": [
                {"criterion": ac.criterion, "met": ac.met}
                for ac in ticket.acceptance_criteria
            ],
            "failure_reason": ticket.failure_reason,
            "blocking_dependency": ticket.blocking_dependency,
            "started_at": ticket.started_at,
            "completed_at": ticket.completed_at,
        }

    def _all_tickets_completed(self) -> bool:
        """Check if all tickets are in terminal states.

        Returns:
            True if all tickets are COMPLETED, BLOCKED, or FAILED
        """
        terminal_states = {TicketState.COMPLETED, TicketState.BLOCKED, TicketState.FAILED}
        return all(ticket.state in terminal_states for ticket in self.tickets.values())

    def _has_active_tickets(self) -> bool:
        """Check if any tickets are actively being worked on.

        Returns:
            True if any tickets are IN_PROGRESS or AWAITING_VALIDATION
        """
        active_states = {TicketState.IN_PROGRESS, TicketState.AWAITING_VALIDATION}
        return any(ticket.state in active_states for ticket in self.tickets.values())
