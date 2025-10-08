# Epic: Python State Machine Enforcement for Epic Execution

## Epic Summary

Replace LLM-driven coordination with a Python state machine that enforces
structured execution of epic tickets. The state machine acts as a programmatic
gatekeeper, enforcing precise git strategies (stacked branches with final
collapse), state transitions, and merge correctness while the LLM focuses solely
on implementing ticket requirements.

**Git Strategy Summary:**

- Tickets execute synchronously (one at a time)
- Each ticket branches from previous ticket's final commit (true stacking)
- Epic branch stays at baseline during execution
- After all tickets complete, collapse all branches into epic branch (squash
  merge)
- Push epic branch to remote for human review

## Problem Statement

The current execute-epic approach leaves too much coordination logic to the LLM
orchestrator:

1. **Inconsistent Execution Quality**: LLM may skip validation steps,
   miscalculate dependencies, or apply git strategies inconsistently
2. **No Enforcement of Invariants**: Critical rules (stacked branches,
   dependency ordering, merge strategies) are documented but not enforced
3. **State Drift**: LLM updates `epic-state.json` manually, leading to potential
   inconsistencies or missing fields
4. **Non-Deterministic Behavior**: Same epic may execute differently on
   different runs based on LLM interpretation
5. **Hard to Debug**: When something goes wrong, unclear if it's LLM error or
   logic error in instructions

**Core Insight**: LLMs are excellent at creative problem-solving (implementing
features, fixing bugs) but poor at following strict procedural rules
consistently. Invert the architecture: **State machine handles procedures, LLM
handles problems**.

## Goals

1. **Deterministic State Transitions**: Python code enforces state machine
   rules, LLM cannot bypass gates
2. **Git Strategy Enforcement**: Stacked branch creation, base commit
   calculation, and merge order handled by code
3. **Validation Gates**: Automated checks before allowing state transitions
   (branch exists, tests pass, etc.)
4. **LLM Interface Boundary**: Clear contract between state machine
   (coordinator) and LLM (worker)
5. **Auditable Execution**: State machine logs all transitions and gate checks
   for debugging
6. **Resumability**: State machine can resume from `epic-state.json` after
   crashes

## Success Criteria

- State machine written in Python with explicit state classes and transition
  rules
- LLM agents interact with state machine via CLI commands only (no direct state
  file manipulation)
- Git operations (branch creation, base commit calculation, merging) are
  deterministic and tested
- Validation gates automatically verify LLM work before accepting state
  transitions
- Epic execution produces identical git structure on every run (given same
  tickets)
- State machine can resume mid-epic execution from state file
- Integration tests verify state machine enforces all invariants

## Architecture Overview

### Core Principle: State Machine as Gatekeeper

```
┌─────────────────────────────────────────────────────────┐
│  execute-epic CLI Command (Python)                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │  EpicStateMachine                                 │  │
│  │  - Owns epic-state.json                           │  │
│  │  - Enforces all state transitions                 │  │
│  │  - Performs git operations                        │  │
│  │  - Validates LLM output against gates             │  │
│  └───────────────────────────────────────────────────┘  │
│                        ▲                                │
│                        │ API calls only                 │
│                        ▼                                │
│  ┌───────────────────────────────────────────────────┐  │
│  │  LLM Orchestrator Agent                           │  │
│  │  - Reads ticket requirements                      │  │
│  │  - Spawns ticket-builder sub-agents               │  │
│  │  - Calls state machine to advance states          │  │
│  │  - NO direct state file access                    │  │
│  └───────────────────────────────────────────────────┘  │
│                        │                                │
│                        │ Task tool spawns               │
│                        ▼                                │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Ticket-Builder Sub-Agents (LLMs)                 │  │
│  │  - Implement ticket requirements                  │  │
│  │  - Create commits on assigned branch              │  │
│  │  - Report completion with artifacts               │  │
│  │  - NO state machine interaction                   │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Git Strategy: True Stacked Branches with Final Collapse

```
Timeline View:

main ──────────────────────────────────────────────────────────►
  │
  └─► epic/feature (created from main, stays at baseline)
        │
        └─► ticket/A ──► (final commit: aaa111)
               │
               └─► ticket/B ──► (final commit: bbb222)
                      │
                      └─► ticket/C ──► (final commit: ccc333)

[All tickets validated and complete]

epic/feature ──► [squash merge A] ──► [squash merge B] ──► [squash merge C] ──► push
                 (clean up ticket/A)  (clean up ticket/B)  (clean up ticket/C)
```

**Key Properties:**

1. **Epic branch stays at baseline** during ticket execution (no progressive
   merging)
2. **Tickets stack on each other**: Each ticket branches from previous ticket's
   final commit
3. **Synchronous execution**: One ticket at a time (concurrency = 1)
4. **Deferred merging**: All merges happen after all tickets are complete
5. **Squash strategy**: Each ticket becomes single commit on epic branch
6. **Cleanup**: Ticket branches deleted after merge

**Execution Flow:**

```
Phase 1: Build tickets (stacked branches)
  ticket/A branches from epic baseline → work → complete (aaa111)
  ticket/B branches from aaa111 → work → complete (bbb222)
  ticket/C branches from bbb222 → work → complete (ccc333)

Phase 2: Collapse into epic branch
  epic/feature ← squash merge ticket/A
  epic/feature ← squash merge ticket/B
  epic/feature ← squash merge ticket/C
  delete ticket/A, ticket/B, ticket/C
  push epic/feature

Phase 3: Human review
  epic/feature pushed to remote
  Human creates PR (epic/feature → main)
```

**Why This Strategy:**

- **Stacking**: Each ticket sees previous ticket's changes (realistic
  development)
- **Clean history**: Epic branch has one commit per ticket (squash merge)
- **Auditability**: Ticket branches preserved in git history (until cleanup)
- **Simplicity**: No concurrent merges, no merge conflicts between tickets
- **Flexibility**: Can pause between tickets, tickets are independently
  reviewable

### State Machine Design

#### Ticket State Enum

```python
from enum import Enum, auto

class TicketState(Enum):
    """Strictly enforced ticket lifecycle states"""

    # Initial state - ticket defined but dependencies not met
    PENDING = auto()

    # Dependencies met, ready for execution
    READY = auto()

    # Branch created from base commit (stacked)
    BRANCH_CREATED = auto()

    # LLM actively working on ticket
    IN_PROGRESS = auto()

    # LLM claims completion, awaiting validation
    AWAITING_VALIDATION = auto()

    # Validation passed, work complete (NOT YET MERGED)
    COMPLETED = auto()

    # Terminal states
    FAILED = auto()
    BLOCKED = auto()  # Dependency failed
```

**Important**: `COMPLETED` means ticket work is done and validated, but **NOT
yet merged** into epic branch. Merging happens in the final collapse phase.

#### Epic State Enum

```python
class EpicState(Enum):
    """Epic-level execution states"""

    INITIALIZING = auto()      # Creating epic branch, parsing tickets
    EXECUTING = auto()         # Building tickets synchronously
    MERGING = auto()           # Collapsing ticket branches into epic
    FINALIZED = auto()         # Epic branch pushed to remote
    FAILED = auto()            # Critical ticket failed
    ROLLED_BACK = auto()       # Rollback completed
```

**Epic State Flow:**

```
INITIALIZING → EXECUTING → MERGING → FINALIZED
                    ↓
                 FAILED → ROLLED_BACK (if rollback_on_failure=true)
```

#### State Transition Gates

**Gates** are validation functions that must return `True` before a state
transition is allowed. The state machine runs gates automatically.

```python
class TransitionGate(Protocol):
    """Gate that validates a state transition is allowed"""

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """
        Returns:
            GateResult(passed=True) if transition allowed
            GateResult(passed=False, reason="...") if blocked
        """
        ...

class GateResult:
    passed: bool
    reason: Optional[str] = None
    metadata: dict = {}
```

#### Gate Definitions by Transition

**PENDING → READY**

```python
class DependenciesMetGate(TransitionGate):
    """Verify all dependencies are COMPLETED (not merged yet - merging happens at end)"""

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        for dep_id in ticket.depends_on:
            dep_ticket = context.get_ticket(dep_id)
            if dep_ticket.state != TicketState.COMPLETED:
                return GateResult(
                    passed=False,
                    reason=f"Dependency {dep_id} not complete (state: {dep_ticket.state})"
                )
        return GateResult(passed=True)
```

**READY → BRANCH_CREATED**

```python
class CreateBranchGate(TransitionGate):
    """Create git branch from correct base commit"""

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        base_commit = self._calculate_base_commit(ticket, context)
        branch_name = f"ticket/{ticket.id}"

        try:
            # State machine performs git operation
            context.git.create_branch(branch_name, base_commit)
            context.git.push_branch(branch_name)

            return GateResult(
                passed=True,
                metadata={
                    "branch_name": branch_name,
                    "base_commit": base_commit
                }
            )
        except GitError as e:
            return GateResult(passed=False, reason=str(e))

    def _calculate_base_commit(self, ticket: Ticket, context: EpicContext) -> str:
        """
        Deterministic base commit calculation for stacked branches.

        Strategy:
        - First ticket: Branch from epic baseline (main HEAD at epic start)
        - Later tickets: Branch from previous ticket's final commit (STACKING)

        This creates: ticket/A → ticket/B → ticket/C (each builds on previous)
        """
        if not ticket.depends_on:
            # No dependencies: branch from epic baseline
            return context.epic_baseline_commit

        elif len(ticket.depends_on) == 1:
            # Single dependency: branch from its final commit (TRUE STACKING)
            dep = context.get_ticket(ticket.depends_on[0])

            # Safety: dependency must be COMPLETED with git_info
            if dep.state != TicketState.COMPLETED:
                raise StateError(f"Dependency {dep.id} not complete (state: {dep.state})")

            if not dep.git_info or not dep.git_info.final_commit:
                raise StateError(f"Dependency {dep.id} missing final commit")

            return dep.git_info.final_commit

        else:
            # Multiple dependencies: find most recent final commit
            # Handles diamond dependencies (B depends on A, C depends on A+B)
            dep_commits = []
            for dep_id in ticket.depends_on:
                dep = context.get_ticket(dep_id)
                if dep.state != TicketState.COMPLETED:
                    raise StateError(f"Dependency {dep_id} not complete")
                dep_commits.append(dep.git_info.final_commit)

            # Use git to find most recent commit by timestamp
            return context.git.find_most_recent_commit(dep_commits)
```

**BRANCH_CREATED → IN_PROGRESS**

```python
class LLMStartGate(TransitionGate):
    """Verify LLM agent can start work (synchronous execution enforced)"""

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        # Enforce synchronous execution (concurrency = 1)
        active_count = context.count_tickets_in_states([
            TicketState.IN_PROGRESS,
            TicketState.AWAITING_VALIDATION
        ])

        if active_count >= 1:  # Hardcoded to 1 for synchronous execution
            return GateResult(
                passed=False,
                reason=f"Another ticket in progress (synchronous execution only)"
            )

        # Verify branch exists and is pushed
        branch_name = ticket.git_info.branch_name
        if not context.git.branch_exists_remote(branch_name):
            return GateResult(
                passed=False,
                reason=f"Branch {branch_name} not found on remote"
            )

        return GateResult(passed=True)
```

**IN_PROGRESS → AWAITING_VALIDATION**

```python
class LLMCompletionGate(TransitionGate):
    """LLM signals work is complete"""

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        # This gate is triggered by LLM calling state machine API
        # No automatic checks - just transition
        # Validation happens in next gate
        return GateResult(passed=True)
```

**AWAITING_VALIDATION → COMPLETED**

```python
class ValidationGate(TransitionGate):
    """
    Comprehensive validation of LLM work.

    Note: This transitions to COMPLETED (not VALIDATED).
    COMPLETED means work is done but NOT yet merged.
    Merging happens in final collapse phase.
    """

    def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
        checks = [
            self._check_branch_has_commits,
            self._check_final_commit_exists,
            self._check_tests_pass,
            self._check_acceptance_criteria
        ]

        # Note: NO merge conflict check here - conflicts will be resolved during
        # final collapse phase when merging into epic branch

        for check in checks:
            result = check(ticket, context)
            if not result.passed:
                return result

        return GateResult(passed=True)

    def _check_branch_has_commits(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Verify ticket branch has new commits beyond base"""
        branch = ticket.git_info.branch_name
        base = ticket.git_info.base_commit

        commits = context.git.get_commits_between(base, branch)
        if len(commits) == 0:
            return GateResult(passed=False, reason="No commits on ticket branch")

        return GateResult(passed=True, metadata={"commit_count": len(commits)})

    def _check_final_commit_exists(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Verify final commit SHA is valid and on branch"""
        final_commit = ticket.git_info.final_commit

        if not context.git.commit_exists(final_commit):
            return GateResult(passed=False, reason=f"Commit {final_commit} not found")

        if not context.git.commit_on_branch(final_commit, ticket.git_info.branch_name):
            return GateResult(
                passed=False,
                reason=f"Commit {final_commit} not on branch {ticket.git_info.branch_name}"
            )

        return GateResult(passed=True)


    def _check_tests_pass(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Verify tests pass on ticket branch"""
        # Option 1: Trust LLM's test report
        if ticket.test_suite_status == "passing":
            return GateResult(passed=True)

        # Option 2: Run tests ourselves (expensive)
        # test_result = context.test_runner.run_on_branch(ticket.git_info.branch_name)
        # return GateResult(passed=test_result.passed)

        if ticket.test_suite_status == "skipped":
            # Allow skipped tests if ticket is not critical
            if ticket.critical:
                return GateResult(passed=False, reason="Critical ticket must have passing tests")
            return GateResult(passed=True, metadata={"tests_skipped": True})

        return GateResult(passed=False, reason=f"Tests not passing: {ticket.test_suite_status}")

    def _check_acceptance_criteria(self, ticket: Ticket, context: EpicContext) -> GateResult:
        """Verify all acceptance criteria marked as met"""
        if not ticket.acceptance_criteria:
            return GateResult(passed=True)  # No criteria defined

        unmet = [ac for ac in ticket.acceptance_criteria if not ac.met]
        if unmet:
            return GateResult(
                passed=False,
                reason=f"Unmet acceptance criteria: {[ac.criterion for ac in unmet]}"
            )

        return GateResult(passed=True)
```

**Note**: There is NO `VALIDATED` or `MERGED` state for individual tickets
during execution. Tickets go from `AWAITING_VALIDATION` → `COMPLETED`. The merge
phase happens separately after all tickets are complete.

### State Machine Core Implementation

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path

@dataclass
class Ticket:
    """Immutable ticket data"""
    id: str
    path: Path
    title: str
    depends_on: List[str]
    critical: bool
    state: TicketState
    git_info: Optional[GitInfo] = None
    test_suite_status: Optional[str] = None
    acceptance_criteria: List[AcceptanceCriterion] = None
    failure_reason: Optional[str] = None
    blocking_dependency: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@dataclass
class GitInfo:
    branch_name: str
    base_commit: str
    final_commit: Optional[str] = None

class EpicStateMachine:
    """
    Core state machine that enforces epic execution rules.

    LLM orchestrator interacts with this via public API methods only.
    State file is private to the state machine.
    """

    def __init__(self, epic_file: Path, resume: bool = False):
        self.epic_file = epic_file
        self.epic_dir = epic_file.parent
        self.state_file = self.epic_dir / "artifacts" / "epic-state.json"

        if resume:
            self._load_state()
        else:
            self._initialize_new_epic()

    # === Public API for LLM Orchestrator ===

    def get_ready_tickets(self) -> List[Ticket]:
        """
        Returns tickets that can be started (dependencies met, slots available)

        State machine handles:
        - Dependency checking
        - Concurrency limits
        - State transitions from PENDING → READY
        """
        ready_tickets = []

        for ticket in self.tickets.values():
            if ticket.state == TicketState.PENDING:
                # Check if dependencies met
                gate = DependenciesMetGate()
                result = gate.check(ticket, self.context)

                if result.passed:
                    # Transition to READY
                    self._transition_ticket(ticket.id, TicketState.READY)
                    ready_tickets.append(ticket)

        # Sort by priority
        ready_tickets.sort(key=lambda t: (
            0 if t.critical else 1,
            -self._calculate_dependency_depth(t)
        ))

        return ready_tickets

    def start_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """
        Prepare ticket for LLM execution.

        State machine handles:
        - Branch creation from correct base commit
        - State transitions: READY → BRANCH_CREATED → IN_PROGRESS
        - Git operations

        Returns:
            {
                "branch_name": "ticket/auth-base",
                "base_commit": "abc123",
                "working_directory": "/path/to/worktree" (optional)
            }
        """
        ticket = self.tickets[ticket_id]

        # Gate: Create branch
        if ticket.state == TicketState.READY:
            result = self._run_gate(ticket, CreateBranchGate())
            if not result.passed:
                raise StateTransitionError(f"Cannot create branch: {result.reason}")

            # Update ticket with git info
            ticket.git_info = GitInfo(
                branch_name=result.metadata["branch_name"],
                base_commit=result.metadata["base_commit"]
            )
            self._transition_ticket(ticket_id, TicketState.BRANCH_CREATED)

        # Gate: Check concurrency and start
        result = self._run_gate(ticket, LLMStartGate())
        if not result.passed:
            raise StateTransitionError(f"Cannot start ticket: {result.reason}")

        self._transition_ticket(ticket_id, TicketState.IN_PROGRESS)

        return {
            "branch_name": ticket.git_info.branch_name,
            "base_commit": ticket.git_info.base_commit,
            "ticket_file": str(ticket.path),
            "epic_file": str(self.epic_file)
        }

    def complete_ticket(
        self,
        ticket_id: str,
        final_commit: str,
        test_suite_status: str,
        acceptance_criteria: List[Dict[str, Any]]
    ) -> bool:
        """
        LLM reports ticket completion. State machine validates.

        State machine handles:
        - Validation gates (branch exists, tests pass, etc.)
        - State transitions: IN_PROGRESS → AWAITING_VALIDATION → COMPLETED
        - NO MERGE - merging happens in finalize() after all tickets complete

        Returns:
            True if validation passed and ticket marked COMPLETED
            False if validation failed (ticket state = FAILED)
        """
        ticket = self.tickets[ticket_id]

        if ticket.state != TicketState.IN_PROGRESS:
            raise StateTransitionError(
                f"Ticket {ticket_id} not in progress (state: {ticket.state})"
            )

        # Update ticket with completion info
        ticket.git_info.final_commit = final_commit
        ticket.test_suite_status = test_suite_status
        ticket.acceptance_criteria = [
            AcceptanceCriterion(**ac) for ac in acceptance_criteria
        ]

        # Transition to awaiting validation
        self._transition_ticket(ticket_id, TicketState.AWAITING_VALIDATION)

        # Run validation gate
        validation_result = self._run_gate(ticket, ValidationGate())

        if not validation_result.passed:
            # Validation failed
            ticket.failure_reason = validation_result.reason
            self._transition_ticket(ticket_id, TicketState.FAILED)
            self._handle_ticket_failure(ticket)
            return False

        # Validation passed - mark COMPLETED (not merged yet)
        self._transition_ticket(ticket_id, TicketState.COMPLETED)
        ticket.completed_at = datetime.now()

        return True

    def finalize_epic(self) -> Dict[str, Any]:
        """
        Collapse all ticket branches into epic branch and push.

        Called after all tickets are COMPLETED.

        Process:
        1. Get tickets in dependency order (topological sort)
        2. Squash merge each ticket into epic branch sequentially
        3. Delete ticket branches
        4. Push epic branch to remote

        Returns:
            {
                "success": true,
                "epic_branch": "epic/feature",
                "merge_commits": ["sha1", "sha2", ...],
                "pushed": true
            }
        """
        # Verify all tickets are complete
        incomplete = [
            t.id for t in self.tickets.values()
            if t.state not in [TicketState.COMPLETED, TicketState.BLOCKED, TicketState.FAILED]
        ]
        if incomplete:
            raise StateError(f"Cannot finalize: tickets not complete: {incomplete}")

        # Transition to MERGING state
        self.epic_state = EpicState.MERGING
        self._save_state()

        # Get tickets in dependency order
        ordered_tickets = self._topological_sort([
            t for t in self.tickets.values()
            if t.state == TicketState.COMPLETED
        ])

        merge_commits = []

        for ticket in ordered_tickets:
            logger.info(f"Squash merging {ticket.id} into {self.epic_branch}")

            try:
                # Squash merge ticket branch into epic branch
                merge_commit = self.git.merge_branch(
                    source=ticket.git_info.branch_name,
                    target=self.epic_branch,
                    strategy="squash",
                    message=f"feat: {ticket.title}\n\nTicket: {ticket.id}"
                )

                merge_commits.append(merge_commit)
                logger.info(f"Merged {ticket.id} as {merge_commit}")

            except GitError as e:
                # Merge failed - likely merge conflicts
                logger.error(f"Failed to merge {ticket.id}: {e}")
                self.epic_state = EpicState.FAILED
                self._save_state()
                return {
                    "success": False,
                    "error": f"Merge conflict in ticket {ticket.id}: {e}",
                    "merged_tickets": merge_commits
                }

        # Delete all ticket branches (cleanup)
        for ticket in ordered_tickets:
            try:
                self.git.delete_branch(ticket.git_info.branch_name, remote=True)
                logger.info(f"Deleted branch {ticket.git_info.branch_name}")
            except GitError as e:
                logger.warning(f"Failed to delete branch {ticket.git_info.branch_name}: {e}")

        # Push epic branch to remote
        self.git.push_branch(self.epic_branch)
        logger.info(f"Pushed {self.epic_branch} to remote")

        # Mark epic as finalized
        self.epic_state = EpicState.FINALIZED
        self._save_state()

        return {
            "success": True,
            "epic_branch": self.epic_branch,
            "merge_commits": merge_commits,
            "pushed": True
        }

    def fail_ticket(self, ticket_id: str, reason: str):
        """LLM reports ticket cannot be completed"""
        ticket = self.tickets[ticket_id]
        ticket.failure_reason = reason
        self._transition_ticket(ticket_id, TicketState.FAILED)
        self._handle_ticket_failure(ticket)

    def get_epic_status(self) -> Dict[str, Any]:
        """Get current epic execution status"""
        return {
            "epic_state": self.epic_state.name,
            "tickets": {
                ticket_id: {
                    "state": ticket.state.name,
                    "critical": ticket.critical,
                    "git_info": ticket.git_info.__dict__ if ticket.git_info else None
                }
                for ticket_id, ticket in self.tickets.items()
            },
            "stats": {
                "total": len(self.tickets),
                "completed": self._count_tickets_in_state(TicketState.COMPLETED),
                "in_progress": self._count_tickets_in_state(TicketState.IN_PROGRESS),
                "failed": self._count_tickets_in_state(TicketState.FAILED),
                "blocked": self._count_tickets_in_state(TicketState.BLOCKED)
            }
        }

    def all_tickets_completed(self) -> bool:
        """Check if all non-blocked/failed tickets are complete"""
        return all(
            t.state in [TicketState.COMPLETED, TicketState.BLOCKED, TicketState.FAILED]
            for t in self.tickets.values()
        )

    # === Private State Machine Implementation ===

    def _transition_ticket(self, ticket_id: str, new_state: TicketState):
        """
        Internal state transition with validation and logging.
        Updates state file atomically.
        """
        ticket = self.tickets[ticket_id]
        old_state = ticket.state

        # Validate transition is allowed
        if not self._is_valid_transition(old_state, new_state):
            raise StateTransitionError(
                f"Invalid transition: {old_state.name} → {new_state.name}"
            )

        # Update ticket state
        ticket.state = new_state

        # Log transition
        self._log_transition(ticket_id, old_state, new_state)

        # Persist state
        self._save_state()

        # Update epic state if needed
        self._update_epic_state()

    def _run_gate(self, ticket: Ticket, gate: TransitionGate) -> GateResult:
        """Execute a validation gate and log result"""
        result = gate.check(ticket, self.context)

        self._log_gate_check(
            ticket.id,
            gate.__class__.__name__,
            result
        )

        return result

    def _handle_ticket_failure(self, ticket: Ticket):
        """
        Handle ticket failure:
        - Block dependent tickets
        - Check if epic should fail
        - Trigger rollback if configured
        """
        # Block all dependent tickets
        for dependent_id in self._find_dependents(ticket.id):
            dependent = self.tickets[dependent_id]
            if dependent.state not in [TicketState.COMPLETED, TicketState.FAILED]:
                dependent.blocking_dependency = ticket.id
                self._transition_ticket(dependent_id, TicketState.BLOCKED)

        # Check epic failure condition
        if ticket.critical:
            if self.epic_config.rollback_on_failure:
                self._execute_rollback()
            else:
                self.epic_state = EpicState.FAILED

        self._save_state()

    def _save_state(self):
        """Atomically save state to JSON file"""
        state_data = {
            "epic_id": self.epic_id,
            "epic_branch": self.epic_branch,
            "epic_state": self.epic_state.name,
            "baseline_commit": self.baseline_commit,
            "started_at": self.started_at.isoformat(),
            "tickets": {
                ticket_id: {
                    "id": ticket.id,
                    "path": str(ticket.path),
                    "state": ticket.state.name,
                    "critical": ticket.critical,
                    "depends_on": ticket.depends_on,
                    "git_info": ticket.git_info.__dict__ if ticket.git_info else None,
                    "test_suite_status": ticket.test_suite_status,
                    "failure_reason": ticket.failure_reason,
                    "blocking_dependency": ticket.blocking_dependency,
                    "started_at": ticket.started_at.isoformat() if ticket.started_at else None,
                    "completed_at": ticket.completed_at.isoformat() if ticket.completed_at else None
                }
                for ticket_id, ticket in self.tickets.items()
            }
        }

        # Atomic write: write to temp file, then rename
        temp_file = self.state_file.with_suffix(".json.tmp")
        with open(temp_file, 'w') as f:
            json.dump(state_data, f, indent=2)

        temp_file.replace(self.state_file)

    def _log_transition(self, ticket_id: str, old_state: TicketState, new_state: TicketState):
        """Log state transition for auditing"""
        logger.info(
            "State transition",
            extra={
                "ticket_id": ticket_id,
                "old_state": old_state.name,
                "new_state": new_state.name,
                "timestamp": datetime.now().isoformat()
            }
        )
```

### LLM Orchestrator Interface

The LLM orchestrator (execute-epic.md) receives simplified instructions:

````markdown
# Execute Epic Orchestrator Instructions

You are the epic orchestrator. Your job is to coordinate ticket execution using
the state machine API.

## Your Responsibilities

1. **Read the epic file** to understand all tickets
2. **Call state machine API** to get ready tickets
3. **Spawn LLM sub-agents** for ready tickets using Task tool
4. **Report completion** back to state machine
5. **Handle failures** by calling state machine failure API

## What You DO NOT Do

- ❌ Create git branches (state machine does this)
- ❌ Calculate base commits (state machine does this)
- ❌ Merge tickets (state machine does this)
- ❌ Update epic-state.json (state machine does this)
- ❌ Validate ticket completion (state machine does this)

## API Commands

### Get Ready Tickets

```bash
buildspec epic status <epic-file> --ready
```
````

Returns JSON:

```json
{
  "ready_tickets": [
    {
      "id": "auth-base",
      "title": "Set up base authentication",
      "critical": true
    }
  ]
}
```

### Start Ticket

```bash
buildspec epic start-ticket <epic-file> <ticket-id>
```

Returns JSON:

```json
{
  "branch_name": "ticket/auth-base",
  "base_commit": "abc123def",
  "ticket_file": "/path/to/ticket.md",
  "epic_file": "/path/to/epic.yaml"
}
```

State machine creates branch automatically.

### Complete Ticket

```bash
buildspec epic complete-ticket <epic-file> <ticket-id> \
  --final-commit <sha> \
  --test-status passing \
  --acceptance-criteria <json-file>
```

State machine validates (NO MERGE - merging happens in finalize step).

Returns:

```json
{
  "success": true,
  "state": "COMPLETED"
}
```

Or if validation fails:

```json
{
  "success": false,
  "reason": "Tests not passing",
  "ticket_state": "FAILED"
}
```

### Finalize Epic

```bash
buildspec epic finalize <epic-file>
```

Collapses all ticket branches into epic branch and pushes.

Returns:

```json
{
  "success": true,
  "epic_branch": "epic/feature-name",
  "merge_commits": ["sha1", "sha2", "sha3"],
  "pushed": true
}
```

### Fail Ticket

```bash
buildspec epic fail-ticket <epic-file> <ticket-id> --reason "Cannot resolve merge conflicts"
```

State machine handles blocking dependent tickets.

## Execution Loop (Synchronous)

```python
# Phase 1: Execute all tickets synchronously
while True:
    # Get ready tickets from state machine
    ready = call_api("epic status --ready")

    if not ready["ready_tickets"]:
        # Check if all tickets done
        status = call_api("epic status")
        if all_tickets_complete(status):
            break
        else:
            # Waiting for dependencies or blocked
            continue

    # Synchronous execution: only 1 ticket at a time
    ticket = ready["ready_tickets"][0]

    # Start ticket (state machine creates branch)
    start_info = call_api(f"epic start-ticket {ticket['id']}")

    # Spawn LLM sub-agent (synchronously - wait for completion)
    result = spawn_sub_agent_and_wait(
        ticket_file=start_info["ticket_file"],
        branch_name=start_info["branch_name"],
        base_commit=start_info["base_commit"]
    )

    # Report result to state machine
    if result.success:
        call_api(f"epic complete-ticket {ticket['id']} ...")
    else:
        call_api(f"epic fail-ticket {ticket['id']} ...")

# Phase 2: Collapse all ticket branches into epic branch
finalize_result = call_api("epic finalize")

if finalize_result["success"]:
    print(f"Epic complete! Branch {finalize_result['epic_branch']} pushed to remote")
else:
    print(f"Epic finalization failed: {finalize_result['error']}")
```

## Sub-Agent Instructions

Your sub-agents receive these parameters:

- `ticket_file`: Path to ticket markdown
- `branch_name`: Git branch to work on (already created)
- `base_commit`: Base commit (for reference)

Sub-agent must:

1. Check out the branch
2. Implement ticket requirements
3. Commit changes
4. Push branch
5. Report final commit SHA and test status

````

### CLI Implementation

```python
# buildspec/cli/epic_commands.py

import click
from buildspec.epic.state_machine import EpicStateMachine

@click.group()
def epic():
    """Epic execution commands"""
    pass

@epic.command()
@click.argument('epic_file', type=click.Path(exists=True))
@click.option('--ready', is_flag=True, help='Show only ready tickets')
def status(epic_file, ready):
    """Get epic execution status"""
    sm = EpicStateMachine(epic_file, resume=True)

    if ready:
        ready_tickets = sm.get_ready_tickets()
        click.echo(json.dumps({
            "ready_tickets": [
                {"id": t.id, "title": t.title, "critical": t.critical}
                for t in ready_tickets
            ]
        }, indent=2))
    else:
        status = sm.get_epic_status()
        click.echo(json.dumps(status, indent=2))

@epic.command()
@click.argument('epic_file', type=click.Path(exists=True))
@click.argument('ticket_id')
def start_ticket(epic_file, ticket_id):
    """Start ticket execution (creates branch)"""
    sm = EpicStateMachine(epic_file, resume=True)

    try:
        result = sm.start_ticket(ticket_id)
        click.echo(json.dumps(result, indent=2))
    except StateTransitionError as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)

@epic.command()
@click.argument('epic_file', type=click.Path(exists=True))
@click.argument('ticket_id')
@click.option('--final-commit', required=True)
@click.option('--test-status', required=True, type=click.Choice(['passing', 'failing', 'skipped']))
@click.option('--acceptance-criteria', type=click.File('r'), required=True)
def complete_ticket(epic_file, ticket_id, final_commit, test_status, acceptance_criteria):
    """Complete ticket (validates and merges)"""
    sm = EpicStateMachine(epic_file, resume=True)

    ac_data = json.load(acceptance_criteria)

    success = sm.complete_ticket(
        ticket_id=ticket_id,
        final_commit=final_commit,
        test_suite_status=test_status,
        acceptance_criteria=ac_data
    )

    if success:
        click.echo(json.dumps({"success": True, "state": "COMPLETED"}))
    else:
        ticket = sm.tickets[ticket_id]
        click.echo(json.dumps({
            "success": False,
            "reason": ticket.failure_reason,
            "ticket_state": ticket.state.name
        }), err=True)
        sys.exit(1)

@epic.command()
@click.argument('epic_file', type=click.Path(exists=True))
@click.argument('ticket_id')
@click.option('--reason', required=True)
def fail_ticket(epic_file, ticket_id, reason):
    """Mark ticket as failed"""
    sm = EpicStateMachine(epic_file, resume=True)
    sm.fail_ticket(ticket_id, reason)
    click.echo(json.dumps({"ticket_id": ticket_id, "state": "FAILED"}))

@epic.command()
@click.argument('epic_file', type=click.Path(exists=True))
def finalize(epic_file):
    """Finalize epic (collapse tickets, push epic branch)"""
    sm = EpicStateMachine(epic_file, resume=True)

    try:
        result = sm.finalize_epic()
        click.echo(json.dumps(result, indent=2))

        if not result["success"]:
            sys.exit(1)
    except StateError as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(1)
````

## Implementation Strategy

### Phase 1: Core State Machine (Week 1)

1. **State enums and data classes** (`buildspec/epic/models.py`)
2. **Gate interface and base gates** (`buildspec/epic/gates.py`)
3. **State machine core** (`buildspec/epic/state_machine.py`)
4. **Git operations wrapper** (`buildspec/epic/git_operations.py`)
5. **State file persistence** (atomic writes, JSON schema validation)

### Phase 2: CLI Commands (Week 1)

1. **Click commands** for epic status, start-ticket, complete-ticket,
   fail-ticket
2. **JSON input/output** for LLM consumption
3. **Error handling** with clear messages

### Phase 3: LLM Integration (Week 2)

1. **Update execute-epic.md** with simplified orchestrator instructions
2. **Update execute-ticket.md** with completion reporting requirements
3. **Test orchestrator** calling state machine API

### Phase 4: Validation Gates (Week 2)

1. **Implement all transition gates**
2. **Git validation** (branch exists, commit exists, merge conflicts)
3. **Test validation** (optional: run tests in CI, or trust LLM report)
4. **Acceptance criteria validation**

### Phase 5: Error Recovery (Week 3)

1. **Rollback implementation**
2. **Partial success handling**
3. **Resume from state file** (orchestrator crash recovery)
4. **Dependency blocking**

### Phase 6: Integration Tests (Week 3)

1. **Happy path**: Simple epic with 3 tickets, all succeed
2. **Critical failure**: Critical ticket fails, rollback triggered
3. **Non-critical failure**: Non-critical fails, dependents blocked, others
   continue
4. **Complex dependencies**: Diamond dependency graph
5. **Crash recovery**: Stop mid-execution, resume from state file

## Key Design Decisions

### 1. State Machine Owns Git Operations

**Decision**: State machine performs all git operations (branch creation,
merging)

**Rationale**:

- Ensures deterministic branch naming and base commit calculation
- LLM cannot create branches from wrong commits
- Merge strategy is consistent (squash vs merge)
- Easier to test git operations in isolation

### 2. Validation Gates Run After LLM Reports Completion

**Decision**: LLM claims completion, then state machine validates

**Rationale**:

- LLM can fail validation (tests didn't actually pass)
- State machine can programmatically check git state
- Clear separation: LLM does work, state machine verifies
- Allows for retries if validation fails

### 3. State File is Private to State Machine

**Decision**: LLM never reads or writes `epic-state.json` directly

**Rationale**:

- Prevents state corruption from LLM mistakes
- State machine guarantees consistency
- LLM uses CLI commands only (clear API boundary)
- State schema can evolve without breaking LLM instructions

### 4. Deferred Merging (Final Collapse Phase)

**Decision**: Tickets marked COMPLETED after validation, merging happens in
separate finalize phase

**Rationale**:

- **Stacked branches preserved**: Tickets remain stacked during execution
- **Epic branch stays clean**: Epic branch only updated once at end
- **Simpler conflict resolution**: All merges happen sequentially in one phase
- **Auditable**: Can inspect all ticket branches before collapse
- **Flexible**: Can pause epic execution without partial merges

### 5. Synchronous Execution (Concurrency = 1)

**Decision**: State machine enforces synchronous execution (one ticket at a
time)

**Rationale**:

- **Simplifies stacking**: Each ticket waits for previous to complete
- **Easier debugging**: Linear execution flow
- **No race conditions**: Only one builder agent active at a time
- **Future-proof**: Can add parallel execution later if needed
- **Safer**: No concurrent git operations or state updates

### 6. Base Commit Calculation is Deterministic

**Decision**: Explicit algorithm for stacked base commits (dependency's final
commit)

**Rationale**:

- **True stacking**: ticket/B always branches from ticket/A's final commit
- **Same epic always produces same branch structure**: Deterministic and
  testable
- **No LLM interpretation**: State machine calculates, not LLM
- **Dependency graph encoded in git history**: Can visualize ticket dependencies
  via git log

## Resolved Design Decisions

1. **Test Execution**: Trust LLM report (faster, simpler)
   - State machine validates test status is "passing" or "skipped"
   - Can add programmatic test execution later if needed

2. **Merge Strategy**: Squash (confirmed)
   - Clean epic branch history (one commit per ticket)
   - Ticket branches preserve detailed commit history

3. **Worktrees**: Not using worktrees (for now)
   - Builder agents check out ticket branch in main repo
   - Can add worktree support later for isolation

4. **State Machine as Service**: CLI commands (simpler)
   - State machine loads from epic-state.json each time
   - No long-running process needed

5. **Concurrency**: Synchronous execution (concurrency = 1)
   - One ticket at a time
   - Parallel execution can be added in future epic

## Success Metrics

- **Determinism**: Same epic produces identical git history on every run
- **Correctness**: State machine prevents invalid transitions 100% of time
- **Auditability**: All state transitions logged with timestamps
- **Resumability**: Epic can resume from any state after crash
- **LLM Independence**: Changing LLM model does not affect epic execution
  correctness

## Next Steps

1. Review this spec for feedback
2. Create tickets for each implementation phase
3. Set up `buildspec/epic/` module structure
4. Implement Phase 1 (core state machine)
5. Add unit tests for state transitions and gates
