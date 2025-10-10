# tickets-review

Review generated ticket files for quality, consistency, and completeness.

## Usage

```
/tickets-review <epic-file-path>
```

## Description

This command performs a comprehensive review of all ticket files generated from an epic to identify quality issues, missing information, inconsistencies, and areas for improvement. It provides specific, actionable feedback to improve tickets before epic execution.

## What This Reviews

### 1. Ticket File Existence and Structure
- Are all tickets from the epic YAML file present in the tickets directory?
- Does each ticket file follow the expected markdown structure?
- Are required sections present (Description, Dependencies, Acceptance Criteria, etc.)?

### 2. Ticket Description Quality
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

### 5. Dependencies and Files
- Do dependencies match what's declared in the epic YAML?
- Are file paths specific and correct?
- Do files_to_modify lists make sense for the ticket scope?
- Are there missing files that should be included?

### 6. Consistency Across Tickets
- Do tickets use consistent terminology?
- Are shared concepts (like data models, interfaces) referenced consistently?
- Do tickets that should coordinate with each other align properly?
- Are naming conventions consistent (function names, class names, file paths)?

### 7. Implementation Clarity
- Is it clear what code needs to be written?
- Are there ambiguous requirements that could be interpreted multiple ways?
- Are there missing specifications (error handling, validation, edge cases)?
- Would a developer know exactly what to build from this ticket?

## Review Process

When this command is invoked, you should:

1. **Read the epic YAML file** to understand the ticket structure and dependencies
2. **Read all ticket files** in the tickets directory
3. **Analyze each ticket** against the criteria above
4. **Identify patterns** across tickets (repeated issues, missing sections)
5. **Create the artifacts directory** if it doesn't exist (e.g., `.epics/[epic-name]/artifacts/`)
6. **Write findings** to `.epics/[epic-name]/artifacts/tickets-review.md` using the Write tool

## Output Format

Your review should be written to `.epics/[epic-name]/artifacts/tickets-review.md` with this structure:

```markdown
---
date: [current date in YYYY-MM-DD format]
epic: [epic name]
ticket_count: [number of tickets reviewed]
---

# Tickets Review Report

## Executive Summary
[2-3 sentence overview of ticket quality]

## Critical Issues
[Issues that would block execution or cause failures]

## Quality Improvements
[Significant improvements to ticket clarity and completeness]

## Missing Information
[Required details that are absent from tickets]

## Consistency Issues
[Inconsistencies across tickets that need alignment]

## Strengths
[What the tickets do well]

## Recommendations
[Prioritized list of improvements, organized by priority]
```

**Note:** Session IDs (`builder_session_id` and `reviewer_session_id`) will be added automatically by the build system after review completion. You don't need to include them in the frontmatter.

## Example

```
/tickets-review .epics/user-auth/user-auth.epic.yaml
```

This will:
1. Read the user-auth epic YAML to understand ticket structure
2. Read all ticket markdown files in `.epics/user-auth/tickets/`
3. Analyze each ticket for quality, completeness, and consistency
4. Write comprehensive review to `.epics/user-auth/artifacts/tickets-review.md`

## Important Notes

- Focus on actionable feedback that improves ticket quality
- Point out specific tickets and sections that need improvement
- Suggest concrete fixes, not just problems
- Consider whether tickets provide enough detail for LLM execution
- Check that tickets coordinate properly (shared interfaces, data models, etc.)
- Verify that testing requirements are adequate
- Ensure acceptance criteria are measurable and complete
