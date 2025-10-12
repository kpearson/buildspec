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

0. **CRITICAL: Read ticket quality standards FIRST**:
   - Read: ~/.claude/standards/ticket-standards.md
   - Read: ~/.claude/standards/test-standards.md
   - These define MANDATORY requirements for every ticket you create
   - Tickets that don't meet these standards will cause epic execution to fail
   - **This is not optional** - standards compliance is the primary success criterion

1. Run pre-flight validation:
   - Execute: bash ~/.claude/scripts/validate-epic.sh [epic-file-path]
   - If validation fails, STOP and report the validation errors
   - Only proceed if all pre-flight checks pass

2. Create comprehensive ticket structure (MANDATORY per ticket-standards.md):

   **Required Sections** (from ticket-standards.md):
   - **Title**: Clear, descriptive action
   - **User Stories**: As a [user/developer/system], I want [goal], so that [benefit]
   - **Acceptance Criteria**: Specific, measurable, testable (when met + tests pass = mergable)
   - **Technical Context**: Brief explanation of system impact
   - **Dependencies**: Both "Depends on" and "Blocks" lists with actual ticket names
   - **Collaborative Code Context**: Provides to/Consumes from/Integrates with
   - **Function Profiles**: Signatures with arity and intent (e.g., `validateEmail(email: string) -> bool - Validates email format using RFC 5322`)
   - **Automated Tests** (MANDATORY per test-standards.md):
     * Unit Tests: test_[function]_[scenario]_[expected]() with coverage targets
     * Integration Tests: test_[feature]_[when]_[then]()
     * E2E Tests (if applicable)
     * Coverage Target: 80% minimum, 100% for critical paths
   - **Definition of Done**: Checklist beyond acceptance criteria
   - **Non-Goals**: Explicitly state what this ticket will NOT do

   **Quality Requirements**:
   - Each ticket must be 50-150 lines of detailed planning
   - Must pass the Deployability Test: "If I deployed only this change, would it provide value and not break anything?"
   - Must be self-contained (no external research needed)
   - Must have single responsibility
   - When acceptance criteria met and tests pass → ticket is mergable

3. For each ticket, verify against standards before creating:
   - [ ] Has clear user stories (who benefits, why)
   - [ ] Has specific, testable acceptance criteria
   - [ ] Lists both blocking and blocked dependencies
   - [ ] Explains collaborative code context (provides/consumes/integrates)
   - [ ] Includes function profiles with signatures
   - [ ] Specifies unit/integration/E2E tests with actual test names
   - [ ] Has definition of done beyond acceptance criteria
   - [ ] Explicitly states non-goals
   - [ ] Passes deployability test
   - [ ] Is 50-150 lines of detailed planning

4. Read and parse the epic file at: [epic-file-path]
   - Detect epic format (auto-detect based on fields present):
     * Format A: Has "epic:" field (from create-epic command)
     * Format B: Has "name:" field (manually created)
   - Extract YAML configuration
   - Parse epic metadata, acceptance criteria, and ticket definitions
   - Extract epic summary, architecture, and goals for context
   - Adapt field names based on detected format:
     * Epic title: "epic" field OR "name" field
     * Ticket ID: "id" field OR "name" field
     * Dependencies: "depends_on" field OR "dependencies" field
     * Objectives: "acceptance_criteria" OR "objectives"

5. For each ticket defined in the epic configuration:
   - Create a new markdown file at the path specified in the ticket
     * Use "path" field if present in ticket definition
     * Otherwise generate path as: tickets/[ticket-id].md
   - Use the loaded ticket template as the base structure
   - Replace ALL template placeholders with specific, contextual information
   - Populate with epic context and ticket-specific information
   - Include proper dependency references from depends_on OR dependencies field
   - Use ticket ID from "id" OR "name" field (must be git-branch-friendly)

6. Create detailed ticket content following ticket-standards.md and test-standards.md:

   **TITLE AND ID**:
   - Use ticket name/id from epic (must be git-branch-friendly)
   - Add descriptive subtitle based on ticket role in epic

   **ISSUE SUMMARY** (2-3 sentences):
   - Concise description of what this ticket accomplishes
   - Based on ticket's specific role within the epic
   - Reference epic objectives and how this ticket contributes

   **USER STORY**:
   - As a [developer/user/system]: Derive from epic context
   - I want [specific goal]: Extract from ticket description and acceptance criteria
   - So that [benefit]: Connect to epic objectives and success criteria

   **ACCEPTANCE CRITERIA** (detailed):
   - Expand each acceptance criterion from epic into specific, testable requirement
   - Include error handling, logging, and observability requirements
   - Add validation requirements (input validation, state validation, etc.)
   - Include performance criteria if relevant
   - Specify test coverage requirements

   **TECHNICAL IMPLEMENTATION**:
   - List files to modify from epic files_to_modify field (actual paths!)
   - Describe code structure using epic context and constraints
   - Specify classes/functions to create (with actual names from epic)
   - Include import paths and module structure
   - Reference architectural patterns from epic constraints

   **INTEGRATION POINTS**:
   - List dependencies from epic (actual ticket IDs)
   - Specify which interfaces/APIs this ticket provides for other tickets
   - Specify which interfaces/APIs this ticket consumes from dependencies
   - Include specific file/line references where integration happens

   **ERROR HANDLING**:
   - Define specific exception classes for this ticket's domain
   - Specify error messages and error codes
   - Define logging strategy (what to log, at what level)
   - Include retry/fallback strategies if applicable

   **AUTOMATED TESTS** (MANDATORY per test-standards.md):
   - **Unit Tests**: List with pattern test_[function]_[scenario]_[expected]()
     * Example: test_validate_email_valid_format_returns_true()
     * Example: test_validate_email_missing_at_symbol_returns_false()
     * Must test happy path, edge cases, error conditions
   - **Integration Tests**: List with pattern test_[feature]_[when]_[then]()
     * Example: test_state_machine_when_validation_fails_then_transitions_to_failed()
     * Must verify collaborative code from other tickets works together
   - **E2E Tests** (if applicable): test_[workflow]_[expected]()
   - **Test Framework**: Infer from files_to_modify (tests/epic/test_*.py → pytest)
   - **Test Commands**: Provide actual commands (e.g., "uv run pytest tests/epic/test_models.py -v")
   - **Coverage Target**: 80% minimum line coverage, 100% for critical paths
   - **Performance**: Unit tests < 100ms, integration < 5s per test-standards.md
   - NO generic "add tests" - must list specific test names and scenarios

   **DEPENDENCIES**:
   - Upstream: List tickets from epic dependencies/depends_on field
   - Downstream: Identify tickets that will depend on this one
   - Explain what this ticket provides for dependents

   **DEFINITION OF DONE** (per ticket-standards.md):
   - [ ] All acceptance criteria met
   - [ ] All tests passing (unit, integration, E2E)
   - [ ] Code coverage meets target (80% minimum)
   - [ ] Code reviewed
   - [ ] Documentation updated
   - [ ] Add any project-specific requirements from epic

   **NON-GOALS** (explicitly state to prevent scope creep):
   - What this ticket will NOT do
   - Features deferred to other tickets
   - Out-of-scope items

7. Ensure ticket consistency:
   - All tickets reference the same epic properly
   - Dependencies match the epic configuration exactly
   - Architecture context is consistent across tickets
   - Each ticket clearly understands its role in the epic
   - ALL template placeholders are replaced with real, specific content

8. Create files at paths specified in epic:
   - Use the exact path specified in each ticket's "path" field
   - Create parent directories if they don't exist
   - Save each populated ticket template to its specified location

9. Validate all tickets against standards before reporting:
   - Run validation prompts from ticket-standards.md for each ticket
   - Verify test specifications meet test-standards.md requirements
   - Ensure each ticket is 50-150 lines and passes deployability test
   - Confirm all required sections are present and detailed

10. Return comprehensive report:
   - List of all created ticket files
   - Dependency graph visualization
   - Epic context summary
   - Any issues or recommendations

CRITICAL SUCCESS CRITERIA (tickets must meet ticket-standards.md and test-standards.md):

**Mandatory Standards Compliance**:
- Read ticket-standards.md and test-standards.md FIRST before creating any tickets
- Every ticket MUST meet all requirements from both standards documents
- Tickets that don't meet standards will cause epic execution to fail
- Standards compliance is more important than speed - take time to get it right

**Ticket Quality Requirements** (from ticket-standards.md):
- 50-150 lines per ticket minimum
- Passes deployability test: can be deployed independently without breaking anything
- Self-contained: no external research needed to implement
- Single responsibility: does one thing well
- When acceptance criteria met + tests pass → ticket is mergable

**Testing Requirements** (from test-standards.md):
- Every acceptance criterion has corresponding automated tests
- Unit tests with pattern: test_[function]_[scenario]_[expected]()
- Integration tests with pattern: test_[feature]_[when]_[then]()
- 80% minimum code coverage, 100% for critical paths
- Actual test names (not "add tests" or xtest patterns)
- Test commands specified (e.g., "uv run pytest tests/epic/test_models.py -v")

**Epic Format Handling**:
- Auto-detect: Format A (epic:/id:/depends_on:) OR Format B (name:/name:/dependencies:)
- Extract from correct fields based on detected format
- Use context/objectives/constraints for rich background
- Use files_to_modify for actual file paths
- Infer framework, language, modules from file paths

**No Generic Placeholders**:
- NO [COMPONENT], [language], [module], xtest, etc.
- Use actual names from epic: buildspec.epic.models, pytest, Python
- Extract real test framework from files_to_modify paths
- Derive component names from ticket description and context

**Validation Before Completion**:
- Each ticket passes validation prompts from ticket-standards.md
- Each ticket meets test-standards.md requirements
- Dependencies correctly map blocking/blocked relationships
- Collaborative code context explains integration with other tickets
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
