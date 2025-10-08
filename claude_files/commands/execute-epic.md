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

## Base Commit Calculation

### calculate_base_commit() Function

**Purpose:** Determine which git commit a ticket branch should be created from.

**Input:** Ticket object with depends_on list

**Output:** Git SHA string (valid commit in repository)

**Algorithm:**

```python
def calculate_base_commit(state: EpicState, ticket: Ticket) -> str:
    """
    Calculate base commit for ticket branch based on dependencies.

    Returns git SHA to use as base for ticket branch creation.

    Raises:
        StateInconsistencyError: If dependency git_info missing or invalid
    """
    # Case 1: No dependencies
    if not ticket.depends_on or len(ticket.depends_on) == 0:
        # Branch from epic baseline
        base_commit = state.baseline_commit
        logger.info(f"{ticket.id}: No dependencies, branching from epic baseline {base_commit[:8]}")
        return base_commit

    # Case 2: Single dependency
    if len(ticket.depends_on) == 1:
        dep_id = ticket.depends_on[0]
        dep_state = state.tickets[dep_id]

        # Validate dependency has git_info
        if not dep_state.git_info:
            raise StateInconsistencyError(
                f"Dependency {dep_id} missing git_info. "
                f"Cannot calculate base commit for {ticket.id}"
            )

        # Validate final_commit exists
        final_commit = dep_state.git_info.get('final_commit')
        if not final_commit:
            raise StateInconsistencyError(
                f"Dependency {dep_id} has null final_commit. "
                f"Cannot stack {ticket.id} on incomplete dependency"
            )

        # Branch from dependency's final commit
        logger.info(f"{ticket.id}: Single dependency {dep_id}, branching from {final_commit[:8]}")
        return final_commit

    # Case 3: Multiple dependencies
    if len(ticket.depends_on) > 1:
        # Collect all dependency final_commits
        dep_commits = []

        for dep_id in ticket.depends_on:
            dep_state = state.tickets[dep_id]

            # Validate dependency has git_info
            if not dep_state.git_info:
                raise StateInconsistencyError(
                    f"Dependency {dep_id} missing git_info. "
                    f"Cannot calculate base commit for {ticket.id}"
                )

            # Validate final_commit exists
            final_commit = dep_state.git_info.get('final_commit')
            if not final_commit:
                raise StateInconsistencyError(
                    f"Dependency {dep_id} has null final_commit. "
                    f"Cannot stack {ticket.id} on incomplete dependency"
                )

            dep_commits.append((dep_id, final_commit))

        # Find most recent commit by timestamp
        most_recent_commit = find_most_recent_commit(dep_commits)

        logger.info(
            f"{ticket.id}: Multiple dependencies {ticket.depends_on}, "
            f"branching from most recent {most_recent_commit[:8]}"
        )
        return most_recent_commit
```

### Finding Most Recent Commit

**Purpose:** Among multiple dependency commits, find the most recent.

**Implementation:**

```python
def find_most_recent_commit(dep_commits: List[Tuple[str, str]]) -> str:
    """
    Find most recent commit among multiple dependencies.

    Args:
        dep_commits: List of (dep_id, commit_sha) tuples

    Returns:
        SHA of most recent commit
    """
    # Get commit timestamps using git
    commit_times = []

    for dep_id, commit_sha in dep_commits:
        # Get commit timestamp
        result = subprocess.run(
            ['git', 'show', '-s', '--format=%ct', commit_sha],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(f"Failed to get timestamp for {commit_sha}: {result.stderr}")
            raise GitError(f"Commit {commit_sha} not found in repository")

        timestamp = int(result.stdout.strip())
        commit_times.append((commit_sha, timestamp, dep_id))

    # Sort by timestamp (newest first)
    commit_times.sort(key=lambda x: x[1], reverse=True)

    # Return most recent commit SHA
    most_recent_sha, most_recent_time, most_recent_dep = commit_times[0]

    logger.debug(
        f"Most recent commit: {most_recent_sha[:8]} from {most_recent_dep} "
        f"(timestamp: {most_recent_time})"
    )

    return most_recent_sha
```

### Base Commit Calculation Examples

**Example 1: No Dependencies**

```python
# Ticket A has no dependencies
ticket_a = Ticket(id='add-auth-base', depends_on=[])

base_commit = calculate_base_commit(state, ticket_a)
# Returns: epic.baseline_commit (e.g., "abc123...")

# Ticket A branches directly from epic branch HEAD
```

**Example 2: Single Dependency**

```python
# Ticket B depends on Ticket A
ticket_b = Ticket(id='add-auth-sessions', depends_on=['add-auth-base'])

# Ticket A completed with final_commit = "def456..."
state.tickets['add-auth-base'].git_info = {
    'branch_name': 'ticket/add-auth-base',
    'base_commit': 'abc123...',
    'final_commit': 'def456...'
}

base_commit = calculate_base_commit(state, ticket_b)
# Returns: "def456..." (Ticket A's final_commit)

# Ticket B branches from Ticket A's final commit
```

**Example 3: Multiple Dependencies (Diamond)**

```python
# Ticket D depends on Tickets B and C
ticket_d = Ticket(id='combine-features', depends_on=['feature-b', 'feature-c'])

# Ticket B completed at timestamp 1000
state.tickets['feature-b'].git_info = {
    'final_commit': 'bbb111...'
}

# Ticket C completed at timestamp 2000 (more recent)
state.tickets['feature-c'].git_info = {
    'final_commit': 'ccc222...'
}

base_commit = calculate_base_commit(state, ticket_d)
# Returns: "ccc222..." (Ticket C's final_commit, most recent)

# Ticket D branches from most recent dependency (Ticket C)
```

### Edge Case Handling

**Missing git_info:**

```python
# Dependency completed but git_info is missing (state corruption)
state.tickets['dependency'].git_info = None

calculate_base_commit(state, ticket)
# Raises: StateInconsistencyError("Dependency missing git_info...")
```

**Null final_commit:**

```python
# Dependency marked completed but final_commit is null (invalid state)
state.tickets['dependency'].git_info = {
    'branch_name': 'ticket/dep',
    'base_commit': 'abc123...',
    'final_commit': None
}

calculate_base_commit(state, ticket)
# Raises: StateInconsistencyError("Dependency has null final_commit...")
```

**Merge Conflicts:**

```python
# Base commit calculated successfully, but merge conflicts exist
base_commit = calculate_base_commit(state, ticket)  # Returns "def456..."

# Sub-agent attempts to create branch
git checkout -b ticket/my-ticket $base_commit

# If merge conflicts would occur, git handles it
# Sub-agent reports failure in completion report:
# status='failed', failure_reason='merge_conflicts_on_branch_creation'
```

### Validation After Calculation

**Verify commit exists:**

```python
def validate_base_commit(base_commit: str) -> bool:
    """
    Verify base commit SHA exists in repository.

    Returns True if valid, raises GitError if not.
    """
    result = subprocess.run(
        ['git', 'rev-parse', '--verify', base_commit],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise GitError(f"Base commit {base_commit} not found in repository")

    return True
```

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
