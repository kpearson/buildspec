# epic-validator-module

## Description

Create cli/utils/epic_validator.py module for post-creation validation to detect
oversized epics that need splitting.

This module provides the core validation logic that examines epic YAML files and
determines if they exceed the ticket count threshold (>=13 tickets), triggering
the split workflow.

## Acceptance Criteria

- parse_epic_yaml() function parses YAML and extracts ticket_count field
- validate_ticket_count() function returns True if ticket_count >= 13 (needs
  split)
- YAML parsing errors are handled gracefully with informative error messages
- Function returns structured dict with: {'ticket_count': int, 'epic': str,
  'tickets': list}
- Module is importable from cli.utils.epic_validator
- All edge cases handled: missing ticket_count field, invalid YAML, file not
  found
- Unit tests cover all validation scenarios

## Files to Modify

- /Users/kit/Code/buildspec/cli/utils/epic_validator.py (NEW FILE)

## Dependencies

None - This is a foundational module

## Implementation Notes

### Function Signatures

```python
def parse_epic_yaml(epic_file_path: str) -> dict:
    """
    Parse epic YAML file and extract ticket count for validation.

    Args:
        epic_file_path: Absolute path to epic YAML file

    Returns:
        dict with keys: 'ticket_count', 'epic', 'tickets'

    Raises:
        FileNotFoundError: If epic file doesn't exist
        yaml.YAMLError: If YAML is malformed
        KeyError: If required fields missing
    """
    pass

def validate_ticket_count(ticket_count: int) -> bool:
    """
    Check if ticket count exceeds threshold and needs splitting.

    Args:
        ticket_count: Number of tickets in epic

    Returns:
        True if ticket_count >= 13 (needs split), False otherwise
    """
    pass
```

### Error Handling

- Gracefully handle missing files with FileNotFoundError
- Handle YAML parsing errors with yaml.YAMLError
- Provide clear error messages for missing required fields
- Log validation attempts for debugging

### Coordination Role

Provides ticket count validation interface for create-epic command. This is the
foundation for automatic epic splitting detection.
