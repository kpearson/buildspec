# Multi-Turn Agent Architecture for Epic Creation

## Executive Summary

Based on analysis of your requirements and existing system, a **dedicated
multi-turn agent is absolutely the right approach**. The agent needs iterative
capability to:

1. Draft initial epic/ticket breakdown
2. Self-review for completeness and granularity
3. Refine ticket boundaries and dependencies
4. Validate against spec requirements
5. Output final YAML

## Why Multi-Turn Over Single-Shot

### Critical Advantages

- **Self-correction**: Can catch missed requirements or redundant tickets
- **Refinement loops**: Can adjust ticket granularity after seeing full
  breakdown
- **Validation**: Can validate completeness by checking each spec section mapped
  to tickets
- **Dependency resolution**: Can spot circular dependencies and fix them
- **Quality control**: Can apply ticket standards and verify each ticket meets
  criteria

### Single-Shot Limitations

- No ability to reconsider decisions
- Can't adjust if ticket overlap discovered
- Hard to enforce "review your own work" in one pass
- No iterative improvement on ticket quality

## Agent Architecture

### Agent Type

**Custom MCP Agent** with multi-turn conversation capability and access to:

- Read tool (for spec analysis)
- Write tool (for YAML output)
- Internal reasoning loops (for self-review)

### Core Phases

```
Phase 1: Analysis & Understanding
Phase 2: Initial Draft
Phase 3: Self-Review & Refinement
Phase 4: Validation & Output
```

## Phase 1: Analysis & Understanding

### Objective

Deeply understand the spec without making assumptions about structure.

### Process

1. **Read entire spec holistically**
   - Don't assume structure
   - Note all features/requirements mentioned
   - Identify architectural decisions
   - Spot integration points

2. **Extract coordination essentials**
   - Function signatures (name, arity, intent)
   - Directory structure requirements
   - Technology choices locked in
   - Performance/security constraints
   - Integration contracts
   - Breaking changes prohibited

3. **Identify requirement types**
   - Functional: User-facing features
   - Non-functional: Performance, security, scalability
   - Technical: Architecture, patterns, tech stack
   - Integration: External systems, APIs
   - Infrastructure: Setup, deployment, CI/CD

4. **Build mental model**
   - What's the core value proposition?
   - What are the major subsystems?
   - What are the integration boundaries?
   - What can run in parallel vs sequential?

### Output (Internal)

- Structured notes about spec contents
- List of all requirements found
- Coordination requirements extracted
- Mental model of system architecture

## Phase 2: Initial Draft

### Objective

Create first-pass epic structure and ticket breakdown.

### Process

1. **Draft epic metadata**
   - Epic title (core objective)
   - Description (coordination purpose)
   - Acceptance criteria (concrete, measurable)

2. **Extract coordination requirements**

   ```yaml
   coordination_requirements:
     function_profiles:
       [ComponentName]:
         [methodName]:
           arity: N
           intent: "1-2 sentence description"
           signature: "full method signature with types"

     directory_structure:
       required_paths:
         - "specific directories that must exist"
       organization_patterns:
         [component_type]: "directory pattern"
       shared_locations:
         [resource]: "exact path"

     breaking_changes_prohibited:
       - "APIs that must stay unchanged"

     architectural_decisions:
       technology_choices:
         - "Locked-in tech decisions"
       patterns:
         - "Code organization patterns"
       constraints:
         - "Design constraints"

     performance_contracts:
       [metric]: "specific requirement"

     security_constraints:
       - "Security requirements"

     integration_contracts:
       [ticket-id]:
         provides: ["APIs/services created"]
         consumes: ["Dependencies required"]
         interfaces: ["Interface specifications"]
   ```

3. **Draft initial tickets**
   - Identify logical work units
   - Each ticket = testable, deployable unit
   - Apply vertical slicing where possible
   - Consider integration boundaries

4. **For each ticket, draft**

   ```yaml
   - id: kebab-case-id
     description: |
       3-5 paragraph detailed description including:

       Para 1: What this ticket accomplishes and why (user story)

       Para 2: Technical approach and integration points

       Para 3: Acceptance criteria (specific, measurable, testable)

       Para 4: Testing requirements and coverage expectations

       Para 5 (optional): Non-goals and boundaries

     depends_on: [prerequisite-ticket-ids]
     critical: true/false
     coordination_role: "What this provides for other tickets"
   ```

5. **Map dependencies**
   - Infrastructure tickets usually have no dependencies
   - Feature tickets depend on infrastructure
   - Integration tickets depend on components they integrate

### Output (Internal)

- Draft epic YAML structure
- Initial ticket breakdown
- Dependency graph (may have issues)

## Phase 3: Self-Review & Refinement

### Objective

Systematically improve the draft through self-criticism.

### Review Checklist

#### 3.1 Completeness Check

**Question**: Does this epic capture ALL requirements from the spec?

**Process**:

- Go through spec section by section
- For each requirement, identify which ticket(s) address it
- Flag any requirements not covered
- Add tickets for missing requirements

**Refinement**:

- Add missing tickets
- Update existing tickets to cover gaps

#### 3.2 Ticket Quality Check

**Question**: Does each ticket meet quality standards?

**Standards** (from ticket-standards.md and your feedback):

- **Deployability Test**: "If I deployed only this, would it add value without
  breaking things?"
- **Single Responsibility**: Does one thing well
- **Self-Contained**: All info needed to complete work
- **Smallest Deliverable Value**: Atomic unit that can deploy independently
- **Testable**: Can verify completion objectively

**For each ticket, verify**:

- ✅ Has detailed description (3-5 paragraphs minimum)
- ✅ Includes user story (who benefits, why)
- ✅ Specific acceptance criteria (measurable, testable)
- ✅ Technical context (what part of system)
- ✅ Dependencies clearly identified
- ✅ Testing requirements specified
- ✅ Definition of done stated
- ✅ Non-goals documented

**Refinement**:

- Expand thin ticket descriptions
- Add missing acceptance criteria
- Clarify testing requirements
- Document non-goals

#### 3.3 Granularity Check

**Question**: Are tickets appropriately sized?

**Too Large Signs**:

- Touches multiple subsystems
- Takes multiple days to implement
- Blocks many other tickets
- Hard to write specific acceptance criteria

**Too Small Signs**:

- Can't deploy independently
- No testable value add
- Just a refactor or code organization
- Not meaningful in isolation

**Refinement**:

- Split large tickets into smaller deliverables
- Combine tiny tickets into meaningful units
- Ensure each ticket is testable in isolation

#### 3.4 Dependency Check

**Question**: Are dependencies logical and minimal?

**Problems to catch**:

- Circular dependencies (A → B → A)
- Unnecessary dependencies (B doesn't actually need A)
- Missing dependencies (C uses D's API but doesn't list it)
- Over-constrained (too many sequential dependencies)

**Refinement**:

- Remove circular dependencies
- Add missing dependencies
- Remove unnecessary dependencies
- Restructure for more parallelism

#### 3.5 Coordination Check

**Question**: Do tickets have clear integration contracts?

**For each ticket, verify**:

- What interfaces does it provide?
- What interfaces does it consume?
- Are function signatures specified?
- Are directory structures clear?

**Refinement**:

- Add missing function profiles
- Clarify integration contracts
- Document shared interfaces
- Specify directory organization

#### 3.6 Critical Path Check

**Question**: Are critical tickets marked correctly?

**Critical = True when**:

- Core functionality essential to epic success
- Infrastructure that others depend on
- Integration points enabling coordination

**Critical = False when**:

- Nice-to-have features
- Optimizations
- Enhancements

**Refinement**:

- Update critical flags
- Ensure critical path is clear

#### 3.7 Parallelism Check

**Question**: Can we maximize parallel work?

**Look for**:

- Tickets in same "layer" that can run parallel
- Unnecessary sequential dependencies
- Opportunities to split for parallelism

**Refinement**:

- Remove false dependencies
- Restructure for parallel execution
- Document parallel opportunities

### Output (Internal)

- Refined epic YAML
- Improved ticket descriptions
- Validated dependency graph
- Quality issues addressed

## Phase 4: Validation & Output

### Objective

Final validation and generate output file.

### Process

#### 4.1 Final Validation

Run through validation checklist:

- [ ] Every spec requirement mapped to ticket(s)
- [ ] Every ticket meets quality standards
- [ ] No circular dependencies
- [ ] All tickets have coordination context
- [ ] Critical path identified
- [ ] Parallel opportunities documented
- [ ] YAML structure valid
- [ ] ticket_count matches tickets array length

#### 4.2 Generate Output

- Write YAML to `[spec-dir]/[epic-name].epic.yaml`
- Ensure proper YAML formatting
- Verify file created successfully

#### 4.3 Generate Report

Create comprehensive report with:

```markdown
# Epic Creation Report

## Generated File

- Path: [full path to epic file]
- Tickets: [count]
- Critical: [count]

## Dependency Graph

[Text visualization of dependencies]

## Parallelism Opportunities

- Wave 1: [tickets with no dependencies]
- Wave 2: [tickets depending only on Wave 1]
- ...

## Coordination Requirements Summary

- Function profiles: [count] functions across [count] components
- Directory structure: [count] required paths
- Integration contracts: [count] contracts defined
- Performance contracts: [count] metrics specified

## Quality Metrics

- Average ticket description length: [words]
- Tickets with explicit testing requirements: [count/total]
- Tickets with acceptance criteria: [count/total]

## Filtered Content

Items excluded from epic (implementation noise):

- [List items that were in spec but excluded]
- Reason: [why each was filtered]
```

### Output (Final)

- Epic YAML file written
- Comprehensive report
- Validation passed

## Agent Prompt Structure

### Context Setting

```
You are a specialized multi-turn agent for transforming unstructured feature
specifications into actionable, executable epics with detailed ticket breakdowns.

You have the capability to iterate on your work through multiple rounds of:
1. Analysis
2. Drafting
3. Self-review
4. Refinement

Your goal is to produce a high-quality epic file that enables autonomous ticket
execution while filtering out implementation speculation and planning noise.
```

### Input Description

```
You will receive:
- Path to feature specification (1k-2k lines, unstructured)
- Output path for epic YAML file

The spec is UNSTRUCTURED by design. Do not assume sections, headings, or format.
Your job is to understand CONTENT, not parse STRUCTURE.
```

### Output Specification

```
You must produce:
1. Epic YAML file with:
   - Epic metadata (title, description, acceptance_criteria)
   - Coordination requirements (detailed)
   - Detailed ticket descriptions (3-5 paragraphs each)
   - Dependency graph
   - ticket_count field

2. Comprehensive report including:
   - File path and stats
   - Dependency visualization
   - Parallelism opportunities
   - Quality metrics
   - Filtered content explanation
```

### Process Instructions

```
PHASE 1: ANALYSIS (1-2 turns)
- Read and understand entire spec
- Extract all requirements
- Identify coordination essentials
- Build mental model

PHASE 2: INITIAL DRAFT (1 turn)
- Draft epic structure
- Create initial tickets
- Map dependencies

PHASE 3: SELF-REVIEW (2-3 turns)
- Check completeness
- Verify ticket quality
- Validate dependencies
- Refine granularity
- Improve coordination contracts

PHASE 4: OUTPUT (1 turn)
- Final validation
- Write YAML file
- Generate report

IMPORTANT: Show your work! Document your reasoning at each phase.
```

### Quality Criteria

```
Self-evaluate against these criteria:

COMPLETENESS:
- Every spec requirement mapped to ticket(s)
- No critical features missing

TICKET QUALITY:
- Each ticket 3-5 paragraphs minimum
- Specific acceptance criteria
- Testing requirements specified
- Deployability test passes

COORDINATION:
- Function profiles documented
- Integration contracts clear
- Directory structure specified
- Breaking changes identified

DEPENDENCIES:
- No circular dependencies
- Logical dependency graph
- Parallelism maximized
- Critical path clear
```

### Examples

```yaml
# GOOD TICKET EXAMPLE
- id: create-auth-service
  description: |
    Create UserAuthenticationService to handle all user authentication logic,
    serving as the central authentication coordinator for the system. This service
    will provide authentication, session validation, and logout functionality
    using JWT tokens stored in httpOnly cookies.

    The service must implement three key methods: authenticate(email, password)
    for user login returning AuthResult, validateSession(token) for verifying
    active sessions returning User object, and logout(sessionId) for session
    cleanup. Integration with TokenService (from jwt-token-service ticket) is
    required for JWT operations, and UserModel (from database-models ticket)
    for user data access.

    Acceptance criteria: (1) authenticate() validates credentials and returns
    JWT token in AuthResult, (2) validateSession() verifies token and returns
    User or throws AuthenticationError, (3) logout() invalidates session and
    cleans up state, (4) All methods include proper error handling for invalid
    inputs, (5) Service follows established service layer pattern, (6) Unit
    tests achieve minimum 80% coverage.

    Testing requirements: Unit tests for all three methods with mock
    dependencies (TokenService, UserModel). Edge cases include invalid
    credentials, expired tokens, malformed tokens, null inputs. Integration
    tests with real TokenService and UserModel. Performance test ensuring
    authenticate() completes in < 200ms. Minimum 80% line coverage per
    test-standards.md.

    Non-goals: This ticket does NOT implement password reset, MFA, OAuth
    integration, or user registration. Those are separate tickets with their
    own requirements.

  depends_on: [jwt-token-service, database-models]
  critical: true
  coordination_role:
    "Provides UserAuthenticationService interface for API controllers and
    middleware"

# BAD TICKET EXAMPLE (too thin)
- id: auth-service
  description: "Create authentication service with login and logout"
  depends_on: []
  critical: true
  coordination_role: "Authentication"
```

## Decision Points & Heuristics

### When to Split a Ticket

- **Split if**: Touches multiple subsystems independently
- **Split if**: Can extract infrastructure piece others need
- **Split if**: Has multiple user stories that could deploy separately
- **Split if**: Acceptance criteria list is > 8 items

### When to Combine Tickets

- **Combine if**: Neither part is testable alone
- **Combine if**: Neither part provides value alone
- **Combine if**: They must always deploy together
- **Combine if**: Splitting creates artificial dependency

### When to Mark Critical

- **Critical if**: Core feature blocking other work
- **Critical if**: Infrastructure required by others
- **Critical if**: Integration point enabling coordination
- **Non-critical if**: Enhancement or nice-to-have
- **Non-critical if**: Performance optimization
- **Non-critical if**: Can be skipped without breaking system

### How to Handle Ambiguity

- **Document assumptions** clearly in ticket
- **Suggest follow-up questions** in report
- **Mark as risk** in coordination requirements
- **Provide reasonable defaults** with justification

### How to Handle Different Requirement Types

#### Functional Requirements

- Map to user-facing tickets
- Focus on value delivery
- Testable through user flows

#### Non-Functional Requirements

- Extract as coordination constraints
- Add to performance_contracts or security_constraints
- Ensure tickets address them in acceptance criteria

#### Technical Requirements

- Architecture decisions → coordination_requirements
- Tech stack choices → architectural_decisions.technology_choices
- Patterns → architectural_decisions.patterns

#### Integration Requirements

- Create integration tickets
- Document in integration_contracts
- Ensure consuming tickets depend on them

## Implementation Considerations

### Agent Capabilities Required

- **Multi-turn conversation**: Essential for iteration
- **Long context**: Must hold 1k-2k line spec in context
- **Structured output**: YAML generation
- **Self-reflection**: Ability to critique own work
- **Pattern recognition**: Identify similar tickets, deduplicate

### Potential Challenges

#### Challenge 1: Context Management

**Problem**: 1k-2k line spec may push context limits **Solution**:

- Summarize spec after Phase 1
- Keep summary in context
- Reference original only when refining specific sections

#### Challenge 2: Knowing When to Stop Iterating

**Problem**: Could refine forever **Solution**:

- Max 3 refinement loops
- Track changes per loop
- Stop if < 10% of tickets modified in loop

#### Challenge 3: Balancing Detail vs Brevity

**Problem**: Ticket descriptions could explode **Solution**:

- Target 3-5 paragraphs per ticket
- Each paragraph serves specific purpose
- Remove redundancy across tickets

#### Challenge 4: Handling Truly Unstructured Specs

**Problem**: Spec is intentionally chaotic **Solution**:

- Don't try to impose structure
- Extract requirements via keyword/concept search
- Build requirements list bottom-up, not top-down

## Success Metrics

### Epic Quality Metrics

- All spec requirements covered: 100%
- Tickets meeting standards: 100%
- Average ticket description: 150-300 words
- Dependency graph: Acyclic
- Parallelism opportunities: Maximized

### Process Metrics

- Phases completed: 4/4
- Refinement loops: 1-3
- Validation checks passed: 100%
- Time to completion: < 10 min

## Next Steps

To implement this architecture:

1. **Create custom agent definition** in `.claude/agents/`
2. **Write agent prompt** incorporating phases above
3. **Add validation tools** for YAML structure check
4. **Create example** with small spec (200 lines)
5. **Test iteration behavior** (does it actually self-refine?)
6. **Refine prompt** based on test results
7. **Test with full spec** (1k-2k lines)
8. **Deploy and monitor**

## Open Questions

1. **Should there be a separate reviewer agent?**
   - Pros: Fresh eyes, specialized critique
   - Cons: More complexity, handoff overhead
   - Recommendation: Start with self-review, add reviewer if quality issues

2. **How to handle specs > 2k lines?**
   - Option A: Require splitting
   - Option B: Chunk and process iteratively
   - Option C: Summarization phase
   - Recommendation: Option C with summarization

3. **Should ticket-standards.md be formal schema?**
   - Pros: Programmatic validation
   - Cons: Reduces flexibility
   - Recommendation: Keep as guidance, not schema

4. **How to version epic files?**
   - Git provides version control
   - Consider epic-v2.yaml pattern if major changes
   - Recommendation: Git + semantic versions in epic metadata
