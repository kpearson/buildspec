# split-epic-specialist-command

## Description

Create claude_files/commands/split-epic.md with specialist agent instructions
for analyzing and splitting oversized epics into independent deliverables.

This command file defines how the specialist agent should analyze epics
with >=13 tickets and intelligently split them into multiple fully independent
epics, each representing a cohesive deliverable capability.

## Acceptance Criteria

- Command file documents deliverable-focused grouping criteria
- Specifies full independence requirement (no cross-epic dependencies)
- Defines subdirectory structure for split epics
- Includes grouping heuristics in priority order
- Documents ticket count limits (soft: 12, hard: 15)
- Provides examples of good vs bad epic names
- Specifies dependency preservation rules (keep dependent tickets together)
- Includes edge case handling instructions

## Files to Modify

- /Users/kit/Code/buildspec/claude_files/commands/split-epic.md (NEW FILE)

## Dependencies

None - This defines the specialist agent contract

## Implementation Notes

### Key Content Sections

1. **Purpose and Goals**
   - Automatically split oversized epics (>=13 tickets)
   - Preserve all context and quality from original
   - Create fully independent deliverable-focused epics
   - Each epic <= 12 tickets (soft) or <= 15 tickets (hard)

2. **Deliverable-Focused Grouping Criteria**
   - What capability does this group provide?
   - Can it be delivered and tested independently?
   - Does it represent complete user-facing or system capability?
   - Does the name describe a deliverable (not "part1", "part2")?

3. **Grouping Heuristics (Priority Order)**
   - Full independence - each epic deployable without others
   - Dependency chains - keep ALL dependent tickets together
   - Feature boundaries - complete capabilities (auth, caching, validation)
   - Architecture layers - infrastructure → features → integration
   - Ticket count limits - 8-12 tickets per epic (soft), 15 max (hard)

4. **File Structure Requirements**

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

5. **Epic Naming Guidelines**
   - GOOD: "token-caching", "user-session-management", "api-rate-limiting"
   - BAD: "user-auth-part1", "tickets-1-through-12", "epic-split-1"

6. **Edge Cases**
   - Circular dependencies: Keep all tickets together
   - Long dependency chain: Cannot split - keep entire chain
   - Too many tickets: Create 3+ independent epics
   - Cannot achieve independence: Fail split, warn user

7. **Output Requirements**
   - Multiple independent epic YAML files
   - Each epic has clear deliverable purpose
   - Summary report showing what each epic delivers
   - No cross-epic dependencies

### Coordination Role

Provides specialist agent instructions and split epic format specification,
defining the behavior and output contract for the split workflow.
