# add-atomic-state-updates

## Description

Implement atomic epic-state.json updates with JSON schema validation to prevent
corruption.

Epic-state.json is the single source of truth for orchestration. Updates must be
atomic to prevent corruption from concurrent writes or interruptions, and must
validate schema before writing to catch bugs early.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. Atomic state updates ensure epic-state.json
remains consistent and recoverable even during crashes or failures.

**Architecture:** Uses temp file + atomic rename pattern for writes. JSON schema
validation prevents invalid state. Timestamps track all state changes for
debugging.

## Story

As a **buildspec orchestrator**, I need **atomic state updates with validation**
so that **epic-state.json never becomes corrupted, remains the single source of
truth, and can recover from crashes reliably**.

## Acceptance Criteria

### Core Requirements

- update_epic_state() implements atomic write with temp file + rename
- JSON schema validation prevents invalid state writes
- Timestamps are included with all state changes
- Previous state is preserved for debugging
- Concurrent update safety is ensured
- Execute-epic.md documents complete update algorithm

### Atomic Write Implementation

- Use temp file + atomic rename pattern
- Write to temp file first
- Validate JSON before rename
- Rename temp to epic-state.json (atomic operation)
- Never write directly to epic-state.json

### JSON Schema Validation

- Define JSON schema for epic-state.json structure
- Validate epic-level required fields
- Validate ticket-level required fields
- Fail update if schema validation fails
- Log validation errors for debugging

### Timestamp Tracking

- Include timestamp with every state change
- Update started_at when tickets move to executing
- Update completed_at when tickets move to completed
- Update epic completed_at when epic reaches terminal state

### Previous State Tracking

- Preserve previous status for debugging
- Record state transition history (optional)
- Enable debugging of unexpected state transitions

## Integration Points

### Upstream Dependencies

- **update-execute-epic-state-machine**: Provides EpicState and TicketState
  schema

### Downstream Dependencies

- All tickets that update epic-state.json use this function

## Current vs New Flow

### BEFORE (Current State)

No atomic update mechanism. Direct writes to epic-state.json risk corruption.

### AFTER (This Ticket)

Execute-epic.md contains complete update_epic_state() implementation with:

- Temp file + rename for atomic writes
- JSON schema validation before writing
- Timestamp tracking for all changes
- Previous state preservation
- Examples showing state updates

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-epic.md`

Add "Atomic State Updates" section:

````markdown
## Atomic State Updates

### update_epic_state() Function

**Purpose:** Atomically update epic-state.json with validation.

**Input:**

- `state`: Current EpicState object
- `updates`: Dict of updates to apply

**Output:** None (writes to epic-state.json)

**Guarantees:**

- Atomic write (no partial updates)
- Schema validation (no invalid state)
- Timestamp tracking (audit trail)

**Algorithm:**

```python
def update_epic_state(state: EpicState, updates: dict):
    """
    Atomically update epic-state.json with validation.

    Uses temp file + rename for atomic write.
    Validates JSON schema before writing.

    Args:
        state: Current EpicState object
        updates: Dict of ticket_id -> TicketState updates

    Raises:
        ValidationError: If schema validation fails
        IOError: If file write fails
    """
    # 1. Apply updates to state object
    apply_updates(state, updates)

    # 2. Add timestamp
    state.last_updated = datetime.now(UTC).isoformat()

    # 3. Validate schema
    validate_state_schema(state)

    # 4. Write atomically
    write_state_file_atomic(state)
```
````

### Apply Updates

**Purpose:** Apply updates to state object in memory.

**Implementation:**

```python
def apply_updates(state: EpicState, updates: dict):
    """
    Apply updates to state object.

    Args:
        updates: Dict of ticket_id -> TicketState or epic-level updates
    """
    for key, value in updates.items():
        if key in state.tickets:
            # Ticket-level update
            ticket_state = state.tickets[key]

            # Preserve previous status
            if 'status' in value and value['status'] != ticket_state.status:
                ticket_state.previous_status = ticket_state.status

            # Apply updates to ticket
            for field, field_value in value.items():
                setattr(ticket_state, field, field_value)

        else:
            # Epic-level update
            if key == 'status' and hasattr(state, 'status'):
                # Preserve previous epic status
                state.previous_status = state.status

            setattr(state, key, value)
```

### JSON Schema Validation

**Purpose:** Validate state object matches expected schema.

**Schema Definition:**

```python
EPIC_STATE_SCHEMA = {
    "type": "object",
    "required": ["epic_id", "epic_branch", "baseline_commit", "status", "started_at", "tickets"],
    "properties": {
        "epic_id": {"type": "string"},
        "epic_branch": {"type": "string"},
        "baseline_commit": {"type": "string"},
        "epic_pr_url": {"type": ["string", "null"]},
        "status": {
            "type": "string",
            "enum": ["initializing", "ready_to_execute", "executing_wave",
                     "completed", "failed", "rolled_back", "partial_success"]
        },
        "started_at": {"type": "string", "format": "date-time"},
        "completed_at": {"type": ["string", "null"], "format": "date-time"},
        "failure_reason": {"type": ["string", "null"]},
        "last_updated": {"type": "string", "format": "date-time"},
        "tickets": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["path", "depends_on", "critical", "status", "phase"],
                "properties": {
                    "path": {"type": "string"},
                    "depends_on": {"type": "array", "items": {"type": "string"}},
                    "critical": {"type": "boolean"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "queued", "executing", "validating",
                                 "completed", "failed", "blocked"]
                    },
                    "phase": {
                        "type": "string",
                        "enum": ["not-started", "completed"]
                    },
                    "git_info": {
                        "type": ["object", "null"],
                        "properties": {
                            "base_commit": {"type": "string"},
                            "branch_name": {"type": "string"},
                            "final_commit": {"type": ["string", "null"]}
                        }
                    },
                    "started_at": {"type": ["string", "null"]},
                    "completed_at": {"type": ["string", "null"]},
                    "failure_reason": {"type": ["string", "null"]},
                    "blocking_dependency": {"type": ["string", "null"]},
                    "previous_status": {"type": ["string", "null"]}
                }
            }
        }
    }
}

def validate_state_schema(state: EpicState):
    """
    Validate state object matches JSON schema.

    Raises ValidationError if schema validation fails.
    """
    try:
        import jsonschema
        state_dict = state.to_dict()
        jsonschema.validate(state_dict, EPIC_STATE_SCHEMA)
    except jsonschema.ValidationError as e:
        logger.error(f"State schema validation failed: {e.message}")
        logger.error(f"Failed path: {e.json_path}")
        raise ValidationError(f"Invalid state schema: {e.message}") from e
```

### Atomic File Write

**Purpose:** Write state to file atomically using temp file + rename.

**Implementation:**

```python
def write_state_file_atomic(state: EpicState):
    """
    Write state to epic-state.json atomically.

    Uses temp file + rename pattern for atomic write.

    Args:
        state: EpicState object to write

    Raises:
        IOError: If file write fails
    """
    state_file = Path(state.epic_directory) / 'artifacts' / 'epic-state.json'
    temp_file = state_file.with_suffix('.json.tmp')

    try:
        # 1. Serialize state to JSON
        state_json = json.dumps(
            state.to_dict(),
            indent=2,
            ensure_ascii=False
        )

        # 2. Write to temp file
        temp_file.write_text(state_json, encoding='utf-8')

        # 3. Atomic rename (overwrites epic-state.json)
        temp_file.replace(state_file)

        logger.debug(f"State written atomically to {state_file}")

    except Exception as e:
        # Clean up temp file on error
        if temp_file.exists():
            temp_file.unlink()

        logger.error(f"Failed to write state file: {e}")
        raise IOError(f"Failed to write epic-state.json: {e}") from e
```

### Timestamp Tracking

**Purpose:** Track when state changes occur.

**Implementation:**

```python
def update_timestamps(state: EpicState, ticket_id: str = None):
    """
    Update timestamps based on state changes.

    Args:
        state: EpicState object
        ticket_id: Optional ticket ID if updating ticket state
    """
    now = datetime.now(UTC).isoformat()

    # Epic-level timestamps
    if not state.started_at:
        state.started_at = now

    if state.status in ['completed', 'failed', 'rolled_back', 'partial_success']:
        if not state.completed_at:
            state.completed_at = now

    # Ticket-level timestamps
    if ticket_id:
        ticket = state.tickets[ticket_id]

        if ticket.status == 'executing' and not ticket.started_at:
            ticket.started_at = now

        if ticket.status in ['completed', 'failed', 'blocked']:
            if not ticket.completed_at:
                ticket.completed_at = now

    # Always update last_updated
    state.last_updated = now
```

### Previous State Tracking

**Purpose:** Preserve previous state for debugging.

**Implementation:**

```python
def preserve_previous_state(state: EpicState, updates: dict):
    """
    Preserve previous state before applying updates.

    Useful for debugging unexpected state transitions.
    """
    for ticket_id, update in updates.items():
        if 'status' in update:
            ticket = state.tickets[ticket_id]
            new_status = update['status']

            if new_status != ticket.status:
                # Status transition: preserve previous
                ticket.previous_status = ticket.status
                logger.info(f"{ticket_id}: {ticket.status} → {new_status}")
```

### Update Examples

**Example 1: Ticket Status Update**

```python
# Update ticket from pending to executing
updates = {
    'add-auth-base': {
        'status': 'executing',
        'started_at': datetime.now(UTC).isoformat()
    }
}

update_epic_state(state, updates)

# Result:
# - tickets['add-auth-base'].previous_status = 'pending'
# - tickets['add-auth-base'].status = 'executing'
# - tickets['add-auth-base'].started_at = '2024-01-15T10:30:00Z'
# - state.last_updated = '2024-01-15T10:30:00Z'
# - epic-state.json written atomically
```

**Example 2: Multiple Ticket Updates**

```python
# Update multiple tickets simultaneously
updates = {
    'ticket-a': {'status': 'completed', 'completed_at': now},
    'ticket-b': {'status': 'executing', 'started_at': now},
    'ticket-c': {'status': 'blocked', 'blocking_dependency': 'ticket-x'}
}

update_epic_state(state, updates)

# All updates applied atomically in single write
```

**Example 3: Epic Status Update**

```python
# Update epic status
updates = {
    'status': 'completed',
    'completed_at': datetime.now(UTC).isoformat()
}

update_epic_state(state, updates)

# Result:
# - state.previous_status = 'executing_wave'
# - state.status = 'completed'
# - state.completed_at = '2024-01-15T11:00:00Z'
```

### Consistency Rules

**Never update during execution:**

- Wait for sub-agent to return before updating
- Do not update while reading (use read-modify-write pattern)

**Always validate before writing:**

- Schema validation catches bugs early
- Invalid state never written to disk

**Use atomic rename:**

- Prevents partial writes on crash
- File is always in valid state

````

### Implementation Details

1. **Add Atomic State Updates Section:** Insert after State Machine in execute-epic.md

2. **Document update_epic_state():** Complete implementation with all steps

3. **JSON Schema:** Full schema for epic-state.json validation

4. **Atomic Write:** Temp file + rename pattern

5. **Timestamp Tracking:** Automatic timestamp updates

6. **Previous State:** Preservation for debugging

7. **Examples:** Various update scenarios

### Integration with Existing Code

Atomic state updates integrate with:
- EpicState and TicketState schema definitions
- All functions that modify epic-state.json
- File system for atomic rename operation
- JSON schema library for validation

## Error Handling Strategy

- **Schema Validation Failure:** Raise ValidationError, do not write file, log details
- **File Write Failure:** Raise IOError, clean up temp file, preserve existing state
- **Temp File Cleanup:** Always remove temp file on error
- **Partial Updates:** Never possible (atomic write guarantees)

## Testing Strategy

### Validation Tests

1. **Atomic Write:**
   - Test temp file created
   - Test atomic rename
   - Test temp file cleaned up on error
   - Test no partial writes on interruption

2. **Schema Validation:**
   - Test valid state passes
   - Test missing required fields fails
   - Test invalid enum values fails
   - Test invalid types fails

3. **Timestamp Tracking:**
   - Test started_at set on first update
   - Test completed_at set on terminal states
   - Test last_updated always updated

4. **Previous State:**
   - Test previous_status preserved on status change
   - Test previous_status null on first status

### Test Commands

```bash
# Run atomic state update tests
uv run pytest tests/unit/test_state_updates.py::test_update_epic_state -v

# Test atomic write
uv run pytest tests/unit/test_state_updates.py::test_atomic_write -v

# Test schema validation
uv run pytest tests/unit/test_state_updates.py::test_schema_validation -v

# Test timestamp tracking
uv run pytest tests/unit/test_state_updates.py::test_timestamps -v
````

## Dependencies

- **update-execute-epic-state-machine**: Provides EpicState and TicketState
  schema

## Coordination Role

Provides atomic state update function used by all tickets that modify
epic-state.json. Ensures state consistency, crash recovery, and single source of
truth for coordination.
