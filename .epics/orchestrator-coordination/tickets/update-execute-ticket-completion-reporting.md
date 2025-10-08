# update-execute-ticket-completion-reporting

## Description

Update execute-ticket.md to require standardized completion reporting from
ticket-builder sub-agents.

Sub-agents must return standardized completion reports so the orchestrator can
validate and coordinate. This ticket updates execute-ticket.md with
comprehensive TicketCompletionReport requirements, documenting all
required/optional fields, providing examples, and clarifying validation
expectations.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. Standardized completion reporting is the
contract enabling orchestrator to validate sub-agent work before accepting
completion.

**Architecture:** Sub-agents return TicketCompletionReport in JSON format.
Orchestrator validates git claims, test status, and acceptance criteria before
marking tickets complete.

## Story

As a **ticket-builder sub-agent**, I need **clear completion report
requirements** so that **I know exactly what information to provide to the
orchestrator for successful ticket validation**.

## Acceptance Criteria

### Core Requirements

- Execute-ticket.md documents complete TicketCompletionReport structure
- All required and optional fields are documented with types
- Examples provided for success, failure, and blocked scenarios
- Validation expectations are clearly stated
- Instructions are unambiguous for Claude agents

### Required Fields Documentation

- ticket_id: Identifier matching ticket file
- status: completed | failed | blocked
- branch_name: Git branch created (e.g., ticket/auth-base)
- base_commit: SHA ticket was branched from
- final_commit: SHA of final commit (null if failed)
- files_modified: List of file paths changed
- test_suite_status: passing | failing | skipped
- acceptance_criteria: [{criterion: text, met: bool}]

### Optional Fields Documentation

- failure_reason: Description if status=failed
- blocking_dependency: Ticket ID if status=blocked
- warnings: List of non-fatal issues
- artifacts: Future distributed execution support (null for now)

### Completion Report Examples

- **Example 1:** Successful completion with passing tests
- **Example 2:** Failure with error details
- **Example 3:** Blocked due to dependency

### Validation Expectations

- Sub-agent must ensure all required fields are present
- Orchestrator will validate git claims (branch, commit existence)
- Test failures may cause validation failure
- Acceptance criteria format must match specification

## Integration Points

### Upstream Dependencies

- **define-sub-agent-lifecycle-protocol**: Defines TicketCompletionReport schema

### Downstream Dependencies

- Sub-agents (ticket-builder) read execute-ticket.md for completion report
  format

## Current vs New Flow

### BEFORE (Current State)

Execute-ticket.md lacks standardized completion reporting. Sub-agents don't know
what format to return.

### AFTER (This Ticket)

Execute-ticket.md contains comprehensive "Completion Reporting" section with:

- Complete TicketCompletionReport structure
- All required/optional fields with types and descriptions
- JSON examples for success, failure, blocked scenarios
- Validation expectations clearly stated
- Instructions for generating acceptance criteria list

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-ticket.md`

Add "Completion Reporting" section at the end:

````markdown
## Completion Reporting

### TicketCompletionReport Format

**IMPORTANT:** When you complete ticket execution, you MUST return a
standardized TicketCompletionReport in JSON format.

The orchestrator validates this report before marking the ticket complete. All
required fields must be present and accurate.

### Required Fields

**ticket_id** (string)

- The ticket identifier matching the ticket markdown filename
- Example: "add-user-authentication"

**status** (enum: "completed" | "failed" | "blocked")

- "completed": Ticket work finished successfully
- "failed": Execution failed with errors
- "blocked": Cannot execute due to missing dependency

**branch_name** (string)

- Git branch you created for this ticket
- Format: "ticket/{ticket-id}"
- Example: "ticket/add-user-authentication"

**base_commit** (string)

- Git SHA you branched from (provided by orchestrator)
- Example: "abc123def456789..."

**final_commit** (string | null)

- Git SHA of your final commit on the ticket branch
- Use `git rev-parse HEAD` after completing work
- null if status="failed" or "blocked"

**files_modified** (list of strings)

- List of file paths you created or modified
- Use absolute paths from repository root
- Example: ["/Users/kit/Code/buildspec/cli/auth.py",
  "/Users/kit/Code/buildspec/tests/test_auth.py"]

**test_suite_status** (enum: "passing" | "failing" | "skipped")

- "passing": All tests passed
- "failing": Some tests failed
- "skipped": Tests were not run (document why in warnings)

**acceptance_criteria** (list of objects)

- List of acceptance criteria with met status
- Each object: `{"criterion": "Description", "met": true/false}`
- Extract criteria from ticket markdown's "Acceptance Criteria" section
- Mark each criterion as met or not met based on your work

### Optional Fields

**failure_reason** (string | null)

- Required if status="failed"
- Describe what went wrong
- Include error messages, stack traces, or failure details

**blocking_dependency** (string | null)

- Required if status="blocked"
- Ticket ID of the dependency you're blocked on
- Example: "add-authentication-base"

**warnings** (list of strings)

- Non-fatal issues encountered during execution
- Examples: deprecation warnings, skipped tests, partial implementations
- Empty list if no warnings

**artifacts** (null)

- Reserved for future distributed execution support
- Always set to null

### Example Reports

**Example 1: Successful Completion**

```json
{
  "ticket_id": "add-user-authentication",
  "status": "completed",
  "branch_name": "ticket/add-user-authentication",
  "base_commit": "abc123def456789",
  "final_commit": "789ghi012jkl345",
  "files_modified": [
    "/Users/kit/Code/buildspec/cli/auth.py",
    "/Users/kit/Code/buildspec/cli/models/user.py",
    "/Users/kit/Code/buildspec/tests/unit/test_auth.py"
  ],
  "test_suite_status": "passing",
  "acceptance_criteria": [
    { "criterion": "User can authenticate with password", "met": true },
    { "criterion": "Invalid credentials are rejected", "met": true },
    { "criterion": "Session tokens are generated correctly", "met": true },
    { "criterion": "Token expiration is enforced", "met": true }
  ],
  "warnings": []
}
```
````

**Example 2: Failed Execution**

```json
{
  "ticket_id": "add-user-authentication",
  "status": "failed",
  "branch_name": "ticket/add-user-authentication",
  "base_commit": "abc123def456789",
  "final_commit": null,
  "files_modified": ["/Users/kit/Code/buildspec/cli/auth.py"],
  "test_suite_status": "failing",
  "acceptance_criteria": [],
  "failure_reason": "Test suite failed: test_password_validation failed with AssertionError: Expected password hashing to use bcrypt, but got plaintext storage. Stack trace:\n  File test_auth.py, line 45, in test_password_validation\n    assert user.password.startswith('$2b$')",
  "warnings": [
    "bcrypt library not found in dependencies",
    "Partial implementation completed before test failure"
  ]
}
```

**Example 3: Blocked by Dependency**

```json
{
  "ticket_id": "add-user-sessions",
  "status": "blocked",
  "branch_name": "ticket/add-user-sessions",
  "base_commit": "abc123def456789",
  "final_commit": null,
  "files_modified": [],
  "test_suite_status": "skipped",
  "acceptance_criteria": [],
  "blocking_dependency": "add-user-authentication",
  "failure_reason": "Cannot implement sessions without authentication base. The add-user-authentication ticket has not been completed, and sessions require auth infrastructure.",
  "warnings": []
}
```

### Validation Expectations

The orchestrator will validate your completion report:

**Git Verification:**

- Verify `branch_name` exists: `git rev-parse --verify refs/heads/{branch_name}`
- Verify `final_commit` exists: `git rev-parse --verify {final_commit}`
- Verify commit is on branch: `git branch --contains {final_commit}`

**Test Suite Validation:**

- If `test_suite_status` is "failing", validation will fail
- If "passing", validation proceeds
- If "skipped", document reason in warnings

**Acceptance Criteria Validation:**

- Each criterion must have "criterion" (string) and "met" (boolean) fields
- All criteria from ticket markdown should be included
- Unmet criteria (met=false) are logged but don't fail validation

**Field Validation:**

- All required fields must be present
- Field types must match specification
- Enums must use exact values (case-sensitive)

### Generating Acceptance Criteria List

**Read ticket acceptance criteria:**

```python
# From ticket markdown "Acceptance Criteria" section
acceptance_criteria = [
    "User can authenticate with password",
    "Invalid credentials are rejected",
    "Session tokens are generated correctly",
    "Token expiration is enforced"
]
```

**Evaluate each criterion:**

```python
# For each criterion, determine if your work met it
report_criteria = []
for criterion in acceptance_criteria:
    met = evaluate_criterion(criterion)  # Your implementation logic
    report_criteria.append({
        "criterion": criterion,
        "met": met
    })
```

**Include in completion report:**

```python
completion_report = {
    # ... other fields
    "acceptance_criteria": report_criteria
}
```

### How to Generate final_commit

After completing your work:

```bash
# Ensure you're on your ticket branch
git checkout ticket/{ticket-id}

# Commit your final changes
git add .
git commit -m "Complete {ticket-id}: {description}"

# Get final commit SHA
final_commit=$(git rev-parse HEAD)

# Use in completion report
echo "final_commit: $final_commit"
```

### Common Mistakes to Avoid

**Missing required fields:**

- Always include all 8 required fields
- Use null for final_commit if status is not "completed"

**Invalid status values:**

- Use exact values: "completed", "failed", "blocked"
- NOT: "complete", "success", "done"

**Wrong branch name format:**

- Use "ticket/{ticket-id}", not just "{ticket-id}"
- Example: "ticket/add-auth" not "add-auth"

**Empty acceptance_criteria:**

- Always include criteria from ticket markdown
- Mark each as met=true or met=false
- Empty list only acceptable if status="failed" or "blocked"

**Files_modified with relative paths:**

- Use absolute paths from repository root
- NOT: "../cli/auth.py"
- YES: "/Users/kit/Code/buildspec/cli/auth.py"

### Submitting Your Report

Return your completion report as the final output of ticket execution:

```json
{
  "ticket_id": "...",
  "status": "...",
  ...
}
```

The orchestrator will:

1. Parse your JSON report
2. Validate all fields are present and correct
3. Run git verification commands
4. Check test suite status
5. Record completion in epic-state.json
6. Mark ticket as completed or failed based on validation

````

### Implementation Details

1. **Add Completion Reporting Section:** Insert at end of execute-ticket.md

2. **Document Required Fields:** All 8 required fields with types, descriptions, examples

3. **Document Optional Fields:** 4 optional fields with usage guidance

4. **Provide Examples:** Three complete JSON examples (success, failure, blocked)

5. **Validation Expectations:** Explain what orchestrator will check

6. **Generation Instructions:** How to generate acceptance_criteria and final_commit

7. **Common Mistakes:** List typical errors to avoid

### Integration with Existing Code

Completion reporting integrates with:
- TicketCompletionReport schema from define-sub-agent-lifecycle-protocol
- Orchestrator validation via validate_completion_report()
- Epic-state.json updates based on report content
- Sub-agent instructions in execute-ticket.md

## Error Handling Strategy

- **Missing Required Fields:** Orchestrator validation fails, provides specific error
- **Invalid Field Types:** JSON parsing fails, orchestrator logs error
- **Invalid Enum Values:** Validation fails with enum constraint error
- **Git Verification Failures:** Validation fails with git error details

## Testing Strategy

### Validation Tests

1. **Documentation Completeness:**
   - Verify all required fields documented
   - Check all optional fields documented
   - Ensure examples are valid JSON

2. **Example Validation:**
   - Parse all JSON examples successfully
   - Verify examples match schema
   - Check examples include all required fields

3. **Integration with Orchestrator:**
   - Test orchestrator accepts valid reports
   - Test orchestrator rejects invalid reports
   - Verify validation error messages are helpful

### Test Commands

```bash
# Review completion reporting documentation
cat /Users/kit/Code/buildspec/claude_files/commands/execute-ticket.md | rg -A 500 "Completion Reporting"

# Validate JSON examples
echo '<example_json>' | jq . # Should parse successfully

# Test with orchestrator (integration test)
uv run pytest tests/integration/test_completion_reporting.py -v
````

## Dependencies

- **define-sub-agent-lifecycle-protocol**: Defines TicketCompletionReport schema

## Coordination Role

Updates sub-agent instructions to produce reports matching orchestrator
validation requirements. Establishes the communication contract ensuring
sub-agents provide all necessary information for orchestrator to validate
completion.
