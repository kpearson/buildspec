# epic-review

Review an epic file for quality, dependencies, and coordination issues.

## Usage

```
/epic-review <epic-file-path>
```

## Description

This command performs a comprehensive review of an epic file to identify issues with dependencies, ticket quality, coordination requirements, and overall structure. It provides specific, actionable feedback to improve the epic before execution.

## What This Reviews

### 1. Dependency Issues
- Circular dependencies (A → B → A)
- Missing dependencies (ticket consumes interface but doesn't depend on it)
- Unnecessary dependencies
- Over-constrained dependency chains

### 2. Function Examples in Tickets
- Each ticket's Paragraph 2 should have concrete function examples
- Format: `function_name(params: types) -> return_type: intent`
- Flag tickets missing these examples

### 3. Coordination Requirements
- Are function profiles complete (arity, intent, signature)?
- Is directory structure specific (not vague like 'buildspec/epic/')?
- Are integration contracts clear (what each ticket provides/consumes)?
- Is 'epic baseline' or similar concepts explicitly defined?

### 4. Ticket Quality
- 3-5 paragraphs per ticket?
- Specific, measurable acceptance criteria?
- Testing requirements specified?
- Non-goals documented?
- Passes deployability test?

### 5. Architectural Consistency
- Do tickets align with coordination_requirements?
- Are technology choices consistent?
- Do patterns match across tickets?

### 6. Big Picture Issues
- Is ticket granularity appropriate?
- Are there missing tickets for critical functionality?
- Is the epic too large (>12 tickets)?
- Would splitting improve clarity?

## Review Process

When this command is invoked, you should:

1. **Read the epic file** at the provided path
2. **Analyze all aspects** listed above
3. **Provide specific feedback** with exact ticket IDs, line issues, and concrete improvements
4. **Create the artifacts directory** if it doesn't exist (e.g., `.epics/[epic-name]/artifacts/`)
5. **Write findings** to `.epics/[epic-name]/artifacts/epic-review.md` using the Write tool

## Output Format

Your review should be written to `.epics/[epic-name]/artifacts/epic-review.md` with this structure:

```markdown
---
date: [current date in YYYY-MM-DD format]
epic: [epic name from epic file]
ticket_count: [number of tickets]
---

# Epic Review Report

## Executive Summary
[2-3 sentence overview of epic quality]

## Critical Issues
[List blocking issues that must be fixed]

## Major Improvements
[Significant changes that would improve quality]

## Minor Issues
[Small fixes and polish]

## Strengths
[What the epic does well]

## Recommendations
[Prioritized list of changes to make]
```

**Note:** Session IDs (`builder_session_id` and `reviewer_session_id`) will be added automatically by the build system after review completion. You don't need to include them in the frontmatter.

## Example

```
/epic-review .epics/user-auth/user-auth.epic.yaml
```

This will:
1. Read and analyze the user-auth epic
2. Check all dependency relationships
3. Validate ticket quality and coordination requirements
4. Write comprehensive review to `.epics/user-auth/artifacts/epic-review.md`

## Important Notes

- Be thorough but constructive in feedback
- Point out exact ticket IDs and line numbers
- Suggest concrete improvements, not just problems
- Focus on coordination and quality issues that would impact execution
- Consider both high-level architecture and low-level details
