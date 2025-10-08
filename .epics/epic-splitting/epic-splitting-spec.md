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
3. Use a specialist agent to intelligently split oversized epics
4. Preserve all context and quality from the original epic
5. Maintain ticket dependencies across split epics
6. Support execution of coordinated multi-epic workflows

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
   
3. Create multiple standalone epic YAML files:
   - `token-caching.epic.yaml` (complete deliverable)
   - `token-caching-integration.epic.yaml` (complete deliverable)
   - Each epic has a clear deliverable purpose
   
4. **No epic hierarchies, no orchestrator epics** - Each split epic is independent
   
5. Preserve ticket dependencies **within each epic**:
   - Dependencies that span epics become ordering constraints
   - Document execution order in split summary

**Output:**
- Multiple epic files in same directory, each named for its deliverable
- Each epic has <= 12 tickets (soft limit), <= 15 tickets (hard limit)
- Preserved dependencies within each epic
- Summary report showing:
  - What each epic delivers
  - How the split preserves the original intent
- **Each epic is independent** - execute separately as needed

### File Structure

```
.epics/user-auth/
├── user-auth-spec.md              # Original spec
├── user-auth.epic.yaml            # Original oversized epic (25 tickets) - archived
├── token-caching.epic.yaml        # Deliverable 1: Token caching (10 tickets)
└── token-caching-integration.epic.yaml  # Deliverable 2: Token caching use cases (4 tickets)
```

**No hierarchy, no orchestrator epic** - Each split epic is a standalone deliverable.

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
Root Claude creates epic (unconstrained, high quality)
  ↓
Epic file created: my-epic.epic.yaml
  ↓
Python: Parse YAML, check ticket_count
  ↓
ticket_count = 25 (>= 13) → Trigger split
  ↓
Root Claude spawns specialist agent
  ↓
Specialist reads original epic, proposes split
  ↓
Creates: token-caching.epic.yaml (10 tickets) 
         token-caching-integration.epic.yaml (4 tickets)
  ↓
Display: "Epic split into 2 independent deliverables (25 → 14 tickets)"
         "Created: token-caching.epic.yaml (10 tickets)"
         "Created: token-caching-integration.epic.yaml (4 tickets)"
         "Execute each independently as needed"
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

1. **Feature boundaries** - Complete capabilities (auth, caching, validation)
2. **Dependency chains** - Keep dependent tickets together when possible
3. **Architecture layers** - Infrastructure → Features → Integration (if they're distinct deliverables)
4. **Ticket count limits** - 8-12 tickets per epic (soft), 15 max (hard)

## Edge Cases

1. **Circular dependencies across split** - Keep in same epic
2. **Too many tickets to split reasonably** - Create 3+ epics
3. **Single dependency chain** - Split by phases within chain
4. **User specifies --no-split flag** - Skip splitting, warn about size

## Success Criteria

1. Epic creation produces unconstrained, high-quality epics
2. Oversized epics (>=13 tickets) are automatically detected
3. Split epics maintain all context and quality
4. Split epics are <= 12 tickets (soft) or <= 15 tickets (hard)
5. Dependencies are preserved within and across epics
6. No manual intervention required
7. Clear feedback about split results

## Future Enhancements

1. **Split preview** - Show proposed split before creating files (with approval step)
2. **Adaptive splitting** - Learn optimal deliverable boundaries over time
3. **Code review agent** - Automatically runs after epic execution, scores work quality, triggers improvement cycle if below threshold

## Testing Strategy

1. Create epic with exactly 12 tickets - should NOT split
2. Create epic with 13 tickets - should split
3. Create epic with 25 tickets - should split into 2 epics
4. Create epic with 40 tickets - should split into 3+ epics
5. Verify dependencies preserved across split
6. Verify ticket quality maintained after split

## Related Work

- High-quality ticket definition (to be added to epic creation)
- Epic orchestration for multi-epic workflows
- Dependency visualization across epics
