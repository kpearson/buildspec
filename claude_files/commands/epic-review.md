# epic-review

Review all files in an epic directory for quality, consistency, and execution readiness.

## Usage

```
/epic-review <epic-file-path>
```

## Task

Your developer wrote up this epic plan. Review all files in the epic directory and subdirectories.

**Give feedback on it - high-level and down to the nitty-gritty.**

How can we improve it? Are there any big architectural changes we should make?

## Description

This command performs a comprehensive review of ALL files in the epic directory (spec, epic YAML, tickets, and any other generated files) to validate the epic is ready for execution. It assesses:

1. **Consistency across planning documents** - Do the spec, epic YAML, and tickets align?
2. **Implementation completeness** - Will implementing the tickets as described produce the functionality described in the spec?
3. **Test coverage gaps** - Are there areas described in the spec that lack corresponding test requirements in tickets?

The review identifies quality issues, missing information, inconsistencies, and architectural problems.

**Scope**: Reviews everything in `.epics/[epic-name]/`

## What This Reviews

### 1. Consistency Across Planning Documents
- Do the spec, epic YAML, and ticket files tell the same story?
- Are features described in the spec properly reflected in tickets?
- Are architectural decisions consistent between spec and epic YAML?
- Do coordination requirements in epic YAML match what tickets need?

### 2. Implementation Completeness (Spec → Tickets Mapping)
- Will implementing all tickets produce the functionality described in the spec?
- Are there spec features missing corresponding tickets?
- Are there tickets implementing things not in the spec?
- Do ticket acceptance criteria cover spec requirements?

### 3. Test Coverage Gaps
- Do tickets include test requirements for all spec functionality?
- Are edge cases from the spec covered by test requirements?
- Are integration scenarios from the spec addressed in test tickets?
- Are non-functional requirements (performance, security) tested?

### 4. Epic Architecture and Design
- Is the overall epic architecture sound?
- Are there major architectural issues or design flaws?
- Should the epic be split or restructured?
- Are coordination requirements clear and complete?

### 5. Ticket File Existence and Structure
- Are all tickets from the epic YAML file present in the tickets directory?
- Does each ticket file follow the expected markdown structure?
- Are required sections present (Description, Dependencies, Acceptance Criteria, etc.)?

### 3. Ticket Description Quality
- Is the description clear and specific enough for implementation?
- Does it follow the 3-5 paragraph structure?
- Does Paragraph 2 include concrete function examples with signatures?
- Are implementation details specific rather than vague?

### 3. Acceptance Criteria Completeness
- Are acceptance criteria specific and measurable?
- Do they cover all functionality mentioned in the description?
- Are edge cases and error handling addressed?
- Are there enough criteria to validate completion?

### 4. Testing Requirements
- Are testing requirements specified?
- Do they include unit test expectations?
- Are integration test scenarios defined where needed?
- Is test coverage mentioned?

### 5. Epic YAML Coordination Quality
- Are function profiles complete (arity, intent, signature)?
- Is directory structure specific (not vague)?
- Are integration contracts clear (what each ticket provides/consumes)?
- Are architectural decisions documented?
- Are constraints and patterns defined?

### 6. Dependencies and Files
- Do dependencies match what's declared in the epic YAML?
- Are file paths specific and correct?
- Do files_to_modify lists make sense for the ticket scope?
- Are there missing files that should be included?

### 7. Consistency Across Tickets
- Do tickets use consistent terminology?
- Are shared concepts (like data models, interfaces) referenced consistently?
- Do tickets that should coordinate with each other align properly?
- Are naming conventions consistent (function names, class names, file paths)?

### 8. Implementation Clarity
- Is it clear what code needs to be written?
- Are there ambiguous requirements that could be interpreted multiple ways?
- Are there missing specifications (error handling, validation, edge cases)?
- Would a developer know exactly what to build from this ticket?

## Review Process

When this command is invoked, you should:

1. **Read the spec file** (`*-spec.md`) to understand what functionality needs to be built
2. **Read the epic YAML file** to understand architecture, coordination requirements, and dependencies
3. **Read all ticket files** in the tickets directory
4. **Read any other artifacts** (state files, documentation, etc.)
5. **Assess consistency** - Do spec, epic YAML, and tickets align?
6. **Check implementation completeness** - Will tickets build what the spec describes?
7. **Identify test coverage gaps** - Are all spec features tested?
8. **Perform architectural analysis** - Are there big problems or design flaws?
9. **Identify cross-cutting issues** and patterns
10. **Create the artifacts directory** if it doesn't exist (e.g., `.epics/[epic-name]/artifacts/`)
11. **Write findings** to `.epics/[epic-name]/artifacts/epic-review.md` using the Write tool

## Output Format

Your review should be written to `.epics/[epic-name]/artifacts/epic-review.md` with this structure:

```markdown
---
date: [current date in YYYY-MM-DD format]
epic: [epic name]
ticket_count: [number of tickets reviewed]
---

# Epic Review Report

## Executive Summary
[2-3 sentences: Is this epic ready for execution? High-level quality assessment.]

## Consistency Assessment
[Do the spec, epic YAML, and tickets align? Are there contradictions or mismatches?]

## Implementation Completeness
[Will implementing the tickets produce what the spec describes? What's missing or extra?]

## Test Coverage Analysis
[Are all spec features covered by test requirements? What gaps exist?]

## Architectural Assessment
[High-level architectural feedback - big picture issues or design flaws]

## Critical Issues
[Blocking issues that must be fixed before execution]

## Major Improvements
[Significant changes that would substantially improve quality]

## Minor Issues
[Small fixes and polish items]

## Strengths
[What the epic does well]

## Recommendations
[Prioritized list of improvements: Priority 1 (must fix), Priority 2 (should fix), Priority 3 (nice to have)]
```

**Note:** Session IDs (`builder_session_id` and `reviewer_session_id`) will be added automatically by the build system after review completion. You don't need to include them in the frontmatter.

## Example

```
/epic-review .epics/user-auth/user-auth.epic.yaml
```

This will:
1. Read `user-auth-spec.md` to understand required functionality
2. Read the user-auth epic YAML for architecture and coordination
3. Read all ticket markdown files in `.epics/user-auth/tickets/`
4. Review any other artifacts in the epic directory
5. Assess consistency, completeness, and test coverage
6. Perform comprehensive architectural and implementation review
7. Write review to `.epics/user-auth/artifacts/epic-review.md`

## Important Notes

- **Start with the spec** - it's the source of truth for what needs to be built
- **Provide both high-level and nitty-gritty feedback** as requested
- Focus on the three key assessments:
  1. Consistency across planning documents
  2. Implementation completeness (spec → tickets mapping)
  3. Test coverage gaps
- Point out specific tickets, files, and sections that need work
- Suggest concrete fixes, not just problems
- Consider: Can this epic be executed successfully as-is?
- Will the implementation match what the spec promises?
- Ensure the epic is truly ready for execution
