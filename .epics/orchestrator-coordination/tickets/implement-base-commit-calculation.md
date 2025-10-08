# implement-base-commit-calculation

## Description

Implement the calculate_base_commit() function to determine the correct base
commit for stacked ticket branches based on dependency relationships.

Tickets with dependencies must stack their branches on top of dependency work.
This function implements the stacked branch strategy by calculating which git
commit each ticket should branch from, handling no dependencies, single
dependency, and multiple dependencies cases.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. Base commit calculation enables stacked
branches where dependent tickets build on top of their dependencies' work.

**Architecture:** Uses git_info.final_commit from completed dependencies as
stacking points. Independent tickets branch from epic.baseline_commit. Multiple
dependencies use most recent final_commit.

## Story

As a **buildspec orchestrator**, I need **base commit calculation for stacked
branches** so that **dependent tickets branch from their dependencies' work
instead of the epic baseline, enabling sequential feature development**.

## Acceptance Criteria

### Core Requirements

- calculate_base_commit() correctly handles no dependencies, single dependency,
  and multiple dependencies
- Function validates dependency git_info exists before using
- Edge cases are documented and handled appropriately
- Function returns valid git SHA that exists in repository
- Execute-epic.md documents complete algorithm

### No Dependencies Case

- Input: Ticket with depends_on=[]
- Output: epic.baseline_commit
- Rationale: Independent ticket branches from epic branch HEAD

### Single Dependency Case

- Input: Ticket with depends_on=[dep_id]
- Output: state.tickets[dep_id].git_info.final_commit
- Rationale: Stack on top of dependency's work
- Validation: Ensure dependency git_info exists and final_commit is not null

### Multiple Dependencies Case

- Input: Ticket with depends_on=[dep1_id, dep2_id, ...]
- Strategy: Find most recent final_commit among dependencies
- Implementation: Use git commit timestamps to find newest
- Rationale: Stack on the most recent dependency work

### Edge Cases

- **Missing git_info:** Fail with state inconsistency error
- **Null final_commit:** Fail with validation error (dependency must be
  completed)
- **Merge conflicts:** Let git handle during branch creation, sub-agent reports
  failure if conflicts occur

## Integration Points

### Upstream Dependencies

- **update-execute-epic-state-machine**: Provides ticket state with git_info
  field

### Downstream Dependencies

- **define-git-workflow-strategy**: Documents branch stacking strategy that uses
  this calculation
- **add-wave-execution-algorithm**: Calls calculate_base_commit() before
  spawning sub-agents

## Current vs New Flow

### BEFORE (Current State)

No base commit calculation exists. Unclear how to handle stacked branches for
dependent tickets.

### AFTER (This Ticket)

Execute-epic.md contains complete calculate_base_commit() algorithm with:

- Logic for no dependencies, single dependency, multiple dependencies
- Validation of dependency git_info existence
- Edge case handling and error conditions
- Examples showing base commit calculation for various dependency graphs

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-epic.md`

Add "Base Commit Calculation" section:

````markdown
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
````

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

````

### Implementation Details

1. **Add Base Commit Calculation Section:** Insert after Concurrency Control in execute-epic.md

2. **Document calculate_base_commit():** Complete algorithm with all three cases

3. **Multiple Dependencies Logic:** Explain most-recent-commit strategy with git timestamps

4. **Edge Cases:** Document missing git_info, null final_commit, merge conflict handling

5. **Examples:** Show calculation for no deps, single dep, multiple deps (diamond)

6. **Validation:** Document commit existence verification

### Integration with Existing Code

Base commit calculation integrates with:
- EpicState.baseline_commit for independent tickets
- TicketState.git_info.final_commit for stacked branches
- Git repository for timestamp queries and commit verification
- Spawn logic to provide base_commit to sub-agents

## Error Handling Strategy

- **Missing git_info:** Raise StateInconsistencyError (epic-state.json is corrupted)
- **Null final_commit:** Raise StateInconsistencyError (dependency not truly complete)
- **Commit Not Found:** Raise GitError (git_info contains invalid SHA)
- **Multiple Dependencies Timestamp Failure:** Raise GitError (cannot determine order)

## Testing Strategy

### Validation Tests

1. **No Dependencies:**
   - Test returns epic.baseline_commit
   - Verify commit exists in repository

2. **Single Dependency:**
   - Test returns dependency final_commit
   - Test raises error if git_info missing
   - Test raises error if final_commit is null

3. **Multiple Dependencies:**
   - Test returns most recent final_commit
   - Test with 2 dependencies (different timestamps)
   - Test with 3+ dependencies (diamond graph)

4. **Edge Cases:**
   - Test missing git_info raises StateInconsistencyError
   - Test null final_commit raises StateInconsistencyError
   - Test invalid commit SHA raises GitError

### Test Commands

```bash
# Run base commit calculation tests
uv run pytest tests/unit/test_base_commit.py::test_calculate_base_commit -v

# Test no dependencies case
uv run pytest tests/unit/test_base_commit.py::test_no_dependencies -v

# Test single dependency case
uv run pytest tests/unit/test_base_commit.py::test_single_dependency -v

# Test multiple dependencies case
uv run pytest tests/unit/test_base_commit.py::test_multiple_dependencies -v

# Test edge cases
uv run pytest tests/unit/test_base_commit.py::test_edge_cases -v
````

## Dependencies

- **update-execute-epic-state-machine**: Provides ticket state with git_info
  field

## Coordination Role

Provides base commit calculation used by spawn logic to create stacked branches.
Enables dependent tickets to build on top of their dependencies' work, creating
a linear or tree-structured commit history.
