# add-wave-execution-algorithm

## Description

Implement the main wave execution algorithm that orchestrates parallel ticket
execution by integrating all coordination components.

This is the core orchestration loop that coordinates parallel ticket execution.
It integrates all previous tickets (state machine, concurrency control,
spawning, validation, error recovery, git workflow) into a cohesive execution
algorithm that manages epic execution from initialization through completion.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. The wave execution algorithm is the main
orchestrator loop bringing all coordination patterns together.

**Architecture:** Wave-based execution with calculate_ready_tickets(),
MAX_CONCURRENT_TICKETS enforcement, wait-for-any-completion, validation, error
recovery, git merging, and remote push.

## Story

As a **buildspec orchestrator**, I need **a complete wave execution algorithm**
so that **I can coordinate parallel ticket execution, handle failures
gracefully, merge results, and deliver the epic branch as a cohesive
deliverable**.

## Acceptance Criteria

### Core Requirements

- Wave loop correctly calculates ready tickets each iteration
- Concurrency slots are respected (never exceed MAX_CONCURRENT_TICKETS)
- Wait-for-any-completion enables parallel execution tracking
- Epic failure conditions properly trigger rollback or partial success
- Epic completion correctly determines final status
- Finalization merges ticket branches and pushes epic branch
- All git workflow steps execute in correct order
- Execute-epic.md documents complete wave execution algorithm

### Wave Loop Initialization

- Read epic YAML and parse tickets with dependencies
- Create dependency graph adjacency list
- Detect cycles and fail if found
- Initialize all tickets with status=pending, phase=not-started
- Create epic branch and artifacts directory
- Initialize epic-state.json

### Main Wave Loop

While tickets remain in pending/queued/executing:

- Calculate ready tickets using calculate_ready_tickets()
- Check for blocked tickets (dependencies failed)
- Prioritize ready tickets (critical first, dependency depth second)
- Calculate available concurrency slots
- Spawn sub-agents for ready tickets up to available slots
- Wait for at least one sub-agent completion
- Validate completion reports and update state
- Check epic failure conditions (critical ticket failed)
- Check epic completion (all tickets terminal)

### Wait-for-Any-Completion Logic

- Use Task tool to wait for any sub-agent to complete
- Return completion report from completed sub-agent
- Continue tracking other executing sub-agents
- Handle sub-agent failures gracefully

### Epic Failure Handling

- If critical ticket fails and rollback_on_failure=true: trigger rollback and
  break
- If critical ticket fails and rollback_on_failure=false: set partial_success
- Continue wave loop until all tickets terminal

### Epic Completion Logic

- All tickets in terminal state (completed/failed/blocked)
- All critical tickets completed → epic status = completed
- Any critical ticket failed → epic status = partial_success

### Finalization

- Switch to epic branch
- Merge all ticket branches using merge_ticket_branches()
- Commit all artifacts to epic branch
- Push epic branch to remote using push_epic_branch() if remote exists
- Generate comprehensive execution report

## Integration Points

### Upstream Dependencies

- **implement-concurrency-control**: Provides calculate_ready_tickets()
- **define-sub-agent-lifecycle-protocol**: Provides spawn protocol
- **implement-completion-report-validation**: Provides
  validate_completion_report()
- **add-error-recovery-workflows**: Provides error recovery procedures
- **implement-base-commit-calculation**: Provides calculate_base_commit()
- **add-atomic-state-updates**: Provides update_epic_state()
- **update-execute-ticket-completion-reporting**: Sub-agents return correct
  format
- **implement-ticket-branch-merging**: Provides merge_ticket_branches()
- **implement-remote-push-logic**: Provides push_epic_branch()

### Downstream Dependencies

- **add-orchestrator-integration-tests**: Tests wave execution algorithm

## Current vs New Flow

### BEFORE (Current State)

Execute-epic.md has vague orchestration instructions without concrete algorithm.

### AFTER (This Ticket)

Execute-epic.md contains complete wave execution algorithm with:

- Initialization steps
- Main wave loop with all checks
- Wait-for-any-completion logic
- Failure handling
- Completion detection
- Finalization steps
- Complete example walkthroughs

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-epic.md`

Add "Wave Execution Algorithm" section:

````markdown
## Wave Execution Algorithm

### Overview

The wave execution algorithm is the main orchestrator loop that coordinates
parallel ticket execution. It manages the entire epic lifecycle from
initialization through completion, integrating all coordination components.

### Algorithm Phases

1. **Initialization:** Create epic branch, parse tickets, build dependency graph
2. **Wave Loop:** Calculate ready tickets, spawn sub-agents, validate
   completions
3. **Finalization:** Merge branches, push to remote, generate report

### Phase 1: Initialization

```python
def initialize_epic_execution(epic_file: Path) -> EpicState:
    """
    Initialize epic execution.

    Creates epic branch, artifacts directory, baseline state.

    Returns EpicState object ready for wave execution.
    """
    logger.info(f"Initializing epic execution from {epic_file}...")

    # 1. Read and parse epic YAML
    epic_data = yaml.safe_load(epic_file.read_text())

    epic_name = epic_data['epic']
    rollback_on_failure = epic_data.get('rollback_on_failure', True)
    tickets = epic_data['tickets']

    # 2. Detect dependency cycles
    detect_cycles(tickets)

    # 3. Verify working directory is clean
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.stdout.strip():
        raise GitError("Working directory has uncommitted changes. Commit or stash before starting epic.")

    # 4. Create epic branch
    epic_branch = f"epic/{slugify(epic_name)}"
    subprocess.run(['git', 'checkout', '-b', epic_branch], check=True)

    baseline_commit = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True
    ).stdout.strip()

    logger.info(f"Created epic branch: {epic_branch} at {baseline_commit[:8]}")

    # 5. Create artifacts directory
    epic_dir = epic_file.parent
    artifacts_dir = epic_dir / 'artifacts'
    artifacts_dir.mkdir(exist_ok=True)

    tickets_dir = artifacts_dir / 'tickets'
    tickets_dir.mkdir(exist_ok=True)

    # 6. Initialize epic state
    state = EpicState(
        epic_id=epic_name,
        epic_branch=epic_branch,
        baseline_commit=baseline_commit,
        epic_pr_url=None,
        status='initializing',
        started_at=datetime.now(UTC).isoformat(),
        completed_at=None,
        failure_reason=None,
        rollback_on_failure=rollback_on_failure,
        tickets={}
    )

    # 7. Initialize ticket states
    for ticket in tickets:
        ticket_id = ticket['id']
        state.tickets[ticket_id] = TicketState(
            path=ticket['path'],
            depends_on=ticket.get('depends_on', []),
            critical=ticket.get('critical', True),
            status='pending',
            phase='not-started',
            git_info=None,
            started_at=None,
            completed_at=None,
            failure_reason=None,
            blocking_dependency=None
        )

    # 8. Save initial state
    state.status = 'ready_to_execute'
    update_epic_state(state, {})

    logger.info(f"Epic initialized with {len(tickets)} tickets")

    return state
```
````

### Phase 2: Main Wave Loop

```python
def execute_wave_loop(state: EpicState, epic_path: Path) -> EpicState:
    """
    Execute main wave loop for parallel ticket execution.

    Continues until all tickets reach terminal state.

    Returns final EpicState.
    """
    logger.info("Starting wave execution loop...")

    # Track executing sub-agents
    executing_handles = {}  # ticket_id -> SubAgentHandle

    while not all_tickets_terminal(state):
        # Update epic status
        if executing_handles:
            state.status = 'executing_wave'
        else:
            state.status = 'ready_to_execute'
        update_epic_state(state, {})

        # 1. Calculate ready tickets
        ready_tickets = calculate_ready_tickets(state)
        logger.info(f"Ready tickets: {[t.id for t in ready_tickets]}")

        # 2. Check for epic failure conditions
        if should_fail_epic(state):
            logger.error("Critical ticket failed. Checking rollback...")
            handle_epic_failure(state)
            break

        # 3. Calculate available concurrency slots
        executing_count = len(executing_handles)
        available_slots = MAX_CONCURRENT_TICKETS - executing_count

        logger.info(f"Executing: {executing_count}, Available slots: {available_slots}")

        # 4. Spawn sub-agents for ready tickets (up to available slots)
        if available_slots > 0 and ready_tickets:
            tickets_to_spawn = ready_tickets[:available_slots]

            for ticket in tickets_to_spawn:
                try:
                    # Calculate base commit
                    base_commit = calculate_base_commit(state, ticket)

                    # Spawn sub-agent
                    handle = spawn_ticket_sub_agent_with_retry(
                        ticket,
                        base_commit,
                        session_id=generate_session_id()
                    )

                    executing_handles[ticket.id] = handle

                    # Update ticket state
                    state.tickets[ticket.id].status = 'queued'
                    state.tickets[ticket.id].status = 'executing'
                    state.tickets[ticket.id].started_at = datetime.now(UTC).isoformat()
                    update_epic_state(state, {ticket.id: state.tickets[ticket.id]})

                    logger.info(f"Spawned sub-agent for {ticket.id}")

                except Exception as e:
                    logger.error(f"Failed to spawn {ticket.id}: {e}")
                    state.tickets[ticket.id].status = 'failed'
                    state.tickets[ticket.id].failure_reason = f'spawn_error: {str(e)}'
                    update_epic_state(state, {ticket.id: state.tickets[ticket.id]})

        # 5. Wait for at least one completion (if any executing)
        if executing_handles:
            completed_ticket_id, completion_report = wait_for_any_completion(executing_handles)

            # Remove from executing handles
            del executing_handles[completed_ticket_id]

            # 6. Validate completion report
            ticket = state.tickets[completed_ticket_id]
            ticket.status = 'validating'
            update_epic_state(state, {completed_ticket_id: ticket})

            validation_result = validate_completion_report(ticket, completion_report)

            if validation_result.passed:
                # Validation passed
                ticket.status = 'completed'
                ticket.phase = 'completed'
                ticket.completed_at = datetime.now(UTC).isoformat()
                ticket.git_info = {
                    'branch_name': completion_report['branch_name'],
                    'base_commit': completion_report['base_commit'],
                    'final_commit': completion_report['final_commit']
                }
                logger.info(f"Ticket {completed_ticket_id} completed successfully")
            else:
                # Validation failed
                ticket.status = 'failed'
                ticket.failure_reason = f'validation_failed: {validation_result.error}'
                ticket.completed_at = datetime.now(UTC).isoformat()
                logger.error(f"Ticket {completed_ticket_id} validation failed: {validation_result.error}")

            update_epic_state(state, {completed_ticket_id: ticket})

        elif not ready_tickets:
            # No executing, no ready → check if done
            if all_tickets_terminal(state):
                logger.info("All tickets reached terminal state")
                break
            else:
                # Waiting for dependencies
                logger.info("No ready tickets, waiting for dependencies...")
                time.sleep(5)  # Brief wait before rechecking

    logger.info("Wave execution loop complete")
    return state
```

### Phase 3: Finalization

```python
def finalize_epic_execution(state: EpicState) -> EpicState:
    """
    Finalize epic execution.

    Merges ticket branches, pushes to remote, generates report.

    Returns final EpicState.
    """
    logger.info("Finalizing epic execution...")

    # 1. Determine final epic status
    completed_tickets = [
        tid for tid, t in state.tickets.items()
        if t.status == 'completed'
    ]

    critical_tickets = [
        tid for tid, t in state.tickets.items()
        if t.critical
    ]

    critical_completed = [
        tid for tid in critical_tickets
        if state.tickets[tid].status == 'completed'
    ]

    if len(critical_completed) == len(critical_tickets):
        # All critical tickets completed
        final_status = 'completed'
    else:
        # Some critical tickets failed or blocked
        final_status = 'partial_success'

    state.status = final_status
    logger.info(f"Epic final status: {final_status}")

    # 2. Merge ticket branches (if any completed)
    if completed_tickets:
        logger.info(f"Merging {len(completed_tickets)} completed ticket branches...")
        merge_ticket_branches(state)
    else:
        logger.warning("No completed tickets to merge")

    # 3. Push epic branch to remote (if remote exists)
    if state.status == 'completed':
        logger.info("Pushing epic branch to remote...")
        push_success = push_epic_branch(state)

        if not push_success:
            logger.warning("Push failed or skipped, but epic completed successfully")

    # 4. Update final state
    state.completed_at = datetime.now(UTC).isoformat()
    update_epic_state(state, {})

    # 5. Generate execution report
    generate_execution_report(state)

    logger.info(f"Epic execution finalized: {state.status}")

    return state
```

### Helper Functions

**all_tickets_terminal:**

```python
def all_tickets_terminal(state: EpicState) -> bool:
    """Check if all tickets are in terminal state."""
    terminal_states = ['completed', 'failed', 'blocked']
    return all(
        t.status in terminal_states
        for t in state.tickets.values()
    )
```

**should_fail_epic:**

```python
def should_fail_epic(state: EpicState) -> bool:
    """Check if epic should fail due to critical ticket failure."""
    for ticket_id, ticket in state.tickets.items():
        if ticket.critical and ticket.status == 'failed':
            if state.rollback_on_failure:
                return True
    return False
```

**handle_epic_failure:**

```python
def handle_epic_failure(state: EpicState):
    """Handle epic failure due to critical ticket failure."""
    if state.rollback_on_failure:
        logger.warning("Critical ticket failed with rollback_on_failure=true. Executing rollback...")
        execute_rollback(state)
    else:
        logger.warning("Critical ticket failed with rollback_on_failure=false. Marking partial_success...")
        state.status = 'partial_success'
        update_epic_state(state, {})
```

**wait_for_any_completion:**

```python
def wait_for_any_completion(handles: Dict[str, SubAgentHandle]) -> Tuple[str, dict]:
    """
    Wait for any sub-agent to complete.

    Returns (ticket_id, completion_report) for completed sub-agent.
    """
    # Use Task tool to wait for any completion
    # (Implementation depends on Task tool API)
    ticket_id, report = Task.wait_for_any(handles)
    return ticket_id, report
```

### Complete Example: Execution Walkthrough

**Epic:** user-authentication (3 tickets)

**Tickets:**

- A: add-auth-base (critical, no deps)
- B: add-sessions (critical, depends on A)
- C: add-permissions (non-critical, depends on A)

**Execution:**

```
Initialization:
- Create epic/user-authentication
- baseline_commit = abc123
- All tickets: status=pending

Wave 1:
- Ready: [A] (no dependencies)
- Spawn A (base_commit = abc123)
- A executing...

Wave 2:
- A completes (final_commit = aaa111)
- Validate A → passed
- A: status=completed
- Ready: [B, C] (dependencies met)
- Available slots: 2
- Spawn B (base_commit = aaa111)
- Spawn C (base_commit = aaa111)
- B, C executing...

Wave 3:
- B completes (final_commit = bbb222)
- Validate B → passed
- B: status=completed
- C completes (final_commit = ccc333)
- Validate C → passed
- C: status=completed

Finalization:
- All tickets terminal
- All critical (A, B) completed → epic status = completed
- Merge order: [A, B, C] (topological sort)
- Merge A into epic/user-authentication
- Merge B into epic/user-authentication
- Merge C into epic/user-authentication
- Push epic/user-authentication to remote
- Generate execution report
- Epic status = completed
```

### Main Entry Point

```python
def execute_epic(epic_file: Path):
    """
    Main entry point for epic execution.

    Orchestrates complete epic execution from initialization to finalization.
    """
    try:
        # Phase 1: Initialize
        state = initialize_epic_execution(epic_file)

        # Phase 2: Execute waves
        state = execute_wave_loop(state, epic_file)

        # Phase 3: Finalize
        state = finalize_epic_execution(state)

        # Report final status
        if state.status == 'completed':
            logger.info("✅ Epic execution completed successfully")
        elif state.status == 'partial_success':
            logger.warning("⚠️  Epic execution completed with partial success")
        elif state.status == 'rolled_back':
            logger.error("❌ Epic execution failed and rolled back")
        else:
            logger.error(f"❌ Epic execution failed: {state.status}")

    except Exception as e:
        logger.error(f"Epic execution failed with exception: {e}")
        raise
```

````

### Implementation Details

1. **Add Wave Execution Section:** Insert after all component sections in execute-epic.md

2. **Document All Phases:** Initialization, wave loop, finalization

3. **Provide Complete Algorithms:** Full pseudocode for main loop and helpers

4. **Example Walkthrough:** Complete execution example with 3 tickets

5. **Main Entry Point:** Orchestration function calling all phases

### Integration with Existing Code

Wave execution algorithm integrates:
- calculate_ready_tickets() for ready ticket calculation
- spawn_ticket_sub_agent_with_retry() for sub-agent spawning
- validate_completion_report() for validation
- calculate_base_commit() for stacked branches
- update_epic_state() for state persistence
- merge_ticket_branches() for branch merging
- push_epic_branch() for remote push
- execute_rollback() for failure recovery

## Error Handling Strategy

- **Initialization Failure:** Fail fast with clear error (dirty repo, cycle detection)
- **Spawn Failure:** Mark ticket as failed, continue with other tickets
- **Validation Failure:** Mark ticket as failed, block dependents
- **Critical Failure:** Trigger rollback or partial_success based on rollback_on_failure
- **Merge Conflict:** Fail epic with clear error message
- **Push Failure:** Mark partial_success, preserve local work

## Testing Strategy

### Validation Tests

1. **Initialization:**
   - Test epic branch creation
   - Test baseline commit recording
   - Test ticket state initialization
   - Test cycle detection

2. **Wave Loop:**
   - Test ready ticket calculation
   - Test concurrency limit enforcement
   - Test wait-for-any-completion
   - Test validation integration

3. **Finalization:**
   - Test merge execution
   - Test remote push
   - Test final status determination
   - Test execution report generation

4. **Complete Scenarios:**
   - Test successful epic (all tickets complete)
   - Test partial success (some tickets fail)
   - Test rollback (critical failure)
   - Test complex dependency graph (diamond)

### Test Commands

```bash
# Run wave execution tests
uv run pytest tests/integration/test_wave_execution.py -v

# Test complete epic execution
uv run pytest tests/integration/test_wave_execution.py::test_complete_execution -v

# Test with failures
uv run pytest tests/integration/test_wave_execution.py::test_partial_success -v
````

## Dependencies

- **implement-concurrency-control**
- **define-sub-agent-lifecycle-protocol**
- **implement-completion-report-validation**
- **add-error-recovery-workflows**
- **implement-base-commit-calculation**
- **add-atomic-state-updates**
- **update-execute-ticket-completion-reporting**
- **implement-ticket-branch-merging**
- **implement-remote-push-logic**

## Coordination Role

Integrates all coordination components including git workflow into main
execution algorithm. This is the core orchestrator that brings everything
together for complete epic execution.
