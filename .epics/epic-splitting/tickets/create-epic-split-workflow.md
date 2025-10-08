# create-epic-split-workflow

## Description

Add split workflow to cli/commands/create_epic.py to handle oversized epics
after creation.

After epic creation succeeds, this enhancement validates the ticket count and
orchestrates the complete split process when needed (>=13 tickets), including
invoking the specialist agent, creating subdirectories, archiving the original,
and displaying results.

## Acceptance Criteria

- After epic file created, parse_epic_yaml() is called to extract ticket count
- validate_ticket_count() checks if ticket_count >= 13
- If >= 13 tickets: invoke handle_split_workflow()
- If < 13 tickets: success, no split needed (existing behavior)
- handle_split_workflow() orchestrates complete process:
  - Build specialist prompt using PromptBuilder.build_split_epic()
  - Invoke Claude subprocess with specialist prompt
  - Parse specialist output to get split epic names
  - Create subdirectories for each split epic
  - Archive original epic with .original suffix
  - Display split results with epic names and ticket counts
- All file operations use absolute paths
- Errors are handled gracefully with clear messages
- Rollback on failure if specified in epic YAML

## Files to Modify

- /Users/kit/Code/buildspec/cli/commands/create_epic.py

## Dependencies

- epic-validator-module
- prompts-build-split-epic

## Implementation Notes

### Workflow Integration Point

Add after epic file creation in create_epic.py:

```python
# After successful epic creation
epic_path = ... # path to created epic file

# Validate ticket count
try:
    from cli.utils.epic_validator import parse_epic_yaml, validate_ticket_count

    epic_data = parse_epic_yaml(epic_path)
    ticket_count = epic_data['ticket_count']

    if validate_ticket_count(ticket_count):
        # Trigger split workflow
        handle_split_workflow(epic_path, spec_path, ticket_count)
    else:
        # Normal success path
        console.print(f"[green]Epic created successfully: {epic_path}[/green]")
except Exception as e:
    console.print(f"[yellow]Warning: Could not validate epic: {e}[/yellow]")
    # Continue - don't fail epic creation on validation error
```

### handle_split_workflow() Implementation

```python
def handle_split_workflow(epic_path: str, spec_path: str, ticket_count: int) -> None:
    """
    Orchestrate complete epic split process.

    Args:
        epic_path: Path to original oversized epic
        spec_path: Path to spec document
        ticket_count: Number of tickets in epic

    Raises:
        RuntimeError: If split workflow fails
    """
    console.print(f"[yellow]Epic has {ticket_count} tickets (>= 13). Initiating split workflow...[/yellow]")

    # 1. Build specialist prompt
    from cli.core.prompts import PromptBuilder
    prompt_builder = PromptBuilder()
    specialist_prompt = prompt_builder.build_split_epic(epic_path, spec_path, ticket_count)

    # 2. Invoke Claude subprocess
    console.print("[blue]Invoking specialist agent to analyze and split epic...[/blue]")
    result = subprocess.run(
        ["claude", "--prompt", specialist_prompt],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Specialist agent failed: {result.stderr}")

    # 3. Parse specialist output to get epic names
    # (specialist should output structured data with epic names and paths)
    split_epics = parse_specialist_output(result.stdout)

    # 4. Create subdirectories
    base_dir = Path(epic_path).parent
    epic_names = [e['name'] for e in split_epics]
    created_dirs = create_split_subdirectories(base_dir, epic_names)

    # 5. Archive original
    archived_path = archive_original_epic(epic_path)

    # 6. Display results
    display_split_results(split_epics, archived_path)
```

### Error Handling

- Validate all paths are within .epics/ directory
- Handle subprocess failures gracefully
- Rollback changes if split fails and rollback_on_failure is true
- Provide clear error messages for debugging

### Coordination Role

Main orchestration point that coordinates validation, splitting, and file
operations. Brings together epic_validator, prompts, and file operations into
cohesive workflow.
