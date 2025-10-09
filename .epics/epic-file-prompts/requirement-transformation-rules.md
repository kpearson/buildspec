# Requirement Transformation Rules

## Overview

This document defines how to transform different types of requirements from
unstructured specs into epic coordination requirements and ticket descriptions.
Since specs are unstructured by design, these rules focus on **content
patterns** rather than structural markers.

## Core Principle

**Extract coordination essentials, filter implementation noise.**

- **Coordination Essentials**: Information needed for autonomous agents to work
  together successfully
- **Implementation Noise**: Speculation, brainstorming, "how we might"
  discussions, pseudo-code

## Requirement Types & Transformations

### 1. Functional Requirements

**Definition**: User-facing features and behaviors

**How to Identify in Specs**:

- User stories ("As a user, I want...")
- Feature descriptions ("The system shall...")
- User flows ("When user clicks X, then Y happens")
- Use cases
- Behavioral descriptions

**Transform To**:

- **Epic Level**: Acceptance criteria (what user can do when epic complete)
- **Ticket Level**: User story paragraphs in ticket descriptions
- **Coordination**: Integration contracts (which tickets provide user-facing
  APIs)

**Example Transformation**:

Spec says:

```
Users need to log in with email and password. After successful login, they
should be redirected to dashboard with a session token stored in a cookie.
The session should expire after 15 minutes of inactivity.
```

Transforms to:

**Epic acceptance_criteria**:

```yaml
acceptance_criteria:
  - "Users can authenticate with email/password via login endpoint"
  - "Successful authentication creates session with 15-minute expiration"
  - "Session tokens stored in httpOnly cookies"
```

**Ticket description** (in auth-api-endpoints ticket):

```yaml
description: |
  Create authentication API endpoints to enable user login functionality.
  Users authenticate by posting email and password to /api/auth/login endpoint,
  which validates credentials and returns JWT token in httpOnly cookie with
  15-minute expiration.

  [rest of detailed description...]
```

**Integration contract**:

```yaml
integration_contracts:
  auth-api-endpoints:
    provides:
      - "POST /api/auth/login endpoint accepting {email, password}"
      - "Returns JWT token in httpOnly cookie"
    consumes:
      - "UserService.authenticate(email, password)"
    interfaces:
      - "POST /api/auth/login → {success: boolean, user: User}"
```

**What to Include**:

- ✅ User-facing behavior
- ✅ API contracts
- ✅ Response formats
- ✅ Success/error conditions

**What to Exclude**:

- ❌ Internal validation logic
- ❌ Database query details
- ❌ Algorithm specifics
- ❌ Implementation steps

---

### 2. Non-Functional Requirements

**Definition**: Performance, security, scalability, reliability requirements

#### 2a. Performance Requirements

**How to Identify**:

- Response time constraints ("must respond in < 200ms")
- Throughput requirements ("handle 10,000 requests/sec")
- Scale requirements ("support 1M users")
- Resource constraints ("use < 512MB RAM")

**Transform To**:

- **Epic Level**: `performance_contracts` in coordination_requirements
- **Ticket Level**: Acceptance criteria specifying performance bounds
- **Coordination**: Constraints all tickets must respect

**Example Transformation**:

Spec says:

```
The authentication system must handle 10,000 concurrent users with login
response times under 200ms and token validation under 50ms.
```

Transforms to:

**Coordination requirements**:

```yaml
coordination_requirements:
  performance_contracts:
    auth_response_time: "< 200ms for login operations"
    token_validation: "< 50ms average"
    concurrent_sessions: "10,000+ simultaneous authenticated users"
```

**Ticket acceptance criteria**:

```yaml
- id: auth-api-endpoints
  description: |
    [...]

    Acceptance criteria: [...] (6) Login endpoint responds in < 200ms for 95th
    percentile, (7) Token validation completes in < 50ms average, (8)
    Performance tests verify concurrent user handling.
```

**What to Include**:

- ✅ Specific numeric bounds
- ✅ Measurable metrics
- ✅ Scale requirements
- ✅ Resource limits

**What to Exclude**:

- ❌ Vague terms ("fast", "scalable")
- ❌ Optimization suggestions
- ❌ Implementation techniques

#### 2b. Security Requirements

**How to Identify**:

- Authentication/authorization requirements
- Encryption requirements
- Data protection rules
- Compliance requirements (GDPR, HIPAA, etc.)
- Input validation rules

**Transform To**:

- **Epic Level**: `security_constraints` in coordination_requirements
- **Ticket Level**: Security acceptance criteria
- **Coordination**: Security patterns all tickets follow

**Example Transformation**:

Spec says:

```
All passwords must be hashed using bcrypt with at least 12 rounds. JWT tokens
must expire within 15 minutes. No plaintext passwords should ever be logged.
All user data must be encrypted at rest per GDPR requirements.
```

Transforms to:

**Coordination requirements**:

```yaml
coordination_requirements:
  security_constraints:
    - "All passwords bcrypt hashed with minimum 12 rounds"
    - "JWT tokens expire within 15 minutes maximum"
    - "No plaintext passwords logged anywhere (code, logs, errors)"
    - "User data encrypted at rest per GDPR compliance"
    - "All authentication endpoints use HTTPS only"
```

**Ticket acceptance criteria**:

```yaml
- id: auth-database-models
  description: |
    [...]

    Acceptance criteria: [...] (4) Password hashing uses bcrypt with 12 rounds
    minimum, (5) No plaintext passwords stored or logged, (6) User data fields
    encrypted per GDPR requirements.
```

**What to Include**:

- ✅ Specific security rules
- ✅ Encryption requirements
- ✅ Compliance constraints
- ✅ Data handling rules

**What to Exclude**:

- ❌ General security advice
- ❌ Best practices without specifics
- ❌ Optional security enhancements

#### 2c. Scalability Requirements

**How to Identify**:

- Horizontal scaling needs
- Load balancing requirements
- Database sharding
- Caching strategies (when mandated)

**Transform To**:

- **Epic Level**: Architectural decisions
- **Ticket Level**: Implementation constraints
- **Coordination**: Patterns enabling scale

**Example Transformation**:

Spec says:

```
System must scale horizontally across multiple application servers. Session
state must be stored in Redis to support horizontal scaling. Database must
support read replicas for query distribution.
```

Transforms to:

**Coordination requirements**:

```yaml
coordination_requirements:
  architectural_decisions:
    technology_choices:
      - "Session storage in Redis for horizontal scaling"
      - "Database read replicas for query distribution"
    patterns:
      - "Stateless application servers (no in-memory sessions)"
      - "All session state externalized to Redis"
    constraints:
      - "No local caching that breaks horizontal scaling"
      - "All auth services must support multi-instance deployment"
```

**What to Include**:

- ✅ Horizontal scaling requirements
- ✅ State management decisions
- ✅ Distributed system patterns

**What to Exclude**:

- ❌ Optimization suggestions
- ❌ "Nice to have" scalability
- ❌ Premature optimization

---

### 3. Technical Requirements

**Definition**: Architecture, technology stack, patterns, technical constraints

#### 3a. Technology Stack Requirements

**How to Identify**:

- Framework choices ("use Express.js")
- Language requirements ("TypeScript only")
- Database choices ("PostgreSQL for persistence")
- Library/tool mandates

**Transform To**:

- **Epic Level**: `architectural_decisions.technology_choices`
- **Ticket Level**: Technology context in descriptions
- **Coordination**: Locked-in tech decisions

**Example Transformation**:

Spec says:

```
Use TypeScript for all authentication code. PostgreSQL for user data storage.
Redis for session caching. Express.js framework for HTTP servers. JWT tokens
stored in httpOnly cookies.
```

Transforms to:

**Coordination requirements**:

```yaml
coordination_requirements:
  architectural_decisions:
    technology_choices:
      - "TypeScript for all authentication code"
      - "PostgreSQL for user data persistence"
      - "Redis for session and token caching"
      - "Express.js framework for all HTTP services"
      - "JWT tokens stored in httpOnly cookies only"
```

**What to Include**:

- ✅ Specific framework/library versions (if specified)
- ✅ Language requirements
- ✅ Database choices
- ✅ Storage mechanisms

**What to Exclude**:

- ❌ Suggested alternatives
- ❌ "Consider using X"
- ❌ Tool preferences without rationale

#### 3b. Architectural Patterns

**How to Identify**:

- Design pattern requirements ("use Repository pattern")
- Layering requirements ("separate business logic from controllers")
- Code organization mandates
- Architectural styles (microservices, monolith, etc.)

**Transform To**:

- **Epic Level**: `architectural_decisions.patterns`
- **Ticket Level**: Pattern application in descriptions
- **Coordination**: Consistent patterns across tickets

**Example Transformation**:

Spec says:

```
All database access must use Repository pattern. Business logic in service
layer separate from HTTP controllers. Middleware pattern for authentication.
Each service owns its data - no cross-service database access.
```

Transforms to:

**Coordination requirements**:

```yaml
coordination_requirements:
  architectural_decisions:
    patterns:
      - "Repository pattern for all database access"
      - "Service layer pattern for business logic"
      - "Middleware pattern for request authentication"
    design_principles:
      - "Each service owns its data - no cross-service DB access"
      - "Clear separation: Controllers → Services → Repositories"
```

**What to Include**:

- ✅ Required patterns
- ✅ Layer separation rules
- ✅ Ownership boundaries
- ✅ Design principles

**What to Exclude**:

- ❌ Implementation details of patterns
- ❌ Suggested patterns without mandate
- ❌ Internal class structure

#### 3c. Technical Constraints

**How to Identify**:

- Limitations ("cannot modify X")
- Restrictions ("must use existing Y")
- Prohibitions ("don't use Z")
- Compatibility requirements

**Transform To**:

- **Epic Level**: `breaking_changes_prohibited`,
  `architectural_decisions.constraints`
- **Ticket Level**: Constraints in acceptance criteria
- **Coordination**: Hard boundaries

**Example Transformation**:

Spec says:

```
Cannot modify existing User model schema. Must maintain backward compatibility
with existing /api/auth/* endpoints. MFA codes must expire after 5 minutes.
Cannot add new database tables without migration.
```

Transforms to:

**Coordination requirements**:

```yaml
coordination_requirements:
  breaking_changes_prohibited:
    - "Existing User model schema must remain unchanged"
    - "All /api/auth/* endpoints must maintain backward compatibility"
    - "Existing JWT token format cannot change"

  architectural_decisions:
    constraints:
      - "MFA codes expire after 5 minutes maximum"
      - "All database changes require migration scripts"
      - "No breaking changes to public APIs"
```

**What to Include**:

- ✅ Hard constraints
- ✅ Breaking change prohibitions
- ✅ Compatibility requirements
- ✅ Technical limitations

**What to Exclude**:

- ❌ Suggestions
- ❌ Best practices without constraints
- ❌ Future considerations

---

### 4. Interface/Integration Requirements

**Definition**: How components integrate, APIs, contracts between systems

**How to Identify**:

- API specifications
- Integration points
- Data flow descriptions
- Interface contracts
- Method signatures

**Transform To**:

- **Epic Level**: `function_profiles`, `shared_interfaces`,
  `integration_contracts`
- **Ticket Level**: Integration paragraphs in descriptions
- **Coordination**: Clear contracts between tickets

**Example Transformation**:

Spec says:

```
UserService needs an authenticate method that takes email and password,
validates them, and returns an AuthResult with user info and token. It should
throw AuthenticationError if credentials invalid. The TokenService generates
JWT tokens from user objects and validates existing tokens. Both services used
by the AuthController to handle HTTP requests.
```

Transforms to:

**Function profiles**:

```yaml
coordination_requirements:
  function_profiles:
    UserService:
      authenticate:
        arity: 2
        intent: "Validates user credentials and returns authentication result"
        signature:
          "authenticate(email: string, password: string): Promise<AuthResult>"
    TokenService:
      generateJWT:
        arity: 1
        intent: "Creates JWT token from user data with expiration"
        signature: "generateJWT(user: User): string"
      validateJWT:
        arity: 1
        intent: "Validates JWT token and returns payload"
        signature: "validateJWT(token: string): Promise<TokenPayload>"
```

**Shared interfaces**:

```yaml
coordination_requirements:
  shared_interfaces:
    UserService:
      - "authenticate(email, password): Promise<AuthResult>"
      - "Throws AuthenticationError for invalid credentials"
    TokenService:
      - "generateJWT(user): string"
      - "validateJWT(token): Promise<TokenPayload>"
```

**Integration contracts**:

```yaml
coordination_requirements:
  integration_contracts:
    user-authentication-service:
      provides:
        - "UserService.authenticate(email, password) method"
        - "AuthResult interface with {user, token} fields"
      consumes:
        - "UserModel interface for credential lookup"
      interfaces:
        - "authenticate(): Promise<AuthResult>"
        - "AuthenticationError exception for invalid credentials"

    jwt-token-service:
      provides:
        - "TokenService.generateJWT(user) method"
        - "TokenService.validateJWT(token) method"
      consumes:
        - "User interface from user-authentication-service"
      interfaces:
        - "generateJWT(): string"
        - "validateJWT(): Promise<TokenPayload>"

    auth-api-controller:
      provides:
        - "POST /api/auth/login HTTP endpoint"
        - "GET /api/auth/validate HTTP endpoint"
      consumes:
        - "UserService.authenticate()"
        - "TokenService.validateJWT()"
      interfaces:
        - "POST /api/auth/login → {success, user, token}"
```

**What to Include**:

- ✅ Function names exactly as specified
- ✅ Parameter counts (arity)
- ✅ Return types
- ✅ Exception types
- ✅ Integration dependencies

**What to Exclude**:

- ❌ Implementation details
- ❌ Internal helper functions
- ❌ Private methods
- ❌ Algorithm descriptions

---

### 5. Data/Schema Requirements

**Definition**: Data models, database schemas, data structures

**How to Identify**:

- Entity descriptions
- Field specifications
- Relationship definitions
- Schema constraints
- Data validation rules

**Transform To**:

- **Epic Level**: `breaking_changes_prohibited` (for existing schemas)
- **Ticket Level**: Schema specifications in acceptance criteria
- **Coordination**: Data model contracts

**Example Transformation**:

Spec says:

```
User model needs email (unique, required), password hash (bcrypt), MFA settings
(optional), and session tracking. Session model has user reference, token,
expiration (15 minutes), and created timestamp. Users can have multiple active
sessions.
```

Transforms to:

**Coordination requirements** (if extending existing):

```yaml
coordination_requirements:
  breaking_changes_prohibited:
    - "Existing User model fields (id, email, createdAt) must remain unchanged"
```

**Integration contract**:

```yaml
coordination_requirements:
  integration_contracts:
    auth-database-models:
      provides:
        - "UserModel with email, passwordHash, mfaSettings, sessions fields"
        - "SessionModel with userId, token, expiresAt, createdAt fields"
        - "UserModel.findByEmail(email) method"
        - "SessionModel.create(userId, token) method"
      consumes: []
      interfaces:
        - "UserModel interface for credential storage and lookup"
        - "SessionModel interface for session management"
```

**Ticket description** (auth-database-models):

```yaml
description: |
  Create User and Session models with authentication-specific fields. UserModel
  includes email (unique, required), passwordHash (bcrypt with 12 rounds per
  security constraints), mfaSettings (optional JSON), and sessions relationship.
  SessionModel includes userId (foreign key), token (unique), expiresAt (15
  minutes from creation per security constraints), and createdAt timestamp.

  [rest of description...]

  Acceptance criteria: (1) UserModel has all required fields with proper
  constraints, (2) email field has unique constraint, (3) passwordHash never
  null, (4) SessionModel enforces 15-minute expiration, (5) Database migrations
  create tables with proper indexes, (6) Foreign key relationship User →
  Sessions properly configured.
```

**What to Include**:

- ✅ Field names and types
- ✅ Constraints (unique, required, etc.)
- ✅ Relationships between models
- ✅ Validation rules
- ✅ Index requirements

**What to Exclude**:

- ❌ ORM implementation details
- ❌ Query optimization techniques
- ❌ Internal data structures
- ❌ Caching strategies (unless mandated)

---

### 6. File/Directory Organization Requirements

**Definition**: Where code should live, file naming, directory structure

**How to Identify**:

- Path specifications ("put models in src/models/")
- File naming conventions
- Module organization
- Import path requirements

**Transform To**:

- **Epic Level**: `directory_structure` in coordination_requirements
- **Ticket Level**: File location in acceptance criteria
- **Coordination**: Consistent organization across tickets

**Example Transformation**:

Spec says:

```
All authentication code goes in src/auth/. Models in src/auth/models/,
services in src/auth/services/, controllers in src/auth/controllers/. Each
model gets its own file named [ModelName].ts. Services follow
[ServiceName]Service.ts pattern. Shared types go in src/auth/types/.
```

Transforms to:

**Coordination requirements**:

```yaml
coordination_requirements:
  directory_structure:
    required_paths:
      - "src/auth/models/"
      - "src/auth/services/"
      - "src/auth/controllers/"
      - "src/auth/middleware/"
      - "src/auth/types/"
    organization_patterns:
      models: "src/auth/models/[ModelName].ts"
      services: "src/auth/services/[ServiceName]Service.ts"
      controllers: "src/auth/controllers/[Entity]Controller.ts"
      types: "src/auth/types/[TypeName].ts"
    shared_locations:
      auth_types: "src/auth/types/AuthTypes.ts"
      auth_errors: "src/auth/types/AuthErrors.ts"
      auth_constants: "src/auth/constants/AuthConstants.ts"
```

**Ticket acceptance criteria**:

```yaml
- id: auth-database-models
  description: |
    [...]

    Acceptance criteria: [...] (7) UserModel created at
    src/auth/models/UserModel.ts, (8) SessionModel created at
    src/auth/models/SessionModel.ts, (9) Shared types exported from
    src/auth/types/AuthTypes.ts.
```

**What to Include**:

- ✅ Specific directory paths
- ✅ File naming patterns
- ✅ Shared resource locations
- ✅ Import conventions

**What to Exclude**:

- ❌ Suggested organizations
- ❌ Internal file structure
- ❌ Private helper file locations

---

## Filtering Rules: What to Exclude

### Always Exclude (Implementation Noise)

1. **Pseudo-code and algorithms**
   - Spec: "We could hash passwords using bcrypt.hash(password, salt) in a
     loop..."
   - Action: Extract "bcrypt hashing required", exclude implementation

2. **Brainstorming and "We could" statements**
   - Spec: "We could add OAuth later, or maybe SAML, worth discussing..."
   - Action: Exclude entirely (not a firm requirement)

3. **Planning discussions**
   - Spec: "Team discussed whether to use Redis or Memcached..."
   - Action: If decision made, include it; if not, exclude

4. **Alternative approaches**
   - Spec: "Option A: JWT in cookies. Option B: JWT in localStorage..."
   - Action: Include only if decision made ("Use Option A")

5. **Step-by-step implementation plans**
   - Spec: "First create User model, then add email field, then add password..."
   - Action: Extract "User model with email, password", exclude steps

6. **Internal implementation details**
   - Spec: "Internally, we'll cache validated tokens in a Map..."
   - Action: Exclude unless it affects coordination

7. **Development workflow**
   - Spec: "We'll use feature branches and code review..."
   - Action: Exclude (not part of epic coordination)

8. **Tool preferences without technical reason**
   - Spec: "I prefer VSCode for TypeScript development..."
   - Action: Exclude

9. **Early iterations and experiments**
   - Spec: "First version had session in localStorage but we changed it..."
   - Action: Include only current decision

10. **Vague aspirations**
    - Spec: "Should be fast and scalable and secure..."
    - Action: Exclude unless specific metrics provided

### Context-Dependent (Include if affects coordination)

1. **Caching strategies**
   - Include if: Affects horizontal scaling or coordination
   - Exclude if: Internal optimization only

2. **Error handling patterns**
   - Include if: Shared error types across tickets
   - Exclude if: Internal error handling

3. **Logging patterns**
   - Include if: Specific constraints (like "no password logging")
   - Exclude if: General logging advice

4. **Testing approaches**
   - Include if: Specific test requirements or coverage mandates
   - Exclude if: General "should test" suggestions

5. **Data flow patterns**
   - Include if: Affects multiple tickets
   - Exclude if: Internal to one ticket

---

## Ticket Creation from Requirements

### Process

1. **Group related requirements**
   - Look for requirements that naturally cluster
   - Consider testing boundaries
   - Consider deployment boundaries

2. **Apply vertical slicing where possible**
   - Each ticket should provide user/developer/system value
   - Prefer thin vertical slices over horizontal layers

3. **Respect technical dependencies**
   - Infrastructure before features
   - Data layer before business logic before API
   - But look for parallel opportunities

4. **Ensure each ticket is testable**
   - Unit testable: Has clear inputs/outputs
   - Integration testable: Can verify with dependencies
   - E2E testable: Can verify user-facing behavior

### Example: Breaking Requirements into Tickets

**Spec Requirements**:

- User authentication with email/password
- JWT token generation and validation
- Session management with 15-min expiration
- REST API endpoints for login/logout
- MFA support with TOTP

**Initial Ticket Breakdown**:

```yaml
tickets:
  # Infrastructure / Data Layer (no dependencies)
  - id: auth-database-models
    description: "User and Session models with fields and relationships"
    depends_on: []
    critical: true

  # Business Logic Layer (depends on data)
  - id: jwt-token-service
    description: "JWT generation and validation service"
    depends_on: [auth-database-models]
    critical: true

  - id: mfa-totp-service
    description: "TOTP generation, QR code, and verification"
    depends_on: [auth-database-models]
    critical: false

  # API Layer (depends on business logic)
  - id: auth-api-endpoints
    description: "Login/logout/validate HTTP endpoints"
    depends_on: [jwt-token-service, mfa-totp-service]
    critical: true
```

**Why this breakdown**:

- ✅ Each ticket is independently testable
- ✅ Each provides value (data layer, business logic, API)
- ✅ Clear dependencies (data → logic → API)
- ✅ Opportunities for parallelism (jwt-token-service and mfa-totp-service)
- ✅ Critical path identified (database-models → jwt-token-service →
  auth-api-endpoints)

---

## Summary Checklist

When transforming requirements, ask:

- [ ] **Functional**: Identified user-facing behaviors and mapped to tickets?
- [ ] **Performance**: Extracted specific numeric bounds to
      performance_contracts?
- [ ] **Security**: Documented security constraints affecting all tickets?
- [ ] **Technical**: Captured locked-in technology and pattern decisions?
- [ ] **Integration**: Defined function profiles and integration contracts?
- [ ] **Data**: Specified data models and breaking change prohibitions?
- [ ] **Organization**: Documented directory structure and file patterns?
- [ ] **Filtered**: Removed pseudo-code, brainstorming, implementation details?
- [ ] **Coordination**: Every requirement mapped to coordination context?
- [ ] **Testable**: Every ticket has clear acceptance criteria?

## When in Doubt

**Ask these questions**:

1. Does this help autonomous agents coordinate? → Include
2. Is this implementation speculation? → Exclude
3. Is this a firm decision or discussion? → Include if firm, exclude if
   discussion
4. Does this affect multiple tickets? → Include in coordination_requirements
5. Is this testable and measurable? → Include
6. Is this vague or aspirational? → Exclude or make specific

**Default stance**: When unclear, **exclude** and note in report. Better to have
agents ask for clarification than to include noise.
