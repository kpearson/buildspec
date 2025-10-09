# Epic Creation Prompt

This is the prompt that will be used when `/create-epic <spec-file>` is invoked.

---

# Your Task: Transform Specification into Executable Epic

You are transforming an unstructured feature specification into an executable epic YAML file that enables autonomous ticket execution.

## Input

You have been given:
- **Spec file path**: `{spec_file_path}`
- **Output epic path**: `{epic_file_path}`

## Your Goal

Create a high-quality epic YAML file that:
1. Captures ALL requirements from the spec
2. Extracts coordination essentials (function profiles, integration contracts, etc.)
3. Filters out implementation noise (pseudo-code, brainstorming, speculation)
4. Breaks work into testable, deployable tickets
5. Defines clear dependencies enabling parallel execution

## Critical Context

**Specs are UNSTRUCTURED by design.** Do not assume sections, headings, or format. Your job is to understand CONTENT, not parse STRUCTURE.

**Multi-turn approach required.** You will iterate through phases:
1. Analysis & Understanding
2. Initial Draft
3. Self-Review & Refinement
4. Validation & Output

## Reference Documents

Before starting, read these documents to understand the standards and structure:
- **Ticket Standards**: Read `~/.claude/standards/ticket-standards.md` - What makes a good ticket (quality standards)
- **Epic Schema**: Reference the schema structure below for YAML format
- **Transformation Rules**: Follow the transformation guidelines below
- **Ticket Quality Standards**: Each ticket description must meet the standards from ticket-standards.md

## Phase 1: Analysis & Understanding

### Step 1.1: Read the Spec Holistically

Read the entire spec from `{spec_file_path}`. As you read:
- Note all features/requirements mentioned
- Identify architectural decisions (tech stack, patterns, constraints)
- Spot integration points between components
- Flag performance/security requirements
- Note function signatures, directory structure requirements
- Identify what's a firm decision vs brainstorming

### Step 1.2: Extract Coordination Essentials

Build your coordination requirements map:

**Function Profiles**:
- What functions/methods are specified?
- What are their parameter counts (arity)?
- What's their intent (1-2 sentences)?
- What are their signatures?

**Directory Structure**:
- What directory paths are specified?
- What file naming conventions exist?
- Where do shared resources live?

**Integration Contracts**:
- How do components integrate?
- What APIs does each component provide?
- What does each component consume?

**Architectural Decisions**:
- What tech stack is locked in?
- What patterns must be followed?
- What constraints exist?

**Breaking Changes**:
- What existing APIs must remain unchanged?
- What schemas can't be modified?

**Performance/Security**:
- What are the numeric performance bounds?
- What security constraints exist?

### Step 1.3: Build Mental Model

Answer these questions:
- What's the core value proposition?
- What are the major subsystems?
- What are the integration boundaries?
- What can run in parallel vs sequential?

### Output Phase 1

Document in your response:
```markdown
## Phase 1: Analysis Complete

### Requirements Found
- [List all requirements identified]

### Coordination Essentials
- Function Profiles: [summary]
- Directory Structure: [summary]
- Integration Contracts: [summary]
- Architectural Decisions: [summary]
- Performance/Security: [summary]

### Mental Model
- Core Value: [...]
- Major Subsystems: [...]
- Integration Boundaries: [...]
```

---

## Phase 2: Initial Draft

### Step 2.1: Draft Epic Metadata

Create:
- **Epic title**: Core objective only (not implementation)
- **Description**: Coordination purpose (2-4 sentences)
- **Acceptance criteria**: 3-7 concrete, measurable criteria

### Step 2.2: Draft Coordination Requirements

Using your Phase 1 extraction, create the `coordination_requirements` section:

```yaml
coordination_requirements:
  function_profiles:
    ComponentName:
      methodName:
        arity: N
        intent: "..."
        signature: "..."

  directory_structure:
    required_paths:
      - "..."
    organization_patterns:
      component_type: "..."
    shared_locations:
      resource_name: "..."

  breaking_changes_prohibited:
    - "..."

  architectural_decisions:
    technology_choices:
      - "..."
    patterns:
      - "..."
    constraints:
      - "..."

  performance_contracts:
    metric_name: "..."

  security_constraints:
    - "..."

  integration_contracts:
    ticket-id:
      provides:
        - "..."
      consumes:
        - "..."
      interfaces:
        - "..."
```

### Step 2.3: Draft Tickets

For each logical work unit, create a ticket:

**Ticket Structure**:
```yaml
- id: kebab-case-id
  description: |
    [Paragraph 1: What & Why - User story, value proposition]

    [Paragraph 2: Technical Approach - Integration points, dependencies]

    [Paragraph 3: Acceptance Criteria - Specific, measurable, testable]

    [Paragraph 4: Testing Requirements - Unit/integration tests, coverage]

    [Paragraph 5 (optional): Non-Goals - What this does NOT do]

  depends_on: [prerequisite-ticket-ids]
  critical: true/false
  coordination_role: "What this provides for other tickets"
```

**Ticket Creation Guidelines**:
- Each ticket = testable, deployable unit
- Vertical slicing preferred (user/developer/system value)
- Smallest viable size while still being testable
- 3-5 paragraphs minimum per description

### Step 2.4: Map Dependencies

- Infrastructure tickets → no dependencies
- Business logic tickets → depend on infrastructure
- API tickets → depend on business logic
- Integration tickets → depend on components they integrate

### Output Phase 2

Document in your response:
```markdown
## Phase 2: Initial Draft Complete

### Epic Metadata
- Title: [...]
- Description: [...]
- Acceptance Criteria: [count] criteria

### Coordination Requirements
- Function profiles: [count] functions
- Directory paths: [count] paths
- Integration contracts: [count] contracts

### Tickets
- Total: [count]
- Critical: [count]
- Dependencies: [summary of dep structure]

### Initial Dependency Graph
[Text visualization showing ticket dependencies]
```

**Then show the draft YAML structure** (abbreviated, don't need full tickets yet)

---

## Phase 3: Self-Review & Refinement

Now systematically review and improve your draft.

### Review 3.1: Completeness Check

Go through the spec requirement by requirement:
- Is each requirement covered by at least one ticket?
- Are there any gaps?

**Action**: Add missing tickets or update existing ones to cover gaps.

### Review 3.2: Ticket Quality Check

For each ticket, verify:
- ✅ Description is 3-5 paragraphs (150-300 words)
- ✅ Includes user story (who benefits, why)
- ✅ Specific acceptance criteria (measurable, testable)
- ✅ Testing requirements specified
- ✅ Non-goals documented (when relevant)
- ✅ Passes deployability test: "If I deployed only this, would it add value?"

**Action**: Expand thin tickets, add missing details.

### Review 3.3: Granularity Check

Check each ticket for proper sizing:

**Too Large?**
- Touches multiple subsystems independently
- Takes multiple days
- Blocks many other tickets
- Hard to write specific acceptance criteria

**Too Small?**
- Can't deploy independently
- No testable value add
- Just refactoring/organization
- Not meaningful in isolation

**Action**: Split large tickets, combine tiny tickets.

### Review 3.4: Dependency Check

Check for:
- ❌ Circular dependencies (A → B → A)
- ❌ Unnecessary dependencies (B doesn't need A)
- ❌ Missing dependencies (C uses D's API but doesn't list it)
- ❌ Over-constrained (too many sequential deps)

**Action**: Fix dependency issues, maximize parallelism.

### Review 3.5: Coordination Check

For each ticket, verify:
- What interfaces does it provide? (clear?)
- What interfaces does it consume? (clear?)
- Are function signatures specified?
- Are directory structures clear?

**Action**: Add missing function profiles, clarify integration contracts.

### Review 3.6: Critical Path Check

Verify critical flags:
- Critical = true: Core functionality, infrastructure, integration points
- Critical = false: Nice-to-have, optimizations, enhancements

**Action**: Correct critical flags.

### Review 3.7: Parallelism Check

Identify parallelism opportunities:
- Which tickets can run in parallel (same layer, no coordination needed)?
- Are there false dependencies limiting parallelism?

**Action**: Remove false dependencies, restructure for parallel execution.

### Output Phase 3

Document in your response:
```markdown
## Phase 3: Self-Review Complete

### Changes Made
- Completeness: [tickets added/updated]
- Quality: [tickets improved]
- Granularity: [tickets split/combined]
- Dependencies: [issues fixed]
- Coordination: [contracts clarified]
- Critical Path: [flags updated]
- Parallelism: [opportunities identified]

### Refined Stats
- Total tickets: [count]
- Critical tickets: [count]
- Average description length: [words]
- Max parallel tickets: [count] (Wave 1)

### Refined Dependency Graph
[Text visualization of improved dependencies]
```

---

## Phase 4: Validation & Output

### Step 4.1: Final Validation

Run through checklist:
- [ ] Every spec requirement mapped to ticket(s)
- [ ] Every ticket meets quality standards (3-5 paragraphs, acceptance criteria, testing)
- [ ] No circular dependencies
- [ ] All tickets have coordination context (function profiles, integration contracts)
- [ ] Critical path identified
- [ ] Parallel opportunities documented
- [ ] YAML structure valid
- [ ] `ticket_count` matches tickets array length

### Step 4.2: Generate Epic YAML File

Write the complete epic YAML to `{epic_file_path}`:

```yaml
epic: "[Epic Title]"
description: "[Epic Description]"
ticket_count: [exact count]

acceptance_criteria:
  - "[criterion 1]"
  - "[criterion 2]"
  # ...

rollback_on_failure: true

coordination_requirements:
  # [Full coordination requirements from your draft]

tickets:
  # [Full ticket list with complete descriptions]
```

**Use the Write tool** to create the file.

### Step 4.3: Verify File Creation

**Use the Read tool** to verify the file was created successfully.

### Step 4.4: Generate Report

Create a comprehensive report:

```markdown
## Epic Creation Report

### Generated File
- **Path**: {epic_file_path}
- **Tickets**: [count]
- **Critical**: [count]

### Dependency Graph
```
[Text visualization showing all tickets and dependencies]
```

### Parallelism Opportunities
- **Wave 1** (no dependencies): [ticket-ids]
- **Wave 2** (depends only on Wave 1): [ticket-ids]
- **Wave 3** (depends on Wave 1-2): [ticket-ids]
- ...

### Coordination Requirements Summary
- Function profiles: [count] functions across [count] components
- Directory paths: [count] required paths
- Integration contracts: [count] contracts defined
- Performance contracts: [count] metrics specified
- Security constraints: [count] constraints defined

### Quality Metrics
- Average ticket description: [word count] words
- Tickets with testing requirements: [count]/[total]
- Tickets with acceptance criteria: [count]/[total]
- Tickets with non-goals: [count]/[total]

### Requirement Coverage
All spec requirements mapped to tickets:
- [Requirement 1] → [ticket-ids]
- [Requirement 2] → [ticket-ids]
- ...

### Filtered Content
Implementation noise excluded from epic:
- [Item 1] - Reason: [pseudo-code/brainstorming/speculation]
- [Item 2] - Reason: [...]
- ...

## Next Steps

1. Review the generated epic at: {epic_file_path}
2. Run `/create-tickets {epic_file_path}` to generate individual ticket files (optional)
3. Run `/execute-epic {epic_file_path}` to begin execution
```

---

## Key Principles (Review Before Starting)

### Coordination Over Implementation
- **INCLUDE**: Function signatures, parameter counts, integration contracts, directory structures
- **EXCLUDE**: Pseudo-code, implementation steps, algorithm details, "how we might" discussions

### Specific Over Vague
- **GOOD**: "< 200ms response time", "10,000+ concurrent users"
- **BAD**: "Fast performance", "High scalability"

### Testable Over Aspirational
- **GOOD**: "Users authenticate via POST /api/auth/login endpoint"
- **BAD**: "Authentication works well"

### Filter Ruthlessly
- **EXCLUDE**: Brainstorming, planning discussions, alternatives considered, early iterations
- **INCLUDE**: Firm decisions, architectural choices, integration requirements, constraints

### Ticket Quality Standards

Each ticket must pass:
1. **Deployability Test**: "If I deployed only this, would it add value without breaking things?"
2. **Single Responsibility**: Does one thing well
3. **Self-Contained**: All info needed to complete work
4. **Smallest Deliverable Value**: Atomic unit deployable independently
5. **Testable**: Can verify completion objectively

---

## Sub-Agent Usage (If Needed)

**Question**: Should you spawn sub-agents for any part of this work?

**Consider sub-agents for**:
- Reading extremely large specs (> 2k lines)
- Validating complex dependency graphs
- Generating ticket descriptions in parallel

**Do NOT use sub-agents for**:
- The core analysis/drafting/review work (you should do this)
- Writing the final YAML (you should do this)

**If you use sub-agents**, document why and what you delegated.

---

## Begin

Start with Phase 1. Read the spec at `{spec_file_path}` and begin your analysis.

Remember: **Show your work at each phase.** Document your reasoning, decisions, and refinements.
