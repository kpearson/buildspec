# implement-concurrency-control

## Description

Implement concurrency control logic for parallel ticket execution in the
execute-epic orchestrator.

The orchestrator needs to manage parallel sub-agent execution with resource
limits. This ticket implements the MAX_CONCURRENT_TICKETS limit (3 concurrent
sub-agents) and the algorithm for calculating which tickets are ready to execute
based on dependency completion and available concurrency slots.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. Concurrency control ensures the orchestrator
doesn't spawn too many sub-agents simultaneously, balancing parallel execution
with resource constraints.

**Architecture:** Uses wave-based execution pattern with
MAX_CONCURRENT_TICKETS=3 limit. The calculate_ready_tickets() function evaluates
dependency graph to find tickets ready for execution, while concurrency slot
calculation prevents exceeding resource limits.

## Story

As a **buildspec orchestrator**, I need **concurrency control with
MAX_CONCURRENT_TICKETS limit** so that **I can execute tickets in parallel
without overwhelming system resources or spawning too many Claude sub-agents
simultaneously**.

## Acceptance Criteria

### Core Requirements

- MAX_CONCURRENT_TICKETS constant is defined and documented (value: 3)
- calculate_ready_tickets() function correctly identifies tickets with satisfied
  dependencies
- Concurrency slot calculation prevents spawning more than
  MAX_CONCURRENT_TICKETS sub-agents
- Prioritization logic ensures critical tickets and longer dependency chains
  execute first
- Documentation in execute-epic.md explains concurrency control algorithm

### Concurrency Limit

- MAX_CONCURRENT_TICKETS = 3 (documented rationale: balance parallel execution
  with resource limits)
- Never spawn more than 3 sub-agents concurrently
- Count tickets in 'executing' or 'validating' states toward concurrency limit
- Available slots = MAX_CONCURRENT_TICKETS - (executing_count +
  validating_count)

### Ready Ticket Calculation

- Identify all tickets with status='pending'
- For each pending ticket, check if all depends_on tickets are in
  status='completed'
- Return list of tickets where all dependencies are satisfied
- Exclude tickets where any dependency is in status='failed' (these become
  'blocked')

### Prioritization Logic

Sort ready tickets by:

1. **Critical first:** Tickets with critical=true come before critical=false
2. **Dependency depth:** Longer dependency chains execute before shorter ones
3. **Stable sort:** Preserve original order for tickets with equal priority

Dependency depth = length of longest chain from ticket to leaf dependency

### Error Handling

- Handle circular dependencies (should be caught during epic initialization)
- Handle missing dependency references gracefully
- Validate epic-state.json schema before reading

## Integration Points

### Upstream Dependencies

- **update-execute-epic-state-machine**: Provides ticket state definitions
  (pending, executing, validating, completed, failed, blocked)

### Downstream Dependencies

- **add-wave-execution-algorithm**: Uses calculate_ready_tickets() to determine
  which tickets to spawn in each wave

## Current vs New Flow

### BEFORE (Current State)

Execute-epic.md has vague instructions about parallel execution but no specific
concurrency limits or algorithm for determining ready tickets.

### AFTER (This Ticket)

Execute-epic.md contains:

- MAX_CONCURRENT_TICKETS = 3 constant with documented rationale
- calculate_ready_tickets() algorithm specification
- Concurrency slot calculation formula
- Prioritization algorithm for ready tickets
- Examples showing wave execution with concurrency limits

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-epic.md`

Add a new "Concurrency Control" section:

````markdown
## Concurrency Control

### Maximum Concurrent Tickets

**Constant:** MAX_CONCURRENT_TICKETS = 3

**Rationale:** Balances parallel execution benefits with system resource limits.
Running more than 3 Claude sub-agents simultaneously can:

- Consume excessive memory and CPU
- Create too many concurrent git operations
- Reduce individual sub-agent performance
- Make error debugging harder

### Concurrency Slot Calculation

Before spawning new sub-agents, calculate available concurrency slots:

```python
executing_count = count tickets with status in ['executing', 'validating']
available_slots = MAX_CONCURRENT_TICKETS - executing_count

if available_slots > 0:
    # Can spawn up to available_slots more sub-agents
    spawn_count = min(available_slots, len(ready_tickets))
else:
    # Wait for at least one sub-agent to complete
    wait_for_any_completion()
```
````

### calculate_ready_tickets() Algorithm

**Purpose:** Determine which tickets are ready to execute based on dependency
completion.

**Input:** EpicState object with all tickets and their current states

**Output:** Sorted list of Ticket objects ready for execution

**Algorithm:**

```python
def calculate_ready_tickets(state: EpicState) -> List[Ticket]:
    ready_tickets = []

    for ticket_id, ticket_state in state.tickets.items():
        # Only consider pending tickets
        if ticket_state.status != 'pending':
            continue

        # Check if all dependencies are completed
        all_deps_met = True
        any_dep_failed = False

        for dep_id in ticket_state.depends_on:
            dep_state = state.tickets[dep_id]

            if dep_state.status != 'completed':
                all_deps_met = False

            if dep_state.status == 'failed':
                any_dep_failed = True
                break

        # If any dependency failed, mark ticket as blocked
        if any_dep_failed:
            ticket_state.status = 'blocked'
            ticket_state.blocking_dependency = dep_id
            update_epic_state(state, {ticket_id: ticket_state})
            continue

        # If all dependencies met, ticket is ready
        if all_deps_met:
            ready_tickets.append(ticket_state)

    # Prioritize ready tickets
    return prioritize_tickets(ready_tickets)
```

### Prioritization Algorithm

**Purpose:** Sort ready tickets to execute critical tickets and long dependency
chains first.

**Algorithm:**

```python
def prioritize_tickets(tickets: List[Ticket]) -> List[Ticket]:
    def priority_key(ticket: Ticket) -> tuple:
        # Primary sort: critical tickets first (critical=True sorts before False)
        critical_priority = 0 if ticket.critical else 1

        # Secondary sort: dependency depth (longer chains first, so negate depth)
        dep_depth = calculate_dependency_depth(ticket)

        # Return tuple for sorting (lower values sort first)
        return (critical_priority, -dep_depth)

    return sorted(tickets, key=priority_key)

def calculate_dependency_depth(ticket: Ticket) -> int:
    """Calculate longest chain from ticket to leaf dependency."""
    if not ticket.depends_on:
        return 0

    max_depth = 0
    for dep_id in ticket.depends_on:
        dep_ticket = state.tickets[dep_id]
        dep_depth = calculate_dependency_depth(dep_ticket)
        max_depth = max(max_depth, dep_depth)

    return max_depth + 1
```

### Example: Wave Execution with Concurrency Control

**Epic with 7 tickets:**

- A (critical, no dependencies)
- B (non-critical, no dependencies)
- C (critical, depends on A)
- D (non-critical, depends on A)
- E (critical, depends on A, B)
- F (non-critical, depends on C)
- G (non-critical, depends on D, E)

**Wave 1:** (all pending, no completed dependencies yet)

- Ready tickets: A (critical, depth 0), B (non-critical, depth 0)
- Prioritization: A (critical) before B (non-critical)
- Spawn: A, B (2 of 3 slots used)

**Wave 2:** (A completed)

- Ready tickets: C (critical, depth 1), D (non-critical, depth 1)
- Prioritization: C (critical) before D
- Available slots: 3 - 1 (B still executing) = 2 slots
- Spawn: C, D (all 3 slots now used: B, C, D)

**Wave 3:** (B, C completed)

- Ready tickets: E (critical, depth 2), F (non-critical, depth 2)
- Prioritization: E (critical) before F
- Available slots: 3 - 1 (D still executing) = 2 slots
- Spawn: E, F (all 3 slots used: D, E, F)

**Wave 4:** (D, E, F completed)

- Ready tickets: G (non-critical, depth 3)
- Available slots: 3 - 0 = 3 slots
- Spawn: G

````

### Implementation Details

1. **Add Concurrency Control Section:** Insert after State Machine section in execute-epic.md

2. **Define MAX_CONCURRENT_TICKETS:** Explicitly document the constant and rationale

3. **Document calculate_ready_tickets():** Provide complete algorithm with pseudocode

4. **Document prioritize_tickets():** Explain sorting criteria and algorithm

5. **Provide Examples:** Show wave execution with various dependency graphs

### Integration with Existing Code

The concurrency control algorithm integrates with:
- `EpicState` schema: reads ticket states and depends_on relationships
- `update_epic_state()` function: marks tickets as 'blocked' when dependencies fail
- Wave execution loop: calls calculate_ready_tickets() each iteration
- Spawn logic: respects available_slots when spawning sub-agents

## Error Handling Strategy

- **Circular Dependencies:** Should be detected during epic initialization (not here)
- **Missing Dependency:** If depends_on references non-existent ticket, log error and mark ticket as failed
- **State Corruption:** If epic-state.json is invalid, fail with clear error message
- **Concurrency Violation:** If executing_count exceeds MAX_CONCURRENT_TICKETS, log warning and wait

## Testing Strategy

### Validation Tests

1. **Ready Ticket Calculation:**
   - Test with no dependencies (all tickets ready)
   - Test with linear dependency chain (one ticket ready at a time)
   - Test with diamond dependencies (multiple tickets ready after shared dependency)
   - Test with failed dependency (dependent ticket becomes blocked)

2. **Concurrency Limit:**
   - Verify never more than 3 tickets in executing/validating states
   - Test available slot calculation
   - Test spawn count capping

3. **Prioritization:**
   - Critical tickets execute before non-critical
   - Longer dependency chains execute before shorter
   - Stable sort preserves order for equal priority

### Test Commands

```bash
# Run integration tests for concurrency control
uv run pytest tests/integration/test_execute_epic.py::test_concurrency_control -v

# Test ready ticket calculation
uv run pytest tests/unit/test_concurrency.py::test_calculate_ready_tickets -v

# Test prioritization logic
uv run pytest tests/unit/test_concurrency.py::test_prioritize_tickets -v
````

## Dependencies

- **update-execute-epic-state-machine**: Provides ticket state definitions

## Coordination Role

Provides ready ticket calculation that the wave execution algorithm depends on.
The concurrency control ensures resource limits are respected while maximizing
parallel execution efficiency.
