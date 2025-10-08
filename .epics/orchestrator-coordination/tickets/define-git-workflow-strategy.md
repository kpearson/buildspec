# define-git-workflow-strategy

## Description

Document the complete git workflow strategy in execute-epic.md, establishing
explicit rules for epic branch lifecycle, ticket branch strategy, branch
stacking, merge workflow, and remote push strategy.

The orchestrator creates and manages multiple git branches (epic branch, ticket
branches) during execution. The git workflow must be explicitly defined to
establish guardrails and ensure consistency across all autonomous agent work.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. The git workflow strategy is the foundation
ensuring all git operations are deterministic, project-agnostic, and produce
clean commit history.

**Architecture:** Epic branch contains all merged ticket work. Ticket branches
are local-only, stacked on dependencies, and merged in dependency order. Remote
push is optional and project-agnostic (no PR creation).

## Story

As a **buildspec orchestrator developer**, I need **explicit git workflow
documentation** so that **all git operations are deterministic, branches are
properly stacked, and the epic branch provides a clean deliverable for human
review**.

## Acceptance Criteria

### Core Requirements

- Execute-epic.md documents complete epic branch lifecycle
- Ticket branch strategy clearly defines local-only branches
- Branch stacking rules match calculate_base_commit() implementation
- Merge workflow specifies dependency-ordered merging into epic branch
- Remote push strategy is project-agnostic (no PR assumptions)
- Git state validation checkpoints are enumerated

### Epic Branch Lifecycle

- Created at initialization from current HEAD
- Name format: `epic/{epic-name}`
- Serves as baseline for all ticket branches
- All ticket branches merge into epic branch (not main)
- Pushed to remote as single human-facing deliverable

### Ticket Branch Strategy

- Name format: `ticket/{ticket-id}`
- Created by sub-agents during ticket execution
- Stacked on dependencies via calculate_base_commit()
- Stay local (never pushed to remote)
- Merged into epic branch after validation

### Branch Stacking Rules

- No dependencies: branch from epic.baseline_commit
- Single dependency: branch from dependency.git_info.final_commit
- Multiple dependencies: branch from most recent final_commit
- Dependencies must be validated before calculating base commit

### Merge Workflow

- Performed after all tickets reach completed state
- Use topological sort of dependency graph for merge order
- Merge ticket branches into epic branch (not main)
- Fast-forward where possible, preserve commit history
- Verify merge success before marking epic complete

### Remote Push Strategy

- Check if git remote exists (`git remote -v`)
- If remote exists: push epic branch only
- Never push ticket branches (implementation details)
- No PR creation (project-agnostic)
- Epic branch on remote is complete feature for human review

## Integration Points

### Upstream Dependencies

- **update-execute-epic-state-machine**: Provides state checkpoints for git
  validation
- **implement-base-commit-calculation**: Provides algorithm for branch stacking

### Downstream Dependencies

- **implement-ticket-branch-merging**: Implements merge workflow defined here
- **implement-remote-push-logic**: Implements remote push strategy defined here
- **add-wave-execution-algorithm**: Follows git workflow for all operations

## Current vs New Flow

### BEFORE (Current State)

Execute-epic.md mentions creating epic branch and ticket branches but lacks
explicit workflow documentation.

### AFTER (This Ticket)

Execute-epic.md contains comprehensive "Git Workflow Strategy" section with:

- Complete epic branch lifecycle documentation
- Ticket branch creation and stacking rules
- Merge workflow with dependency ordering
- Remote push strategy (project-agnostic)
- Git state validation checkpoints
- Examples for various dependency graphs

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-epic.md`

Add "Git Workflow Strategy" section:

````markdown
## Git Workflow Strategy

### Epic Branch Lifecycle

**Purpose:** Epic branch is the single deliverable containing all ticket work.

**Creation:**

```bash
# At epic initialization (from current HEAD)
git checkout -b epic/{epic-name}

# Record baseline commit
epic.baseline_commit = $(git rev-parse HEAD)
```
````

**Name Format:** `epic/{epic-name}`

- Example: `epic/user-authentication`
- Example: `epic/payment-integration`

**Properties:**

- Created from current HEAD at initialization
- Serves as baseline for independent ticket branches
- All ticket branches eventually merge into epic branch
- Never deleted during execution (unless rollback)
- Pushed to remote if remote exists (final step)

**Lifecycle States:**

1. **Created:** During epic initialization
2. **Active:** While tickets are executing
3. **Merged:** After all ticket branches merged
4. **Pushed:** After push to remote (if remote exists)

### Ticket Branch Strategy

**Purpose:** Ticket branches are implementation details, local-only working
branches.

**Creation:**

```bash
# Sub-agent creates ticket branch during execution
base_commit=$(calculate_base_commit $ticket_id)
git checkout -b ticket/{ticket-id} $base_commit
```

**Name Format:** `ticket/{ticket-id}`

- Example: `ticket/add-auth-base`
- Example: `ticket/implement-sessions`

**Properties:**

- Created by ticket-builder sub-agents
- Stacked on dependencies (or epic baseline if no dependencies)
- Stay local (never pushed to remote)
- Merged into epic branch after ticket completion
- Deleted after successful merge (optional cleanup)

**Stacking Strategy:**

- Independent tickets: branch from `epic.baseline_commit`
- Dependent tickets: branch from `dependency.git_info.final_commit`
- See "Branch Stacking Rules" for details

### Branch Stacking Rules

**Purpose:** Enable dependent tickets to build on dependency work.

**Rule 1: No Dependencies**

```bash
# Ticket has no dependencies
ticket.depends_on = []

# Branch from epic baseline
base_commit = epic.baseline_commit
git checkout -b ticket/{ticket-id} $base_commit
```

**Rule 2: Single Dependency**

```bash
# Ticket depends on one ticket
ticket.depends_on = ['dependency-id']

# Branch from dependency's final commit
dependency_final_commit = state.tickets['dependency-id'].git_info.final_commit
git checkout -b ticket/{ticket-id} $dependency_final_commit
```

**Rule 3: Multiple Dependencies**

```bash
# Ticket depends on multiple tickets
ticket.depends_on = ['dep-1', 'dep-2', 'dep-3']

# Branch from most recent dependency final commit
base_commit = find_most_recent_commit([
    state.tickets['dep-1'].git_info.final_commit,
    state.tickets['dep-2'].git_info.final_commit,
    state.tickets['dep-3'].git_info.final_commit
])
git checkout -b ticket/{ticket-id} $base_commit
```

**Validation Before Stacking:**

- Verify all dependencies have status='completed'
- Verify all dependencies have git_info with final_commit
- Verify base_commit exists in repository

### Merge Workflow

**Purpose:** Combine all ticket work into epic branch in dependency order.

**Trigger:** After all tickets reach terminal state (completed/failed/blocked)

**Algorithm:**

```python
def merge_ticket_branches(state: EpicState):
    """
    Merge all completed ticket branches into epic branch.

    Merges in dependency order using topological sort.
    """
    # 1. Switch to epic branch
    subprocess.run(['git', 'checkout', state.epic_branch])

    # 2. Get completed tickets in dependency order
    completed_tickets = [
        ticket_id for ticket_id, ticket_state in state.tickets.items()
        if ticket_state.status == 'completed'
    ]

    # 3. Topological sort (dependencies before dependents)
    merge_order = topological_sort(completed_tickets, state)

    # 4. Merge each ticket branch in order
    for ticket_id in merge_order:
        ticket_state = state.tickets[ticket_id]
        branch_name = ticket_state.git_info['branch_name']

        logger.info(f"Merging {branch_name} into {state.epic_branch}...")

        # Merge with --no-ff to preserve ticket branch structure
        result = subprocess.run(
            ['git', 'merge', '--no-ff', branch_name, '-m',
             f"Merge {branch_name}: {ticket_state.description}"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # Merge conflict or failure
            logger.error(f"Merge failed for {branch_name}: {result.stderr}")

            # Abort merge
            subprocess.run(['git', 'merge', '--abort'])

            # Fail epic
            raise MergeConflictError(
                f"Merge conflict merging {branch_name}. "
                f"Epic cannot be completed. Manual resolution required."
            )

        logger.info(f"Successfully merged {branch_name}")

    # 5. Verify final epic branch state
    verify_epic_branch_contains_all_tickets(state)
```

**Topological Sort:**

```python
def topological_sort(ticket_ids: List[str], state: EpicState) -> List[str]:
    """
    Sort tickets in dependency order (dependencies first).

    Uses Kahn's algorithm for topological sorting.
    """
    # Build adjacency list and in-degree count
    graph = {ticket_id: [] for ticket_id in ticket_ids}
    in_degree = {ticket_id: 0 for ticket_id in ticket_ids}

    for ticket_id in ticket_ids:
        ticket = state.tickets[ticket_id]
        for dep_id in ticket.depends_on:
            if dep_id in ticket_ids:  # Only consider completed tickets
                graph[dep_id].append(ticket_id)
                in_degree[ticket_id] += 1

    # Kahn's algorithm
    queue = [tid for tid in ticket_ids if in_degree[tid] == 0]
    sorted_order = []

    while queue:
        current = queue.pop(0)
        sorted_order.append(current)

        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_order) != len(ticket_ids):
        raise CyclicDependencyError("Cycle detected in dependency graph")

    return sorted_order
```

**Merge Conflict Handling:**

- If merge conflict: abort merge, fail epic
- Log conflict details for manual resolution
- Epic status = 'failed' with failure_reason='merge_conflict'
- Do not attempt automatic conflict resolution

### Remote Push Strategy

**Purpose:** Push epic branch to remote for human review (if remote exists).

**Strategy:** Project-agnostic (no assumptions about main branch or PR workflow)

**Algorithm:**

```bash
# 1. Check if remote exists
git remote -v

# If no remote: skip push, epic complete
if [ $? -ne 0 ]; then
    echo "No remote configured, skipping push"
    epic.status = 'completed'
    exit 0
fi

# 2. Push epic branch with upstream tracking
git push -u origin epic/{epic-name}

# If push succeeds: record success
if [ $? -eq 0 ]; then
    epic.epic_pr_url = null  # No PR created
    epic.status = 'completed'
else
    # Push failed: mark partial success
    epic.status = 'partial_success'
    epic.failure_reason = 'push_failed'
fi
```

**Properties:**

- Only epic branch is pushed (not ticket branches)
- No PR creation (project-agnostic)
- Push failure does not fail epic (mark partial_success)
- Epic branch on remote is human-facing deliverable

### Git State Validation Checkpoints

**Purpose:** Verify git state at key points during execution.

**Checkpoint 1: Initialization**

```bash
# Verify working directory is clean
git status --porcelain

# If dirty: fail initialization
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Working directory has uncommitted changes"
    exit 1
fi
```

**Checkpoint 2: Before Ticket Spawn**

```bash
# Verify base commit exists
base_commit=$(calculate_base_commit $ticket_id)
git rev-parse --verify $base_commit

# If not found: fail spawn
if [ $? -ne 0 ]; then
    echo "ERROR: Base commit $base_commit not found"
    exit 1
fi
```

**Checkpoint 3: After Ticket Completion**

```bash
# Verify ticket branch exists
git rev-parse --verify refs/heads/$branch_name

# Verify final commit exists
git rev-parse --verify $final_commit

# Verify commit is on branch
git branch --contains $final_commit | grep $branch_name
```

**Checkpoint 4: Before Merge**

```bash
# Verify all ticket branches exist
for ticket_id in completed_tickets:
    branch_name = ticket.git_info.branch_name
    git rev-parse --verify refs/heads/$branch_name
```

**Checkpoint 5: After Merge**

```bash
# Verify epic branch contains all ticket commits
for ticket_id in completed_tickets:
    final_commit = ticket.git_info.final_commit
    git branch --contains $final_commit | grep $epic_branch
```

**Checkpoint 6: Before Push**

```bash
# Verify remote exists
git remote -v

# Verify remote is reachable
git ls-remote origin
```

### Git Workflow Examples

**Example 1: Linear Dependency Chain**

```
Epic: user-authentication
Tickets:
  A: add-auth-base (no deps)
  B: add-sessions (depends on A)
  C: add-permissions (depends on B)

Git Workflow:
1. Create epic branch: epic/user-authentication (from HEAD)
2. Ticket A: branch from epic baseline → ticket/add-auth-base
3. Ticket A completes → final_commit = A1
4. Ticket B: branch from A1 → ticket/add-sessions
5. Ticket B completes → final_commit = B1
6. Ticket C: branch from B1 → ticket/add-permissions
7. Ticket C completes → final_commit = C1
8. Merge order: A, B, C (topological sort)
9. Merge into epic/user-authentication
10. Push epic/user-authentication to remote
```

**Example 2: Diamond Dependency**

```
Epic: feature-integration
Tickets:
  A: base-feature (no deps)
  B: feature-variant-1 (depends on A)
  C: feature-variant-2 (depends on A)
  D: combine-features (depends on B, C)

Git Workflow:
1. Create epic branch: epic/feature-integration
2. Ticket A: branch from epic baseline → completes at A1
3. Ticket B: branch from A1 → completes at B1
4. Ticket C: branch from A1 → completes at C1
5. Ticket D: branch from most recent of (B1, C1) → completes at D1
6. Merge order: A, B, C, D (topological sort)
7. Merge all into epic/feature-integration
```

````

### Implementation Details

1. **Add Git Workflow Section:** Insert after Base Commit Calculation in execute-epic.md

2. **Document All Phases:** Epic branch lifecycle, ticket branches, stacking, merging, pushing

3. **Provide Algorithms:** Topological sort, merge workflow, validation checkpoints

4. **Examples:** Linear chain, diamond dependency showing complete git workflow

### Integration with Existing Code

Git workflow strategy integrates with:
- calculate_base_commit() for branch stacking
- merge_ticket_branches() for dependency-ordered merging
- push_epic_branch() for remote push
- validate_completion_report() for git verification

## Error Handling Strategy

- **Dirty Working Directory:** Fail initialization with clear error
- **Base Commit Not Found:** Fail spawn with commit SHA error
- **Merge Conflicts:** Abort merge, fail epic, require manual resolution
- **Push Failure:** Mark epic as partial_success, do not fail

## Testing Strategy

### Validation Tests

1. **Epic Branch Lifecycle:**
   - Test epic branch creation from HEAD
   - Verify baseline_commit recorded correctly
   - Test epic branch persists during execution

2. **Ticket Branch Stacking:**
   - Test no dependencies branches from epic baseline
   - Test single dependency branches from dependency final_commit
   - Test multiple dependencies branches from most recent

3. **Merge Workflow:**
   - Test topological sort with linear chain
   - Test topological sort with diamond dependency
   - Test merge conflict detection and abort

4. **Remote Push:**
   - Test push when remote exists
   - Test skip push when no remote
   - Test partial success on push failure

### Test Commands

```bash
# Run git workflow integration tests
uv run pytest tests/integration/test_git_workflow.py -v

# Test branch stacking
uv run pytest tests/integration/test_git_workflow.py::test_branch_stacking -v

# Test merge workflow
uv run pytest tests/integration/test_git_workflow.py::test_merge_workflow -v
````

## Dependencies

- **update-execute-epic-state-machine**: Provides state checkpoints
- **implement-base-commit-calculation**: Provides stacking algorithm

## Coordination Role

Defines git workflow that all other tickets follow for branch creation, merging,
and pushing. Establishes the contract ensuring all git operations produce clean,
reviewable commit history.
