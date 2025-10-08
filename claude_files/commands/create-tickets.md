# create-tickets

Generate individual ticket files from an epic using the ticket template.

## Usage

```
/create-tickets <epic-file-path>
```

## Description

This command reads an epic file and generates individual ticket markdown files
based on the ticket template. Each ticket is populated with:

- Epic context and goals
- Specific task requirements
- Proper dependency relationships
- Architecture context from the epic

**Important**: This command spawns a Task agent that creates comprehensive
tickets with full epic context.

## Process Flow

When you run this command from main Claude:

1. **Parse Epic**: Extract YAML configuration and epic content
2. **Generate Tickets**: Create individual ticket files for each task
3. **Add Epic Context**: Include relevant epic information in each ticket
4. **Set Dependencies**: Ensure ticket dependency relationships are documented
5. **Report Results**: Summary of created tickets and their relationships

## Implementation

When this command is invoked, main Claude will:

1. **Verify the epic file exists** at the provided path
2. **Spawn a Task agent** with type "general-purpose"
3. **Pass the epic file path** and ticket creation instructions to the agent
4. **Return creation report** with list of generated tickets

### Task Agent Instructions

Main Claude will provide these exact instructions to the Task agent:

```
You are creating individual tickets from an epic file. Your task is to:

0. Run pre-flight validation:
   - Execute: bash ~/.claude/scripts/validate-epic.sh [epic-file-path]
   - If validation fails, STOP and report the validation errors
   - Only proceed if all pre-flight checks pass

1. Read the ticket template (if available):
   - Check for template at: ~/.claude/templates/planning-ticket-template.md
   - If template exists, use it as the base structure
   - Otherwise, create tickets with standard markdown format
   - Understand the template structure and placeholder sections

2. Read and parse the epic file at: [epic-file-path]
   - Extract the YAML frontmatter block
   - Parse epic metadata, acceptance criteria, and ticket definitions
   - Extract epic summary, architecture, and goals for context

3. For each ticket defined in the epic configuration:
   - Create a new markdown file at the path specified in the epic
   - Use the loaded ticket template as the base structure
   - Replace ALL template placeholders with specific, contextual information
   - Populate with epic context and ticket-specific information
   - Include proper dependency references
   - Use descriptive ticket IDs that work as git branch names (lowercase, hyphen-separated, e.g., "add-user-authentication", "refactor-api-endpoints")

4. Template population process using planning-ticket-template.md:

   Replace template placeholders with specific content:

   TITLE SECTION:
   - [COMPONENT/MODULE]: Determine component from epic architecture and ticket role
   - [Short Descriptive Title]: Create specific title from ticket ID and purpose
   - Ticket ID should be descriptive and usable as a git branch name (lowercase, hyphen-separated)

   ISSUE SUMMARY:
   - Replace placeholder with concise 1-2 sentence description
   - Based on ticket's specific role within the epic

   STORY SECTION:
   - [user/developer/system]: Derive from epic stakeholders and ticket context
   - [goal/requirement]: Extract from ticket's role in achieving epic goals
   - [benefit/reason]: Connect to epic success criteria and user outcomes

   ACCEPTANCE CRITERIA:
   - Core Requirements: Create 3-5 specific requirements for this ticket
   - Replace generic placeholders with actual functional requirements
   - Include error handling, logging, and observability specific to this ticket

   INTEGRATION POINTS:
   - Replace placeholders with actual dependencies from epic
   - Include specific file/line references where integration will happen
   - Add feature flag control and fallback mechanisms

   CURRENT/NEW FLOW:
   - BEFORE: Describe current system state relevant to this ticket
   - AFTER: Describe new functionality this ticket will implement
   - Use actual code examples, not placeholder pseudocode

   TECHNICAL DETAILS:
   - File Modifications: Specify actual files and line ranges to modify
   - Implementation Details: Provide real code structure with project-specific details
   - Integration with Existing Code: Use actual import paths and module names

   ERROR HANDLING STRATEGY:
   - Create specific exception classes and error handling for this ticket
   - Use actual logging patterns and error codes from the project

   TESTING STRATEGY:
   - Replace xtest patterns with actual test names and commands
   - Use real test framework commands (pytest, npm test, etc.)
   - Provide specific test scenarios for this ticket's functionality

   DEPENDENCIES SECTION:
   - Upstream Dependencies: List actual tickets this depends on from epic
   - Downstream Dependencies: List tickets that depend on this one
   - Use actual ticket IDs and paths from the epic

5. Ensure ticket consistency:
   - All tickets reference the same epic properly
   - Dependencies match the epic configuration exactly
   - Architecture context is consistent across tickets
   - Each ticket clearly understands its role in the epic
   - ALL template placeholders are replaced with real, specific content

6. Create files at paths specified in epic:
   - Use the exact path specified in each ticket's "path" field
   - Create parent directories if they don't exist
   - Save each populated ticket template to its specified location

7. Return comprehensive report:
   - List of all created ticket files
   - Dependency graph visualization
   - Epic context summary
   - Any issues or recommendations

IMPORTANT:
- Load and use the actual planning-ticket-template.md as the base structure
- Replace EVERY placeholder in the template with specific, contextual content
- No placeholder should remain unreplaced ([COMPONENT], [language], xtest, etc.)
- Every ticket must include full epic context
- Tickets should be self-contained but epic-aware
- Dependencies must exactly match the epic configuration
- Use epic architecture to inform all technical decisions
- Ensure consistency across all generated tickets
- Create tickets that execute-ticket can successfully implement
- CRITICAL: Ticket IDs must be descriptive and git-branch-friendly:
  * Use lowercase with hyphens (kebab-case)
  * Be descriptive of the work (e.g., "add-user-authentication", not "ticket-1")
  * Suitable for use as git branch names
  * Avoid generic names like "task-1", "feature-2", etc.
- CRITICAL: Use real project specifics:
  * Actual framework names (pytest, not "test_framework")
  * Actual commands ("uv run pytest", not "run tests")
  * Actual module names (myproject.auth, not [module])
  * Actual file paths and project structure
  * Specific languages (python, typescript, not [language])
  * Real test names and commands, no xtest patterns
  * Specific component/module names relevant to the epic
```

## Example Output

After running the command, you'll get tickets at the paths specified in your
epic:

```
tickets/
├── implement-auth-models.md        # Foundation authentication models
├── add-auth-api-endpoints.md       # API endpoint implementation
├── build-auth-ui-components.md     # User interface components
└── integrate-auth-end-to-end.md    # End-to-end integration testing
```

Each ticket will contain:

- Fully populated planning-ticket-template structure
- ALL placeholders replaced with specific content
- Complete epic context and dependencies
- Clear acceptance criteria derived from epic goals
- Specific technical implementation guidance
- Real testing requirements with actual commands
- Proper dependency references matching epic

## Integration with Other Commands

The created tickets work seamlessly with:

- `/execute-epic`: Reads the same ticket files for orchestration
- `/execute-ticket`: Executes individual tickets with epic context
- `/code-review`: Reviews ticket implementation with epic understanding

## Options

- `--output-dir <path>`: Override default tasks/ directory
- `--dry-run`: Show what tickets would be created without writing files
- `--verbose`: Include detailed epic context in each ticket

## Best Practices

1. **Run after epic planning** - Ensure epic is complete before generating
   tickets
2. **Review generated tickets** - Verify they capture your intent correctly
3. **Customize as needed** - Generated tickets are starting points, refine as
   needed
4. **Maintain consistency** - If you modify tickets, keep epic context accurate

## Error Handling

The command handles:

- Missing or invalid epic files
- Malformed YAML configuration
- Directory creation issues
- Template processing errors
- Dependency validation problems

## Related Commands

- `/execute-epic`: Execute the entire epic with generated tickets
- `/execute-ticket`: Execute individual tickets
- `/code-review`: Review ticket implementations
- `/validate-epic`: Validate epic before ticket generation
