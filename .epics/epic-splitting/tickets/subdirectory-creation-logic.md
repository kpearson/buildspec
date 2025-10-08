# subdirectory-creation-logic

## Description

Implement create_split_subdirectories() in cli/commands/create_epic.py to create
the subdirectory structure for each split epic.

This function creates the proper directory organization that the specialist
agent expects, with each split epic getting its own subdirectory containing the
epic YAML file and a tickets/ folder.

## Acceptance Criteria

- create_split_subdirectories() signature: (base_dir: str, epic_names:
  list[str]) -> list[str]
- For each epic name, creates [base-dir]/[epic-name]/ directory
- Creates [base-dir]/[epic-name]/tickets/ subdirectory
- Validates all paths are within .epics/ directory (security check)
- Returns list of created directory paths for verification
- Handles directory creation errors gracefully
- Uses pathlib.Path for cross-platform compatibility
- Skips creation if directory already exists (idempotent)

## Files to Modify

- /Users/kit/Code/buildspec/cli/commands/create_epic.py

## Dependencies

- create-epic-split-workflow

## Implementation Notes

### Function Signature

```python
def create_split_subdirectories(base_dir: str, epic_names: list[str]) -> list[str]:
    """
    Create subdirectory structure for each split epic.

    Creates the directory structure:
    [base-dir]/[epic-name]/
    [base-dir]/[epic-name]/tickets/

    Args:
        base_dir: Base directory path (e.g., .epics/user-auth/)
        epic_names: List of epic names for subdirectories

    Returns:
        List of created directory paths

    Raises:
        ValueError: If paths are outside .epics/ directory
        OSError: If directory creation fails
    """
    base_path = Path(base_dir).resolve()
    epics_root = Path(".epics").resolve()

    # Security: Validate paths are within .epics/
    if not str(base_path).startswith(str(epics_root)):
        raise ValueError(f"Path {base_path} is outside .epics/ directory")

    created_dirs = []

    for epic_name in epic_names:
        # Create epic subdirectory
        epic_dir = base_path / epic_name
        epic_dir.mkdir(parents=True, exist_ok=True)

        # Create tickets subdirectory
        tickets_dir = epic_dir / "tickets"
        tickets_dir.mkdir(exist_ok=True)

        created_dirs.append(str(epic_dir))
        console.print(f"[green]Created directory: {epic_dir}[/green]")

    return created_dirs
```

### Directory Structure Example

After execution for epics ["token-caching", "token-caching-integration"]:

```
.epics/user-auth/
├── user-auth-spec.md (already exists)
├── token-caching/
│   ├── tickets/
│   └── (epic YAML will be written by specialist)
└── token-caching-integration/
    ├── tickets/
    └── (epic YAML will be written by specialist)
```

### Error Handling

- Check permissions before creating directories
- Provide clear error messages if creation fails
- Validate epic names are valid directory names
- Log all directory creation for debugging

### Coordination Role

Creates file system structure that split epics will be written into, ensuring
the specialist agent has the expected directory layout for its output.
