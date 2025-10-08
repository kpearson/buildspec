# split-edge-case-handling

## Description

Add edge case handling to split workflow in cli/commands/create_epic.py.

Handle complex dependency scenarios where splitting may fail or produce
suboptimal results, ensuring the system gracefully handles circular
dependencies, long chains, and cases where independence cannot be achieved.

## Acceptance Criteria

- Circular dependencies: Keep all tickets with circular deps in same epic
- Long dependency chain: Cannot split - keep entire chain in one epic, warn user
- Too many tickets: Create 3+ independent epics if needed (not just 2)
- Cannot achieve independence: Fail split gracefully, warn user epic is too
  coupled
- Add --no-split flag to CLI: Skip splitting workflow, warn about size
  implications
- Validate split epics meet independence criteria before finalizing
- Provide clear error messages for each edge case
- Log edge case handling for debugging

## Files to Modify

- /Users/kit/Code/buildspec/cli/commands/create_epic.py
- /Users/kit/Code/buildspec/cli/app.py (for --no-split flag)

## Dependencies

- create-epic-split-workflow

## Implementation Notes

### Edge Case Detection

```python
def validate_split_independence(split_epics: list[dict]) -> tuple[bool, str]:
    """
    Validate that split epics are fully independent.

    Args:
        split_epics: List of split epic data with dependencies

    Returns:
        (is_valid, error_message) tuple
    """
    # Check for cross-epic dependencies
    for epic in split_epics:
        for ticket in epic['tickets']:
            for dep in ticket.get('depends_on', []):
                # Check if dependency is in a different epic
                if not is_dependency_in_same_epic(dep, epic):
                    return False, f"Cross-epic dependency found: {ticket['id']} depends on {dep}"

    return True, ""

def detect_circular_dependencies(tickets: list[dict]) -> list[set]:
    """
    Detect circular dependency groups that must stay together.

    Returns:
        List of ticket ID sets that have circular dependencies
    """
    # Build dependency graph
    # Use graph algorithms to detect cycles
    # Return groups of tickets in cycles
    pass

def detect_long_chains(tickets: list[dict]) -> list[list]:
    """
    Detect long dependency chains that cannot be split.

    Returns:
        List of ticket ID lists representing dependency chains
    """
    # Build dependency graph
    # Find longest paths
    # Return chains that span too many tickets
    pass
```

### --no-split Flag Implementation

Add to create_epic command in app.py:

```python
@click.option('--no-split', is_flag=True, help='Skip automatic epic splitting even if ticket count >= 13')
def create_epic(spec_path: str, no_split: bool = False):
    """Create an epic from a specification."""
    # ... existing logic ...

    # Skip split if flag set
    if no_split:
        console.print("[yellow]Warning: --no-split flag set. Epic has {ticket_count} tickets which may be difficult to execute.[/yellow]")
        return

    # ... normal split validation ...
```

### Edge Case Handling in Workflow

```python
def handle_split_workflow(epic_path: str, spec_path: str, ticket_count: int) -> None:
    """Orchestrate epic split with edge case handling."""

    # Parse epic to analyze dependencies
    epic_data = parse_epic_yaml(epic_path)
    tickets = epic_data['tickets']

    # Detect circular dependencies
    circular_groups = detect_circular_dependencies(tickets)
    if circular_groups:
        console.print(f"[yellow]Warning: Found {len(circular_groups)} circular dependency groups. These will stay together.[/yellow]")

    # Detect long chains
    long_chains = detect_long_chains(tickets)
    if long_chains and any(len(chain) > 12 for chain in long_chains):
        console.print("[red]Error: Epic has dependency chain longer than 12 tickets. Cannot split while preserving dependencies.[/red]")
        console.print("[yellow]Recommendation: Review epic design to reduce coupling between tickets.[/yellow]")
        return

    # Invoke specialist with edge case context
    specialist_prompt = build_split_epic_with_constraints(
        epic_path, spec_path, ticket_count,
        circular_groups=circular_groups,
        long_chains=long_chains
    )

    # ... rest of workflow ...

    # Validate split results
    is_valid, error_msg = validate_split_independence(split_epics)
    if not is_valid:
        console.print(f"[red]Error: Split validation failed: {error_msg}[/red]")
        console.print("[yellow]Epic is too tightly coupled to split. Keeping as single epic.[/yellow]")
        # Rollback split
        return
```

### Error Messages

Provide clear, actionable error messages:

- **Circular dependencies**: "Found N circular dependency groups. Tickets with
  circular dependencies will stay together."
- **Long chain**: "Dependency chain exceeds 12 tickets. Cannot split without
  breaking dependencies. Consider reducing coupling."
- **Cannot achieve independence**: "Split failed: epics would have
  cross-dependencies. Epic is too tightly coupled to split."
- **--no-split warning**: "Epic has {count} tickets (>12 recommended). Execution
  may take longer than 2 hours."

### Coordination Role

Ensures split process handles complex dependency scenarios correctly, preventing
invalid splits that would break dependencies or create unexecutable epics.
