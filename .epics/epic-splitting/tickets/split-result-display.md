# split-result-display

## Description

Add display logic to show split results in cli/commands/create_epic.py.

After split completes successfully, display clear and actionable feedback about
what was created, emphasizing the independence of each split epic and providing
next steps for execution.

## Acceptance Criteria

- Displays total split summary: "Epic split into N independent deliverables (X →
  Y tickets)"
- Lists each created epic with path and ticket count
- Shows archived original epic location
- Emphasizes independence: "Execute each epic independently - no dependencies
  between them"
- Uses rich console formatting for clarity (colors, formatting)
- Clear and actionable messaging
- Follows existing console output patterns in create_epic.py

## Files to Modify

- /Users/kit/Code/buildspec/cli/commands/create_epic.py

## Dependencies

- create-epic-split-workflow
- subdirectory-creation-logic
- archive-original-epic

## Implementation Notes

### Function Signature

```python
def display_split_results(split_epics: list[dict], archived_path: str) -> None:
    """
    Display split results with clear, actionable messaging.

    Args:
        split_epics: List of dicts with 'name', 'path', 'ticket_count' keys
        archived_path: Path to archived original epic
    """
    total_tickets = sum(e['ticket_count'] for e in split_epics)
    original_count = ...  # Get from archived epic

    console.print()
    console.print("[bold green]Epic Split Complete![/bold green]")
    console.print()
    console.print(f"[blue]Epic split into {len(split_epics)} independent deliverables ({original_count} → {total_tickets} tickets)[/blue]")
    console.print()

    console.print("[bold]Created Split Epics:[/bold]")
    for epic in split_epics:
        console.print(f"  [green]✓[/green] {epic['path']} ({epic['ticket_count']} tickets)")
        console.print(f"    Deliverable: {epic['description']}")
    console.print()

    console.print(f"[dim]Original epic archived as: {archived_path}[/dim]")
    console.print()

    console.print("[bold yellow]Next Steps:[/bold yellow]")
    console.print("  Execute each epic independently using:")
    for epic in split_epics:
        console.print(f"    buildspec execute-epic {epic['path']}")
    console.print()
    console.print("[bold]Note:[/bold] Each epic is fully independent - no dependencies between them")
```

### Output Example

```
Epic Split Complete!

Epic split into 2 independent deliverables (25 → 14 tickets)

Created Split Epics:
  ✓ .epics/user-auth/token-caching/token-caching.epic.yaml (10 tickets)
    Deliverable: Token caching system with Redis backend
  ✓ .epics/user-auth/token-caching-integration/token-caching-integration.epic.yaml (4 tickets)
    Deliverable: Integration of token caching into authentication flow

Original epic archived as: .epics/user-auth/user-auth.epic.yaml.original

Next Steps:
  Execute each epic independently using:
    buildspec execute-epic .epics/user-auth/token-caching/token-caching.epic.yaml
    buildspec execute-epic .epics/user-auth/token-caching-integration/token-caching-integration.epic.yaml

Note: Each epic is fully independent - no dependencies between them
```

### Design Considerations

- Use rich console for colors and formatting
- Provide copy-pasteable commands
- Emphasize independence to prevent confusion
- Show deliverable descriptions to clarify purpose
- Keep messaging concise but informative

### Coordination Role

Provides user feedback about split process and next steps, ensuring users
understand the split results and how to proceed with execution.
