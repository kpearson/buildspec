# update-execute-epic-orchestrator-instructions

## Description
Update execute-epic.md with simplified orchestrator instructions using state machine API

## Epic Context
This ticket updates the LLM orchestrator instructions to use the new state machine API. The orchestrator's role is simplified: it no longer handles git operations, state management, or coordination logic. It simply queries the state machine for ready tickets and spawns sub-agents to execute them.

**Core Insight**: LLMs are excellent at creative problem-solving but poor at following strict procedural rules consistently. The new architecture has the state machine handle all procedures while the LLM handles spawning workers and collecting results.

**Key Objectives**:
- LLM Interface Boundary: Clear contract between state machine (coordinator) and LLM (worker)
- Deterministic State Transitions: State machine enforces all rules, LLM just reports results

**Key Constraints**:
- LLM agents interact with state machine via CLI commands only
- Synchronous execution enforced (concurrency = 1)

## Acceptance Criteria
- execute-epic.md describes LLM orchestrator responsibilities
- Documents all state machine API commands with examples
- Shows synchronous execution loop (Phase 1 and Phase 2)
- Explains what LLM does NOT do (create branches, merge, update state file)
- Provides clear error handling patterns
- Documents sub-agent spawning with Task tool
- Shows how to report completion back to state machine

## Dependencies
- create-epic-cli-commands

## Files to Modify
- /Users/kit/Code/buildspec/.claude/prompts/execute-epic.md

## Additional Notes
The new orchestrator instructions should follow this pattern:

**Phase 1: Initialization**
1. Call `buildspec epic status <epic_file>` to get current state
2. If resuming, understand which tickets are already complete

**Phase 2: Execution Loop**
```
while tickets remain:
  1. Call `buildspec epic status <epic_file> --ready` to get ready tickets
  2. If no ready tickets and no in_progress tickets, epic is done
  3. Pick first ready ticket
  4. Call `buildspec epic start-ticket <epic_file> <ticket_id>`
  5. Spawn sub-agent with Task tool to execute ticket
  6. Wait for sub-agent to complete
  7. Sub-agent reports: final_commit, test_status, acceptance_criteria
  8. Call `buildspec epic complete-ticket <epic_file> <ticket_id> ...`
  9. If validation fails, handle error (retry or call fail-ticket)
  10. Repeat
```

**Phase 3: Finalization**
1. Call `buildspec epic finalize <epic_file>` to collapse branches

**What LLM Does NOT Do**:
- Does NOT create git branches
- Does NOT merge branches
- Does NOT update epic-state.json directly
- Does NOT calculate base commits
- Does NOT validate ticket completion

All of that is handled by the state machine via CLI commands.
