# update-execute-epic-state-machine

## Description

Add formal state machine documentation to the execute-epic.md command file,
establishing the foundational state machine that all other coordination tickets
depend on.

The execute-epic orchestrator currently lacks a formal state machine definition,
leading to ambiguous state transitions and inconsistent state management. This
ticket documents the complete epic-level and ticket-level states with explicit
transition rules, conditions, and consistency requirements.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. The state machine is the foundation that
enables deterministic orchestration, error recovery, and resumability after
crashes.

**Architecture:** The orchestrator uses a state machine pattern with explicit
states and transitions documented in execute-epic.md. Epic-state.json serves as
the single source of truth for coordination state, enabling resumability and
explicit state tracking.

## Story

As a **buildspec orchestrator developer**, I need **formal state machine
documentation in execute-epic.md** so that **all state transitions are
deterministic, explicit, and resumable after orchestrator crashes**.

## Acceptance Criteria

### Core Requirements

- Execute-epic.md contains complete state machine documentation with all epic
  and ticket states
- All valid epic-level state transitions are documented with trigger conditions
- All valid ticket-level state transitions are documented with trigger
  conditions
- State update protocol specifies when and how to update epic-state.json
  atomically
- Documentation includes examples of state transitions during epic execution

### Epic-Level States

Document the following epic states in execute-epic.md:

- **initializing**: Creating epic branch, artifacts directory, baseline state
- **ready_to_execute**: Waiting to spawn next wave of tickets
- **executing_wave**: One or more sub-agents actively executing
- **completed**: All tickets complete, finalizing artifacts
- **failed**: Critical ticket failed, rollback if configured
- **rolled_back**: Changes reverted, epic branch deleted
- **partial_success**: Rollback disabled, preserving completed work

### Ticket-Level States

Document the following ticket states:

- **pending**: Waiting for dependencies
- **queued**: Dependencies met, ready to spawn
- **executing**: Sub-agent actively working
- **validating**: Orchestrator validating completion report
- **completed**: Ticket work complete, artifacts recorded
- **failed**: Execution or validation failed
- **blocked**: Cannot execute due to dependency failure

### Error Handling

- State transitions must handle failure conditions explicitly
- Invalid transitions must be documented and prevented
- Crash recovery procedures must reference state machine for restart logic

### Observability

- All state transitions must include timestamp tracking requirements
- Previous state tracking for debugging and audit trail
- State machine diagram or table showing all valid transitions

## Integration Points

### Upstream Dependencies

None - this is a foundational ticket

### Downstream Dependencies

- **implement-concurrency-control**: Uses state definitions for ready ticket
  calculation
- **define-sub-agent-lifecycle-protocol**: Uses states for
  spawn/monitor/validate workflow
- **implement-completion-report-validation**: Uses validating state during
  report checks
- **add-error-recovery-workflows**: Uses state machine for rollback and recovery
  procedures
- **implement-base-commit-calculation**: Uses completed state to access git_info
- **define-git-workflow-strategy**: Uses state machine for git operation
  checkpoints
- **add-atomic-state-updates**: Implements atomic writes for state transitions
- **add-wave-execution-algorithm**: Core loop implements state machine
  transitions

## Current vs New Flow

### BEFORE (Current State)

The execute-epic.md file has vague instructions like "spawn sub-agents" and
"track progress" without explicit state definitions. State transitions are
implicit and not documented, making error recovery and resumability unclear.

### AFTER (This Ticket)

Execute-epic.md contains a comprehensive state machine section with:

- Explicit epic-level and ticket-level state definitions
- State transition table showing valid transitions, conditions, and actions
- State update protocol specifying atomic epic-state.json updates
- Examples showing state flow during normal execution and failure scenarios
- Crash recovery procedures that reference state machine for restart logic

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-epic.md`

Add a new "State Machine" section after the "Overview" section with the
following structure:

```markdown
## State Machine

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
```

### Implementation Details

1. **Add State Machine Section:** Insert comprehensive state machine
   documentation into execute-epic.md after the Overview section

2. **State Transition Table:** Create tables showing all valid transitions with
   conditions and actions

3. **Update Protocol:** Document atomic update requirements for epic-state.json

4. **Recovery Procedures:** Explain how to use state machine for crash recovery

5. **Examples:** Include example state flows for:
   - Normal execution with 3 tickets (no dependencies)
   - Diamond dependency graph execution
   - Critical ticket failure with rollback
   - Non-critical ticket failure with partial success
   - Orchestrator crash and recovery

### Integration with Existing Code

The state machine documentation integrates with:

- `epic-state.json` schema (EpicState and TicketState interfaces)
- `calculate_ready_tickets()` function (checks ticket states)
- `spawn_ticket_sub_agent()` function (transitions queued → executing)
- `validate_completion_report()` function (transitions validating →
  completed/failed)
- `execute_rollback()` function (transitions failed → rolled_back)

## Error Handling Strategy

- **Invalid State Transitions:** Document which transitions are prohibited and
  why
- **Concurrent Updates:** Specify atomic write requirements to prevent
  corruption
- **Missing State:** If epic-state.json is corrupted, fail with clear error
  message
- **State Inconsistency:** Document validation checks to detect inconsistent
  state

## Testing Strategy

### Validation Tests

1. **State Machine Completeness:**
   - Verify all epic states have documented transitions
   - Verify all ticket states have documented transitions
   - Check for unreachable states

2. **Documentation Quality:**
   - Verify examples match state machine rules
   - Check transition conditions are unambiguous
   - Ensure recovery procedures are complete

3. **Integration with Code:**
   - Read updated execute-epic.md
   - Verify state machine matches EpicState/TicketState schema
   - Confirm examples are accurate

### Test Commands

```bash
# Read and review state machine documentation
cat /Users/kit/Code/buildspec/claude_files/commands/execute-epic.md | grep -A 100 "State Machine"

# Verify state machine is complete (manual review)
# Check: all states documented, all transitions listed, examples provided
```

## Dependencies

None - this is a foundational ticket

## Coordination Role

Defines the state machine foundation that all other tickets use for state
transitions and coordination. The state machine establishes the contract for:

- Valid epic and ticket states
- Permitted state transitions
- State update protocol
- Crash recovery procedures

All subsequent tickets reference this state machine for their implementation.
