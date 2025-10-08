# implement-ticket-branch-merging

## Description

Implement the merge_ticket_branches() function to merge all completed ticket
branches into the epic branch in dependency order.

After all tickets complete, their branches must be merged into the epic branch
following the dependency graph order. This creates a single coherent branch with
all feature work that can be pushed to remote for human review.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. Ticket branch merging is the final
integration step that combines all ticket work into the epic branch deliverable.

**Architecture:** Uses topological sort of dependency graph to determine merge
order. Merges into epic branch (not main). Detects and handles merge conflicts
by failing epic.

## Story

As a **buildspec orchestrator**, I need **dependency-ordered ticket branch
merging** so that **all ticket work is combined into the epic branch in the
correct order, preserving commit history and creating a clean deliverable**.

## Acceptance Criteria

### Core Requirements

- merge_ticket_branches() performs topological sort for merge order
- Merges execute in correct dependency order (dependencies before dependents)
- Merge conflicts are detected and handled appropriately
- Final epic branch contains all ticket work
- Epic-state.json is updated with merge status
- Execute-epic.md documents complete merge algorithm

### Merge Order Calculation

- Perform topological sort of dependency graph
- Tickets with no dependencies merge first
- Dependent tickets merge after their dependencies
- Use Kahn's algorithm for topological sorting

### Merge Execution

- Switch to epic branch before merging
- For each ticket in merge order:
  - Merge ticket branch with `--no-ff` (preserve structure)
  - Use descriptive commit message
  - Verify merge succeeded (check exit code)
  - Record merge in epic-state.json

### Merge Conflict Handling

- If merge conflict occurs, fail the epic
- Record which ticket merge failed and why
- Abort merge to leave repository in clean state
- Document that conflicts require manual resolution

### Final Validation

- Verify epic branch contains all ticket commits
- Count commits from baseline to HEAD
- Confirm all ticket final_commits are ancestors of epic HEAD

## Integration Points

### Upstream Dependencies

- **define-git-workflow-strategy**: Defines merge workflow strategy
- **implement-base-commit-calculation**: Provides understanding of dependency
  relationships

### Downstream Dependencies

- **add-wave-execution-algorithm**: Calls merge_ticket_branches() after all
  tickets complete

## Current vs New Flow

### BEFORE (Current State)

No merge implementation exists. Execute-epic.md mentions merging but lacks
algorithm.

### AFTER (This Ticket)

Execute-epic.md contains complete merge_ticket_branches() implementation with:

- Topological sort algorithm (Kahn's)
- Merge execution loop with --no-ff
- Conflict detection and handling
- Final validation checks
- Examples for various dependency graphs

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-epic.md`

Add "Ticket Branch Merging" section:

````markdown
## Ticket Branch Merging

### merge_ticket_branches() Function

**Purpose:** Merge all completed ticket branches into epic branch in dependency
order.

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
````

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

````

### Implementation Details

1. **Add Merging Section:** Insert after Git Workflow Strategy in execute-epic.md

2. **Document merge_ticket_branches():** Complete implementation with all steps

3. **Topological Sort:** Full Kahn's algorithm with cycle detection

4. **Merge Execution:** Individual branch merging with --no-ff and conflict handling

5. **Validation:** Post-merge verification that all commits are present

6. **Examples:** Linear chain, diamond dependency, merge conflict scenarios

### Integration with Existing Code

Ticket branch merging integrates with:
- Epic-state.json for ticket metadata and git_info
- Git repository for merge operations
- Topological sort for dependency ordering
- Validation checks for merge success

## Error Handling Strategy

- **Checkout Failure:** Cannot switch to epic branch → raise GitError
- **Merge Conflict:** Git merge fails → abort merge, raise MergeConflictError, epic status='failed'
- **Cycle Detection:** Topological sort fails → raise CyclicDependencyError (should not happen)
- **Missing Commits:** Validation fails → raise ValidationError

## Testing Strategy

### Validation Tests

1. **Topological Sort:**
   - Test linear chain (A → B → C)
   - Test diamond dependency (A → B,C → D)
   - Test independent tickets (no dependencies)
   - Test cycle detection

2. **Merge Execution:**
   - Test successful merge of single ticket
   - Test successful merge of multiple tickets
   - Test merge with --no-ff preserves structure
   - Test merge commit message includes description

3. **Conflict Handling:**
   - Test merge conflict detection
   - Test merge abort on conflict
   - Test epic failure on conflict

4. **Validation:**
   - Test all commits present after merge
   - Test missing commit detection

### Test Commands

```bash
# Run merge tests
uv run pytest tests/integration/test_merge.py::test_merge_ticket_branches -v

# Test topological sort
uv run pytest tests/unit/test_merge.py::test_topological_sort -v

# Test merge conflicts
uv run pytest tests/integration/test_merge.py::test_merge_conflicts -v

# Test validation
uv run pytest tests/integration/test_merge.py::test_validate_after_merge -v
````

## Dependencies

- **define-git-workflow-strategy**: Defines merge workflow
- **implement-base-commit-calculation**: Provides understanding of dependencies

## Coordination Role

Provides ticket branch merging that wave execution calls after all tickets
complete. Combines all ticket work into a single epic branch deliverable for
pushing and human review.
