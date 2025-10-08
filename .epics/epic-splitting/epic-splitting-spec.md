# Epic Splitting Specification

## Overview

Automatically detect oversized epics (>12 tickets) and split them into multiple coordinated epics using a specialist agent. This ensures epics remain manageable while preserving all the high-quality planning from the original epic creation.

## Problem Statement

Epic creation should produce the highest quality epic possible without artificial constraints. However, epics with >12 tickets become difficult to orchestrate:
- Execution time becomes excessive (>2 hours)
- Error accumulation increases
- Dependency management becomes complex
- Context window usage grows

Currently, there's no mechanism to handle oversized epics - they either fail or take too long to execute.

## Goals

1. Allow epic creation to produce unconstrained, high-quality epics
2. Automatically detect when an epic needs splitting (>12 tickets)
3. Use a specialist agent to intelligently split oversized epics into independent deliverables
4. Preserve all context and quality from the original epic
5. Ensure each split epic is fully independent and deployable
6. Preserve ticket dependencies within each epic (no cross-epic dependencies)

## Non-Goals

- Constraining epic creation (let it be pure)
- Manual epic splitting by users
- Losing context or quality during split
- Breaking existing single-epic workflows

## Technical Design

### Phase 1: Post-Creation Validation

After `create-epic` completes successfully:

1. **Python validation** (cheap, fast):
   - Parse the generated epic YAML
   - Count tickets in the `tickets:` array
   - If count >= 13: trigger split workflow
   - If count <= 12: success, done

2. **Epic metadata requirement**:
   - Epic YAML must include `ticket_count: N` field (add to create-epic instructions)
   - This makes validation trivial without full YAML parsing

### Phase 2: Specialist Splitting Agent

When ticket count >= 13, invoke specialist agent:

**Input:**
- Original epic YAML (high quality, complete)
- Original spec document
- Ticket count and soft limit (12)

**Specialist agent tasks:**
1. Analyze tickets and identify **cohesive deliverables**:
   - What meaningful feature/capability does this group provide?
   - Can this group be delivered and tested independently?
   - Does this represent a complete user-facing or system capability?
   
2. Group tickets into deliverable-focused epics:
   - Example: 10 tickets that deliver "token caching" as a complete feature
   - Example: 4 tickets that deliver "token caching use cases" 
   - NOT: arbitrary splits like "part1" and "part2"
   
3. Create subdirectories for each split epic:
   - `token-caching/token-caching.epic.yaml` (complete deliverable)
   - `token-caching-integration/token-caching-integration.epic.yaml` (complete deliverable)
   - Each epic gets its own directory with tickets/ subdirectory
   - Each epic has a clear deliverable purpose
   
4. **No epic hierarchies, no orchestrator epics** - Each split epic is independent
   
5. Ensure full independence:
   - Each epic is fully deployable on its own
   - No cross-epic dependencies - tickets that depend on each other stay in same epic
   - If tickets must be split across epics, they cannot have dependencies

**Output:**
- Multiple epic files in same directory, each named for its deliverable
- Each epic has <= 12 tickets (soft limit), <= 15 tickets (hard limit)
- Preserved dependencies within each epic
- Summary report showing:
  - What each epic delivers
  - How the split preserves the original intent
- **Each epic is independent** - execute separately as needed

### File Structure

When splitting, create subdirectories for each split epic:

```
.epics/user-auth/
├── user-auth-spec.md              # Original spec
├── user-auth.epic.yaml.original   # Original oversized epic (archived)
├── token-caching/
│   ├── token-caching.epic.yaml    # Deliverable 1: Token caching (10 tickets)
│   └── tickets/                   # Ticket files for this epic
└── token-caching-integration/
    ├── token-caching-integration.epic.yaml  # Deliverable 2: Integration (4 tickets)
    └── tickets/                   # Ticket files for this epic
```

**Benefits:**
- Clean organization - each split epic has its own directory
- Ticket files are scoped to their epic
- Original spec and archived epic remain at top level
- No hierarchy - each subdirectory is independent

### Epic YAML Format Updates

**Add `ticket_count` field:**
```yaml
epic: "User Authentication System"
description: "..."
ticket_count: 25  # NEW: Required field for validation
acceptance_criteria: [...]
tickets: [...]
```

**No epic-level dependencies** - Split epics are independent deliverables that can be executed in sequence or parallel as needed. Ticket-level dependencies within each epic remain unchanged.

### Implementation Plan

**File Changes:**

1. **cli/commands/create_epic.py**:
   - After epic creation succeeds
   - Parse YAML to get `ticket_count`
   - If >= 13, invoke split workflow
   - Create subdirectories for each split epic
   - Move/archive original epic
   - Display split results

2. **cli/core/prompts.py**:
   - Add `build_split_epic()` method
   - Creates specialist prompt for splitting

3. **claude_files/commands/create-epic.md**:
   - Add instruction: MUST include `ticket_count: N` at top of YAML

4. **claude_files/commands/split-epic.md** (NEW):
   - Specialist agent instructions for splitting oversized epics

5. **cli/utils/epic_validator.py** (NEW):
   - Parse epic YAML
   - Extract ticket_count
   - Validate ticket count limits

### Workflow

```
User: buildspec create-epic spec.md
  ↓
Claude creates epic (unconstrained, high quality)
  ↓
Epic file created: my-epic.epic.yaml
  ↓
Python: Parse YAML, check ticket_count
  ↓
ticket_count = 25 (>= 13) → Trigger split
  ↓
Buildspec invokes specialist agent via Claude subprocess
  ↓
Specialist reads original epic, identifies independent deliverables
  ↓
Creates: token-caching/token-caching.epic.yaml (10 tickets) 
         token-caching-integration/token-caching-integration.epic.yaml (4 tickets)
Archives: my-epic.epic.yaml → my-epic.epic.yaml.original
  ↓
Display: "Epic split into 2 independent deliverables (25 → 14 tickets)"
         "Created: token-caching/token-caching.epic.yaml (10 tickets)"
         "Created: token-caching-integration/token-caching-integration.epic.yaml (4 tickets)"
         "Original epic archived as: my-epic.epic.yaml.original"
         "Execute each epic independently - no dependencies between them"
```

## Ticket Count Thresholds

- **Soft limit: 12 tickets** - Ideal epic size
- **Hard limit: 15 tickets** - Maximum per epic after split
- **Split trigger: 13 tickets** - When to invoke specialist

**Rationale:**
- 12 tickets = 1-2 hours execution (sweet spot)
- 13-15 tickets = still manageable but should avoid
- Split aims for 8-12 tickets per epic

## Epic Splitting Philosophy

**Core Principle:** Each split epic must represent a **cohesive, independently deliverable capability**.

### Why This Matters

The three-step process exists because of AI agent strengths/weaknesses:

1. **Spec (1-2k lines)**: LLM reasons about all factors centrally - no grepping around codebase
2. **Epic (filtered)**: Removes pseudo-code, keeps intent, method profiles, directory structure, ticket outline
3. **Ticket**: Detailed unit of work for builder agent

**Epic splitting must preserve this philosophy** - each split epic delivers something meaningful, not arbitrary chunks.

### Deliverable-Focused Grouping

The specialist agent should identify deliverables by asking:

1. **What capability does this provide?** 
   - "Token caching system" (infrastructure)
   - "Token caching use cases" (features using the infrastructure)
   
2. **Can it be delivered independently?**
   - Can be built, tested, and validated on its own
   - Provides value even if other epics aren't done yet
   
3. **Does it have natural boundaries?**
   - Clear start and end points
   - Minimal cross-epic dependencies
   
4. **Does the name describe a deliverable?**
   - ✓ "user-session-management.epic.yaml"
   - ✓ "api-rate-limiting.epic.yaml"
   - ✗ "user-auth-part1.epic.yaml"
   - ✗ "tickets-1-through-12.epic.yaml"

### Grouping Heuristics (in priority order)

1. **Full independence** - Each epic must be deployable without any other epic
2. **Dependency chains** - Keep ALL dependent tickets in the same epic (cannot split dependencies)
3. **Feature boundaries** - Complete capabilities (auth, caching, validation)
4. **Architecture layers** - Infrastructure → Features → Integration (only if fully independent)
5. **Ticket count limits** - 8-12 tickets per epic (soft), 15 max (hard)

## Edge Cases

1. **Circular dependencies** - Keep all tickets with circular deps in same epic
2. **Long dependency chain** - Cannot split - keep entire chain in one epic
3. **Too many tickets to split** - Create 3+ independent epics, each fully standalone
4. **Cannot achieve independence** - Fail split, warn user epic is too coupled to split
5. **User specifies --no-split flag** - Skip splitting, warn about size

## Success Criteria

1. Epic creation produces unconstrained, high-quality epics
2. Oversized epics (>=13 tickets) are automatically detected
3. Split epics maintain all context and quality
4. Split epics are <= 12 tickets (soft) or <= 15 tickets (hard)
5. **Each split epic is fully independent** - no cross-epic dependencies
6. Dependencies are preserved within each epic only
7. No manual intervention required
8. Clear feedback about split results
9. Original epic is archived for reference

## Future Enhancements

1. **Split preview** - Show proposed split before creating files (with approval step)
2. **Adaptive splitting** - Learn optimal deliverable boundaries over time
3. **Code review agent** - Automatically runs after epic execution, scores work quality, triggers improvement cycle if below threshold

## Testing Strategy

1. Create epic with exactly 12 tickets - should NOT split
2. Create epic with 13 independent tickets - should split into 2 independent epics
3. Create epic with 25 independent tickets - should split into 2-3 independent epics
4. Create epic with 20 tickets in dependency chain - should NOT split (cannot break dependencies)
5. Create epic with 40 tickets - should split into 3+ independent epics
6. Verify each split epic is fully independent (no cross-epic dependencies)
7. Verify dependencies preserved within each epic
8. Verify ticket quality maintained after split
9. Verify original epic is archived

## Related Work

- High-quality ticket definition (to be added to epic creation)
- Code review agent for quality scoring and improvement cycles
- Dependency visualization within epics
