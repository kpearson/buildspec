# Epic YAML Schema Definition

## Overview

This document defines the formal structure for epic YAML files used by the buildspec system. Epic files serve as coordination documents that enable autonomous ticket execution by capturing essential interfaces, contracts, and dependencies while filtering out implementation speculation.

## Complete Schema

```yaml
# Top-level epic metadata
epic: string                    # Required: Epic title (core objective only)
description: string             # Required: Epic summary (coordination purpose only)
ticket_count: integer           # Required: Exact count of tickets in tickets array
                                # Used for validation and split detection

# Epic success criteria
acceptance_criteria:            # Required: List of concrete, measurable criteria
  - string                      # Each criterion should be specific and testable
  - string
  # Criteria define when epic is considered complete

rollback_on_failure: boolean    # Optional: Whether to rollback on critical ticket failure
                                # Default: true

# Coordination essentials for autonomous ticket execution
coordination_requirements:      # Required: All coordination context needed

  # Function/method interfaces that tickets must implement or consume
  function_profiles:            # Optional but recommended
    ComponentName:              # Component or service name
      methodName:               # Method or function name
        arity: integer          # Parameter count
        intent: string          # 1-2 sentence description of purpose
        signature: string       # Full method signature with types
      anotherMethod:
        arity: integer
        intent: string
        signature: string
    AnotherComponent:
      functionName:
        arity: integer
        intent: string
        signature: string

  # Directory and file organization requirements
  directory_structure:          # Optional but recommended
    required_paths:             # Directories that must exist
      - string                  # Specific directory path
      - string
    organization_patterns:      # How different types of files are organized
      component_type: string    # Pattern for this component type
      file_type: string         # Pattern for this file type
    shared_locations:           # Exact paths for shared resources
      resource_name: string     # Path to shared resource
      another_resource: string

  # APIs and interfaces that must remain unchanged
  breaking_changes_prohibited:  # Optional but important for existing systems
    - string                    # API or interface that must not change
    - string                    # Data model that must maintain compatibility

  # Interfaces that multiple tickets share and must follow
  shared_interfaces:            # Optional but recommended for multi-ticket epics
    ServiceName:                # Service or component name
      - string                  # Required method signature
      - string                  # Contract specification
    ComponentName:
      - string                  # Interface definition
      - string                  # Expected behavior

  # Non-negotiable performance requirements
  performance_contracts:        # Optional but important for performance-critical systems
    metric_name: string         # Specific requirement (e.g., "< 200ms", "10,000+ users")
    another_metric: string      # Another performance bound

  # Security requirements affecting multiple tickets
  security_constraints:         # Optional but critical for security-sensitive systems
    - string                    # Security requirement
    - string                    # Compliance requirement

  # Architecture decisions locked in for this epic
  architectural_decisions:      # Optional but recommended
    technology_choices:         # Tech stack decisions
      - string                  # Framework or library decision
      - string                  # Technology choice affecting all tickets
    patterns:                   # Code organization and design patterns
      - string                  # Pattern that must be followed
      - string                  # Data flow pattern
    constraints:                # Design constraints
      - string                  # Constraint limiting implementation
      - string                  # Pattern that must be applied

  # Integration contracts between tickets
  integration_contracts:        # Optional but critical for multi-ticket coordination
    ticket-id:                  # Ticket ID this contract applies to
      provides:                 # What this ticket creates/exposes
        - string                # Concrete API or service
        - string                # Interface provided
      consumes:                 # What this ticket depends on
        - string                # Specific dependency
        - string                # Required interface
      interfaces:               # Exact interface specifications
        - string                # Interface definition
        - string                # Contract specification
    another-ticket-id:
      provides:
        - string
      consumes:
        - string
      interfaces:
        - string

# Tickets to be executed
tickets:                        # Required: List of all tickets
  - id: string                  # Required: Unique kebab-case identifier
    description: string         # Required: Detailed 3-5 paragraph description
                                # Must include:
                                # - User story (who benefits, why)
                                # - Technical approach
                                # - Acceptance criteria (specific, measurable)
                                # - Testing requirements
                                # - Non-goals (optional)
    depends_on:                 # Required: List of prerequisite ticket IDs
      - string                  # Empty array if no dependencies
      - string
    critical: boolean           # Required: Whether ticket is critical to epic success
                                # Critical tickets:
                                # - Core functionality essential to epic
                                # - Infrastructure others depend on
                                # - Integration points enabling coordination
                                # Non-critical tickets:
                                # - Nice-to-have features
                                # - Performance optimizations
                                # - Enhancement features
    coordination_role: string   # Required: What this ticket provides for coordination
                                # Examples:
                                # - "Provides UserModel interface for all auth tickets"
                                # - "Exposes REST API consumed by frontend"
                                # - "Creates shared validation utilities"

  - id: string
    description: string
    depends_on: []
    critical: boolean
    coordination_role: string

  # ... more tickets
```

## Field Descriptions

### Top-Level Fields

#### `epic` (required, string)
- **Purpose**: Core objective of the epic in one concise phrase
- **Guidelines**:
  - Focus on WHAT, not HOW
  - User or system value, not implementation
  - Examples:
    - Good: "User Authentication System"
    - Good: "Real-time Progress Tracking UI"
    - Bad: "Implement JWT tokens and session management" (too implementation-focused)
    - Bad: "Authentication stuff" (too vague)

#### `description` (required, string)
- **Purpose**: Summary of epic's coordination purpose
- **Guidelines**:
  - 2-4 sentences
  - Focus on coordination needs, not implementation
  - Explain why tickets need coordination
  - Examples:
    - Good: "Secure user authentication with multi-factor support. Requires coordination between token service, database models, and API endpoints to maintain backward compatibility with existing auth flows."
    - Bad: "We will build an auth system using JWT tokens and bcrypt for password hashing" (implementation details)

#### `ticket_count` (required, integer)
- **Purpose**: Exact count of tickets in the `tickets` array
- **Usage**:
  - Validation: Ensures YAML is complete
  - Split detection: Identifies when epic should be split
  - Automation: Used by tooling to verify epic integrity
- **Rules**:
  - MUST match length of `tickets` array exactly
  - Update when tickets added/removed

#### `acceptance_criteria` (required, list of strings)
- **Purpose**: Define when epic is considered complete
- **Guidelines**:
  - Each criterion must be concrete and measurable
  - Focus on outcomes, not implementation
  - Should be testable (know when it's met)
  - Typically 3-7 criteria
- **Examples**:
  - Good: "Users can authenticate via existing auth endpoints without breaking changes"
  - Good: "System handles 10,000+ concurrent authenticated sessions"
  - Good: "All tests pass with minimum 80% coverage"
  - Bad: "Code is written" (not specific)
  - Bad: "It works" (not measurable)

#### `rollback_on_failure` (optional, boolean, default: true)
- **Purpose**: Whether to automatically rollback on critical ticket failure
- **Guidelines**:
  - `true`: Failed critical tickets trigger epic rollback
  - `false`: Continue epic execution despite critical failures
  - Most epics should use `true` for safety

### Coordination Requirements

The `coordination_requirements` section captures ALL context needed for autonomous ticket execution while filtering out implementation speculation.

#### `function_profiles` (optional but recommended, nested object)

**Purpose**: Document function/method interfaces tickets must implement or consume

**Structure**:
```yaml
function_profiles:
  ComponentName:
    methodName:
      arity: integer          # Number of parameters
      intent: string          # 1-2 sentence purpose
      signature: string       # Full signature with types
```

**When to use**:
- Tickets implement or consume functions
- Interface contracts must be exact
- Parameter counts matter for coordination

**Example**:
```yaml
function_profiles:
  UserService:
    authenticate:
      arity: 2
      intent: "Validates user credentials and returns authentication result with token"
      signature: "authenticate(email: string, password: string): Promise<AuthResult>"
    validateSession:
      arity: 1
      intent: "Validates session token and returns user object or throws error"
      signature: "validateSession(token: string): Promise<User>"
```

**What to include**:
- ✅ Function names exact as they should be implemented
- ✅ Parameter counts (arity) for validation
- ✅ Brief intent (1-2 sentences)
- ✅ Full signature with types

**What to exclude**:
- ❌ Implementation details
- ❌ Internal helper functions
- ❌ Pseudo-code
- ❌ Step-by-step algorithms

#### `directory_structure` (optional but recommended, nested object)

**Purpose**: Specify where files should be created and how they're organized

**Structure**:
```yaml
directory_structure:
  required_paths:             # Directories that must exist
    - string
  organization_patterns:      # How different components are organized
    component_type: string
  shared_locations:           # Exact paths for shared resources
    resource_name: string
```

**When to use**:
- Tickets create new files
- File organization matters for imports
- Shared resources need consistent paths

**Example**:
```yaml
directory_structure:
  required_paths:
    - "src/auth/models/"
    - "src/auth/services/"
    - "src/auth/controllers/"
  organization_patterns:
    models: "src/auth/models/[ModelName].ts"
    services: "src/auth/services/[ServiceName]Service.ts"
  shared_locations:
    auth_types: "src/auth/types/AuthTypes.ts"
    auth_constants: "src/auth/constants/AuthConstants.ts"
```

**What to include**:
- ✅ Specific directory paths
- ✅ Naming conventions
- ✅ Organization patterns
- ✅ Shared resource locations

**What to exclude**:
- ❌ Internal file structure
- ❌ Implementation files not affecting coordination
- ❌ Temporary or build artifacts

#### `breaking_changes_prohibited` (optional, list of strings)

**Purpose**: Document APIs/interfaces that MUST remain unchanged

**When to use**:
- Working with existing systems
- Backward compatibility required
- External consumers depend on interfaces

**Example**:
```yaml
breaking_changes_prohibited:
  - "existing auth API endpoints (/api/auth/*)"
  - "UserModel database schema"
  - "JWT token format and expiration"
  - "session cookie names and structure"
```

**What to include**:
- ✅ Existing API endpoints
- ✅ Data models/schemas
- ✅ Token formats
- ✅ Public interfaces

**What to exclude**:
- ❌ Internal implementation details
- ❌ Private methods
- ❌ Test-only interfaces

#### `shared_interfaces` (optional, nested object)

**Purpose**: Define interfaces multiple tickets must follow consistently

**Structure**:
```yaml
shared_interfaces:
  ServiceName:
    - string                  # Method signature
    - string                  # Contract specification
```

**Example**:
```yaml
shared_interfaces:
  UserService:
    - "authenticate(email, password): Promise<AuthResult>"
    - "validateSession(token): Promise<User>"
  TokenService:
    - "generateJWT(user): string"
    - "validateJWT(token): Promise<TokenPayload>"
```

**What to include**:
- ✅ Public method signatures
- ✅ Contract specifications
- ✅ Expected behaviors
- ✅ Return types

**What to exclude**:
- ❌ Implementation details
- ❌ Private methods
- ❌ Internal helpers

#### `performance_contracts` (optional, nested object)

**Purpose**: Specify non-negotiable performance requirements

**Structure**:
```yaml
performance_contracts:
  metric_name: string         # Specific requirement
```

**Example**:
```yaml
performance_contracts:
  auth_response_time: "< 200ms for login/validation"
  concurrent_sessions: "10,000+ simultaneous users"
  token_validation: "< 50ms average"
  database_queries: "< 100ms for user lookups"
```

**What to include**:
- ✅ Specific numeric bounds
- ✅ Measurable metrics
- ✅ Critical performance requirements
- ✅ Scale requirements

**What to exclude**:
- ❌ Vague goals ("fast", "scalable")
- ❌ Optimization suggestions
- ❌ Nice-to-have improvements

#### `security_constraints` (optional, list of strings)

**Purpose**: Document security requirements affecting multiple tickets

**Example**:
```yaml
security_constraints:
  - "All passwords must be bcrypt hashed with minimum 12 rounds"
  - "JWT tokens must expire within 15 minutes"
  - "Refresh tokens must expire within 7 days"
  - "OAuth state parameter required for CSRF protection"
  - "No plaintext passwords logged anywhere"
```

**What to include**:
- ✅ Encryption requirements
- ✅ Token expiration rules
- ✅ CSRF protection
- ✅ Sensitive data handling
- ✅ Compliance requirements

**What to exclude**:
- ❌ General security advice
- ❌ Implementation suggestions
- ❌ Tool recommendations

#### `architectural_decisions` (optional, nested object)

**Purpose**: Document locked-in architectural choices affecting all tickets

**Structure**:
```yaml
architectural_decisions:
  technology_choices:         # Tech stack decisions
    - string
  patterns:                   # Design patterns required
    - string
  constraints:                # Design constraints
    - string
```

**Example**:
```yaml
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
```

**What to include**:
- ✅ Framework/library choices
- ✅ Required design patterns
- ✅ Architectural constraints
- ✅ Data flow patterns

**What to exclude**:
- ❌ Suggested approaches
- ❌ Alternative options
- ❌ Tool preferences (unless affecting coordination)

#### `integration_contracts` (optional, nested object)

**Purpose**: Define what each ticket provides/consumes for coordination

**Structure**:
```yaml
integration_contracts:
  ticket-id:
    provides:                 # What this ticket creates
      - string
    consumes:                 # What this ticket needs
      - string
    interfaces:               # Interface specifications
      - string
```

**Example**:
```yaml
integration_contracts:
  auth-database-models:
    provides:
      - "UserModel interface with findByEmail(), create(), update()"
      - "SessionModel interface with create(), validate(), destroy()"
      - "Database migrations for users and sessions tables"
    consumes: []
    interfaces:
      - "UserModel.findByEmail(email: string): Promise<User | null>"
      - "SessionModel.validate(token: string): Promise<Session>"

  jwt-token-service:
    provides:
      - "TokenService.generate(user: User): string"
      - "TokenService.validate(token: string): Promise<TokenPayload>"
    consumes:
      - "UserModel interface"
    interfaces:
      - "TokenService implements JWT generation/validation"
```

**What to include**:
- ✅ Concrete APIs created
- ✅ Services exposed
- ✅ Specific dependencies
- ✅ Interface definitions

**What to exclude**:
- ❌ Implementation details
- ❌ Internal services
- ❌ Private interfaces

### Tickets

The `tickets` array defines all work items in execution order.

#### `id` (required, string)
- **Purpose**: Unique identifier for the ticket
- **Format**: kebab-case
- **Guidelines**:
  - Descriptive of work item
  - Unique across epic
  - Consistent with directory/file naming
- **Examples**:
  - Good: "auth-database-models"
  - Good: "jwt-token-service"
  - Good: "user-registration-api"
  - Bad: "ticket-1" (not descriptive)
  - Bad: "AuthDatabaseModels" (not kebab-case)

#### `description` (required, string)
- **Purpose**: Comprehensive description of ticket work
- **Length**: 3-5 paragraphs minimum (150-300 words)
- **Structure**:
  ```
  Paragraph 1: What & Why (User Story)
  - What this ticket accomplishes
  - Who benefits
  - Why it's valuable

  Paragraph 2: Technical Approach & Integration
  - Technical approach
  - Integration points with other tickets
  - Dependencies consumed/provided

  Paragraph 3: Acceptance Criteria
  - Specific, measurable criteria
  - Must be testable
  - Concrete success conditions

  Paragraph 4: Testing Requirements
  - Unit test requirements
  - Integration test requirements
  - Coverage expectations
  - Test scenarios

  Paragraph 5 (Optional): Non-Goals
  - What this ticket does NOT do
  - Boundaries and limitations
  - Future work excluded
  ```

- **Example**:
  ```yaml
  description: |
    Create User and Session models with authentication methods to serve as the
    foundation for all authentication tickets. UserModel must include fields for
    email, password hash (bcrypt with 12 rounds per security constraints), MFA
    settings, and session tracking. SessionModel manages user sessions with
    expiration and token validation. Both models must follow the repository
    pattern established in the codebase.

    This ticket provides the core data layer that tickets 'jwt-token-service',
    'mfa-integration', and 'auth-api-endpoints' will depend on. The models must
    expose clean interfaces: UserModel.findByEmail(), UserModel.create(),
    SessionModel.create(), SessionModel.validate(). Integration with the
    TokenService (from jwt-token-service) happens via these interfaces.

    Acceptance criteria: (1) UserModel can save/retrieve users with all required
    fields, (2) SessionModel enforces expiration (15min per security constraints),
    (3) Database migrations included and tested, (4) Repository pattern
    implementation with proper error handling, (5) All methods include validation
    for required fields, (6) Password hashing uses bcrypt with 12 rounds minimum.

    Testing: Unit tests for model validation, save/retrieve operations, edge
    cases (null values, duplicates, invalid data). Integration tests with real
    database connection. Must achieve 80% line coverage minimum per
    test-standards.md. Performance tests ensuring queries complete in < 100ms.

    Non-goals: This ticket does NOT implement user registration endpoints, password
    reset functionality, or MFA setup. Those features are in separate tickets.
  ```

#### `depends_on` (required, array of strings)
- **Purpose**: List prerequisite tickets that must complete first
- **Format**: Array of ticket IDs (empty array if no dependencies)
- **Guidelines**:
  - Only include direct dependencies
  - Ensure no circular dependencies
  - Empty array if no prerequisites
- **Examples**:
  ```yaml
  depends_on: []                                    # No dependencies
  depends_on: ["database-setup"]                    # One dependency
  depends_on: ["auth-service", "user-models"]       # Multiple dependencies
  ```

#### `critical` (required, boolean)
- **Purpose**: Whether ticket is critical to epic success
- **Critical = true when**:
  - Core functionality essential to epic
  - Infrastructure others depend on
  - Integration points enabling coordination
  - Must succeed for epic to succeed
- **Critical = false when**:
  - Nice-to-have features
  - Performance optimizations
  - Enhancement features
  - Can skip without breaking epic
- **Impact**:
  - Critical ticket failure → epic fails (if rollback_on_failure: true)
  - Non-critical ticket failure → epic continues

#### `coordination_role` (required, string)
- **Purpose**: What this ticket provides for other tickets to coordinate with
- **Guidelines**:
  - Focus on interfaces provided
  - Emphasize coordination points
  - Be specific about what others can use
- **Examples**:
  - Good: "Provides UserModel and SessionModel interfaces for all auth tickets"
  - Good: "Exposes REST API endpoints consumed by frontend components"
  - Good: "Creates shared validation utilities used by all form handlers"
  - Bad: "Does authentication stuff" (vague)
  - Bad: "Implements user model" (no coordination context)

## Validation Rules

### Required Fields
All of these fields MUST be present:
- `epic`
- `description`
- `ticket_count`
- `acceptance_criteria` (at least 1 item)
- `tickets` (at least 1 ticket)

Each ticket MUST have:
- `id`
- `description`
- `depends_on` (can be empty array)
- `critical`
- `coordination_role`

### Validation Checks

1. **Ticket Count Match**
   ```python
   assert len(tickets) == ticket_count
   ```

2. **Unique Ticket IDs**
   ```python
   ticket_ids = [t["id"] for t in tickets]
   assert len(ticket_ids) == len(set(ticket_ids))
   ```

3. **Valid Dependencies**
   ```python
   ticket_ids = {t["id"] for t in tickets}
   for ticket in tickets:
       for dep in ticket["depends_on"]:
           assert dep in ticket_ids, f"Unknown dependency: {dep}"
   ```

4. **No Circular Dependencies**
   ```python
   # Build dependency graph
   # Run topological sort
   # If fails, circular dependency exists
   ```

5. **Ticket Description Length**
   ```python
   for ticket in tickets:
       word_count = len(ticket["description"].split())
       assert word_count >= 100, f"Ticket {ticket['id']} description too short"
   ```

6. **Critical Tickets Have Acceptance Criteria in Description**
   ```python
   for ticket in tickets:
       if ticket["critical"]:
           desc = ticket["description"].lower()
           assert "acceptance criteria" in desc or "acceptance:" in desc
   ```

## Best Practices

### Coordination Over Implementation
- **DO**: Include function signatures, parameter counts, return types
- **DON'T**: Include pseudo-code, implementation steps, algorithm details

### Specific Over Vague
- **DO**: "< 200ms response time", "10,000+ concurrent users"
- **DON'T**: "Fast performance", "High scalability"

### Testable Over Aspirational
- **DO**: "Users authenticate via POST /api/auth/login endpoint"
- **DON'T**: "Authentication works well"

### Coordination Context
- **DO**: "Provides UserService interface consumed by auth-api-endpoints"
- **DON'T**: "Implements user service"

### Filter Implementation Noise
- **INCLUDE**: What must be built, how components integrate, what interfaces look like
- **EXCLUDE**: How to implement internally, step-by-step plans, pseudo-code, brainstorming

## Examples

### Minimal Valid Epic
```yaml
epic: "Simple Feature"
description: "A simple feature for testing"
ticket_count: 1

acceptance_criteria:
  - "Feature works as expected"

tickets:
  - id: simple-ticket
    description: |
      Implement simple feature.

      This provides basic functionality for testing the epic system.

      Acceptance: (1) Feature implemented, (2) Tests pass.

      Testing: Unit tests with 80% coverage.
    depends_on: []
    critical: true
    coordination_role: "Provides simple feature interface"
```

### Comprehensive Epic
See `/Users/kit/Code/buildspec/.epics/state-machine/state-machine.epic.yaml` for a real-world example with all fields populated.

## Schema Version

Current schema version: **2.0**

Changes from v1:
- Added `ticket_count` field (required)
- Enhanced `coordination_requirements` with more specific structures
- Added `function_profiles` with arity and signature
- Added `directory_structure` with organization patterns
- Enhanced `architectural_decisions` with technology_choices, patterns, constraints
- Standardized ticket description format (3-5 paragraphs)
- Added `coordination_role` to tickets (required)
