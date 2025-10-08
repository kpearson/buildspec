# Epic: Orchestrator Coordination Strategy

## Epic Summary

The execute-epic orchestrator (root Claude agent) needs a structured
coordination strategy for managing ticket-builder sub-agents. Currently, the
orchestrator has basic instructions but lacks a systematic approach to state
management, parallel execution coordination, error recovery, and sub-agent
lifecycle management.

This epic defines the coordination patterns, state machine, communication
protocols, and orchestration workflows needed for reliable epic execution with
multiple parallel sub-agents.

## Problem Statement

The current execute-epic orchestrator implementation has several coordination
gaps:

1. **Vague Sub-Agent Management**: Instructions say "spawn sub-agents" but don't
   specify:
   - When to spawn vs queue vs wait
   - How many concurrent sub-agents to allow
   - How to track sub-agent lifecycle states
   - How to handle sub-agent failures mid-execution

2. **Unclear State Transitions**: The epic-state.json structure exists but:
   - No formal state machine defining valid transitions
   - No rules for when to update state (before/after sub-agent spawn?)
   - No recovery procedures when state is inconsistent
   - No locking/consistency guarantees

3. **Ambiguous Parallel Execution Rules**: Documentation says "run in parallel"
   but:
   - No clear algorithm for determining ready tickets
   - No specification of maximum concurrency limits
   - No guidance on resource contention management
   - No clear definition of "completion" for parallel tickets

4. **Missing Error Coordination**: When sub-agents fail:
   - No rollback coordination strategy
   - No partial success handling (some tickets done, some failed)
   - No clear distinction between retryable vs terminal failures
   - No guidance on epic branch cleanup

5. **Weak Communication Contract**: Between orchestrator and ticket-builders:
   - No standard format for sub-agent completion reports
   - No protocol for sub-agents to request orchestrator intervention
   - No validation that sub-agents completed all required work
   - No artifact verification before marking tickets complete

## Goals

1. **Structured State Machine**: Define formal states for epic execution and
   ticket phases with clear transition rules
2. **Sub-Agent Lifecycle Protocol**: Specify spawn, monitor, validate, and
   cleanup procedures for ticket-builder sub-agents
3. **Parallel Execution Algorithm**: Provide concrete algorithm for dependency
   resolution and concurrent ticket execution
4. **Error Recovery Workflows**: Define rollback procedures, partial failure
   handling, and retry strategies
5. **Communication Standards**: Establish completion report format and
   validation requirements
6. **Concurrency Controls**: Set limits and rules for parallel sub-agent
   execution

## Success Criteria

- Epic orchestrator follows deterministic state machine with clear transition
  rules
- Sub-agent spawning uses well-defined algorithm based on dependency graph
- Epic-state.json updates follow consistent locking and ordering rules
- Error handling includes rollback procedures and partial success management
- Maximum concurrency limits prevent resource exhaustion
- Sub-agent completion reports follow standard validation format
- Epic execution is resumable after orchestrator failure
- All coordination logic is documented in execute-epic.md command file

## Architecture Overview

### State Machine Design

#### Epic-Level States

```yaml
epic_states:
  initializing:
    description: "Creating epic branch, artifacts directory, and baseline state"
    transitions:
      - ready_to_execute:
          "All initialization complete, ready to spawn first wave"
      - failed_initialization: "Cannot create branch or artifacts"

  ready_to_execute:
    description: "Waiting to spawn next wave of tickets"
    transitions:
      - executing_wave: "Sub-agents spawned for ready tickets"
      - completed: "All tickets complete"
      - failed: "Critical ticket failed"

  executing_wave:
    description: "One or more sub-agents actively executing tickets"
    transitions:
      - ready_to_execute: "Wave complete, check for next ready tickets"
      - completed: "Final wave complete, all tickets done"
      - failed: "Critical ticket failed during execution"

  completed:
    description: "All tickets complete, finalizing artifacts and PRs"
    transitions:
      - finalized: "Artifacts committed, PRs created"

  failed:
    description: "Critical ticket failed, rollback if configured"
    transitions:
      - rolled_back: "Changes reverted, epic branch deleted"
      - partial_success: "Rollback disabled, preserving completed work"
```

#### Ticket-Level States

```yaml
ticket_states:
  pending:
    description: "Ticket defined, waiting for dependencies"
    ready_condition: "All depends_on tickets in 'completed' state"
    transitions:
      - queued: "Dependencies met, ready to spawn"
      - blocked: "Dependency failed, cannot execute"

  queued:
    description: "Ready to execute, waiting for concurrency slot"
    spawn_condition: "Current active sub-agents < MAX_CONCURRENT_TICKETS"
    transitions:
      - executing: "Sub-agent spawned with Task tool"
      - blocked: "Dependency failed while queued"

  executing:
    description: "Sub-agent actively working on ticket"
    monitoring: "Track sub-agent via Task tool, no state file updates"
    transitions:
      - validating: "Sub-agent returned, validating completion report"
      - failed: "Sub-agent returned with failure status"

  validating:
    description: "Orchestrator validating sub-agent completion report"
    checks:
      - "Git branch created and pushed"
      - "Final commit SHA recorded"
      - "All acceptance criteria addressed"
      - "Test suite status reported"
    transitions:
      - completed: "Validation passed"
      - failed: "Validation failed or incomplete work"

  completed:
    description: "Ticket work complete, artifacts recorded"
    state_update: "Write git_info to epic-state.json, update phase"

  failed:
    description: "Ticket execution failed or validation failed"
    state_update: "Record failure reason and timestamp"

  blocked:
    description: "Cannot execute due to dependency failure"
    state_update: "Record blocking dependency and skip reason"
```

### Concurrency Control

```yaml
concurrency_rules:
  max_concurrent_tickets: 3
    rationale: "Balance parallel execution with resource limits and coordination overhead"

  spawn_algorithm:
    name: "Dependency-Aware Wave Execution"
    steps:
      - "Calculate ready tickets: pending tickets where all depends_on are completed"
      - "Sort ready tickets by priority (critical first, then by dependency depth)"
      - "Count currently executing tickets (in 'executing' or 'validating' states)"
      - "Available slots = MAX_CONCURRENT_TICKETS - current_executing"
      - "Spawn up to available_slots sub-agents from sorted ready list"
      - "Move spawned tickets to 'executing' state"
      - "Wait for at least one sub-agent to complete before spawning next wave"

  wave_completion:
    condition: "All tickets in 'executing' state have transitioned to terminal state (completed/failed/blocked)"
    action: "Recalculate ready tickets and spawn next wave"
```

### Sub-Agent Lifecycle Protocol

```yaml
sub_agent_lifecycle:
  spawn_phase:
    tool: "Task tool with subagent_type: general-purpose"
    prompt_construction:
      - "Read execute-ticket.md Task Agent Instructions"
      - "Inject ticket file path, epic file path"
      - "Inject base commit SHA (from dependency or epic baseline)"
      - "Inject session ID for commit tracking"
      - "Include completion report format requirements"
    state_updates:
      before_spawn: "Ticket state = 'queued'"
      after_spawn: "Ticket state = 'executing', record started_at timestamp"
    error_handling:
      "If Task spawn fails, ticket state = 'failed', reason = 'spawn_error'"

  monitoring_phase:
    strategy: "Passive monitoring - wait for Task tool to return"
    no_polling: "Do NOT poll git or read files while sub-agent is executing"
    parallel_tracking:
      "Track multiple executing sub-agents via Task tool futures"

  completion_phase:
    wait_strategy:
      "Task tool blocks until sub-agent completes and returns report"
    report_format:
      required_fields:
        - "ticket_id: [identifier]"
        - "status: completed|failed|blocked"
        - "branch_name: ticket/[name]"
        - "base_commit: [sha]"
        - "final_commit: [sha] (null if failed)"
        - "files_modified: [list of paths]"
        - "test_suite_status: passing|failing|skipped"
        - "acceptance_criteria: [{criterion: text, met: bool}]"
      optional_fields:
        - "failure_reason: [description]"
        - "blocking_dependency: [ticket-id]"
        - "warnings: [list of issues]"

  validation_phase:
    orchestrator_checks:
      - "Verify branch exists: git rev-parse --verify ticket/[name]"
      - "Verify final commit exists: git rev-parse --verify [final_commit]"
      - "Verify commit is on branch: git branch --contains [final_commit]"
      - "Check test suite status is 'passing' (if not skipped)"
      - "Verify all acceptance criteria have status (met or not met)"
    state_updates:
      validation_pass:
        - "Ticket state = 'completed'"
        - "Update git_info with branch_name, base_commit, final_commit"
        - "Record completed_at timestamp"
        - "Write to epic-state.json atomically"
      validation_fail:
        - "Ticket state = 'failed'"
        - "Record validation failure reason"
        - "Do NOT update git_info"
```

### Error Recovery Workflows

```yaml
error_scenarios:
  critical_ticket_fails:
    detection: "Ticket with critical: true transitions to 'failed' state"
    rollback_on_failure_true:
      steps:
        - "Stop spawning new tickets immediately"
        - "Wait for currently executing tickets to complete (don't interrupt)"
        - "Record all completed tickets in epic-state.json"
        - "Delete epic branch: git branch -D epic/[name]"
        - "Delete ticket branches: git branch -D ticket/* (all created for this
          epic)"
        - "Epic state = 'rolled_back'"
        - "Report: Which ticket failed, what was completed before rollback"
    rollback_on_failure_false:
      steps:
        - "Continue executing non-dependent tickets"
        - "Mark dependent tickets as 'blocked'"
        - "Epic state = 'partial_success'"
        - "Report: Which tickets succeeded, which failed, which blocked"

  non_critical_ticket_fails:
    detection: "Ticket with critical: false transitions to 'failed' state"
    action:
      - "Mark dependent tickets as 'blocked'"
      - "Continue executing independent tickets"
      - "Epic can still reach 'completed' if all critical tickets succeed"

  sub_agent_spawn_fails:
    detection: "Task tool returns error when spawning sub-agent"
    retry_strategy:
      max_retries: 2
      backoff: "Exponential: 5s, 15s"
      after_max_retries:
        "Ticket state = 'failed', reason = 'spawn_failed_after_retries'"

  validation_fails:
    detection: "Sub-agent reports completion but orchestrator validation fails"
    action:
      - "Ticket state = 'failed', reason = 'validation_failed: [specific check]'"
      - "Log sub-agent report for debugging"
      - "Do NOT retry automatically (avoid infinite loops)"
      - "Treat as critical or non-critical based on ticket.critical flag"

  orchestrator_crash:
    detection: "execute-epic command interrupted or terminated"
    recovery_strategy:
      - "On restart: Read epic-state.json to determine current state"
      - "Tickets in 'executing' state are stale (sub-agent lost)"
      - "Reset stale tickets to 'pending' or 'queued' based on dependencies"
      - "Resume from current wave calculation"
    design_principle: "Epic-state.json is single source of truth for restart"
```

### State Update Protocol

```yaml
state_update_rules:
  file_location: "artifacts/epic-state.json (relative to epic directory)"

  atomic_updates:
    strategy: "Read-modify-write with file lock or atomic rename"
    implementation:
      "Read current state, modify in memory, write to temp file, rename to
      epic-state.json"

  update_triggers:
    before_wave_spawn: "Update all tickets moving from 'queued' to 'executing'"
    after_sub_agent_complete:
      "Update ticket to 'completed' or 'failed' after validation"
    on_blocking: "Update dependent tickets to 'blocked' when dependency fails"
    on_epic_state_change: "Update epic status field when transitioning states"

  consistency_rules:
    - "Never update state while sub-agent is executing (wait for completion)"
    - "Always validate state file before writing (JSON schema check)"
    - "Include timestamp with every state change"
    - "Preserve previous state in 'previous_phase' field for debugging"

  state_schema:
    epic_level:
      required:
        ["epic_id", "epic_branch", "baseline_commit", "status", "started_at"]
      optional: ["epic_pr_url", "completed_at", "failure_reason"]
    ticket_level:
      required: ["path", "depends_on", "critical", "status", "phase"]
      optional:
        [
          "git_info",
          "started_at",
          "completed_at",
          "failure_reason",
          "blocking_dependency",
        ]
```

### Parallel Execution Algorithm

```yaml
wave_execution_algorithm:
  initialization:
    - "Read epic YAML and parse tickets with dependencies"
    - "Create dependency graph adjacency list"
    - "Detect cycles and fail if found"
    - "Initialize all tickets with status='pending', phase='not-started'"

  wave_loop:
    while: "Tickets remain in pending/queued/executing states"
    steps:
      - step: "Calculate ready tickets"
        logic: |
          ready_tickets = []
          for ticket in tickets:
            if ticket.status == 'pending':
              all_deps_complete = all(dep.status == 'completed' for dep in ticket.depends_on)
              if all_deps_complete:
                ready_tickets.append(ticket)

      - step: "Check for blocked tickets"
        logic: |
          for ticket in tickets:
            if ticket.status == 'pending':
              any_dep_failed = any(dep.status in ['failed', 'blocked'] for dep in ticket.depends_on)
              if any_dep_failed:
                ticket.status = 'blocked'
                ticket.blocking_dependency = first_failed_dep.id

      - step: "Prioritize ready tickets"
        logic: |
          ready_tickets.sort(key=lambda t: (
            0 if t.critical else 1,  # Critical first
            -dependency_depth(t)      # Deeper dependencies first (longer chains)
          ))

      - step: "Calculate available concurrency slots"
        logic: |
          executing_count = count(ticket.status in ['executing', 'validating'])
          available_slots = MAX_CONCURRENT_TICKETS - executing_count

      - step: "Spawn sub-agents for ready tickets"
        logic: |
          for ticket in ready_tickets[:available_slots]:
            ticket.status = 'queued'
            base_commit = calculate_base_commit(ticket)
            spawn_sub_agent(ticket, base_commit)
            ticket.status = 'executing'
            ticket.started_at = now()

      - step: "Wait for at least one completion"
        logic: |
          if executing_count > 0:
            completed_report = wait_for_any_sub_agent()
            validate_and_update_state(completed_report)

      - step: "Check epic failure condition"
        logic: |
          if any(t.status == 'failed' and t.critical for t in tickets):
            if epic.rollback_on_failure:
              trigger_rollback()
              break
            else:
              epic.status = 'partial_success'

      - step: "Check epic completion"
        logic: |
          all_terminal = all(t.status in ['completed', 'failed', 'blocked'] for t in tickets)
          if all_terminal:
            all_critical_complete = all(
              t.status == 'completed' for t in tickets if t.critical
            )
            epic.status = 'completed' if all_critical_complete else 'partial_success'
            break

  finalization:
    - "Commit all artifacts to epic branch"
    - "Create ticket PRs in dependency order"
    - "Update epic PR from draft to ready"
    - "Generate comprehensive execution report"
```

### Base Commit Calculation

```yaml
base_commit_strategy:
  purpose:
    "Determine which commit a ticket branch should be created from (stacked
    branches)"

  algorithm:
    no_dependencies:
      base_commit: "epic.baseline_commit (epic branch HEAD when started)"
      rationale: "Independent ticket branches from epic baseline"

    single_dependency:
      base_commit: "dependency.git_info.final_commit"
      rationale: "Stack on top of dependency's work"

    multiple_dependencies:
      base_commit: "most_recent_final_commit(dependencies)"
      calculation: |
        dep_commits = [dep.git_info.final_commit for dep in ticket.depends_on]
        # Use git merge-base to find most recent common ancestor approach
        # Or use newest timestamp if commits are linear
        base_commit = find_most_recent_commit(dep_commits)
      rationale: "Stack on the most recent dependency work"

  edge_cases:
    missing_git_info:
      error:
        "Dependency ticket completed but git_info missing - validation failure"
      action: "Fail epic with state inconsistency error"

    merge_conflict_potential:
      detection: "Multiple dependencies modified same files"
      action:
        "Still spawn sub-agent, let git handle merge conflicts during branch
        creation"
      sub_agent_responsibility: "Handle merge conflicts or report failure"
```

## Coordination Requirements

### Breaking Changes Prohibited

- Epic YAML structure must remain compatible with current format
- Ticket YAML format must not change
- Epic-state.json schema can be extended but existing fields must maintain
  meaning
- execute-ticket.md Task Agent Instructions interface must remain stable

### Function Profiles

**ExecuteEpicOrchestrator** (execute-epic.md)

- `initialize_epic_execution(epic_file: Path) -> EpicState`
  - Create epic branch, artifacts directory, epic-state.json
  - Parse epic YAML and build dependency graph
  - Return initialized state object

- `calculate_ready_tickets(state: EpicState) -> List[Ticket]`
  - Evaluate dependency completion for all pending tickets
  - Return sorted list of ready tickets (prioritized)

- `spawn_ticket_sub_agent(ticket: Ticket, base_commit: str, session_id: str) -> SubAgentHandle`
  - Use Task tool to spawn ticket-builder sub-agent
  - Pass execute-ticket.md instructions with context
  - Return handle for tracking completion

- `validate_completion_report(ticket: Ticket, report: dict) -> ValidationResult`
  - Check git branch exists and final commit is valid
  - Verify test suite status and acceptance criteria
  - Return validation result with any errors

- `update_epic_state(state: EpicState, updates: dict) -> None`
  - Atomically update epic-state.json with ticket progress
  - Maintain consistency and include timestamps

- `execute_rollback(state: EpicState) -> None`
  - Delete epic branch and all ticket branches
  - Record rollback reason in epic-state.json
  - Report what was completed before rollback

**CompletionReportFormat** (executed-ticket.md)

- Sub-agents must return standardized report structure
- Orchestrator validates all required fields present
- Schema validation before accepting completion

### Executor Abstraction Layer

**Purpose**: Decouple state machine from execution mechanism to support future distributed execution (worktrees, containers, remote clusters)

**TicketExecutionContext** (execution parameters)
```python
class TicketExecutionContext:
    ticket_path: str       # File system path to ticket markdown
    epic_path: str         # File system path to epic YAML
    base_commit: str       # Git SHA to branch from
    session_id: str        # Session ID for commit tracking
```

**TicketExecutor Interface** (abstraction for where/how tickets execute)
```python
class TicketExecutor(Protocol):
    def spawn(ctx: TicketExecutionContext) -> ExecutionHandle
        """Spawn ticket execution and return handle for tracking"""
    
    def wait_for_completion(handle: ExecutionHandle) -> CompletionReport
        """Block until execution completes, return standardized report"""
```

**Current Implementation: LocalTaskExecutor**
- Uses Task tool with file system paths
- Assumes shared file system and same git repository
- Passes absolute paths to ticket and epic files
- Works for single-machine execution

**Future Implementations** (designed for, not built yet)
- **WorktreeExecutor**: Creates git worktree per ticket, spawns agent in worktree context
- **ContainerExecutor**: Launches Docker container with repo clone, executes ticket in isolation
- **RemoteExecutor**: Submits ticket to distributed execution cluster, polls for completion

**Design Principle**: State machine orchestrator uses TicketExecutor interface, never assumes execution mechanism. Validation happens via git (branch/commit existence checks) which works regardless of where ticket executed.

### Directory Structure

```
.epics/
  [epic-name]/
    [epic-name]-spec.md              # Original planning doc
    [epic-name].epic.yaml             # Epic definition
    artifacts/
      epic-state.json                 # State tracking (orchestrator managed)
      tickets/                        # Ticket completion reports (sub-agent managed)
        [ticket-id]-[sha].md
```

### Shared Interfaces

**EpicState (epic-state.json)**

```yaml
{
  "epic_id": "string",
  "epic_branch": "string",
  "baseline_commit": "string (SHA)",
  "epic_pr_url": "string (nullable)",
  "status": "enum: initializing|ready_to_execute|executing_wave|completed|failed|rolled_back|partial_success",
  "started_at": "ISO8601 timestamp",
  "completed_at": "ISO8601 timestamp (nullable)",
  "failure_reason": "string (nullable)",
  "tickets": {
    "[ticket-id]": {
      "path": "string",
      "depends_on": ["ticket-id"],
      "critical": "boolean",
      "status": "enum: pending|queued|executing|validating|completed|failed|blocked",
      "phase": "enum: not-started|completed",
      "git_info": {
        "base_commit": "string (SHA)",
        "branch_name": "string",
        "final_commit": "string (SHA)"
      } | null,
      "started_at": "ISO8601 timestamp (nullable)",
      "completed_at": "ISO8601 timestamp (nullable)",
      "failure_reason": "string (nullable)",
      "blocking_dependency": "string (nullable)"
    }
  }
}
```

**TicketCompletionReport** (returned by sub-agents)

```yaml
{
  # Required fields (current implementation)
  "ticket_id": "string",
  "status": "enum: completed|failed|blocked",
  "branch_name": "string (e.g., ticket/auth-base)",
  "base_commit": "string (SHA)",
  "final_commit": "string (SHA) | null",
  "files_modified": ["string (file paths)"],
  "test_suite_status": "enum: passing|failing|skipped",
  "acceptance_criteria":
    [{ "criterion": "string (text of criterion)", "met": "boolean" }],
  
  # Optional fields (current implementation)
  "failure_reason": "string (nullable)",
  "blocking_dependency": "string (nullable)",
  "warnings": ["string"],
  
  # Optional fields (future distributed execution support)
  "artifacts": {
    "artifact_url": "string (S3/storage URL to ticket artifact bundle)",
    "test_output_url": "string (URL to test execution logs)",
    "git_patch_url": "string (URL to git patch file)",
    "manifest": {
      "files_modified": ["string (relative paths)"],
      "test_results": "object (structured test output)",
      "execution_metadata": "object (executor-specific details)"
    }
  } | null
}
```

**Notes on artifacts field:**
- Not used in current local execution (null/omitted)
- Enables future distributed executors to provide portable artifacts
- Orchestrator can download and verify work independent of git
- Provides audit trail that persists beyond git branches

### Performance Contracts

- **State file read/write**: < 100ms (small JSON file, local disk)
- **Ready ticket calculation**: < 500ms (dependency graph traversal)
- **Git validation checks**: < 1s per ticket (local git commands)
- **Wave spawn overhead**: < 5s (multiple Task tool invocations)

### Security Constraints

- All file operations must validate paths are within project directory
- Git branch operations must validate branch names (no command injection)
- State file updates must validate JSON schema before writing
- Sub-agent reports must be sanitized before logging (no injection attacks)

### Architectural Decisions

**Technology Choices**

- Python for orchestrator logic (already in CLI codebase)
- Task tool for sub-agent spawning (Claude-native mechanism)
- JSON for state tracking (human-readable, easily parseable)
- Git for coordination ground truth (branch/commit existence)

**Patterns**

- State machine pattern for epic execution lifecycle
- Wave-based execution for parallel ticket spawning
- Passive monitoring (no polling, wait for sub-agent return)
- Atomic state updates (read-modify-write with validation)
- Validation-after-completion (verify sub-agent claims)

**Design Principles**

- **Single source of truth**: epic-state.json for all coordination state
- **Resumability**: Epic execution can restart from state file after crash
- **Fail-fast validation**: Validate sub-agent reports before accepting
  completion
- **Explicit over implicit**: All state transitions explicitly recorded
- **No silent failures**: Every error path updates state and logs reason

## Related Issues

### Tickets

1. **update-execute-epic-state-machine**
   - Add formal state machine documentation to execute-epic.md
   - Define epic-level states and ticket-level states with transition rules
   - Document state update protocol and consistency requirements

2. **implement-concurrency-control**
   - Add MAX_CONCURRENT_TICKETS constant and wave execution algorithm
   - Implement calculate_ready_tickets() function
   - Add concurrency slot calculation logic

3. **define-sub-agent-lifecycle-protocol**
   - Document spawn phase with prompt construction details
   - Define completion report format requirements
   - Specify validation phase checks for orchestrator

4. **implement-completion-report-validation**
   - Add validate_completion_report() function to orchestrator
   - Implement git verification checks (branch exists, commit exists)
   - Validate test suite status and acceptance criteria format

5. **add-error-recovery-workflows**
   - Document critical ticket failure handling (rollback vs partial success)
   - Implement non-critical failure handling (mark dependent tickets blocked)
   - Add orchestrator crash recovery from epic-state.json

6. **implement-base-commit-calculation**
   - Add calculate_base_commit() function for stacked branches
   - Handle no dependencies, single dependency, multiple dependencies
   - Document edge cases and error conditions

7. **add-atomic-state-updates**
   - Implement atomic epic-state.json write with temp file + rename
   - Add JSON schema validation before writing
   - Include timestamps and previous state tracking

8. **update-execute-ticket-completion-reporting**
   - Update execute-ticket.md to require standardized completion report
   - Document all required fields and optional fields
   - Add examples of completion reports for success/failure/blocked

9. **add-wave-execution-algorithm**
   - Implement wave loop with ready ticket calculation
   - Add prioritization logic (critical first, dependency depth second)
   - Implement wait-for-any-completion with Task tool

10. **add-orchestrator-integration-tests**
    - Test parallel execution with 3 concurrent tickets
    - Test critical ticket failure with rollback
    - Test non-critical ticket failure with partial success
    - Test orchestrator crash recovery from state file
    - Test complex dependency graphs (diamond, chain, independent)

## Acceptance Criteria

- [ ] Execute-epic.md documents complete state machine with epic and ticket
      states
- [ ] Concurrency control limits parallel sub-agents to MAX_CONCURRENT_TICKETS
- [ ] Sub-agent lifecycle protocol specifies spawn, monitor, validate, cleanup
      steps
- [ ] Completion report format is standardized and validated by orchestrator
- [ ] Error recovery workflows handle critical failures, non-critical failures,
      and crashes
- [ ] Base commit calculation correctly implements stacked branch strategy
- [ ] Epic-state.json updates are atomic with JSON schema validation
- [ ] Wave execution algorithm correctly calculates ready tickets and
      prioritizes them
- [ ] Orchestrator can resume epic execution from state file after crash
- [ ] Integration tests validate all coordination scenarios work end-to-end

## Notes

This spec focuses on coordination strategy and protocols, not implementation.
The execute-epic.md command file should be updated to include all these
coordination details so the orchestrator agent has clear, deterministic
instructions.

The key insight is that the orchestrator is fundamentally a **state machine
coordinator** managing multiple parallel sub-agent lifecycles. By making the
state machine explicit and the communication protocol standardized, we eliminate
ambiguity and enable reliable epic execution.
