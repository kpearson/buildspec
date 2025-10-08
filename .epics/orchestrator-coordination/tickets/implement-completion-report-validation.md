# implement-completion-report-validation

## Description

Implement the validate_completion_report() function in the orchestrator logic to
verify sub-agent completion reports before marking tickets complete.

Sub-agents return completion reports that must be validated before accepting
their claims. This ticket implements comprehensive validation logic including
git verification (branch and commit existence), test suite status checking, and
acceptance criteria format validation.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. Completion report validation is the
trust-but-verify mechanism ensuring sub-agents actually completed their work
before the orchestrator marks tickets as done.

**Architecture:** Validation happens in the 'validating' state after sub-agent
returns. Git commands verify branch and commit existence. Failed validation
transitions ticket to 'failed' state rather than 'completed'.

## Story

As a **buildspec orchestrator**, I need **completion report validation with git
verification** so that **I can trust sub-agent claims and only mark tickets
complete when their work is actually present in the repository**.

## Acceptance Criteria

### Core Requirements

- validate_completion_report() function performs all git verification checks
- Test suite status is validated according to defined rules
- Acceptance criteria format is validated
- State updates correctly handle validation pass and fail scenarios
- Execute-epic.md documents complete validation algorithm

### Git Verification Checks

- Verify branch exists: `git rev-parse --verify refs/heads/{branch_name}`
- Verify final commit exists: `git rev-parse --verify {final_commit}` (if
  status=completed)
- Verify commit is on branch: `git branch --contains {final_commit}` includes
  branch_name
- Handle errors: branch not found, commit not found, commit not on branch

### Test Suite Validation

- Check test_suite_status is one of: 'passing', 'failing', 'skipped'
- If status='failing', validation fails (unless explicitly allowed in future)
- If status='skipped', validation passes (ticket may intentionally skip tests)
- If status='passing', validation passes

### Acceptance Criteria Validation

- Check acceptance_criteria is list of objects
- Each object must have 'criterion' (string) and 'met' (boolean) fields
- Verify all criteria have status (met or not met)
- Log any unmet criteria for reporting

### State Update Logic

- **Validation Pass:** ticket.status='completed', update git_info, record
  completed_at timestamp
- **Validation Fail:** ticket.status='failed', record validation failure reason,
  do NOT update git_info

## Integration Points

### Upstream Dependencies

- **define-sub-agent-lifecycle-protocol**: Defines TicketCompletionReport format
  being validated

### Downstream Dependencies

- **add-wave-execution-algorithm**: Calls validate_completion_report() after
  sub-agent returns

## Current vs New Flow

### BEFORE (Current State)

No validation exists. Execute-epic.md vaguely mentions "verify completion" but
doesn't specify how.

### AFTER (This Ticket)

Execute-epic.md contains complete validate_completion_report() algorithm with:

- Git verification command sequences
- Test suite validation rules
- Acceptance criteria format checking
- State update logic for pass/fail scenarios
- Error handling for each validation failure mode

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-epic.md`

Add "Completion Report Validation" section:

````markdown
## Completion Report Validation

### validate_completion_report() Function

**Purpose:** Verify sub-agent completion report before marking ticket complete.

**Input:**

- `ticket`: Ticket object with metadata
- `report`: TicketCompletionReport dict from sub-agent

**Output:**

- `ValidationResult` object with `passed` (boolean) and `error` (string | null)

**Algorithm:**

```python
def validate_completion_report(ticket: Ticket, report: dict) -> ValidationResult:
    """
    Validate sub-agent completion report.

    Returns ValidationResult with passed=True/False and error message.
    """
    # 1. Validate required fields present
    required_fields = [
        'ticket_id', 'status', 'branch_name', 'base_commit',
        'final_commit', 'files_modified', 'test_suite_status',
        'acceptance_criteria'
    ]

    for field in required_fields:
        if field not in report:
            return ValidationResult(
                passed=False,
                error=f"Missing required field: {field}"
            )

    # 2. Validate ticket_id matches
    if report['ticket_id'] != ticket.id:
        return ValidationResult(
            passed=False,
            error=f"Ticket ID mismatch: expected {ticket.id}, got {report['ticket_id']}"
        )

    # 3. Git verification (only if status=completed)
    if report['status'] == 'completed':
        git_result = verify_git_artifacts(report)
        if not git_result.passed:
            return git_result

    # 4. Test suite validation
    test_result = validate_test_suite_status(report)
    if not test_result.passed:
        return test_result

    # 5. Acceptance criteria format validation
    ac_result = validate_acceptance_criteria_format(report)
    if not ac_result.passed:
        return ac_result

    # All validations passed
    return ValidationResult(passed=True, error=None)
```
````

### Git Verification

**Purpose:** Verify branch and commit actually exist in repository.

**Implementation:**

```python
def verify_git_artifacts(report: dict) -> ValidationResult:
    """
    Verify git branch and commit exist.

    Runs git commands to verify:
    1. Branch exists
    2. Final commit exists
    3. Commit is on the branch
    """
    branch_name = report['branch_name']
    final_commit = report['final_commit']

    # Check branch exists
    result = subprocess.run(
        ['git', 'rev-parse', '--verify', f'refs/heads/{branch_name}'],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return ValidationResult(
            passed=False,
            error=f"Branch not found: {branch_name}"
        )

    # Check final commit exists (if not null)
    if final_commit:
        result = subprocess.run(
            ['git', 'rev-parse', '--verify', final_commit],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return ValidationResult(
                passed=False,
                error=f"Commit not found: {final_commit}"
            )

        # Check commit is on the branch
        result = subprocess.run(
            ['git', 'branch', '--contains', final_commit],
            capture_output=True,
            text=True
        )
        if branch_name not in result.stdout:
            return ValidationResult(
                passed=False,
                error=f"Commit {final_commit} not found on branch {branch_name}"
            )

    return ValidationResult(passed=True, error=None)
```

### Test Suite Validation

**Purpose:** Verify test suite status is valid and acceptable.

**Implementation:**

```python
def validate_test_suite_status(report: dict) -> ValidationResult:
    """
    Validate test suite status.

    Rules:
    - Status must be one of: 'passing', 'failing', 'skipped'
    - 'failing' status causes validation failure
    - 'skipped' status is acceptable
    - 'passing' status is acceptable
    """
    test_status = report['test_suite_status']

    valid_statuses = ['passing', 'failing', 'skipped']
    if test_status not in valid_statuses:
        return ValidationResult(
            passed=False,
            error=f"Invalid test_suite_status: {test_status}. Must be one of {valid_statuses}"
        )

    if test_status == 'failing':
        return ValidationResult(
            passed=False,
            error="Test suite is failing. Ticket cannot be marked complete with failing tests."
        )

    return ValidationResult(passed=True, error=None)
```

### Acceptance Criteria Validation

**Purpose:** Verify acceptance criteria format is correct.

**Implementation:**

```python
def validate_acceptance_criteria_format(report: dict) -> ValidationResult:
    """
    Validate acceptance criteria format.

    Format: list of objects with 'criterion' (string) and 'met' (boolean)
    """
    criteria = report['acceptance_criteria']

    if not isinstance(criteria, list):
        return ValidationResult(
            passed=False,
            error="acceptance_criteria must be a list"
        )

    for i, criterion in enumerate(criteria):
        if not isinstance(criterion, dict):
            return ValidationResult(
                passed=False,
                error=f"acceptance_criteria[{i}] must be an object"
            )

        if 'criterion' not in criterion:
            return ValidationResult(
                passed=False,
                error=f"acceptance_criteria[{i}] missing 'criterion' field"
            )

        if 'met' not in criterion:
            return ValidationResult(
                passed=False,
                error=f"acceptance_criteria[{i}] missing 'met' field"
            )

        if not isinstance(criterion['met'], bool):
            return ValidationResult(
                passed=False,
                error=f"acceptance_criteria[{i}]['met'] must be boolean"
            )

    # Log unmet criteria for reporting
    unmet = [c['criterion'] for c in criteria if not c['met']]
    if unmet:
        logger.warning(f"Ticket {report['ticket_id']} has unmet criteria: {unmet}")

    return ValidationResult(passed=True, error=None)
```

### State Update After Validation

**Validation Passed:**

```python
ticket.status = 'completed'
ticket.completed_at = datetime.now(UTC).isoformat()
ticket.git_info = {
    'branch_name': report['branch_name'],
    'base_commit': report['base_commit'],
    'final_commit': report['final_commit']
}
update_epic_state(state, {ticket.id: ticket})
logger.info(f"Ticket {ticket.id} validated and marked complete")
```

**Validation Failed:**

```python
ticket.status = 'failed'
ticket.failure_reason = f'validation_failed: {validation_result.error}'
ticket.completed_at = datetime.now(UTC).isoformat()
# Do NOT update git_info
update_epic_state(state, {ticket.id: ticket})
logger.error(f"Ticket {ticket.id} validation failed: {validation_result.error}")
```

````

### Implementation Details

1. **Add Validation Section:** Insert after Sub-Agent Lifecycle section in execute-epic.md

2. **Document validate_completion_report():** Complete algorithm with all validation checks

3. **Git Verification:** Exact git commands with error handling

4. **Test Suite Validation:** Rules for passing/failing/skipped statuses

5. **Acceptance Criteria:** Format validation and unmet criteria logging

6. **State Updates:** Logic for validation pass/fail scenarios

### Integration with Existing Code

The validation logic integrates with:
- TicketCompletionReport schema from define-sub-agent-lifecycle-protocol
- Epic-state.json updates via update_epic_state()
- Git repository for verification commands
- Wave execution loop for post-return validation

## Error Handling Strategy

- **Missing Required Fields:** Validation fails with specific field name
- **Branch Not Found:** Git command fails → validation fails
- **Commit Not Found:** Git command fails → validation fails
- **Commit Not On Branch:** Git command succeeds but branch name not in output → validation fails
- **Failing Tests:** test_suite_status='failing' → validation fails
- **Invalid Acceptance Criteria:** Format errors → validation fails with specific issue

## Testing Strategy

### Validation Tests

1. **Git Verification:**
   - Test with valid branch and commit (should pass)
   - Test with missing branch (should fail)
   - Test with missing commit (should fail)
   - Test with commit not on branch (should fail)

2. **Test Suite Validation:**
   - Test with status='passing' (should pass)
   - Test with status='failing' (should fail)
   - Test with status='skipped' (should pass)
   - Test with invalid status (should fail)

3. **Acceptance Criteria:**
   - Test with valid format (should pass)
   - Test with missing 'criterion' field (should fail)
   - Test with missing 'met' field (should fail)
   - Test with non-boolean 'met' (should fail)

### Test Commands

```bash
# Run validation tests
uv run pytest tests/unit/test_validation.py::test_validate_completion_report -v

# Test git verification
uv run pytest tests/unit/test_validation.py::test_verify_git_artifacts -v

# Test test suite validation
uv run pytest tests/unit/test_validation.py::test_validate_test_suite_status -v

# Test acceptance criteria validation
uv run pytest tests/unit/test_validation.py::test_validate_acceptance_criteria_format -v
````

## Dependencies

- **define-sub-agent-lifecycle-protocol**: Defines TicketCompletionReport format

## Coordination Role

Provides completion validation that wave execution uses to transition tickets to
completed state. The validation ensures sub-agent claims are verified before
accepting completion, maintaining data integrity and trust in the coordination
system.
