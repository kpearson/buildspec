# Epic: Code Review Integration

## Epic Summary

Integrate an autonomous code review agent into the ticket execution workflow to
ensure code quality, adherence to requirements, pattern consistency, and test
coverage before marking tickets as complete. The review agent acts as a quality
gate with pass/fail authority and provides actionable feedback for revisions.

## Problem Statement

Currently, ticket execution flows directly from validation to completion:

```
pending → queued → executing → validating → completed
```

**Validation only checks:**

- Git branch/commit exists
- Test suite runs (pass/fail)
- Acceptance criteria are addressed

**Validation does NOT check:**

- Code quality and maintainability
- Adherence to ticket requirements (did it actually build what was requested?)
- Compatibility with epic coordination requirements
- Conformance to codebase patterns and idioms
- Test quality and coverage depth
- Security issues or anti-patterns
- Performance considerations

**This gap means:**

- Low-quality code can reach "completed" status
- Tickets can claim acceptance criteria met while missing the intent
- Pattern violations accumulate across the codebase
- Test coverage can be superficial but passing
- Technical debt builds up invisibly

## Goals

1. **Quality Gate**: Add autonomous code review as mandatory step before ticket
   completion
2. **Review Agent**: Create specialized agent that evaluates code against
   multiple quality dimensions
3. **Feedback Loop**: Enable tickets to iterate based on review feedback
   (revision workflow)
4. **State Machine Extension**: Add review states to ticket lifecycle with retry
   limits
5. **Review Reports**: Standardize review output format for orchestrator
   validation
6. **Pattern Awareness**: Review agent understands epic coordination
   requirements and codebase patterns

## Success Criteria

- Code review state added to ticket lifecycle (validating → reviewing →
  completed)
- Review agent spawned after validation, before completion
- Review reports follow standardized format with pass/fail and actionable
  feedback
- Failed reviews trigger revision workflow (needs_revision → executing with
  feedback)
- Retry limits prevent infinite review loops (max 2 revisions)
- Review agent has access to epic context, ticket requirements, and codebase
  patterns
- Epic-state.json tracks review history and revision attempts
- Integration tests validate review workflow including pass, fail, and retry
  scenarios

## Architecture Overview

### Extended State Machine

#### New Ticket States

```yaml
reviewing:
  description: "Code review agent evaluating ticket work quality"
  entry_conditions:
    - "Ticket status = validating"
    - "Validation passed (git checks, tests pass, acceptance criteria complete)"
  entry_actions:
    - "Spawn code review agent with ticket context"
    - "Update ticket status to 'reviewing'"
    - "Record review_started_at timestamp"
  exit_transitions:
    - to: completed
      condition: "Review status = pass"
      action: "Record review approval, mark ticket complete"
    - to: needs_revision
      condition: "Review status = fail AND revision_count < MAX_REVISIONS"
      action: "Record review feedback, increment revision_count"
    - to: failed
      condition: "Review status = fail AND revision_count >= MAX_REVISIONS"
      action: "Record review failure, mark ticket failed"

needs_revision:
  description:
    "Ticket failed code review, requires improvements based on feedback"
  entry_conditions:
    - "Review status = fail"
    - "revision_count < MAX_REVISIONS"
  entry_actions:
    - "Record review feedback in epic-state.json"
    - "Update ticket status to 'needs_revision'"
    - "Prepare revision context for builder agent"
  exit_transitions:
    - to: executing
      condition: "Ready to retry with review feedback"
      action: "Spawn builder agent with original ticket + review feedback"
  retry_limit: "MAX_REVISIONS = 2 (total: 1 original attempt + 2 revisions)"
```

#### Updated Ticket Lifecycle Flow

```
Standard flow (review passes):
pending → queued → executing → validating → reviewing → completed

Revision flow (review fails):
pending → queued → executing → validating → reviewing → needs_revision → executing → validating → reviewing → completed

Max revisions exceeded:
... → reviewing → needs_revision → executing → validating → reviewing → failed (with review failure reason)
```

### Code Review Agent Specification

#### Agent Type

- **Name**: code-review
- **Purpose**: Autonomous evaluation of ticket implementation quality
- **Invocation**: Spawned by orchestrator after ticket validation passes
- **Tools**: Read, Grep, Glob, Bash (for running linters, coverage tools)
- **Model**: sonnet (fast, cost-effective for review tasks)

#### Agent Inputs

**TicketReviewContext** (provided by orchestrator)

```python
{
  "ticket_id": "string",
  "ticket_path": "string (path to ticket markdown)",
  "epic_path": "string (path to epic YAML for coordination context)",
  "ticket_branch": "string (e.g., ticket/auth-base)",
  "base_commit": "string (SHA where ticket branched from)",
  "final_commit": "string (SHA of completed work)",
  "files_modified": ["list of file paths"],
  "test_suite_status": "passing|failing",
  "acceptance_criteria": [{"criterion": "text", "met": true}],
  "revision_count": "int (0 for first review, 1+ for revisions)",
  "previous_review_feedback": "string | null (feedback from previous review if revision)"
}
```

#### Agent Review Dimensions

**1. Requirement Adherence** (Critical)

- Does the code implement what the ticket actually requested?
- Are all acceptance criteria genuinely met (not just claimed)?
- Are file modifications aligned with ticket technical details?
- Is the work scope appropriate (not over-engineering, not under-delivering)?

**2. Epic Coordination Compliance** (Critical)

- Does code follow coordination requirements from epic YAML?
- Are function profiles (names, arity, intent) implemented as specified?
- Does directory structure match epic organization patterns?
- Are shared interfaces implemented correctly?
- Are breaking changes avoided (prohibited changes)?

**3. Code Quality** (Important)

- Is code readable and maintainable?
- Are functions/classes appropriately sized and focused?
- Are variable names clear and descriptive?
- Is error handling appropriate and comprehensive?
- Are edge cases handled?

**4. Pattern Consistency** (Important)

- Does code follow existing codebase patterns?
- Is it idiomatic for the language/framework?
- Does it match architecture decisions from epic?
- Are common utilities/libraries used (not reinventing)?

**5. Test Quality** (Important)

- Do tests actually validate functionality?
- Is test coverage sufficient for the changes?
- Are edge cases tested?
- Are tests maintainable and clear?
- Do tests follow project testing patterns?

**6. Security & Performance** (Moderate)

- Are there obvious security issues (injection, auth, secrets)?
- Are there performance red flags (N+1 queries, unbounded loops)?
- Are resources properly managed (file handles, connections)?

#### Agent Output Format

**ReviewReport** (standardized schema)

```json
{
  "ticket_id": "string",
  "reviewed_at": "ISO8601 timestamp",
  "reviewer": "code-review-agent",
  "status": "pass | fail",
  "overall_score": "int (0-100)",
  "revision_count": "int",

  "dimension_scores": {
    "requirement_adherence": { "score": 95, "weight": "critical" },
    "coordination_compliance": { "score": 100, "weight": "critical" },
    "code_quality": { "score": 80, "weight": "important" },
    "pattern_consistency": { "score": 85, "weight": "important" },
    "test_quality": { "score": 70, "weight": "important" },
    "security_performance": { "score": 90, "weight": "moderate" }
  },

  "findings": [
    {
      "dimension": "test_quality",
      "severity": "warning | error | info",
      "file": "src/auth/base.py",
      "line": 45,
      "message": "Missing test case for null username input",
      "suggestion": "Add test_authenticate_with_null_username() test case"
    }
  ],

  "blocking_issues": [
    {
      "dimension": "coordination_compliance",
      "message": "authenticateUser function has arity 3 but epic specifies arity 2",
      "required_action": "Remove third parameter or update epic coordination requirements"
    }
  ],

  "revision_notes": "string | null (actionable feedback for builder agent if status=fail)",

  "approved": "boolean (true if status=pass, false if status=fail)",

  "pass_criteria_met": {
    "all_critical_dimensions_pass": "boolean",
    "no_blocking_issues": "boolean",
    "overall_score_above_threshold": "boolean (>= 75)"
  }
}
```

#### Pass/Fail Logic

**Pass Criteria (ALL must be true):**

- `dimension_scores.requirement_adherence.score >= 90` (critical)
- `dimension_scores.coordination_compliance.score >= 90` (critical)
- `dimension_scores.code_quality.score >= 70` (important)
- `dimension_scores.pattern_consistency.score >= 70` (important)
- `dimension_scores.test_quality.score >= 70` (important)
- `blocking_issues.length == 0` (no blocking issues)
- `overall_score >= 75` (weighted average)

**Fail Triggers:**

- Any critical dimension < 90
- Any blocking issue present
- Overall score < 75

### Revision Workflow

#### Revision Context

When review fails and ticket moves to `needs_revision`, the orchestrator
prepares:

```python
RevisionContext = {
  "original_ticket": "TicketContent",
  "review_report": "ReviewReport from failed review",
  "revision_instructions": """
    REVISION REQUIRED

    Your previous implementation was reviewed and requires improvements.

    Review Status: FAIL
    Overall Score: {score}/100

    BLOCKING ISSUES:
    {blocking_issues}

    REQUIRED CHANGES:
    {revision_notes}

    DIMENSION SCORES:
    {dimension_scores}

    Please address all blocking issues and revision notes.
    Maintain all previously working functionality.
    Re-run tests to ensure nothing breaks.
  """
}
```

#### Builder Agent Re-Execution

When spawning builder agent for revision:

1. **Same ticket file** - Requirements haven't changed
2. **Add revision context** - Include review feedback in prompt
3. **Same base commit** - Don't rebase, just improve existing work
4. **Amend or new commits** - Builder decides (both are fine)
5. **Re-validate** - Full validation again (git checks, tests)
6. **Re-review** - Full review again with fresh evaluation

#### Retry Limits

```yaml
MAX_REVISIONS: 2

Attempt tracking:
  - revision_count = 0: Original attempt
  - revision_count = 1: First revision
  - revision_count = 2: Second revision
  - revision_count >= 3: Fail ticket (max retries exceeded)

Epic-state tracking:
  tickets:
    ticket-id:
      revision_count: int
      review_history:
        [
          { attempt: 0, status: fail, score: 65, reviewed_at: timestamp },
          { attempt: 1, status: fail, score: 80, reviewed_at: timestamp },
          { attempt: 2, status: pass, score: 90, reviewed_at: timestamp },
        ]
```

### Orchestrator Integration

#### State Update Protocol

**After validation passes:**

```python
if ticket.status == "validating" and validation_result.passed:
    ticket.status = "reviewing"
    ticket.review_started_at = now()
    review_context = build_review_context(ticket, epic, state)
    review_handle = spawn_review_agent(review_context)
    update_epic_state(state, ticket)
```

**After review completes:**

```python
review_report = wait_for_review_completion(review_handle)

if review_report.status == "pass":
    ticket.status = "completed"
    ticket.review_approved = True
    ticket.completed_at = now()
    update_epic_state(state, ticket)

elif review_report.status == "fail" and ticket.revision_count < MAX_REVISIONS:
    ticket.status = "needs_revision"
    ticket.revision_count += 1
    ticket.review_history.append(review_report)
    update_epic_state(state, ticket)
    # Orchestrator will re-spawn builder in next wave

elif review_report.status == "fail" and ticket.revision_count >= MAX_REVISIONS:
    ticket.status = "failed"
    ticket.failure_reason = f"Review failed after {MAX_REVISIONS} revisions"
    ticket.review_history.append(review_report)
    update_epic_state(state, ticket)
```

### Epic-State Schema Extension

```json
{
  "tickets": {
    "ticket-id": {
      "status": "pending|queued|executing|validating|reviewing|needs_revision|completed|failed|blocked",

      "revision_count": 0,

      "review_started_at": "ISO8601 timestamp | null",
      "review_completed_at": "ISO8601 timestamp | null",
      "review_approved": "boolean | null",

      "review_history": [
        {
          "attempt": 0,
          "reviewed_at": "ISO8601",
          "status": "pass|fail",
          "overall_score": 85,
          "blocking_issues_count": 0,
          "revision_notes": "string | null"
        }
      ],

      "current_review_report": {
        "... full ReviewReport schema ..."
      }
    }
  }
}
```

## Coordination Requirements

### Breaking Changes Prohibited

- Must not change existing ticket state machine for non-reviewed tickets
- Must not modify execute-ticket.md Task Agent Instructions interface
- Must not break existing validation logic
- Must maintain backward compatibility with epic-state.json schema (add fields,
  don't change existing)

### Function Profiles

**ExecuteEpicOrchestrator** (execute-epic.md additions)

- `spawn_review_agent(review_context: ReviewContext) -> ReviewHandle`
  - Spawn code review agent via Task tool
  - Pass ticket context and epic coordination requirements
  - Return handle for tracking review completion

- `build_review_context(ticket: Ticket, epic: Epic, state: EpicState) -> ReviewContext`
  - Extract all context needed for review
  - Include ticket requirements, epic coordination, file changes
  - Include previous review feedback if revision

- `handle_review_result(ticket: Ticket, review_report: ReviewReport) -> None`
  - Process review pass (mark completed)
  - Process review fail (trigger revision or fail ticket)
  - Update epic-state.json with review results

- `build_revision_context(ticket: Ticket, review_report: ReviewReport) -> RevisionContext`
  - Combine original ticket with review feedback
  - Format revision instructions for builder agent
  - Include blocking issues and dimension scores

**CodeReviewAgent** (new agent)

- `review_ticket_implementation(context: ReviewContext) -> ReviewReport`
  - Evaluate code across all review dimensions
  - Generate dimension scores and findings
  - Determine pass/fail based on criteria
  - Provide actionable revision notes if fail

### Directory Structure

```
claude_files/
  agents/
    code-review.md               # Code review agent instructions
  commands/
    execute-epic.md              # Updated with review workflow
    execute-ticket.md            # Updated with revision handling
```

### Shared Interfaces

**ReviewContext** (input to review agent)

- Standardized structure for ticket review
- Includes ticket requirements, epic context, file changes
- Enables review agent to evaluate against multiple dimensions

**ReviewReport** (output from review agent)

- Standardized pass/fail decision format
- Dimension scores with severity weights
- Findings list with actionable suggestions
- Blocking issues that must be resolved

**RevisionContext** (input to builder agent for revisions)

- Original ticket requirements
- Review feedback and blocking issues
- Revision instructions
- Previous attempt history

### Performance Contracts

- **Review execution time**: < 2 minutes per ticket (agent evaluation + tool
  usage)
- **State update overhead**: < 100ms (adding review fields to epic-state.json)
- **Revision spawn time**: < 5s (same as initial ticket spawn)

### Security Constraints

- Review agent must not have write access (read-only evaluation)
- Review reports sanitized before logging (no code injection via findings)
- Revision context must validate review feedback before passing to builder

### Architectural Decisions

**Technology Choices**

- Task tool for review agent spawning (consistent with orchestrator pattern)
- Sonnet model for review agent (cost-effective, sufficient for evaluation)
- JSON schema for ReviewReport (structured, parseable, validatable)

**Patterns**

- Review as quality gate (must pass to reach completed)
- Feedback loop with retry limits (enable improvement, prevent infinite loops)
- Dimension-based scoring (transparent, actionable feedback)
- Passive monitoring (wait for review agent completion, no polling)

**Design Principles**

- **Quality over speed**: Review adds time but ensures quality
- **Actionable feedback**: Review reports must tell builder what to fix
- **Finite retries**: Prevent infinite review loops with MAX_REVISIONS
- **Context-aware review**: Review agent has full epic and codebase context
- **Pass/fail authority**: Review agent has final say on code quality

**Constraints**

- MAX_REVISIONS = 2 (1 original + 2 revisions max)
- Review pass threshold = 75 overall score
- Critical dimensions must score >= 90 (requirement adherence, coordination
  compliance)
- Important dimensions must score >= 70 (code quality, patterns, tests)

## Related Issues

### Tickets

1. **add-review-states-to-state-machine**
   - Add reviewing and needs_revision states to ticket lifecycle
   - Define state transitions for review pass/fail
   - Document retry limit logic

2. **create-code-review-agent**
   - Create claude_files/agents/code-review.md agent definition
   - Document review dimensions and scoring logic
   - Define ReviewReport output format

3. **implement-review-agent-spawning**
   - Add spawn_review_agent() to orchestrator
   - Implement build_review_context() function
   - Trigger review after validation passes

4. **implement-review-result-handling**
   - Add handle_review_result() to orchestrator
   - Process review pass (mark completed)
   - Process review fail (trigger revision workflow)

5. **implement-revision-workflow**
   - Add build_revision_context() function
   - Re-spawn builder agent with review feedback
   - Track revision attempts in epic-state.json

6. **add-review-report-validation**
   - Validate ReviewReport schema before accepting
   - Verify pass/fail logic is correctly applied
   - Ensure blocking issues are present for failures

7. **extend-epic-state-schema**
   - Add review_history, revision_count fields to ticket state
   - Add review_started_at, review_completed_at timestamps
   - Maintain backward compatibility with existing fields

8. **update-execute-ticket-for-revisions**
   - Update execute-ticket.md to handle revision context
   - Document how builder should use review feedback
   - Clarify revision vs fresh implementation approach

9. **add-review-integration-tests**
   - Test review pass (ticket completes)
   - Test review fail with successful revision
   - Test review fail exceeding max revisions (ticket fails)
   - Test review workflow with multiple tickets in parallel

## Acceptance Criteria

- [ ] Ticket state machine includes reviewing and needs_revision states
- [ ] Code review agent spawned after validation, before completion
- [ ] Review reports follow standardized format with dimension scores
- [ ] Review pass marks ticket completed
- [ ] Review fail triggers revision workflow with feedback
- [ ] Revision attempts limited to MAX_REVISIONS (2)
- [ ] After max revisions, ticket marked as failed
- [ ] Epic-state.json tracks review history and revision counts
- [ ] Review agent has access to epic coordination requirements
- [ ] Integration tests validate full review workflow

## Notes

### Why Code Review is Essential for Autonomous Agents

When humans write code:

- Code review catches mistakes before merge
- Humans learn patterns from review feedback
- Quality is maintained through social feedback loops

When autonomous agents write code:

- No inherent quality feedback (they'll happily ship garbage)
- Need explicit quality gate to enforce standards
- Review feedback enables learning within epic context
- Prevents accumulation of technical debt across tickets

### Review Agent vs Human Review

**Review agent provides:**

- Instant feedback (no waiting for human availability)
- Consistent standards (no reviewer mood variations)
- Context awareness (knows epic coordination requirements)
- Scalability (can review 100 tickets in parallel)

**Review agent does NOT replace:**

- Final human review of epic branch before production
- Architectural decisions
- Business logic validation
- UX/design review

The review agent is a **quality gate for ticket completion**, not a replacement
for human oversight of the overall epic.

### Integration with Git Workflow

Review happens **before merging**:

```
Ticket executes on ticket/[id] branch
  → Validation passes (git checks, tests)
  → Review evaluates ticket branch
  → Review passes
  → Ticket marked completed
  → Later: ticket branch merged into epic branch
```

This means:

- Failed reviews don't pollute epic branch
- Revisions happen on ticket branch
- Only reviewed-and-approved work merges into epic
- Epic branch contains only quality-validated code

### Future Enhancements (Not This Epic)

- **Learning from reviews**: Track common failure patterns, update builder agent
  instructions
- **Custom review dimensions**: Project-specific review criteria
- **Review agent specialization**: Different review agents for different ticket
  types
- **Progressive review**: Light review for small changes, deep review for large
  changes
- **Review caching**: Skip review if changes are minimal (risk vs reward)
