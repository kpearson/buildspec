# add-error-recovery-workflows

## Description

Implement error recovery workflows for all failure scenarios in epic execution,
including critical ticket failures, non-critical failures, sub-agent spawn
failures, and orchestrator crashes.

Epic execution can fail in multiple ways requiring different recovery
strategies. This ticket implements rollback procedures for critical failures,
partial success handling for non-critical failures, spawn retry logic, and crash
recovery from epic-state.json.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. Error recovery ensures the orchestrator can
handle failures gracefully, provide rollback when needed, and resume execution
after crashes.

**Architecture:** Uses rollback_on_failure flag to determine rollback vs partial
success. Epic-state.json is single source of truth for crash recovery. Dependent
tickets are marked 'blocked' when dependencies fail.

## Story

As a **buildspec orchestrator**, I need **comprehensive error recovery
workflows** so that **I can handle critical failures with rollback, preserve
partial work when appropriate, and resume execution after crashes without data
loss**.

## Acceptance Criteria

### Core Requirements

- Critical ticket failures trigger appropriate rollback or partial success
  handling
- Non-critical failures mark dependent tickets as blocked
- execute_rollback() correctly deletes branches and updates state
- Orchestrator crash recovery resets stale executing tickets and resumes
- Sub-agent spawn failures retry with exponential backoff

### Critical Ticket Failure Handling

- **Detection:** Ticket with critical=true transitions to status='failed'
- **If rollback_on_failure=true:**
  - Stop spawning new tickets immediately
  - Wait for currently executing tickets to complete
  - Execute execute_rollback() to delete epic and ticket branches
  - Epic status = 'rolled_back'
- **If rollback_on_failure=false:**
  - Mark dependent tickets as 'blocked' (set blocking_dependency field)
  - Continue executing independent tickets
  - Epic status = 'partial_success'

### Non-Critical Ticket Failure Handling

- **Detection:** Ticket with critical=false transitions to status='failed'
- Mark dependent tickets as 'blocked' (set blocking_dependency to failed ticket
  ID)
- Continue executing independent tickets (no dependencies on failed ticket)
- Epic can still reach status='completed' if all critical tickets succeed

### execute_rollback() Function

- Delete epic branch: `git branch -D epic/{epic_name}`
- Delete all ticket branches created for this epic: `git branch -D ticket/*`
- Record rollback reason and list of completed tickets in epic-state.json
- Generate rollback report with failure details and completed work summary
- Epic status = 'rolled_back', completed_at = current timestamp

### Orchestrator Crash Recovery

- **On restart:** Read epic-state.json to determine current state
- **Stale tickets:** Tickets in status='executing' are stale (sub-agent lost)
- **Reset logic:** Reset stale tickets to 'queued' if dependencies still met,
  otherwise 'pending'
- **Resume:** Resume from current wave calculation with recalculated ready
  tickets
- **Single source of truth:** Epic-state.json contains all information needed
  for restart

### Sub-Agent Spawn Retry Logic

- **Max retries:** 2 attempts (total 3 tries including initial spawn)
- **Backoff:** Exponential with 5s, 15s delays
- **After max retries:** Ticket status = 'failed' with
  failure_reason='spawn_failed_after_retries'

## Integration Points

### Upstream Dependencies

- **update-execute-epic-state-machine**: Provides state definitions for failed,
  rolled_back, partial_success, blocked

### Downstream Dependencies

- **add-wave-execution-algorithm**: Uses error recovery workflows when tickets
  fail or orchestrator crashes

## Current vs New Flow

### BEFORE (Current State)

Execute-epic.md has no error recovery documentation. Unclear what happens when
tickets fail or orchestrator crashes.

### AFTER (This Ticket)

Execute-epic.md contains comprehensive "Error Recovery Workflows" section with:

- Critical vs non-critical failure handling
- execute_rollback() implementation
- Crash recovery procedures
- Spawn retry logic with exponential backoff
- Examples for each failure scenario

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-epic.md`

Add "Error Recovery Workflows" section:

````markdown
## Error Recovery Workflows

### Critical Ticket Failure

**Detection:** Ticket with `critical: true` transitions to `status: 'failed'`

**Workflow:**

```python
def handle_critical_ticket_failure(epic_state: EpicState, failed_ticket: Ticket):
    """
    Handle critical ticket failure based on rollback_on_failure setting.
    """
    logger.error(f"Critical ticket {failed_ticket.id} failed: {failed_ticket.failure_reason}")

    if epic_state.rollback_on_failure:
        # Rollback workflow
        logger.warning("rollback_on_failure=true. Initiating rollback...")

        # Stop spawning new tickets
        epic_state.status = 'failed'
        epic_state.failure_reason = f'critical_ticket_failed: {failed_ticket.id}'
        update_epic_state(epic_state, {})

        # Wait for currently executing tickets to complete
        wait_for_all_executing_tickets()

        # Execute rollback
        execute_rollback(epic_state)

    else:
        # Partial success workflow
        logger.warning("rollback_on_failure=false. Continuing with partial success...")

        # Mark dependent tickets as blocked
        mark_dependent_tickets_blocked(epic_state, failed_ticket.id)

        # Epic can continue with independent tickets
        epic_state.status = 'partial_success'
        epic_state.failure_reason = f'critical_ticket_failed_no_rollback: {failed_ticket.id}'
        update_epic_state(epic_state, {})

        # Continue wave execution with remaining tickets
```
````

### Non-Critical Ticket Failure

**Detection:** Ticket with `critical: false` transitions to `status: 'failed'`

**Workflow:**

```python
def handle_non_critical_ticket_failure(epic_state: EpicState, failed_ticket: Ticket):
    """
    Handle non-critical ticket failure.

    Non-critical failures don't trigger rollback, but dependent tickets
    are marked as blocked.
    """
    logger.warning(f"Non-critical ticket {failed_ticket.id} failed: {failed_ticket.failure_reason}")

    # Mark dependent tickets as blocked
    mark_dependent_tickets_blocked(epic_state, failed_ticket.id)

    # Epic continues - can still reach 'completed' if all critical tickets succeed
    # No epic status change needed
```

### Mark Dependent Tickets Blocked

**Purpose:** Mark tickets that depend on failed ticket as blocked.

**Implementation:**

```python
def mark_dependent_tickets_blocked(epic_state: EpicState, failed_ticket_id: str):
    """
    Mark all tickets that depend on failed ticket as blocked.
    """
    for ticket_id, ticket_state in epic_state.tickets.items():
        # Check if this ticket depends on the failed ticket
        if failed_ticket_id in ticket_state.depends_on:
            # Only block if not already in terminal state
            if ticket_state.status not in ['completed', 'failed', 'blocked']:
                ticket_state.status = 'blocked'
                ticket_state.blocking_dependency = failed_ticket_id
                ticket_state.failure_reason = f'dependency_failed: {failed_ticket_id}'
                update_epic_state(epic_state, {ticket_id: ticket_state})
                logger.warning(f"Ticket {ticket_id} blocked due to failed dependency {failed_ticket_id}")
```

### execute_rollback() Function

**Purpose:** Delete epic and ticket branches, record rollback details.

**Implementation:**

```python
def execute_rollback(epic_state: EpicState):
    """
    Roll back epic execution by deleting branches and recording rollback.
    """
    logger.warning(f"Rolling back epic {epic_state.epic_id}...")

    # 1. Delete epic branch
    result = subprocess.run(
        ['git', 'branch', '-D', epic_state.epic_branch],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        logger.error(f"Failed to delete epic branch: {result.stderr}")
    else:
        logger.info(f"Deleted epic branch: {epic_state.epic_branch}")

    # 2. Delete all ticket branches for this epic
    for ticket_id, ticket_state in epic_state.tickets.items():
        if ticket_state.git_info and ticket_state.git_info.get('branch_name'):
            branch_name = ticket_state.git_info['branch_name']
            result = subprocess.run(
                ['git', 'branch', '-D', branch_name],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.warning(f"Failed to delete ticket branch {branch_name}: {result.stderr}")
            else:
                logger.info(f"Deleted ticket branch: {branch_name}")

    # 3. Record rollback in state
    epic_state.status = 'rolled_back'
    epic_state.completed_at = datetime.now(UTC).isoformat()

    # List completed tickets for rollback report
    completed_tickets = [
        ticket_id for ticket_id, ticket_state in epic_state.tickets.items()
        if ticket_state.status == 'completed'
    ]

    if completed_tickets:
        logger.info(f"Rollback discarded work from completed tickets: {completed_tickets}")

    update_epic_state(epic_state, {})

    # 4. Generate rollback report
    generate_rollback_report(epic_state, completed_tickets)

    logger.warning("Rollback complete. Epic branch and ticket branches deleted.")
```

### Orchestrator Crash Recovery

**Scenario:** Orchestrator process crashes or is interrupted during execution.

**Recovery Procedure:**

```python
def recover_from_crash(epic_path: str) -> EpicState:
    """
    Recover epic execution after orchestrator crash.

    Reads epic-state.json and resets stale 'executing' tickets.
    """
    logger.info("Attempting crash recovery...")

    # 1. Read epic-state.json
    state_file = Path(epic_path).parent / 'artifacts' / 'epic-state.json'
    if not state_file.exists():
        raise RuntimeError("Cannot recover: epic-state.json not found")

    epic_state = json.loads(state_file.read_text())

    # 2. Identify stale tickets (in 'executing' state)
    stale_tickets = [
        ticket_id for ticket_id, ticket_state in epic_state.tickets.items()
        if ticket_state.status == 'executing'
    ]

    if stale_tickets:
        logger.warning(f"Found {len(stale_tickets)} stale tickets: {stale_tickets}")

    # 3. Reset stale tickets to queued or pending
    for ticket_id in stale_tickets:
        ticket_state = epic_state.tickets[ticket_id]

        # Check if dependencies are still met
        deps_met = all(
            epic_state.tickets[dep_id].status == 'completed'
            for dep_id in ticket_state.depends_on
        )

        if deps_met:
            # Dependencies met → queued
            ticket_state.status = 'queued'
            logger.info(f"Reset {ticket_id} from executing → queued")
        else:
            # Dependencies not met → pending
            ticket_state.status = 'pending'
            logger.info(f"Reset {ticket_id} from executing → pending")

        # Clear started_at timestamp
        ticket_state.started_at = None

    # 4. Reset epic to ready_to_execute
    if epic_state.status == 'executing_wave':
        epic_state.status = 'ready_to_execute'
        logger.info("Reset epic status from executing_wave → ready_to_execute")

    # 5. Save recovered state
    update_epic_state(epic_state, {})

    logger.info("Crash recovery complete. Resuming epic execution...")
    return epic_state
```

### Sub-Agent Spawn Retry Logic

**Purpose:** Retry sub-agent spawning on transient failures.

**Implementation:**

```python
def spawn_ticket_sub_agent_with_retry(
    ticket: Ticket,
    base_commit: str,
    session_id: str,
    max_retries: int = 2
) -> SubAgentHandle:
    """
    Spawn sub-agent with exponential backoff retry.

    Args:
        max_retries: Maximum number of retry attempts (default: 2)
                    Total attempts = max_retries + 1 (initial try)

    Returns:
        SubAgentHandle if spawn succeeds

    Raises:
        SpawnFailedError if all retries exhausted
    """
    backoff_delays = [5, 15]  # seconds

    for attempt in range(max_retries + 1):
        try:
            # Attempt spawn
            handle = spawn_ticket_sub_agent(ticket, base_commit, session_id)
            logger.info(f"Spawned sub-agent for {ticket.id} (attempt {attempt + 1})")
            return handle

        except SpawnError as e:
            if attempt < max_retries:
                # Retry with backoff
                delay = backoff_delays[attempt]
                logger.warning(f"Spawn failed for {ticket.id} (attempt {attempt + 1}): {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                # Max retries exhausted
                logger.error(f"Spawn failed for {ticket.id} after {max_retries + 1} attempts: {e}")
                ticket.status = 'failed'
                ticket.failure_reason = f'spawn_failed_after_retries: {str(e)}'
                update_epic_state(epic_state, {ticket.id: ticket})
                raise SpawnFailedError(f"Failed to spawn {ticket.id} after {max_retries + 1} attempts") from e
```

### Error Recovery Examples

**Example 1: Critical Failure with Rollback**

- Epic with 5 tickets (all critical), rollback_on_failure=true
- Tickets A, B complete successfully
- Ticket C fails (critical)
- Orchestrator stops spawning D, E
- Waits for any executing tickets to complete
- Calls execute_rollback() → deletes epic branch and all ticket branches
- Epic status = 'rolled_back'

**Example 2: Non-Critical Failure, Partial Success**

- Epic with 5 tickets (C is non-critical), rollback_on_failure=false
- Tickets A, B complete successfully
- Ticket C fails (non-critical)
- Ticket D depends on C → marked 'blocked'
- Ticket E is independent → continues executing and completes
- Epic status = 'partial_success' (4 completed, 1 failed, 1 blocked)

**Example 3: Orchestrator Crash Recovery**

- Epic execution in progress: A, B completed; C, D executing
- Orchestrator crashes
- On restart: Read epic-state.json
- C, D are in 'executing' state but sub-agents lost
- Reset C, D to 'queued' (dependencies A, B completed)
- Resume wave execution from ready_to_execute state

````

### Implementation Details

1. **Add Error Recovery Section:** Insert after Completion Report Validation in execute-epic.md

2. **Document All Failure Scenarios:** Critical failure, non-critical failure, crash recovery, spawn retries

3. **Provide Complete Algorithms:** Full pseudocode for each recovery workflow

4. **Examples:** Show concrete scenarios for each error type

### Integration with Existing Code

Error recovery workflows integrate with:
- State machine transitions (failed, rolled_back, partial_success, blocked states)
- Epic-state.json for crash recovery
- Git commands for branch deletion
- Wave execution loop for failure detection

## Error Handling Strategy

- **Rollback Failures:** If git branch deletion fails, log error but continue rollback
- **State Corruption:** If epic-state.json is corrupted, crash recovery fails (no recovery possible)
- **Spawn Retry Exhaustion:** After max retries, mark ticket as failed (no further attempts)

## Testing Strategy

### Validation Tests

1. **Critical Failure with Rollback:**
   - Create test epic with critical ticket that fails
   - Verify execute_rollback() deletes branches
   - Verify epic status = 'rolled_back'

2. **Non-Critical Failure:**
   - Create test epic with non-critical ticket that fails
   - Verify dependent tickets marked 'blocked'
   - Verify independent tickets continue

3. **Crash Recovery:**
   - Simulate crash by interrupting orchestrator
   - Verify recovery resets stale tickets
   - Verify execution resumes correctly

4. **Spawn Retry:**
   - Simulate spawn failures
   - Verify exponential backoff delays
   - Verify failure after max retries

### Test Commands

```bash
# Run error recovery tests
uv run pytest tests/integration/test_error_recovery.py -v

# Test rollback workflow
uv run pytest tests/integration/test_error_recovery.py::test_rollback -v

# Test crash recovery
uv run pytest tests/integration/test_error_recovery.py::test_crash_recovery -v
````

## Dependencies

- **update-execute-epic-state-machine**: Provides state definitions for error
  states

## Coordination Role

Provides rollback and recovery procedures used by wave execution on failures.
Ensures epic execution is resilient to failures and can recover from crashes
without data loss.
