# define-sub-agent-lifecycle-protocol

## Description

Define the complete sub-agent lifecycle protocol for ticket execution,
establishing the contract between orchestrator and ticket-builder sub-agents.

Sub-agents are spawned via Task tool but lack a standardized protocol for spawn
parameters, completion reporting, and validation. This ticket establishes clear
spawn phase documentation, completion report format, validation phase checks,
and monitoring strategy that both orchestrator and sub-agents must follow.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. The sub-agent lifecycle protocol is the
communication contract enabling reliable coordination between orchestrator and
ticket-builder agents.

**Architecture:** Uses Task tool for sub-agent spawning with passive monitoring
(no polling). Sub-agents return standardized TicketCompletionReport which
orchestrator validates before marking tickets complete.

## Story

As a **buildspec orchestrator**, I need **a standardized sub-agent lifecycle
protocol** so that **I can spawn, monitor, and validate ticket-builder
sub-agents reliably with consistent completion reporting**.

## Acceptance Criteria

### Core Requirements

- Spawn phase documentation includes all prompt construction details
- TicketCompletionReport format is completely specified with all required and
  optional fields
- Validation phase checks are enumerated and documented
- Monitoring strategy clarifies passive approach (no polling)
- Execute-epic.md contains complete sub-agent lifecycle section

### Spawn Phase Documentation

- Tool: Task tool with subagent_type='general-purpose'
- Prompt construction: Read execute-ticket.md, inject ticket path, epic path,
  base commit SHA, session ID
- State updates before spawn: ticket status = 'queued' → 'executing', record
  started_at timestamp
- State updates after spawn: record sub-agent handle for tracking
- Error handling: spawn failure → ticket status = 'failed' with 'spawn_error'
  reason

### Completion Report Format

Document TicketCompletionReport schema with:

- **Required fields:** ticket_id, status, branch_name, base_commit,
  final_commit, files_modified, test_suite_status, acceptance_criteria
- **Optional fields:** failure_reason, blocking_dependency, warnings
- **Field types and validation rules:** strings, enums, lists, nullability
- **Examples:** Success scenario, failure scenario, blocked scenario

### Validation Phase

- Git verification: branch exists, final commit exists, commit is on branch
- Test suite status check (if not skipped)
- Acceptance criteria completeness check
- Validation failure handling: ticket status = 'failed', record validation
  failure reason

### Monitoring Strategy

- Passive monitoring: wait for Task tool to return (no polling)
- Parallel tracking: track multiple sub-agent futures simultaneously
- No active checks during execution (don't poll git or read files)

## Integration Points

### Upstream Dependencies

- **update-execute-epic-state-machine**: Provides ticket state definitions for
  spawn/execute/validate flow

### Downstream Dependencies

- **implement-completion-report-validation**: Implements validation checks
  defined in this protocol
- **update-execute-ticket-completion-reporting**: Updates execute-ticket.md to
  match report format
- **add-wave-execution-algorithm**: Uses spawn protocol to launch sub-agents

## Current vs New Flow

### BEFORE (Current State)

Execute-epic.md mentions "spawn sub-agents via Task tool" but doesn't specify
prompt construction, completion report format, or validation requirements.
Sub-agents return unstructured output.

### AFTER (This Ticket)

Execute-epic.md contains comprehensive "Sub-Agent Lifecycle Protocol" section
with:

- Detailed spawn phase documentation with exact prompt construction
- Complete TicketCompletionReport schema specification
- Validation phase checklist with git verification steps
- Monitoring strategy clarifying passive approach
- Examples for all phases of sub-agent lifecycle

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-epic.md`

Add "Sub-Agent Lifecycle Protocol" section:

````markdown
## Sub-Agent Lifecycle Protocol

### Phase 1: Spawn

**Tool:** Task tool with subagent_type='general-purpose'

**Prompt Construction:**

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
````

**State Updates Before Spawn:**

```python
ticket.status = 'executing'
ticket.started_at = datetime.now(UTC).isoformat()
update_epic_state(state, {ticket.id: ticket})
```

**Error Handling:**

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

The orchestrator does NOT:

- Poll git for new commits
- Read ticket files during execution
- Check process status continuously

The orchestrator DOES:

- Wait for Task tool to return (blocking or async)
- Track multiple sub-agent futures simultaneously
- Respond only when sub-agent completes and returns

**Parallel Tracking:**

```python
# Spawn multiple sub-agents
handles = []
for ticket in ready_tickets[:available_slots]:
    handle = spawn_ticket_sub_agent(ticket, base_commit, session_id)
    handles.append((ticket.id, handle))

# Wait for any completion
completed_ticket_id, completion_report = wait_for_any(handles)
```

### Phase 3: Validate Completion Report

When sub-agent returns, validate the completion report before accepting.

**TicketCompletionReport Schema:**

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

````

### Implementation Details

1. **Add Sub-Agent Lifecycle Section:** Insert after Concurrency Control section in execute-epic.md

2. **Document All Three Phases:** Spawn, Monitor, Validate with complete details

3. **Specify TicketCompletionReport:** Complete schema with required/optional fields, types, examples

4. **Validation Checklist:** Git verification commands, test suite rules, acceptance criteria format

5. **Examples:** Provide JSON examples for success, failure, blocked scenarios

### Integration with Existing Code

The sub-agent lifecycle protocol integrates with:
- Task tool for spawning sub-agents
- TicketExecutionContext passed to sub-agents
- validate_completion_report() function (implemented in separate ticket)
- Epic-state.json updates during spawn and validation
- execute-ticket.md instructions (updated in separate ticket)

## Error Handling Strategy

- **Spawn Failure:** Mark ticket as failed with spawn_error reason, log exception
- **Validation Failure:** Mark ticket as failed with validation_failed reason, preserve completion report for debugging
- **Missing Required Fields:** Validation fails, log which fields are missing
- **Git Verification Failure:** Branch or commit not found → validation fails

## Testing Strategy

### Validation Tests

1. **Spawn Phase:**
   - Verify prompt construction includes all required context
   - Test spawn failure handling
   - Validate state updates before/after spawn

2. **Completion Report Format:**
   - Verify all required fields are documented
   - Check examples are valid JSON
   - Validate schema matches EpicState/TicketState interfaces

3. **Validation Phase:**
   - Test git verification commands work correctly
   - Verify test suite status rules
   - Check acceptance criteria format validation

### Test Commands

```bash
# Review sub-agent lifecycle documentation
cat /Users/kit/Code/buildspec/claude_files/commands/execute-epic.md | rg -A 200 "Sub-Agent Lifecycle"

# Validate TicketCompletionReport JSON examples
echo '<example_json>' | jq . # Should parse successfully
````

## Dependencies

- **update-execute-epic-state-machine**: Provides state definitions for
  spawn/execute/validate flow

## Coordination Role

Defines TicketCompletionReport schema used by validation and execute-ticket
tickets. Establishes the communication contract between orchestrator and
sub-agents, enabling reliable coordination and validation.
