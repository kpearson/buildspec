# split-epic

Analyze and split oversized epics into multiple independent deliverable-focused
epics.

## Usage

```
/split-epic <epic-file-path> <spec-path>
```

## Description

This command analyzes epics with 13 or more tickets and intelligently splits
them into multiple fully independent epics, each representing a cohesive
deliverable capability. The split process:

- Identifies natural deliverable boundaries within the epic
- Creates fully independent epics with no cross-epic dependencies
- Preserves all context and quality from the original epic
- Ensures each split epic contains <= 12 tickets (soft limit) or <= 15 tickets
  (hard limit)
- Maintains dependency integrity within each epic

**Important**: This command is invoked automatically by the create-epic workflow
when ticket count >= 13. It can also be run manually on existing oversized
epics.

## Parameters

- `<epic-file-path>`: Path to the original epic YAML file
- `<spec-path>`: Path to the original specification document

## Process Flow

When this command is invoked:

1. **Analyze Epic Structure**: Understand ticket groupings and dependencies
2. **Identify Deliverables**: Find natural capability boundaries
3. **Group Tickets**: Assign tickets to deliverable-focused epics
4. **Validate Independence**: Ensure no cross-epic dependencies
5. **Create Split Epics**: Generate independent epic YAML files
6. **Archive Original**: Rename original epic with .original suffix

## Split Output Structure

```
.epics/[original-epic-name]/
├── [original-epic-name]-spec.md (unchanged)
├── [original-epic-name].epic.yaml.original (archived)
├── [split-epic-1]/
│   ├── [split-epic-1].epic.yaml
│   └── tickets/
└── [split-epic-2]/
    ├── [split-epic-2].epic.yaml
    └── tickets/
```

## Deliverable-Focused Grouping Criteria

When analyzing tickets for grouping, ask these questions for each potential
group:

1. **What capability does this group provide?**
   - Can you name a specific feature, system, or deliverable?
   - Is it user-facing functionality or infrastructure capability?

2. **Can it be delivered and tested independently?**
   - Can this group be deployed without the other groups?
   - Can you write meaningful tests for just this group?

3. **Does it represent a complete capability?**
   - Would a user or system see value from this group alone?
   - Is it a whole feature vs. "part 1 of a feature"?

4. **Does the name describe a deliverable?**
   - Good: "token-caching", "user-session-management", "api-rate-limiting"
   - Bad: "user-auth-part1", "tickets-1-through-12", "epic-split-1"

## Grouping Heuristics (Priority Order)

Apply these heuristics in order when grouping tickets:

### 1. Full Independence (CRITICAL)

- Each epic must be deployable without any other split epic
- No shared state, no sequential ordering required
- Each epic can be executed and tested in isolation
- **Test**: Could you execute each epic on different days/weeks?

### 2. Dependency Chains (CRITICAL)

- **NEVER split tickets with dependencies across epics**
- If ticket A depends on ticket B, they MUST be in the same epic
- Keep entire dependency chains together in one epic
- Circular dependencies = keep all involved tickets together

### 3. Feature Boundaries (PRIMARY)

- Group by complete user-facing or system capabilities
- Examples:
  - Authentication system (login, session, tokens)
  - Caching layer (cache keys, invalidation, storage)
  - Validation framework (validators, error handling, integration)
- Each group should deliver a cohesive feature set

### 4. Architecture Layers (SECONDARY)

- When no clear feature boundaries exist, group by architectural layers:
  - Infrastructure foundation → Core features → Integration & polish
  - Data layer → Business logic → API/UI layer
- Ensure each layer can be delivered independently

### 5. Ticket Count Limits (CONSTRAINT)

- **Soft limit**: 8-12 tickets per epic (ideal range)
- **Hard limit**: 15 tickets maximum per epic
- **Minimum**: 3 tickets per epic (avoid over-splitting)
- If grouping exceeds 15 tickets, split further by sub-capabilities

## Epic Naming Guidelines

Epic names must describe the deliverable capability, not the split itself.

### Good Epic Names

- `token-caching` - describes the caching capability
- `user-session-management` - describes session handling
- `api-rate-limiting` - describes rate limiting feature
- `validation-framework` - describes validation system
- `deployment-automation` - describes automation capability

### Bad Epic Names

- `user-auth-part1` - "part" indicates incomplete feature
- `tickets-1-through-12` - describes tickets, not capability
- `epic-split-1` - describes the split process, not deliverable
- `miscellaneous-fixes` - no clear deliverable
- `phase-2` - describes sequence, not capability

## Dependency Preservation Rules

Dependencies are CRITICAL to maintain:

1. **Intra-Epic Dependencies** (ALLOWED):
   - Ticket B depends on Ticket A, both in same epic: ✓
   - Dependency graph preserved within epic YAML

2. **Cross-Epic Dependencies** (FORBIDDEN):
   - Ticket B in epic-1 depends on Ticket A in epic-2: ✗
   - This violates independence requirement
   - **Solution**: Move both tickets to same epic

3. **Dependency Chain Handling**:
   - If chain: A → B → C → D, all 4 tickets MUST be together
   - Cannot split at any point in the chain
   - Long chains may prevent splitting (see edge cases)

4. **Circular Dependencies**:
   - If A depends on B and B depends on A (directly or indirectly)
   - Keep all tickets in the cycle together in one epic

## Edge Case Handling

### Long Dependency Chains

**Problem**: Epic with 20 tickets, all in one dependency chain

**Solution**:

- Cannot split - keep entire chain in one epic
- Warn user: "Epic has long dependency chain (20 tickets). Cannot split while
  maintaining independence. Consider refactoring to reduce coupling."

### Circular Dependencies

**Problem**: Multiple tickets with circular dependency relationships

**Solution**:

- Identify all tickets in circular dependency groups
- Keep each circular group together in one epic
- May result in larger epics than ideal

### Too Many Tickets

**Problem**: Epic with 40+ tickets needs splitting but natural groups are large

**Solution**:

- Create 3+ independent epics instead of 2
- Look for finer-grained deliverable boundaries
- Example: Split "user-management" into:
  - `user-authentication` (login, session, tokens)
  - `user-profiles` (profile CRUD, preferences)
  - `user-permissions` (roles, access control)

### Cannot Achieve Independence

**Problem**: All tickets are tightly coupled, cannot form independent groups

**Solution**:

- Fail the split process gracefully
- Report: "Cannot split epic while maintaining independence. All tickets are
  tightly coupled. Consider epic redesign to improve modularity."
- Keep original epic intact with .original suffix removed

### Manual Split Override

**Option**: `--no-split` flag

**Behavior**:

- Skip splitting workflow entirely
- Warn user: "Epic has N tickets (exceeds recommended limit of 12). Proceeding
  without split. Large epics may be harder to execute and track."

## Implementation

When this command is invoked, the specialist agent will:

1. **Parse Epic Structure**:
   - Load epic YAML and spec document
   - Extract ticket list, descriptions, and dependencies
   - Build dependency graph

2. **Analyze Grouping Opportunities**:
   - Identify dependency chains and circular dependencies
   - Find feature boundaries and natural capability groups
   - Score each potential grouping against criteria

3. **Create Split Groups**:
   - Assign tickets to deliverable-focused groups
   - Ensure no cross-epic dependencies
   - Validate ticket count constraints
   - Generate meaningful epic names

4. **Generate Split Epic Files**:
   - Create subdirectory for each split epic
   - Generate epic YAML with proper subset of tickets
   - Preserve ticket descriptions and dependencies
   - Add ticket_count field to each epic

5. **Validate Split Quality**:
   - Verify full independence (no cross-epic deps)
   - Check ticket count limits (soft and hard)
   - Ensure each epic has deliverable focus
   - Validate epic naming quality

6. **Report Results**:
   - List each created epic with:
     - Epic name and deliverable description
     - Ticket count
     - File path
   - Show archived original epic path
   - Emphasize independence for execution

## Task Agent Instructions

Main Claude will provide these exact instructions to the Task agent:

```
You are splitting an oversized epic into multiple independent deliverable-focused
epics. Your task is to:

1. Read and analyze:
   - Epic YAML at: [epic-file-path]
   - Specification document at: [spec-path]
   - Extract ticket list with descriptions and dependencies
   - Build complete dependency graph

2. Identify deliverable groupings:
   - Find natural feature boundaries (auth, caching, validation, etc.)
   - Identify dependency chains that must stay together
   - Look for complete capabilities that can be delivered independently
   - Apply grouping heuristics in priority order:
     a) Full independence - each group deployable alone
     b) Dependency preservation - keep chains together
     c) Feature boundaries - complete capabilities
     d) Architecture layers - if no clear features
     e) Ticket count limits - 8-12 ideal, 15 max

3. Create split groups:
   - Assign each ticket to exactly one deliverable group
   - Ensure NO cross-epic dependencies (critical requirement)
   - Validate each group represents a complete deliverable
   - Generate meaningful epic names (deliverable-focused, not "part1")
   - Ensure each group has 3-15 tickets (min 3, max 15)

4. Generate split epic files:
   - Create subdirectory: .epics/[original-name]/[split-epic-name]/
   - Create tickets subdirectory: .epics/[original-name]/[split-epic-name]/tickets/
   - Generate epic YAML: .epics/[original-name]/[split-epic-name]/[split-epic-name].epic.yaml
   - Include these fields in each split epic YAML:
     * epic: "[Deliverable Name]"
     * description: "[Clear description of what capability this delivers]"
     * ticket_count: N
     * acceptance_criteria: [Subset relevant to this deliverable]
     * coordination_requirements: [Subset relevant to these tickets]
     * tickets: [Only tickets for this epic with preserved dependencies]

5. Archive original epic:
   - Rename: [original].epic.yaml → [original].epic.yaml.original
   - Preserve exact content (no modifications)
   - Keep spec document unchanged at top level

6. Validate split quality:
   - CRITICAL: Verify each split epic has ZERO dependencies on other split epics
   - Check all dependency chains are preserved within single epics
   - Ensure ticket counts meet constraints (3-15 per epic)
   - Verify epic names describe deliverables, not splits
   - Confirm each epic represents a complete, testable capability

7. Handle edge cases:
   - Long dependency chain: Keep entire chain together, may exceed 15 tickets
   - Circular dependencies: Keep all involved tickets together
   - Cannot achieve independence: Fail gracefully, report coupling issue
   - Too many tickets: Create 3+ epics with finer-grained boundaries

8. Report results:
   - For each split epic created:
     * Epic name and deliverable description
     * Ticket count
     * File path
     * Key capabilities included
   - Original epic archive path
   - Confirmation of independence: "Each epic is fully independent and can be
     executed in any order"
   - If split failed: Clear explanation of why (dependencies, coupling, etc.)

CRITICAL REQUIREMENTS:
- Each split epic MUST be fully independent (no cross-epic dependencies)
- All dependency chains MUST stay within single epics
- Epic names MUST describe deliverables, not splits or parts
- Each epic MUST represent a complete, testable capability
- Ticket counts: 3 minimum, 12 ideal, 15 maximum per epic
- If independence cannot be achieved, FAIL the split and report why
```

## Validation Checklist

Before finalizing the split, verify:

- [ ] Each split epic has 3-15 tickets
- [ ] No cross-epic dependencies exist
- [ ] All dependency chains preserved within single epics
- [ ] Epic names describe deliverables (not "part1", "split2", etc.)
- [ ] Each epic represents a complete, testable capability
- [ ] Original epic archived with .original suffix
- [ ] Spec document remains at top level unchanged
- [ ] Subdirectories created for each split epic
- [ ] ticket_count field present in each split epic YAML

## Related Commands

- `/create-epic`: Creates epic YAML from specification (triggers auto-split if
  > = 13 tickets)
- `/execute-epic`: Executes epic tickets (works with split epics independently)
- `/validate-epic`: Validates epic structure and dependencies
