# prompts-build-split-epic

## Description

Add build_split_epic() method to cli/core/prompts.py for specialist prompt
construction.

This method creates the specialist prompt that combines the split-epic command
instructions with context about the specific epic being split, preparing it for
the Claude subprocess that will perform the actual splitting.

## Acceptance Criteria

- build_split_epic() method signature: (original_epic_path: str, spec_path: str,
  ticket_count: int) -> str
- Loads split-epic.md command template from claude_files/commands/
- Injects epic file path, spec path, and ticket count into prompt
- Includes deliverable identification criteria in prompt
- Includes independence requirements and grouping heuristics
- Returns formatted prompt string ready for Claude subprocess
- Handles missing command file gracefully with clear error
- Method follows existing prompts.py patterns

## Files to Modify

- /Users/kit/Code/buildspec/cli/core/prompts.py

## Dependencies

- split-epic-specialist-command

## Implementation Notes

### Method Signature

```python
def build_split_epic(self, original_epic_path: str, spec_path: str, ticket_count: int) -> str:
    """
    Create specialist prompt for splitting oversized epics.

    Args:
        original_epic_path: Absolute path to original epic YAML file
        spec_path: Absolute path to spec document
        ticket_count: Number of tickets in original epic

    Returns:
        Formatted prompt string for Claude subprocess

    Raises:
        FileNotFoundError: If split-epic.md command file missing
    """
    pass
```

### Prompt Construction

The prompt should include:

1. Load split-epic.md command template
2. Add context section with:
   - Original epic path: {original_epic_path}
   - Spec document path: {spec_path}
   - Ticket count: {ticket_count}
   - Soft limit: 12 tickets per epic
   - Hard limit: 15 tickets per epic
3. Include all specialist instructions from command file
4. Format for direct use in subprocess.run()

### Integration Pattern

Follow existing pattern in prompts.py:

- Use Path objects for file handling
- Load command files from claude_files/commands/
- Format with clear section separators
- Include error context for debugging

### Coordination Role

Bridges validation results to specialist agent invocation by constructing the
complete prompt that combines command template with epic-specific context.
