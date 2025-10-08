# add-ticket-count-field

## Description
Update claude_files/commands/create-epic.md to require ticket_count field in epic YAML output.

This establishes the shared interface contract that all epic YAML files must include a ticket_count field at the top level, enabling automatic validation and split detection without expensive full YAML parsing.

## Acceptance Criteria
- create-epic.md includes explicit instruction to add ticket_count field
- Instruction specifies field must be at top level of epic YAML
- Documentation explains field purpose: "Required for automatic validation and split detection"
- Example YAML snippet shows correct placement and format
- Field must be populated with actual ticket array length
- Instruction is clear and unambiguous for Claude agent

## Files to Modify
- /Users/kit/Code/buildspec/claude_files/commands/create-epic.md

## Dependencies
None - This is a foundational requirement

## Implementation Notes

### Required Instruction Text

Add the following to create-epic.md instructions:

```markdown
**CRITICAL: Epic YAML Structure**

The epic YAML file MUST include a `ticket_count` field at the top level:

```yaml
epic: "Epic Name"
description: "Epic description"
ticket_count: 10  # REQUIRED: Number of tickets in this epic
acceptance_criteria:
  - "Criterion 1"
  - "Criterion 2"
tickets:
  - id: ticket-1
    description: "..."
  # ... more tickets
```

The `ticket_count` field is required for automatic validation and split detection. It must be set to the exact number of tickets in the `tickets:` array.
```

### Validation
- After updating, verify create-epic generates YAML with ticket_count field
- Test with sample spec to ensure field is populated correctly
- Ensure field value matches actual ticket count

### Coordination Role
Defines epic YAML format contract with ticket_count field requirement, establishing the shared interface that epic_validator.py will consume.
