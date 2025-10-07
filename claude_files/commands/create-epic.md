# create-epic

Generate an executable epic file from a planning/specification document.

## Usage

```
/create-epic <planning-doc-path> [--output <epic-file-path>]
```

## Description

This command reads a planning/specification document and generates a
self-contained executable epic file that can be used with `/execute-epic`. The
command analyzes the planning document to:

- Extract the epic structure and requirements
- Identify deliverable tickets from the breakdown sections
- Determine dependencies between tickets based on the described layers/phases
- Create the epic YAML file with proper dependency graph and inline ticket
  descriptions

**Important**: This command spawns a Task agent to analyze the planning document
and generate the epic structure autonomously.

## Parameters

- `<planning-doc-path>`: Path to the planning/specification document
- `--output <epic-file-path>`: Output path for the generated epic file (defaults
  to `<spec-dir>/<epic-name>.epic.yaml`)

## Process Flow

When you run this command:

1. **Analyze Planning Document**: Task agent reads and understands the epic
   requirements
2. **Extract Tickets**: Identifies all deliverable tickets from the "Related
   Issues" section
3. **Determine Dependencies**: Maps layer/category relationships to ticket
   dependencies
4. **Generate Epic File**: Creates self-contained epic YAML with dependency
   graph and inline ticket descriptions
5. **Validate Structure**: Ensures epic file is valid and ready for execution

## Examples

### Basic epic creation

```
/create-epic planning/user-auth-spec.md
```

Outputs: `planning/user-auth.epic.yaml`

### Another example with different directory

```
/create-epic docs/payment-system.md
```

Outputs: `docs/payment-system.epic.yaml`

### Specify output location to override default

```
/create-epic planning/payment-system.md --output epics/payment-system.yaml
```

## Implementation

When this command is invoked, main Claude will:

1. **Validate the planning document** exists and is readable
2. **Spawn a Task agent** with type "general-purpose"
3. **Pass the planning document path** and generation instructions to the agent
4. **Return the generated epic file path** and summary when complete

### Task Agent Instructions

Main Claude will provide these exact instructions to the Task agent:

````
You are generating an executable epic from a planning/specification document. Your PRIMARY GOAL is to extract only the coordination essentials needed for ticket execution while filtering out implementation speculation and planning noise.

COORDINATION-FOCUSED ANALYSIS:

1. Read and analyze the planning document at: [planning-doc-path]
   - Extract the directory path from the planning document location
   - Extract epic title, summary, and core objectives ONLY
   - Identify firm architectural decisions (not speculation)
   - Focus on success criteria that define completion
   - FILTER OUT: Early brainstorming, planning discussions, "we could" statements

2. Extract coordination requirements (INCLUDE ONLY):
   - Function/method profiles: Names, arity (parameter count), and 1-2 sentences about intent
   - Directory paths: Specific directory structure and file organization details
   - Architectural decisions affecting multiple tickets
   - Integration contracts between components
   - Shared patterns and interfaces teams must follow
   - Performance/security constraints that are non-negotiable
   - Backward compatibility requirements
   - Breaking changes that are prohibited

3. Extract deliverable tickets from "Related Issues" section:
   - Parse each layer/category for concrete deliverables
   - Extract ticket descriptions that represent actual work items
   - Extract function signatures with parameter counts and descriptions
   - Extract directory organization and file path specifications
   - Map dependency relationships between layers
   - FILTER OUT: Implementation speculation, "how we might" discussions

4. Generate epic YAML structure focused on coordination requirements:
   ```yaml
   epic: "[Epic Title from document]"
   description: "[Epic Summary - core objective only]"

   acceptance_criteria:
     - "[Concrete success criteria only]"
     - "[Measurable completion requirements]"

   rollback_on_failure: true

   # Coordination essentials for ticket collaboration
   coordination_requirements:
     function_profiles:
       [ServiceName]:
         [methodName]:
           arity: [parameter_count]
           intent: "[1-2 sentence description of what this method does]"
           signature: "[full method signature with types]"
       [ComponentName]:
         [functionName]:
           arity: [parameter_count]
           intent: "[brief description of function purpose]"
           signature: "[complete function signature]"

     directory_structure:
       required_paths:
         - "[specific directory that must exist]"
         - "[file path that other tickets depend on]"
       organization_patterns:
         [component_type]: "[directory pattern teams must follow]"
         [file_type]: "[naming convention and location pattern]"
       shared_locations:
         [shared_resource]: "[exact path where shared files live]"

     breaking_changes_prohibited:
       - "[Existing APIs/interfaces that must remain unchanged]"
       - "[Data models that must maintain compatibility]"

     shared_interfaces:
       [ServiceName]: ["[Required method signatures]", "[Contract specifications]"]
       [ComponentName]: ["[Interface definitions]", "[Expected behaviors]"]

     performance_contracts:
       [metric_name]: "[Specific requirement (e.g., < 200ms, 10,000+ users)]"
       [constraint_name]: "[Non-negotiable performance bound]"

     security_constraints:
       - "[Security requirements affecting multiple tickets]"
       - "[Compliance requirements that must be met]"

     architectural_decisions:
       technology_choices:
         - "[Technology choices that are locked in]"
         - "[Framework or library decisions affecting all tickets]"
       patterns:
         - "[Code organization patterns teams must follow]"
         - "[Data flow patterns that affect coordination]"
       constraints:
         - "[Architectural constraints that limit implementation choices]"
         - "[Design patterns that must be consistently applied]"

     integration_contracts:
       [ticket-id]:
         provides: ["[Concrete APIs/services this creates]"]
         consumes: ["[Specific dependencies it requires]"]
         interfaces: ["[Exact interface specifications]"]

   tickets:
     - id: [derived-from-ticket-description]
       description: "[Detailed ticket description with all necessary context]"
       depends_on: [list-of-prerequisite-ticket-ids]
       critical: [true/false based on epic requirements]
       coordination_role: "[What this ticket provides for coordination]"
````

5. Validate the generated epic:
   - Check for circular dependencies
   - Ensure all critical path tickets are marked appropriately
   - Verify dependency graph makes logical sense
   - Confirm epic file follows proper YAML structure

6. Generate epic file with correct naming:
   - Extract directory from planning document path (e.g., "planning/" from
     "planning/user-auth-spec.md")
   - Generate epic filename from document name with .epic.yaml suffix
   - CRITICAL: Filename MUST be [name].epic.yaml (not just [name].yaml)
   - Example: "user-auth.epic.yaml" from "user-auth-spec.md"
   - Example: "progress-ui.epic.yaml" from "progress-ui-spec.md"
   - Create epic file in same directory as planning document

7. Generate comprehensive report including:
   - Path to generated epic file (showing same-directory location)
   - Dependency graph visualization (text format)
   - Summary of parallelization opportunities
   - Any coordination requirements that were filtered out and why

CRITICAL FILTERING GUIDELINES:

INCLUDE (Coordination Essentials): ✅ Function/method profiles with names,
arity, and intent descriptions ✅ Directory paths and file organization
requirements ✅ Architectural decisions affecting multiple tickets ✅
Integration contracts and interface specifications ✅ Shared patterns teams must
follow consistently ✅ Performance/security constraints that are non-negotiable
✅ Backward compatibility requirements ✅ Breaking changes that are prohibited
✅ Technology choices that are locked in ✅ Data flow patterns that affect
coordination ✅ Concrete APIs/services each ticket must provide ✅ Specific
dependencies between components

EXCLUDE (Implementation Noise): ❌ Implementation speculation and pseudo-code ❌
Planning discussions and brainstorming sessions ❌ "We could" or "Maybe we
should" statements ❌ Detailed step-by-step implementation plans ❌ Early
iterations and exploratory ideas ❌ Alternative approaches that were considered
❌ Internal implementation details not affecting coordination ❌ Development
workflow discussions ❌ Tooling preferences unless they affect coordination

COORDINATION-FOCUSED ANALYSIS:

Epic Structure Mapping:

- Epic title → epic field (core objective only)
- Epic Summary → description field (coordination purpose only)
- Firm Success Criteria → acceptance_criteria list (measurable only)
- Related Issues layers → dependency structure (concrete tickets only)
- Architecture decisions → coordination_requirements sections

Coordination Requirements Generation:

- function_profiles: Extract method/function names with arity and intent
- directory_structure: Capture required paths and organization patterns
- breaking_changes_prohibited: Extract what must remain unchanged
- shared_interfaces: Map required method signatures and contracts
- performance_contracts: Extract non-negotiable performance bounds
- security_constraints: Identify requirements affecting multiple tickets
- architectural_decisions: Capture firm technical decisions with enhanced
  structure
- integration_contracts: Map concrete APIs and dependencies

Dependency Logic (Focus on Coordination):

- Same layer/category = can run in parallel (no coordination needed)
- Sequential layers = later layers depend on coordination points from previous
  layers
- Cross-layer dependencies = identify specific coordination interfaces needed
- Infrastructure/setup tickets = usually provide coordination foundations
- Integration tickets = usually coordinate between component tickets

Ticket Coordination Role:

- coordination_role: What this ticket provides for other tickets to coordinate
  with
- Focus on APIs, interfaces, shared components, and integration points
- NOT internal implementation details

Output Structure:

- Epic file: [spec-directory]/[epic-name].epic.yaml with coordination essentials
  and inline ticket descriptions (created in the same directory as the planning
  document)
- Clear dependency graph focused on coordination needs
- Self-contained file with all ticket information inline

Remember: Your goal is to extract the minimum coordination information needed
for teams to work together effectively. Filter out all implementation
speculation and focus only on what enables successful coordination. The epic
file should be entirely self-contained with detailed ticket descriptions
inline - no separate ticket files are created.

````

## Expected Output

The command generates the epic file in the same directory as the input specification document. For example:
- Input: `planning/user-auth-spec.md` → Output: `planning/user-auth.epic.yaml`
- Input: `docs/payment-system.md` → Output: `docs/payment-system.epic.yaml`

The command generates:

### Epic File (YAML format)
```yaml
epic: "User Authentication System"
description: "Secure user authentication with multi-factor support"

acceptance_criteria:
  - "Users authenticate via existing auth endpoints"
  - "Multi-factor authentication integrated without breaking existing flows"
  - "Session management maintains backward compatibility"

rollback_on_failure: true

# Coordination essentials for ticket collaboration
coordination_requirements:
  function_profiles:
    UserService:
      authenticate:
        arity: 2
        intent: "Validates user credentials and returns authentication result"
        signature: "authenticate(email: string, password: string): Promise<AuthResult>"
      validateSession:
        arity: 1
        intent: "Validates session token and returns user object"
        signature: "validateSession(token: string): Promise<User>"
      logout:
        arity: 1
        intent: "Invalidates session and cleans up user state"
        signature: "logout(sessionId: string): Promise<void>"
    TokenService:
      generateJWT:
        arity: 1
        intent: "Creates JWT token from user data with expiration"
        signature: "generateJWT(user: User): string"
      validateJWT:
        arity: 1
        intent: "Validates JWT token and returns payload"
        signature: "validateJWT(token: string): Promise<TokenPayload>"

  directory_structure:
    required_paths:
      - "src/auth/models/"
      - "src/auth/services/"
      - "src/auth/controllers/"
      - "src/auth/middleware/"
    organization_patterns:
      models: "src/auth/models/[ModelName].ts"
      services: "src/auth/services/[ServiceName]Service.ts"
      controllers: "src/auth/controllers/[Entity]Controller.ts"
    shared_locations:
      auth_types: "src/auth/types/AuthTypes.ts"
      auth_constants: "src/auth/constants/AuthConstants.ts"

  breaking_changes_prohibited:
    - "existing auth API endpoints (/api/auth/*)"
    - "UserModel database schema"
    - "existing JWT token format"
    - "session cookie names and structure"

  shared_interfaces:
    UserService:
      - "authenticate(email, password): Promise<AuthResult>"
      - "validateSession(token): Promise<User>"
      - "logout(sessionId): Promise<void>"
    TokenService:
      - "generateJWT(user): string"
      - "validateJWT(token): Promise<TokenPayload>"
      - "refreshToken(refreshToken): Promise<string>"

  performance_contracts:
    auth_response_time: "< 200ms for login/validation"
    concurrent_sessions: "10,000+ simultaneous users"
    token_validation: "< 50ms average"

  security_constraints:
    - "All passwords must be bcrypt hashed with minimum 12 rounds"
    - "JWT tokens must expire within 15 minutes"
    - "Refresh tokens must expire within 7 days"
    - "OAuth state parameter required for CSRF protection"

  architectural_decisions:
    technology_choices:
      - "JWT tokens stored in httpOnly cookies only"
      - "Session storage in Redis for horizontal scaling"
      - "TypeScript for all auth-related code"
    patterns:
      - "Service layer pattern for all auth business logic"
      - "Repository pattern for database access"
      - "Middleware pattern for request authentication"
    constraints:
      - "No plaintext passwords logged anywhere"
      - "MFA codes expire after 5 minutes"
      - "All auth services must implement AuthService interface"

  integration_contracts:
    auth-database-models:
      provides: ["UserModel interface", "SessionModel interface", "database migrations"]
      consumes: []
      interfaces: ["UserModel.findByEmail()", "SessionModel.create()"]

    jwt-token-service:
      provides: ["TokenService.generate()", "TokenService.validate()"]
      consumes: ["UserModel interface"]
      interfaces: ["JWT generation and validation API"]

    auth-api-endpoints:
      provides: ["POST /auth/login", "GET /auth/validate", "POST /auth/refresh"]
      consumes: ["TokenService", "UserModel"]
      interfaces: ["REST API with JSON request/response"]

    mfa-integration:
      provides: ["MFA verification endpoints", "TOTP validation"]
      consumes: ["UserModel", "existing auth flow"]
      interfaces: ["POST /auth/mfa/verify", "GET /auth/mfa/qr"]

tickets:
  - id: auth-database-models
    description: "Create User and Session models with authentication methods. Implement UserModel with fields for email, password hash, MFA settings, and session tracking. Implement SessionModel for managing user sessions with expiration and token validation. Include database migrations and ensure models follow the established repository pattern."
    depends_on: []
    critical: true
    coordination_role: "Provides UserModel and SessionModel interfaces for all auth tickets"

  - id: jwt-token-service
    description: "Implement JWT token generation and validation service. Create TokenService with methods for generating secure JWT tokens, validating tokens, and handling token refresh. Ensure compatibility with existing session management and implement proper error handling for expired or invalid tokens."
    depends_on: [auth-database-models]
    critical: true
    coordination_role: "Provides token generation/validation service for API and MFA tickets"

  - id: mfa-integration
    description: "Add multi-factor authentication support to existing auth system. Implement TOTP-based MFA with QR code generation, backup codes, and MFA verification endpoints. Extend UserModel to support MFA preferences and ensure backward compatibility with non-MFA users."
    depends_on: [auth-database-models]
    critical: false
    coordination_role: "Extends auth flow with MFA verification endpoints"

  - id: auth-api-endpoints
    description: "Create REST API endpoints for authentication flow. Implement POST /auth/login, GET /auth/validate, POST /auth/refresh, and POST /auth/logout endpoints. Integrate with TokenService and MFA system, ensure proper error handling and response formatting, and maintain backward compatibility with existing API consumers."
    depends_on: [jwt-token-service, mfa-integration]
    critical: true
    coordination_role: "Provides HTTP API that frontend components will consume"
````

## Integration with Other Commands

The generated epic can be used with:

- `/execute-epic planning/user-auth.epic.yaml`: Execute the generated epic
  (note: path matches spec directory)
- `/create-tickets planning/user-auth.epic.yaml`: Generate individual ticket
  files from the epic descriptions
- The epic file contains all ticket information inline - use create-tickets to
  later generate individual ticket files when needed

## Best Practices

1. **Coordination-Focused Planning**: Ensure your planning document clearly
   identifies:
   - What interfaces must remain unchanged (backward compatibility)
   - What APIs/services each component must provide
   - Performance and security constraints affecting multiple tickets

2. **Filter Implementation Details**: The command automatically filters out:
   - Brainstorming discussions and "what if" scenarios
   - Detailed implementation steps and pseudo-code
   - Planning conversations and alternative approaches

3. **Review Coordination Requirements**: Check that the generated epic captures:
   - Concrete interface contracts between tickets
   - Non-negotiable performance/security constraints
   - Breaking changes that are prohibited

4. **Focus on Integration Points**: Generated tickets emphasize:
   - What they provide for other tickets to consume
   - What they expect from their dependencies
   - Specific interface contracts and API specifications

## Error Handling

The command handles:

- Missing or invalid planning documents
- Planning documents with insufficient coordination details
- Circular dependency detection in ticket relationships
- Missing interface specifications or integration contracts
- Invalid YAML generation
- File creation permission issues

## Options

- `--output <epic-file-path>`: Override default output location (default: same
  directory as spec file)
- `--dry-run`: Show what would be generated without creating files

## Related Commands

- `/execute-epic`: Execute the generated coordination-focused epic file
- `/create-tickets`: Generate individual ticket files from epic descriptions
- `/execute-ticket`: Work on individual tickets generated from the epic
- `/code-review`: Review ticket implementations against coordination
  requirements
- `/validate-epic`: Validate epic file structure and coordination requirements
