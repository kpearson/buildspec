# archive-original-epic

## Description

Implement archive_original_epic() in cli/commands/create_epic.py to archive the
original oversized epic.

This function preserves the original epic by renaming it with a .original
suffix, allowing users to reference the original planning while the split epics
are executed independently.

## Acceptance Criteria

- archive_original_epic() signature: (epic_path: str) -> str
- Renames [epic].epic.yaml to [epic].epic.yaml.original
- Preserves file content exactly (no modifications to content)
- Returns path to archived file for verification
- Handles file operation errors gracefully with clear messages
- Validates epic_path is within .epics/ directory (security check)
- Uses pathlib.Path for cross-platform compatibility
- Handles case where .original file already exists (overwrites with warning)

## Files to Modify

- /Users/kit/Code/buildspec/cli/commands/create_epic.py

## Dependencies

- create-epic-split-workflow

## Implementation Notes

### Function Signature

```python
def archive_original_epic(epic_path: str) -> str:
    """
    Archive the original oversized epic by renaming with .original suffix.

    Args:
        epic_path: Absolute path to epic YAML file

    Returns:
        Path to archived file (.original)

    Raises:
        ValueError: If path is outside .epics/ directory
        OSError: If file operation fails
    """
    epic_file = Path(epic_path).resolve()
    epics_root = Path(".epics").resolve()

    # Security: Validate path is within .epics/
    if not str(epic_file).startswith(str(epics_root)):
        raise ValueError(f"Path {epic_file} is outside .epics/ directory")

    # Create archived filename
    archived_path = epic_file.with_suffix(epic_file.suffix + ".original")

    # Warn if .original already exists
    if archived_path.exists():
        console.print(f"[yellow]Warning: {archived_path} already exists, overwriting[/yellow]")

    # Rename file
    epic_file.rename(archived_path)
    console.print(f"[green]Archived original epic: {archived_path}[/green]")

    return str(archived_path)
```

### Example Usage

Before:

```
.epics/user-auth/user-auth.epic.yaml
```

After:

```
.epics/user-auth/user-auth.epic.yaml.original
```

### Error Handling

- Check file exists before attempting rename
- Handle permission errors with clear message
- Validate epic_path points to .epic.yaml file
- Log all file operations for debugging

### Coordination Role

Preserves original epic for reference while making room for split epics. Ensures
no data loss during the split process.
