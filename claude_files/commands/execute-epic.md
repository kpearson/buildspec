# execute-epic

Execute an entire epic containing multiple tickets, managing dependencies and
parallel execution.

## Usage

```
/execute-epic <epic-file-path>
```

## Description

This command orchestrates the execution of an entire epic by:

- Understanding ticket dependencies and execution order
- Running independent tickets in parallel
- Ensuring each ticket completes successfully before running dependents
- Validating the full test suite passes after all tickets complete

**Important**: This command spawns a Task agent that manages multiple sub-agents
for ticket execution, ensuring autonomous completion of the entire epic.

## State Machine

The epic execution follows a formal state machine pattern with explicit states
and transitions for both epic-level and ticket-level coordination. This ensures
deterministic behavior, resumability after crashes, and clear error recovery
paths.

### Epic-Level States

The epic execution follows this state machine:

| State            | Description                                         | Transitions To                      | Trigger Condition                                |
| ---------------- | --------------------------------------------------- | ----------------------------------- | ------------------------------------------------ |
| initializing     | Creating epic branch, artifacts dir, baseline state | ready_to_execute, failed            | Initialization success/failure                   |
| ready_to_execute | Waiting to spawn next wave                          | executing_wave, completed           | Ready tickets found, or all tickets terminal     |
| executing_wave   | Sub-agents actively executing                       | ready_to_execute, failed, completed | Sub-agent completion, critical failure, all done |
| completed        | All tickets complete                                | (terminal)                          | All tickets in completed state                   |
| failed           | Critical ticket failed, rolling back                | rolled_back, partial_success        | Rollback execution completes                     |
| rolled_back      | Changes reverted, branches deleted                  | (terminal)                          | Rollback complete                                |
| partial_success  | Rollback disabled, preserving work                  | (terminal)                          | Critical failure with rollback_on_failure=false  |

### Ticket-Level States

Each ticket progresses through these states:

| State      | Description                                  | Transitions To     | Trigger Condition                            |
| ---------- | -------------------------------------------- | ------------------ | -------------------------------------------- |
| pending    | Waiting for dependencies                     | queued, blocked    | Dependencies completed, or dependency failed |
| queued     | Ready to spawn, waiting for concurrency slot | executing          | Concurrency slot available                   |
| executing  | Sub-agent actively working                   | validating, failed | Sub-agent returns, or spawn error            |
| validating | Orchestrator validating completion           | completed, failed  | Validation success/failure                   |
| completed  | Work complete, artifacts recorded            | (terminal)         | Validation passed                            |
| failed     | Execution or validation failed               | (terminal)         | Unrecoverable error                          |
| blocked    | Dependency failed, cannot execute            | (terminal)         | Upstream dependency in failed state          |

### State Transition Rules

1. **Epic Initialization:**
   - Start: initializing
   - Success → ready_to_execute (all tickets pending, dependency graph built)
   - Failure → failed (cannot create epic branch or artifacts directory)

2. **Wave Execution:**
   - ready_to_execute → executing_wave (spawn sub-agents for ready tickets)
   - executing_wave → ready_to_execute (at least one sub-agent completed)
   - executing_wave → completed (all tickets in terminal state, all critical
     tickets completed)
   - executing_wave → failed (critical ticket failed with
     rollback_on_failure=true)

3. **Error Recovery:**
   - failed → rolled_back (execute_rollback completes, epic/ticket branches
     deleted)
   - failed → partial_success (critical failure with rollback_on_failure=false)

4. **Ticket Transitions:**
   - pending → queued (all depends_on tickets in completed state)
   - pending → blocked (any depends_on ticket in failed state)
   - queued → executing (spawn sub-agent successfully)
   - executing → validating (sub-agent returns completion report)
   - validating → completed (validate_completion_report passes)
   - validating → failed (validation fails: branch not found, tests failing,
     etc.)

### State Update Protocol

**When to Update epic-state.json:**

- Before spawning sub-agent: ticket.status = queued → executing
- After sub-agent returns: ticket.status = executing → validating
- After validation: ticket.status = validating → completed/failed
- After epic state change: epic.status updates with timestamp

**Consistency Requirements:**

- Use atomic write (temp file + rename) for all state updates
- Include timestamps for all state changes (started_at, completed_at)
- Validate JSON schema before writing
- Never update state while reading (read-modify-write pattern)

### Crash Recovery

If orchestrator crashes:

1. Read epic-state.json to determine current state
2. Tickets in 'executing' state are stale (sub-agent lost)
3. Reset stale tickets to queued if dependencies still met, otherwise pending
4. Resume from ready_to_execute state, recalculate ready tickets
5. Epic-state.json is single source of truth for restart

### State Machine Examples

**Example 1: Normal Execution (3 Independent Tickets)**

```
Epic State Flow:
initializing → ready_to_execute → executing_wave → ready_to_execute → completed

Ticket States (A, B, C have no dependencies):
  Wave 1: A, B, C: pending → queued → executing
  Wave 2: A: validating → completed, B, C: still executing
  Wave 3: B: validating → completed, C: still executing
  Wave 4: C: validating → completed
  Epic: ready_to_execute → completed
```

**Example 2: Diamond Dependency Graph**

```
Dependency Structure: A → B, A → C, B → D, C → D

Ticket States:
  Wave 1: A: pending → queued → executing → validating → completed
  Wave 2: B, C: pending → queued → executing (parallel execution)
  Wave 3: B: validating → completed, C: validating → completed
  Wave 4: D: pending → queued → executing → validating → completed
  Epic: initializing → ready_to_execute → executing_wave → completed
```

**Example 3: Critical Ticket Failure with Rollback**

```
Epic State Flow:
initializing → ready_to_execute → executing_wave → failed → rolled_back

Ticket States (A is critical, B depends on A):
  Wave 1: A: pending → queued → executing → validating → failed
  Epic: executing_wave → failed (critical ticket failed, rollback_on_failure=true)
  Wave 2: B: pending → blocked (dependency failed)
  Rollback: Delete epic/[name] branch, delete ticket/A branch
  Epic: failed → rolled_back
```

**Example 4: Non-Critical Failure with Partial Success**

```
Epic State Flow:
initializing → ready_to_execute → executing_wave → completed

Ticket States (A is non-critical, B depends on A, C is independent and critical):
  Wave 1: A: pending → queued → executing → validating → failed
  Wave 2: B: pending → blocked (dependency failed)
          C: pending → queued → executing → validating → completed
  Epic: All tickets terminal, critical tickets completed → completed
  Result: partial_success (some non-critical work failed but epic succeeded)
```

**Example 5: Orchestrator Crash and Recovery**

```
Before Crash:
  Epic: executing_wave
  A: completed, B: executing, C: executing, D: pending (depends on B, C)

After Crash (restart from epic-state.json):
  1. Read epic-state.json
  2. Detect B, C in 'executing' state (stale)
  3. Reset B, C to queued (dependencies still met)
  4. Resume: epic.status = ready_to_execute
  5. Recalculate ready tickets: B, C are ready
  6. Spawn B, C sub-agents again
  7. Continue normal execution
```

## Sub-Agent Lifecycle Protocol

The orchestrator spawns ticket-builder sub-agents via the Task tool and coordinates their execution through a standardized lifecycle protocol. This section defines the complete contract between orchestrator and sub-agents for spawn, monitor, and validate phases.

### Phase 1: Spawn

**Tool:** Task tool with subagent_type='general-purpose'

**Prompt Construction:**

The orchestrator constructs the sub-agent prompt by reading execute-ticket.md and injecting ticket-specific context:

```python
# Read execute-ticket.md template
ticket_instructions = Path("/Users/kit/Code/buildspec/claude_files/commands/execute-ticket.md").read_text()

# Inject context
prompt = f"""
{ticket_instructions}

TICKET EXECUTION CONTEXT:
- Ticket Path: {ticket.path}
- Epic Path: {epic_path}
- Base Commit: {base_commit_sha}
- Session ID: {session_id}
- Ticket ID: {ticket.id}

Execute the ticket and return a TicketCompletionReport in JSON format.
"""

# Spawn sub-agent via Task tool
handle = Task.spawn(
    subagent_type='general-purpose',
    prompt=prompt,
    context={'ticket_id': ticket.id, 'epic_id': epic.id}
)
```

**State Updates Before Spawn:**

Before spawning a sub-agent, the orchestrator updates the ticket state:

```python
ticket.status = 'executing'
ticket.started_at = datetime.now(UTC).isoformat()
update_epic_state(state, {ticket.id: ticket})
```

**State Updates After Spawn:**

After successfully spawning, the orchestrator records the sub-agent handle:

```python
# Track sub-agent handle for monitoring
sub_agent_handles[ticket.id] = handle
```

**Error Handling:**

If spawn fails, the ticket is marked as failed:

```python
try:
    handle = Task.spawn(...)
except SpawnError as e:
    ticket.status = 'failed'
    ticket.failure_reason = f'spawn_error: {str(e)}'
    update_epic_state(state, {ticket.id: ticket})
    logger.error(f"Failed to spawn sub-agent for {ticket.id}: {e}")
```

### Phase 2: Monitor

**Strategy:** Passive monitoring (no polling)

The orchestrator uses a passive monitoring approach that waits for Task tool completion rather than actively polling for progress.

**The orchestrator does NOT:**

- Poll git for new commits during execution
- Read ticket files while sub-agent is working
- Check process status continuously
- Make any active checks during execution

**The orchestrator DOES:**

- Wait for Task tool to return (blocking or async)
- Track multiple sub-agent futures simultaneously
- Respond only when sub-agent completes and returns
- Maintain state consistency through completion reports

**Parallel Tracking:**

The orchestrator tracks multiple sub-agents executing in parallel:

```python
# Spawn multiple sub-agents
handles = []
for ticket in ready_tickets[:available_slots]:
    handle = spawn_ticket_sub_agent(ticket, base_commit, session_id)
    handles.append((ticket.id, handle))

# Wait for any completion
completed_ticket_id, completion_report = wait_for_any(handles)
```

This allows the orchestrator to maximize parallelism while respecting concurrency limits (MAX_CONCURRENT_TICKETS).

### Phase 3: Validate Completion Report

When a sub-agent returns, the orchestrator validates the completion report before accepting the ticket as complete.

**TicketCompletionReport Schema:**

The completion report must follow this exact structure:

**Required Fields:**

- `ticket_id` (string): Ticket identifier matching ticket file
- `status` (enum): 'completed' | 'failed' | 'blocked'
- `branch_name` (string): Git branch created (e.g., 'ticket/add-user-auth')
- `base_commit` (string): SHA ticket was branched from
- `final_commit` (string | null): SHA of final commit (null if failed)
- `files_modified` (list[string]): File paths changed during execution
- `test_suite_status` (enum): 'passing' | 'failing' | 'skipped'
- `acceptance_criteria` (list[object]): [{criterion: string, met: boolean}, ...]

**Optional Fields:**

- `failure_reason` (string | null): Description if status='failed'
- `blocking_dependency` (string | null): Ticket ID if status='blocked'
- `warnings` (list[string]): Non-fatal issues encountered

**Example - Success:**

```json
{
  "ticket_id": "add-user-authentication",
  "status": "completed",
  "branch_name": "ticket/add-user-authentication",
  "base_commit": "abc123def456",
  "final_commit": "789ghi012jkl",
  "files_modified": [
    "/Users/kit/Code/buildspec/cli/auth.py",
    "/Users/kit/Code/buildspec/tests/test_auth.py"
  ],
  "test_suite_status": "passing",
  "acceptance_criteria": [
    { "criterion": "User can authenticate with password", "met": true },
    { "criterion": "Invalid credentials rejected", "met": true },
    { "criterion": "Session tokens generated", "met": true }
  ],
  "warnings": []
}
```

**Example - Failure:**

```json
{
  "ticket_id": "add-user-authentication",
  "status": "failed",
  "branch_name": "ticket/add-user-authentication",
  "base_commit": "abc123def456",
  "final_commit": null,
  "files_modified": [],
  "test_suite_status": "failing",
  "acceptance_criteria": [],
  "failure_reason": "Test suite failed: test_password_validation failed with assertion error",
  "warnings": ["Could not import bcrypt library"]
}
```

**Example - Blocked:**

```json
{
  "ticket_id": "add-user-sessions",
  "status": "blocked",
  "branch_name": "ticket/add-user-sessions",
  "base_commit": "abc123def456",
  "final_commit": null,
  "files_modified": [],
  "test_suite_status": "skipped",
  "acceptance_criteria": [],
  "blocking_dependency": "add-user-authentication",
  "failure_reason": "Cannot implement sessions without authentication base"
}
```

### Validation Checks

The orchestrator performs the following validation checks on the completion report:

**Git Verification:**

```bash
# 1. Verify branch exists
git rev-parse --verify refs/heads/$branch_name

# 2. Verify final commit exists (if status=completed)
git rev-parse --verify $final_commit

# 3. Verify commit is on branch
git branch --contains $final_commit | grep $branch_name
```

**Test Suite Validation:**

- If test_suite_status='failing', validation fails (ticket.status='failed')
- If test_suite_status='skipped', accept (ticket may skip tests intentionally)
- If test_suite_status='passing', validation passes

**Acceptance Criteria Validation:**

- Check acceptance_criteria is list of objects with 'criterion' and 'met' fields
- Verify all criteria have boolean 'met' status
- Log any criteria with met=false for reporting

**State Update After Validation:**

```python
# Validation passed
if validation_result.passed:
    ticket.status = 'completed'
    ticket.completed_at = datetime.now(UTC).isoformat()
    ticket.git_info = {
        'branch_name': report['branch_name'],
        'base_commit': report['base_commit'],
        'final_commit': report['final_commit']
    }
    update_epic_state(state, {ticket.id: ticket})

# Validation failed
else:
    ticket.status = 'failed'
    ticket.failure_reason = f'validation_failed: {validation_result.error}'
    update_epic_state(state, {ticket.id: ticket})
```

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

## Epic State File Structure

The orchestrator creates an `artifacts/` directory alongside the epic file and
maintains `artifacts/epic-state.json` to track all progress:

```json
{
  "epic_id": "user-auth-epic",
  "epic_branch": "epic/user-auth-epic",
  "baseline_commit": "ABC123",
  "epic_pr_url": "https://github.com/org/repo/pull/123",
  "status": "in-progress",
  "started_at": "2024-01-01T10:00:00Z",
  "tickets": {
    "auth-base": {
      "path": "path/to/auth-base.md",
      "depends_on": [],
      "critical": true,
      "status": "completed",
      "phase": "completed",
      "git_info": {
        "base_commit": "ABC123",
        "branch_name": "ticket/auth-base",
        "final_commit": "DEF456"
      },
      "started_at": "2024-01-01T10:15:00Z",
      "completed_at": null
    },
    "auth-api": {
      "path": "path/to/auth-api.md",
      "depends_on": ["auth-base"],
      "critical": true,
      "status": "pending",
      "phase": "not-started",
      "git_info": null,
      "started_at": null,
      "completed_at": null,
      "waiting_for": ["auth-base.completed"]
    }
  }
}
```

## Artifacts Structure

```
/project/epics/
├── my-epic.md                   # Epic definition (input)
└── artifacts/
    ├── epic-state.json          # State tracking file
    └── tickets/                 # Ticket execution reports
        ├── user-auth-abc123.md  # Each ticket documents its work
        ├── user-auth-def456.md  # Named with ticket-id and git SHA
        └── payment-api-ghi789.md
```

**Simple approach:**

- Each ticket creates one documentation file when complete
- File named with ticket ID and final commit SHA
- All artifacts committed at epic completion
- `epic-state.json` tracks progress and dependencies

The `epic-state.json` file serves as:

- **Single source of truth** for epic progress
- **Build artifact** showing complete execution history
- **Resume capability** if epic execution is interrupted
- **Dependency tracker** for determining when tickets can start

## Branch Strategy

The orchestrator implements an **epic branch with stacked tickets** approach:

### Epic Branch Structure

```bash
main
└── epic/user-auth-epic (created from main)
    ├── ticket/auth-base (from epic branch)
    ├── ticket/payment-models (from epic branch)
    ├── ticket/auth-api (from auth-base final commit)
    └── ticket/payment-ui (from payment-models final commit)
```

### No Dependencies

```bash
# Tickets branch directly from epic branch baseline
epic/user-auth-epic (ABC123)
├── ticket/auth-base (from ABC123)
├── ticket/payment-models (from ABC123)
```

### Has Dependencies

```bash
# Dependent tickets branch from dependency's final commit
epic/user-auth-epic (ABC123)
├── ticket/auth-base (from ABC123) → final commit: DEF456
│   └── ticket/auth-api (from DEF456) → final commit: GHI789
│       └── ticket/auth-ui (from GHI789)
├── ticket/payment-models (from ABC123) → final commit: JKL012
    └── ticket/payment-ui (from JKL012)
```

### PR Strategy

1. **Epic PR**: `epic/user-auth-epic` → `main` (created at start, draft status)
2. **Ticket PRs**: Sequential numbered PRs targeting epic branch:
   - `[1] Add auth base models` (ticket/auth-base → epic/user-auth-epic)
   - `[2] Implement auth API` (ticket/auth-api → epic/user-auth-epic)
   - `[3] Create auth UI` (ticket/auth-ui → epic/user-auth-epic)
3. **Review Flow**:
   - Numbers indicate required merge order
   - Review and merge ticket PRs in sequence: [1] → [2] → [3]
   - Epic PR provides complete feature overview
   - Epic PR contains all artifacts showing development history

**Key Rules:**

- **Epic isolation**: All epic work happens on epic branch
- **Stacked tickets**: Tickets build on dependencies within epic branch
- **Clean integration**: Epic branch merges to main as complete feature
- **Individual review**: Each ticket gets its own PR for focused review

## Ticket Branch Merging

After all tickets complete, their branches must be merged into the epic branch in dependency order. This creates a single coherent branch with all feature work that can be pushed to remote for human review.

### merge_ticket_branches() Function

**Purpose:** Merge all completed ticket branches into epic branch in dependency order.

**Input:** EpicState with all tickets in terminal states

**Output:** None (merges branches, updates git and state)

**Preconditions:**

- All tickets in terminal state (completed/failed/blocked)
- All completed tickets have git_info with branch_name and final_commit
- Epic branch exists and is clean

**Algorithm:**

```python
def merge_ticket_branches(state: EpicState):
    """
    Merge completed ticket branches into epic branch in dependency order.

    Raises:
        MergeConflictError: If merge conflicts occur
        GitError: If git operations fail
    """
    logger.info(f"Merging ticket branches into {state.epic_branch}...")

    # 1. Switch to epic branch
    result = subprocess.run(
        ['git', 'checkout', state.epic_branch],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise GitError(f"Failed to checkout epic branch: {result.stderr}")

    # 2. Get completed tickets
    completed_tickets = [
        ticket_id for ticket_id, ticket_state in state.tickets.items()
        if ticket_state.status == 'completed'
    ]

    if not completed_tickets:
        logger.warning("No completed tickets to merge")
        return

    logger.info(f"Found {len(completed_tickets)} completed tickets to merge")

    # 3. Calculate merge order (topological sort)
    merge_order = topological_sort(completed_tickets, state)
    logger.info(f"Merge order: {merge_order}")

    # 4. Merge each ticket branch in order
    for ticket_id in merge_order:
        merge_ticket_branch(state, ticket_id)

    # 5. Validate final epic branch state
    validate_epic_branch_after_merge(state, completed_tickets)

    logger.info(f"Successfully merged {len(completed_tickets)} ticket branches")
```

### Topological Sort Implementation

**Purpose:** Calculate dependency-respecting merge order using Kahn's algorithm.

**Implementation:**

```python
def topological_sort(ticket_ids: List[str], state: EpicState) -> List[str]:
    """
    Sort tickets in dependency order (dependencies merge before dependents).

    Uses Kahn's algorithm for topological sorting.

    Args:
        ticket_ids: List of ticket IDs to sort
        state: EpicState with dependency information

    Returns:
        List of ticket IDs in merge order

    Raises:
        CyclicDependencyError: If cycle detected (should not happen if epic initialized correctly)
    """
    # Build adjacency list: dep_id -> [dependent_id, ...]
    graph = {ticket_id: [] for ticket_id in ticket_ids}

    # Build in-degree count: ticket_id -> count of dependencies
    in_degree = {ticket_id: 0 for ticket_id in ticket_ids}

    # Populate graph and in-degree
    for ticket_id in ticket_ids:
        ticket_state = state.tickets[ticket_id]

        for dep_id in ticket_state.depends_on:
            # Only consider dependencies that are also being merged
            if dep_id in ticket_ids:
                graph[dep_id].append(ticket_id)
                in_degree[ticket_id] += 1

    # Kahn's algorithm: start with tickets that have no dependencies
    queue = [tid for tid in ticket_ids if in_degree[tid] == 0]
    sorted_order = []

    while queue:
        # Pop ticket with no remaining dependencies
        current = queue.pop(0)
        sorted_order.append(current)

        # Reduce in-degree for dependents
        for dependent_id in graph[current]:
            in_degree[dependent_id] -= 1

            # If all dependencies now satisfied, add to queue
            if in_degree[dependent_id] == 0:
                queue.append(dependent_id)

    # Verify all tickets sorted (detect cycles)
    if len(sorted_order) != len(ticket_ids):
        unsorted = set(ticket_ids) - set(sorted_order)
        raise CyclicDependencyError(
            f"Cycle detected in dependency graph. Unsorted tickets: {unsorted}"
        )

    return sorted_order
```

### Merge Individual Ticket Branch

**Purpose:** Merge single ticket branch into epic branch.

**Implementation:**

```python
def merge_ticket_branch(state: EpicState, ticket_id: str):
    """
    Merge individual ticket branch into epic branch.

    Uses --no-ff to preserve ticket branch structure in history.

    Raises:
        MergeConflictError: If merge conflicts occur
    """
    ticket_state = state.tickets[ticket_id]
    branch_name = ticket_state.git_info['branch_name']

    logger.info(f"Merging {branch_name} into {state.epic_branch}...")

    # Create merge commit message
    commit_message = f"Merge {branch_name}\n\n{ticket_state.description or ticket_id}"

    # Execute merge with --no-ff
    result = subprocess.run(
        ['git', 'merge', '--no-ff', branch_name, '-m', commit_message],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        # Merge failed (likely conflict)
        logger.error(f"Merge failed for {branch_name}: {result.stderr}")

        # Abort merge to leave repository clean
        subprocess.run(['git', 'merge', '--abort'], capture_output=True)

        # Fail epic with merge conflict error
        raise MergeConflictError(
            f"Merge conflict while merging {branch_name} into {state.epic_branch}. "
            f"Manual resolution required. Merge output:\n{result.stderr}"
        )

    # Merge succeeded
    logger.info(f"Successfully merged {branch_name}")

    # Get merge commit SHA
    merge_commit = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True
    ).stdout.strip()

    # Record merge in state (optional tracking)
    ticket_state.merge_commit = merge_commit
```

### Validate Epic Branch After Merge

**Purpose:** Verify all ticket commits are present in epic branch.

**Implementation:**

```python
def validate_epic_branch_after_merge(state: EpicState, completed_ticket_ids: List[str]):
    """
    Validate epic branch contains all ticket commits.

    Verifies each ticket's final_commit is an ancestor of epic HEAD.

    Raises:
        ValidationError: If any ticket commit missing from epic branch
    """
    logger.info("Validating epic branch contains all ticket commits...")

    epic_head = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True
    ).stdout.strip()

    logger.info(f"Epic branch HEAD: {epic_head[:8]}")

    # Check each ticket's final commit is in epic branch
    missing_commits = []

    for ticket_id in completed_ticket_ids:
        ticket_state = state.tickets[ticket_id]
        final_commit = ticket_state.git_info['final_commit']

        # Check if final_commit is ancestor of epic HEAD
        result = subprocess.run(
            ['git', 'merge-base', '--is-ancestor', final_commit, epic_head],
            capture_output=True
        )

        if result.returncode != 0:
            # Commit is NOT an ancestor (missing from epic branch)
            missing_commits.append((ticket_id, final_commit))
            logger.error(f"Ticket {ticket_id} final_commit {final_commit[:8]} missing from epic branch")

    if missing_commits:
        raise ValidationError(
            f"Epic branch missing commits from tickets: {missing_commits}"
        )

    # Count commits from baseline to HEAD
    commit_count = subprocess.run(
        ['git', 'rev-list', '--count', f'{state.baseline_commit}..HEAD'],
        capture_output=True,
        text=True
    ).stdout.strip()

    logger.info(f"Epic branch has {commit_count} commits from baseline")
    logger.info("Epic branch validation passed: all ticket commits present")
```

### Merge Examples

**Example 1: Linear Chain**

```python
# Tickets: A → B → C
# Dependencies: B depends on A, C depends on B

completed_tickets = ['add-auth-base', 'add-sessions', 'add-permissions']
merge_order = topological_sort(completed_tickets, state)
# Result: ['add-auth-base', 'add-sessions', 'add-permissions']

# Merge execution:
# 1. Merge ticket/add-auth-base
# 2. Merge ticket/add-sessions
# 3. Merge ticket/add-permissions

# Final epic branch:
# baseline → A1 → A2 → (merge A) → B1 → (merge B) → C1 → (merge C)
```

**Example 2: Diamond Dependency**

```python
# Tickets: A, B depends on A, C depends on A, D depends on B and C

completed_tickets = ['base', 'variant-1', 'variant-2', 'combine']
merge_order = topological_sort(completed_tickets, state)
# Result: ['base', 'variant-1', 'variant-2', 'combine']
# (variant-1 and variant-2 can be in either order since both depend only on base)

# Merge execution:
# 1. Merge ticket/base
# 2. Merge ticket/variant-1
# 3. Merge ticket/variant-2
# 4. Merge ticket/combine
```

**Example 3: Merge Conflict**

```python
# Tickets A and B both modify same file

# A completes: modifies auth.py line 10
# B completes: modifies auth.py line 10 (conflict!)

# Merge execution:
# 1. Merge ticket/A → success
# 2. Merge ticket/B → CONFLICT
#    - Git detects conflict in auth.py
#    - merge_ticket_branch() catches failure
#    - Executes: git merge --abort
#    - Raises: MergeConflictError
#    - Epic status = 'failed'
#    - failure_reason = 'merge_conflict: ticket/B'
```

### Integration with Existing Code

Ticket branch merging integrates with:
- Epic-state.json for ticket metadata and git_info
- Git repository for merge operations
- Topological sort for dependency ordering
- Validation checks for merge success

## Remote Push Logic

### push_epic_branch() Function

**Purpose:** Push epic branch to remote if remote exists.

**Input:** Epic branch name (e.g., "epic/user-authentication")

**Output:** Boolean (true if pushed, false if no remote or push failed)

**Design:** Project-agnostic (no assumptions about main branch, PR workflow, or remote structure)

**Algorithm:**

```python
def push_epic_branch(state: EpicState) -> bool:
    """
    Push epic branch to remote if remote exists.

    Returns True if pushed successfully, False otherwise.

    Does NOT fail epic on push failure (marks partial_success instead).
    """
    epic_branch = state.epic_branch

    logger.info(f"Checking for git remote to push {epic_branch}...")

    # 1. Check if remote exists
    has_remote, remote_url = check_remote_exists()

    if not has_remote:
        logger.info("No git remote configured. Skipping push.")
        state.epic_pr_url = None
        update_epic_state(state, {})
        return False

    logger.info(f"Git remote found: {remote_url}. Pushing {epic_branch}...")

    # 2. Push epic branch with upstream tracking
    push_result = execute_push(epic_branch, remote_url)

    # 3. Update state with push result
    update_state_after_push(state, push_result)

    return push_result.success
```

### Check Remote Exists

**Purpose:** Detect if git remote is configured.

**Implementation:**

```python
def check_remote_exists() -> Tuple[bool, Optional[str]]:
    """
    Check if git remote exists.

    Returns:
        (has_remote, remote_url) tuple
    """
    result = subprocess.run(
        ['git', 'remote', '-v'],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        # No remote or git error
        logger.warning(f"git remote command failed: {result.stderr}")
        return (False, None)

    output = result.stdout.strip()

    if not output:
        # No remotes configured
        logger.info("No git remotes configured")
        return (False, None)

    # Parse remote URL (first remote, fetch URL)
    lines = output.split('\n')
    for line in lines:
        if '(fetch)' in line:
            parts = line.split()
            if len(parts) >= 2:
                remote_name = parts[0]  # Usually 'origin'
                remote_url = parts[1]
                logger.info(f"Found remote '{remote_name}': {remote_url}")
                return (True, remote_url)

    # Remote exists but couldn't parse
    return (True, "unknown")
```

### Execute Push

**Purpose:** Push epic branch to remote with upstream tracking.

**Implementation:**

```python
def execute_push(epic_branch: str, remote_url: str) -> PushResult:
    """
    Push epic branch to remote.

    Uses -u flag to set upstream tracking branch.

    Returns PushResult with success status and details.
    """
    # Attempt push with upstream tracking
    result = subprocess.run(
        ['git', 'push', '-u', 'origin', epic_branch],
        capture_output=True,
        text=True,
        timeout=60  # 60 second timeout for network operations
    )

    if result.returncode == 0:
        # Push succeeded
        logger.info(f"Successfully pushed {epic_branch} to remote")
        logger.debug(f"Push output: {result.stdout}")

        return PushResult(
            success=True,
            remote_url=remote_url,
            branch=epic_branch,
            error=None
        )

    else:
        # Push failed
        error_msg = result.stderr.strip()
        logger.error(f"Push failed for {epic_branch}: {error_msg}")

        # Categorize failure
        failure_type = categorize_push_failure(error_msg)

        return PushResult(
            success=False,
            remote_url=remote_url,
            branch=epic_branch,
            error=error_msg,
            failure_type=failure_type
        )
```

### Categorize Push Failure

**Purpose:** Identify type of push failure for better error messages.

**Implementation:**

```python
def categorize_push_failure(error_msg: str) -> str:
    """
    Categorize push failure based on error message.

    Returns failure type: 'authentication', 'network', 'rejected', 'unknown'
    """
    error_lower = error_msg.lower()

    # Authentication failures
    if any(keyword in error_lower for keyword in [
        'authentication', 'permission denied', 'could not read',
        'invalid credentials', 'access denied'
    ]):
        return 'authentication'

    # Network failures
    if any(keyword in error_lower for keyword in [
        'could not resolve host', 'connection refused', 'network',
        'timeout', 'failed to connect'
    ]):
        return 'network'

    # Remote rejection (e.g., protected branch, force push required)
    if any(keyword in error_lower for keyword in [
        'rejected', 'protected branch', 'non-fast-forward',
        'updates were rejected'
    ]):
        return 'rejected'

    return 'unknown'
```

### Update State After Push

**Purpose:** Record push result in epic-state.json.

**Implementation:**

```python
def update_state_after_push(state: EpicState, push_result: PushResult):
    """
    Update epic state with push result.

    If push succeeded: record remote URL
    If push failed: mark epic as partial_success
    """
    push_timestamp = datetime.now(UTC).isoformat()

    if push_result.success:
        # Push succeeded
        state.epic_pr_url = None  # No PR created (project-agnostic)
        state.push_status = 'pushed'
        state.push_timestamp = push_timestamp
        state.remote_url = push_result.remote_url

        logger.info(f"Epic branch pushed successfully at {push_timestamp}")

    else:
        # Push failed (mark partial_success)
        state.status = 'partial_success'
        state.failure_reason = f'push_failed_{push_result.failure_type}: {push_result.error}'
        state.push_status = 'failed'
        state.push_timestamp = push_timestamp

        logger.warning(
            f"Epic marked as partial_success due to push failure. "
            f"All tickets completed locally, but epic branch not pushed to remote."
        )

    update_epic_state(state, {})
```

### Push Examples

**Example 1: Successful Push**

```python
# Remote exists, push succeeds
has_remote = True
push_result = execute_push('epic/user-auth', 'git@github.com:user/repo.git')
# push_result.success = True

# State updates:
# state.epic_pr_url = None
# state.push_status = 'pushed'
# state.status = 'completed'

# Output: "Successfully pushed epic/user-auth to remote"
```

**Example 2: No Remote**

```python
# No remote configured
has_remote = False

push_epic_branch(state)
# Returns: False

# State updates:
# state.epic_pr_url = None
# state.push_status = 'skipped'
# state.status = 'completed'

# Output: "No git remote configured. Skipping push."
```

**Example 3: Authentication Failure**

```python
# Remote exists, push fails (authentication)
has_remote = True
push_result = execute_push('epic/user-auth', 'git@github.com:user/repo.git')
# push_result.success = False
# push_result.failure_type = 'authentication'
# push_result.error = "Permission denied (publickey)"

# State updates:
# state.status = 'partial_success'
# state.failure_reason = 'push_failed_authentication: Permission denied (publickey)'
# state.push_status = 'failed'

# Output: "Push failed: authentication error. Epic marked as partial_success."
```

**Example 4: Network Failure**

```python
# Remote exists, push fails (network)
push_result.failure_type = 'network'
push_result.error = "Could not resolve host: github.com"

# State updates:
# state.status = 'partial_success'
# state.failure_reason = 'push_failed_network: Could not resolve host'
# state.push_status = 'failed'

# Output: "Push failed: network error. All work completed locally."
```

### Project-Agnostic Design

**No PR Creation:**

- Function does NOT create pull requests
- No assumptions about GitHub, GitLab, Bitbucket
- No assumptions about main/master branch
- Epic branch on remote is the deliverable (humans create PR if needed)

**No Main Branch Assumptions:**

- Does NOT merge epic branch into main
- Does NOT push to main branch
- Does NOT assume main branch exists or is named 'main'/'master'

**Graceful Degradation:**

- If no remote: epic completes successfully (work done locally)
- If push fails: epic marked partial_success (work preserved locally)
- Never fail epic due to push issues (push is optional final step)

## Epic File Format

The epic file should contain a TOML configuration block defining the ticket
dependency graph:

### TOML Format (Embedded in Markdown)

````markdown
# Epic: [Epic Title]

## Epic Summary

[Epic planning content...]

## Epic Configuration

```toml
[epic]
name = "[Epic Title]"
description = "[Concise epic description for orchestrator]"
rollback_on_failure = true

acceptance_criteria = [
  "[Primary functional requirement]",
  "[Performance/quality requirement]",
  "[Integration requirement]",
  "[User experience requirement]"
]

# Example tickets - structure yours however makes sense for your project
# You might organize by: feature area, technical layer, team, priority, etc.

[[tickets]]
id = "your-first-task"  # Use meaningful names
path = "tasks/your-first-task.md"
depends_on = []  # No dependencies = can run immediately
critical = true  # Epic fails if this fails

[[tickets]]
id = "your-second-task"
path = "tasks/your-second-task.md"
depends_on = ["your-first-task"]  # Runs after first task
critical = false  # Epic continues even if this fails

# Add as many tickets as needed with any dependency structure
# The orchestrator handles any valid dependency graph
```
````

[Rest of epic planning content...]

```

## Execution Flow

When you run this command from main Claude:

1. **Spawn Orchestrator Agent**: Creates an autonomous agent to manage the epic
2. **Parse Epic File**: Agent reads and validates the epic structure
3. **Build Execution Plan**: Agent determines parallel execution opportunities
4. **Execute Tickets**: Agent spawns sub-agents for ticket execution
5. **Monitor Progress**: Agent tracks completion and manages dependencies
6. **Report Results**: Agent returns epic execution report

## Implementation

When this command is invoked, main Claude will:

1. **Verify the epic file exists** at the provided path
2. **Spawn a Task agent** with type "general-purpose"
3. **Pass the epic file path** and orchestration instructions to the agent
4. **Return the agent's comprehensive report** when complete

### Task Agent Instructions

Main Claude will provide these exact instructions to the Task agent:

```

You are orchestrating an epic containing multiple coding tickets. Your task is
to:

0. Run pre-flight validation:
   - Execute: bash ~/.claude/scripts/validate-epic.sh [epic-file-path]
   - If validation fails, STOP and report the validation errors
   - Only proceed if all pre-flight checks pass

1. Read and parse the epic file at: [epic-file-path]
   - Extract all ticket definitions
   - Understand dependency relationships
   - Identify critical vs non-critical tickets
   - Note acceptance criteria

2. Initialize epic branch and state tracking:
   - Create epic branch from current HEAD: epic/<epic-name>
   - Push epic branch to GitHub: git push -u origin epic/<epic-name>
   - Create GitHub PR: epic/<epic-name> → main (draft status)
   - Switch to epic branch for all subsequent work
   - Create artifacts/ directory at the same level as the epic file
   - Record the epic branch HEAD commit SHA as baseline
   - Create epic-state.json in artifacts/ directory to track all progress
   - Initialize each ticket with status "pending" and phase "not-started"
   - Save dependency graph and epic branch info to the state file

3. Create an execution plan:
   - Identify which tickets can run in parallel
   - Determine execution order based on dependencies
   - Create a visual representation of the execution flow

4. State file management:
   - Read/write epic-state.json from artifacts/ directory
   - Store ticket reports as flat files in artifacts/tickets/ directory
   - epic-state.json structure: { "epic_id": "epic-name", "baseline_commit":
     "abc123", "status": "in-progress", "started_at": "2024-01-01T10:00:00Z",
     "tickets": { "ticket-id": { "path": "path/to/ticket.md", "depends_on":
     ["other-ticket-id"], "critical": true, "status":
     "pending|in-progress|failed|completed", "phase": "not-started|completed",
     "git_info": { "base_commit": "abc123", "branch_name": "ticket/name",
     "final_commit": "def456" }, "started_at": "timestamp", "completed_at":
     "timestamp" } } }

5. Execution workflow for each ticket:
   - Simplified workflow: Execute ticket → phase becomes "completed"
   - No separate review/improvement phases in epic orchestration
   - Each ticket is responsible for its own quality assurance

6. Task launching with base commit calculation:

   For tickets in "not-started" phase:
   - Determine base commit:
     - No dependencies: use epic baseline_commit (epic branch HEAD)
     - Single dependency: use dependency's git_info.final_commit
     - Multiple dependencies: use most recent final_commit among dependencies
   - Launch: /execute-ticket <ticket-path> --base-commit <calculated-sha>
   - After completion: Update state with git_info and set phase to "completed"
   - Ticket will self-document to artifacts/tickets/<ticket-id>-<short-sha>.md

7. Parallel execution rules:
   - Tickets can run in parallel if their dependencies are in "completed" phase
   - Multiple tickets in different phases can run simultaneously
   - Track all running Tasks and wait for completion before updating state

8. Handle failures:
   - If a critical ticket fails, stop the epic execution
   - If a non-critical ticket fails, continue with other tickets
   - Update state file with failure information
   - Document all failures in the final report

9. Generate comprehensive report and finalize artifacts:
   - Epic execution summary (success/partial/failed)
   - Execution timeline showing parallel execution
   - Status of each ticket:
     - ✅ Completed successfully
     - ❌ Failed (with error details)
     - ⏭️ Skipped (due to dependency failure)
   - Acceptance criteria checklist
   - Total execution time
   - Recommendations for follow-up actions (refactoring, additional tickets,
     etc.)

10. Finalize epic and create PRs:

- Add all artifacts/ directory contents to git
- Commit with message: "Add artifacts for <epic-name>"
- Push epic branch with artifacts: git push origin epic/<epic-name>
- Determine merge order based on dependency graph (topological sort)
- Create individual ticket PRs targeting epic branch:
  - PR titles: "[1] Add auth base models", "[2] Implement auth API", "[3] Create
    auth UI"
  - Command: gh pr create --base epic/<epic-name> --head ticket/<ticket-name>
    --title "[<sequence>] <ticket-title>"
- Update epic PR from draft to ready for review
- Epic PR description includes summary of all tickets with merge order

IMPORTANT:

- Create artifacts/ directory alongside the epic file for all build outputs
- Maintain artifacts/epic-state.json as single source of truth for all progress
- Save all ticket artifacts as flat files:
  artifacts/tickets/<ticket-id>-<short-sha>.md
- Keep all artifacts LOCAL during epic execution (don't commit until epic
  complete)
- At epic completion, commit all artifacts together with message "Add artifacts
  for <epic-name>"
- Update state file after EVERY Task completion
- Execute tickets in parallel whenever dependencies allow
- Stop immediately if a critical ticket fails
- Track ticket phases: not-started → completed (simplified workflow)
- Each ticket goes through: execute → done (all quality checks included)
- Code review is available as a separate command, not integrated into execution
- Only start new tickets when their dependencies are in "completed" phase
- Determine branch base commit from dependency final commits (for stacked
  branches)
- The epic succeeds only when ALL critical tickets reach "completed" phase
- Provide epic-state.json as build artifact showing full execution history

PARALLEL EXECUTION RULES:

- Tickets with no dependencies start immediately in parallel
- Tickets with the same dependencies run in parallel once dependencies are met
- Use multiple Task agents simultaneously for parallel execution
- Monitor all parallel agents and wait for completion before proceeding

Example execution for tickets A, B (depends on A), C (depends on A), D (depends
on B and C):

- Phase 1: Execute A
- Phase 2: Execute B and C in parallel (both depend only on A)
- Phase 3: Execute D (after both B and C complete)

````

## Options

- `--dry-run`: Show execution plan without running tickets
- `--continue-on-failure`: Continue even if critical tickets fail
- `--no-parallel`: Execute tickets sequentially (useful for debugging)
- `--verbose`: Show detailed progress for each ticket

## Example Epic Files

### Simple Sequential Epic
```yaml
epic: "Add User Profile Feature"
tickets:
  - id: create-profile-model
    path: tickets/profile-model.md
    depends_on: []
  - id: create-profile-api
    path: tickets/profile-api.md
    depends_on: [create-profile-model]
  - id: create-profile-ui
    path: tickets/profile-ui.md
    depends_on: [create-profile-api]
````

### Complex Parallel Epic

```yaml
epic: "Payment System Integration"
tickets:
  # Foundation layer - runs first
  - id: payment-models
    path: tickets/payment-models.md
    depends_on: []
    critical: true

  # API layer - these can run in parallel
  - id: stripe-integration
    path: tickets/stripe-integration.md
    depends_on: [payment-models]
    critical: true
  - id: paypal-integration
    path: tickets/paypal-integration.md
    depends_on: [payment-models]
    critical: false
  - id: invoice-api
    path: tickets/invoice-api.md
    depends_on: [payment-models]
    critical: true

  # UI layer - depends on APIs
  - id: payment-ui
    path: tickets/payment-ui.md
    depends_on: [stripe-integration, invoice-api]
    critical: true

  # Final integration
  - id: payment-webhooks
    path: tickets/payment-webhooks.md
    depends_on: [stripe-integration, paypal-integration]
    critical: true
```

## Error Handling

The orchestrator handles:

- Missing or invalid epic files
- Circular dependencies in tickets
- Failed ticket execution
- Test suite failures
- Parallel execution conflicts
- Resource contention

## Best Practices

1. **Design epics carefully** - Consider dependencies and parallel opportunities
2. **Mark critical tickets appropriately** - Only mark truly blocking tickets as
   critical
3. **Keep tickets focused** - Smaller tickets are easier to parallelize
4. **Test incrementally** - Use phase validation to catch issues early
5. **Plan for rollback** - Ensure tickets can be reverted if needed

## Monitoring

During execution, the orchestrator provides:

- Real-time status updates
- Parallel execution visualization
- Failure notifications
- Progress percentage
- Estimated time remaining

## Related Commands

- `/execute-ticket`: Execute a single ticket (used internally by execute-epic)
- `/code-review`: Standalone code review command (not integrated into epic
  execution)
- `/validate-epic`: Check epic file for issues before execution
- `/visualize-epic`: Generate a dependency graph for the epic
- `/epic-status`: Check status of a running epic execution
