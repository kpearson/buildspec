# The Anatomy of a Clean Ticket

**Version:** 1.0
**Last Updated:** 2025-10-08

## How to Use This Document

**When creating tickets from an epic:**
1. Read the entire epic document to understand the feature scope
2. Use this document to ensure each ticket meets all required components
3. Consult `test-standards.md` to define testing requirements
4. Use the ticket template (below) as your starting structure
5. Apply the validation prompts to verify ticket quality

**When reviewing existing tickets:**
1. Use the Quick Reference Checklist to identify missing components
2. Apply validation prompts to assess quality
3. Check against Common Mistakes section
4. Verify testing standards are addressed

## Quick Reference Checklist

- [ ] Clear, descriptive title
- [ ] User stories included (user/developer/system)
- [ ] Acceptance criteria defined
- [ ] Automated tests specified
- [ ] Dependencies listed (blocks/blocked by)
- [ ] Technical context provided
- [ ] Collaborative code context identified
- [ ] Function profiles documented (if known)
- [ ] Definition of done stated
- [ ] Non-goals explicitly listed
- [ ] Passes the deployability test

---

## Ticket Template

```markdown
# [Ticket Title: Clear, Descriptive Action]

## User Stories

**As a** [user/developer/system]
**I want** [goal/capability]
**So that** [benefit/value]

[Add additional user stories as needed]

## Acceptance Criteria

1. [Specific, measurable, testable criterion]
2. [Another criterion]
3. [etc.]

## Technical Context

[Brief explanation of what part of the system is affected and why this
change matters. Provide enough context that a developer can start work
without external research.]

## Dependencies

**Depends on:**
- [Ticket name that must be completed first]
- [Another blocking ticket]
- (Or: None)

**Blocks:**
- [Ticket name that depends on this one]
- [Another blocked ticket]
- (Or: None)

## Collaborative Code Context

[Explain which other tickets in the epic interact with this one:]

- **Provides to:** [Tickets that will call/use code from this ticket]
- **Consumes from:** [Tickets that provide interfaces/types this ticket
  will use]
- **Integrates with:** [Tickets that share data structures or state]

## Function Profiles

### `function_name(param1: type, param2: type) -> return_type`
[1-3 sentences describing the intent and behavior of this function]

### `another_function(param: type) -> return_type`
[Intent description]

[Add more as needed, or state "To be determined during implementation"
if not yet known]

## Automated Tests

### Unit Tests
- `test_function_name_scenario_expected_result()` - [What this verifies]
- `test_function_name_edge_case_expected_result()` - [What this
  verifies]
- [Additional unit tests]

### Integration Tests
- `test_integration_scenario_expected_result()` - [What this verifies]
- [Additional integration tests]

### End-to-End Tests (if applicable)
- `test_e2e_workflow_expected_result()` - [What this verifies]

**Coverage Target:** 80% minimum (or 100% for critical paths)

[See `test-standards.md` for detailed testing requirements]

## Definition of Done

- [ ] All acceptance criteria met
- [ ] All tests passing
- [ ] Code coverage meets target
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] [Add any project-specific requirements]

## Non-Goals

[Explicitly state what this ticket will NOT do:]

- [Thing that's out of scope]
- [Another excluded item]
- [etc.]
```

---

## Core Principles

1. **Clear and Descriptive** - The ticket title and description must clearly
   state intent without requiring additional explanation

2. **Single Responsibility** - A ticket does one thing and does it well. No
   combining unrelated changes.

3. **Smallest Piece of Functional, Testable, Deliverable Value** - The atomic
   unit of work that can be deployed independently without breaking anything

4. **Well-Defined Acceptance Criteria** - Specific, testable criteria that leave
   no ambiguity about when the ticket is done

5. **No Duplication** - Must not overlap or duplicate work from other tickets

6. **Readable by Humans** - Written in plain language that any team member can
   understand

7. **Testable** - Clear verification method for completeness and correctness

8. **Self-Contained** - Must contain all necessary information to complete the
   work without requiring external research or clarification

9. **Mergable When Complete** - If acceptance criteria is met and functionality
   is properly tested, the ticket is mergable. No additional work should be
   required.

## Required Components

### User Stories

- **MUST** include one or more user stories
- **Valid users**: end user, developer, or system
- **Format**: "As a [user], I want [goal], so that [benefit]"

### Acceptance Criteria

- **MUST** be specific and measurable
- **MUST** be testable (each criterion requires tests per
  `test-standards.md`)
- **MUST** define "done" unambiguously
- **When met, ticket is mergable** - no hidden requirements

### Automated Tests

- **MUST** include automated tests that verify acceptance criteria
- Tests are not optional; they are part of the definition of done
- **When tests pass and acceptance criteria met, ticket is mergable**
- **See `test-standards.md` for detailed testing requirements including:**
  - Required test types (unit, integration, E2E)
  - Naming conventions and structure
  - Coverage requirements (80% minimum)
  - Performance benchmarks

### Dependencies

- **MUST** explicitly list ticket names that must be completed first (blocking
  dependencies)
- **MUST** explicitly list ticket names that depend on this ticket (blocked
  tickets)
- **EXAMPLE**:
  - **Depends on**: "Create Gate Interface", "Implement State Enums"
  - **Blocks**: "Implement Validation Gate", "Implement Dependencies Met Gate",
    "Create State Machine Core"
- Empty list if no dependencies in either direction

### Technical Context

- **MUST** briefly explain what part of the system is affected and why this
  change matters
- **MUST** provide enough context that a developer can complete the work without
  external research

### Collaborative Code Context

- **MUST** include information about other tickets in the epic that create
  collaborative code
- **MUST** identify which tickets will:
  - Call functions created by this ticket
  - Provide interfaces or types this ticket will consume
  - Share data structures or state with this ticket
  - Integrate with this ticket's components
- **EXAMPLE**: "This ticket creates the `Gate` interface that will be
  implemented by tickets 'Implement Validation Gate', 'Implement Dependencies
  Met Gate', and consumed by ticket 'Create State Machine Core'"

### Function Profiles (To the Extent Known)

- **SHOULD** include function signatures with arity
- **SHOULD** include 1-3 sentences describing intent for each function
- **MUST NOT** include full function definitions or implementation details
- **Examples**:
  - `validateEmail(email: string) -> bool` - Validates email format using RFC
    5322 standard
  - `retryRequest(request: Request, maxAttempts: int, backoff: Duration) -> Response` -
    Retries failed HTTP requests with exponential backoff until max attempts
    reached
  - `calculateDiscount(price: float, userTier: string) -> float` - Applies
    tier-based discount percentage to base price

### Definition of Done

- **MUST** state what else must be true beyond acceptance criteria
- Examples: documentation updated, tests passing, code reviewed, deployed to
  staging
- **When all items complete, ticket is mergable**

### Non-Goals

- **MUST** explicitly state what this ticket will NOT do to prevent scope creep

---

## Right-Sized Units of Work

### The Test

**"If I deployed only this change, would it provide value and not break
anything?"**

- If yes → right-sized
- If no → either too small (incomplete) or too large (too many pieces)

### ✅ Examples of Well-Sized Tickets

**"Add email validation to signup form"**

- Validates one field
- Has clear pass/fail
- Delivers immediate value
- Can be tested independently

**"Implement user login endpoint"**

- Single API endpoint
- Complete flow (request → response)
- Testable with mock data
- Delivers working authentication

**"Create User model with basic fields"**

- One model/entity
- Core fields only (id, name, email)
- Migrations included
- Can save and retrieve

**"Add sort by date to transaction list"**

- One feature on existing UI
- Single sorting dimension
- Observable behavior change
- Testable with sample data

**"Implement retry logic for failed API calls"**

- Single cross-cutting concern
- Defined retry policy
- Testable with mock failures
- Improves system resilience

### ❌ Too Large - Not Atomic

**"Build user authentication system"**

- Too many pieces (login, signup, password reset, sessions, etc.)
- Should be 5-8 separate tickets

**"Refactor payment module"**

- Unclear scope
- No specific deliverable
- Can't test completion

**"Improve performance"**

- Too vague
- Not measurable
- Endless scope

### ❌ Too Small - Not Deliverable

**"Add import statement for validation library"**

- Not functional on its own
- No testable behavior
- Should be part of validation ticket

**"Rename variable from userData to user"**

- Doesn't deliver value independently
- Should be part of larger refactoring if needed

---

## Common Mistakes

### Scope Issues
❌ **Combining multiple features** - "Add user auth and profile editing"
should be 2+ tickets
✅ **Single feature** - "Add user login endpoint"

❌ **Vague scope** - "Improve error handling"
✅ **Specific scope** - "Add retry logic with exponential backoff for
API calls"

❌ **Too small to deploy** - "Add import for requests library"
✅ **Deployable unit** - "Implement HTTP client with retry logic"

### Missing Critical Information
❌ **No acceptance criteria** - Just user stories without defining "done"
✅ **Clear acceptance criteria** - Specific, measurable, testable outcomes

❌ **Missing dependencies** - Not listing blocking or blocked tickets
✅ **Explicit dependencies** - Both "Depends on" and "Blocks" sections
filled

❌ **No collaborative context** - Ignoring how this integrates with other
tickets
✅ **Integration documented** - Explains which tickets consume/provide
interfaces

### Testing Gaps
❌ **Generic test mention** - "Add tests"
✅ **Specific test requirements** - Lists unit/integration tests for each
criterion

❌ **No test coverage target** - Leaving coverage ambiguous
✅ **Coverage specified** - States 80% minimum or higher for critical
paths

### Ambiguous Requirements
❌ **Hidden requirements** - Expecting work not in acceptance criteria
✅ **Complete requirements** - When criteria met and tests pass, ticket
is mergable

❌ **Technical jargon without context** - Assuming knowledge of internal
systems
✅ **Contextual explanations** - Provides enough background to start work

### Poor Function Profiles
❌ **Full implementation** - Including complete function bodies
✅ **Intent only** - Signature + 1-3 sentences describing purpose

❌ **Missing arity** - `processData()` without parameters
✅ **Complete signature** - `process_data(data: dict, options: dict) ->
Result`

## Validation Prompts

Before finalizing a ticket, answer these questions:

### Clarity & Completeness
- [ ] Can a developer start work immediately without asking questions?
- [ ] Are all technical terms and concepts explained or documented?
- [ ] Is the ticket title descriptive enough to understand the work?

### Scope & Size
- [ ] Can this be completed and merged in one work session?
- [ ] Does it pass the deployability test: "If I deployed only this
      change, would it provide value and not break anything?"
- [ ] Have I avoided combining multiple unrelated changes?

### Testing & Verification
- [ ] Does every acceptance criterion have a corresponding test?
- [ ] Have I specified unit, integration, and E2E tests as appropriate?
- [ ] Are the test cases clear enough to implement?
- [ ] Does the test coverage meet the 80% minimum? (See
      `test-standards.md`)

### Dependencies & Collaboration
- [ ] Have I identified all tickets that must be completed first?
- [ ] Have I identified all tickets that depend on this one?
- [ ] Have I documented which tickets will consume this ticket's code?
- [ ] Are the function signatures compatible with dependent tickets?

### Definition of Done
- [ ] Is it clear when this ticket is complete?
- [ ] Have I specified all non-code requirements (docs, reviews, etc.)?
- [ ] Are the non-goals explicitly stated to prevent scope creep?
- [ ] When acceptance criteria are met and tests pass, is the ticket
      mergable?

---

## Summary

A clean ticket is a complete, self-contained contract between intent and
execution. It must contain all necessary information to complete the work
without requiring clarification or external research. When acceptance criteria
are met and functionality is properly tested, the ticket is immediately
mergable. The ticket must be clear enough that any team member can pick it up
and know exactly what needs to be done, small enough to deliver quickly, and
complete enough to provide value on its own. Function profiles provide
implementation guidance without constraining the developer's approach.
Collaborative code context and explicit dependency tracking ensure tickets work
together seamlessly within the epic and can be executed in the correct order.
