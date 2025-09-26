# execute-ticket

Execute a coding work ticket from a markdown file following the planning-ticket-template format.

## Usage

```
/execute-ticket <ticket-file-path> [--base-commit <sha>] [--epic <epic-path>]
```

## Description

This command reads a ticket file that follows the planning-ticket-template format and executes the implementation work described in it.

**Important**: This command always spawns a Task agent for autonomous execution, ensuring the entire ticket is completed without interruption or permission prompts.

The command will:

1. Parse the ticket to understand:
   - The story and acceptance criteria
   - File modifications needed
   - Implementation details
   - Testing requirements
   - Integration points

2. Execute the implementation by:
   - Making the specified file modifications
   - Implementing the code changes described
   - Adding error handling and logging
   - Setting up feature flags if specified
   - Creating or updating tests

3. Validate the work by:
   - Running existing tests to ensure no regressions
   - Creating new tests as specified
   - Checking that acceptance criteria are met
   - Ensuring code quality standards

## Process Flow

When you run this command from main Claude:

1. **Spawn Task Agent**: Creates an autonomous agent to handle the entire ticket
2. **Pre-flight Test Check**: Agent runs full test suite to ensure clean foundation - if any tests fail, ticket is blocked immediately
3. **Parse Ticket**: Agent extracts all relevant information from the ticket
4. **Plan Execution**: Agent creates a todo list based on the ticket requirements
5. **Implement Changes**: Agent executes each file modification systematically
6. **Add Tests**: Agent creates or updates tests as specified
7. **Validate**: Agent runs tests and verifies acceptance criteria
8. **Report**: Agent returns comprehensive summary of completed work

## Examples

### Basic ticket execution
```
/execute-ticket /path/to/tickets/implement-auth.md
```

### With specific base commit
```
/execute-ticket /path/to/tickets/implement-auth.md --base-commit abc123
```

### With epic context
```
/execute-ticket /path/to/tickets/implement-auth.md --epic /path/to/epics/user-management.md
```

## Requirements

The ticket file must follow the planning-ticket-template format with sections for:
- Issue Summary
- Story (As a/I want/So that)
- Acceptance Criteria
- Technical Details with File Modifications
- Implementation Details
- Testing Strategy
- Definition of Done

## Parameters

- `<ticket-file-path>`: Path to the ticket markdown file
- `--base-commit <sha>`: Base commit to branch from (defaults to current HEAD)
- `--epic <epic-path>`: Path to epic file for context about collaborating tickets and overall goals

## Options

- `--dry-run`: Show what would be done without making changes
- `--skip-tests`: Skip test execution (not recommended)
- `--verbose`: Show detailed progress during execution

## Implementation

When this command is invoked, main Claude will:

1. **Verify the ticket file exists** at the provided path
2. **Spawn a Task agent** with type "general-purpose"
3. **Pass the ticket file path** and execution instructions to the agent
4. **Return the agent's report** to you when complete

### Task Agent Instructions

Main Claude will provide these exact instructions to the Task agent:

```
You are executing a coding work ticket. Your task is to:

0. Run critical pre-flight checks:
   - Execute: bash ~/.claude/scripts/validate-epic.sh dummy.md --ticket [ticket-file-path]
   - This validates the ticket file format and git state
   - If validation fails, STOP and report the validation errors
   - Run the full test suite BEFORE starting any work
   - Verify ALL tests are passing before proceeding
   - If ANY tests are failing, IMMEDIATELY STOP and report:
     * Which tests are failing
     * The exact error messages
     * Status: "blocked - pre-flight test failures"
   - Only proceed if all pre-flight checks pass AND all tests are green
   - This ensures we never build on broken foundations

1. Read and understand the context:
   - Read the ticket at: [ticket-file-path]
   - Parse ticket sections: story, acceptance criteria, file modifications, etc.
   - If --epic provided, read the epic at: [epic-file-path] to understand:
     * Overall project goals and architecture
     * How this ticket fits in the bigger picture
     * Dependencies and collaborating tickets
     * Shared patterns and conventions across the epic
     * Integration points with other tickets in the epic

2. Set up git environment:
   - If --base-commit provided, checkout that commit and create branch from there
   - If no --base-commit, create branch from current HEAD
   - Create new git branch: ticket/[ticket-name-or-id]
   - Record the actual base commit SHA used for reporting

3. Create a comprehensive todo list tracking:
   - All ticket requirements (file modifications, implementation steps, tests)
   - Implementation steps in logical order
   - Test creation and validation steps

4. Execute the work:
   - Make ALL specified file changes
   - Follow exact implementation details provided
   - Add proper error handling and logging
   - Implement feature flags as specified
   - Maintain backwards compatibility

5. Create/update tests:
   - Implement all tests specified in the Testing Strategy section
   - Ensure tests follow project conventions
   - Run tests to verify they pass

6. Validate your work:
   - Verify all acceptance criteria are met
   - Run existing tests to ensure no regressions
   - Check that all Definition of Done items are complete

7. Run full test suite:
   - Execute the project's complete test suite
   - Ensure ALL tests pass, not just the ones you modified
   - Fix any test failures your changes may have caused
   - The ticket is NOT complete until the entire test suite is green

8. Commit all changes:
   - Create meaningful commit messages for the work
   - Ensure all changes are committed to the ticket branch
   - Record the final commit SHA

9. Report completion:
   - After completing all work and committing changes, provide a comprehensive summary including:
   - Ticket identification and summary
   - Summary of all changes made
   - Files modified (with line counts)
   - Tests created/updated
   - Acceptance criteria status (✓/✗ for each)
   - Test suite status (MUST show all tests passing)
   - Git information:
     * Base commit SHA (where branch was created from)
     * Branch name created
     * Final commit SHA after all work
   - Status: "completed"
   - Any issues encountered
   - Confirmation that Definition of Done is met

IMPORTANT:
- CRITICAL: The full test suite MUST be passing BEFORE starting any work - if any tests fail during pre-flight check, STOP immediately and report status as "blocked - pre-flight test failures"
- Complete ALL work specified in the ticket
- Do not skip any sections or requirements
- If you encounter blockers, document them but continue with other parts
- Ensure all code follows project conventions
- Make changes exactly as specified in the ticket
- ALL work must happen on the ticket branch you create
- Record accurate git information
- THE ENTIRE TEST SUITE MUST PASS before considering the work complete
- If tests fail after your changes, you must fix them
- Set final status as "completed" when all work is done
- Never build on broken foundations - always validate test suite health first
```

## Error Handling

The command will handle common issues:
- Missing or invalid ticket file
- Incomplete ticket information
- File access errors
- Pre-flight test failures (will block ticket execution)
- Test failures during or after implementation
- Integration conflicts

## Best Practices

1. **Review the ticket** before execution to ensure it's complete
2. **Run with --dry-run** first to see planned changes
3. **Commit existing work** before executing major tickets
4. **Verify tests pass** after execution
5. **Review generated code** to ensure it meets standards

## Related Commands

- `/create-ticket`: Create a new ticket from template
- `/validate-ticket`: Check if a ticket is properly formatted
- `/estimate-ticket`: Get effort estimation for a ticket
