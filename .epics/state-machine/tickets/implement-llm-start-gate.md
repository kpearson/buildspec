# Implement LLM Start Gate

## Description
Implement LLMStartGate to enforce synchronous execution and verify branch exists

## Dependencies
- create-gate-interface-and-protocol
- implement-git-operations-wrapper

## Acceptance Criteria
- [ ] LLMStartGate enforces concurrency = 1 (only one ticket in IN_PROGRESS or AWAITING_VALIDATION)
- [ ] Returns GateResult with passed=False if another ticket is active
- [ ] Verifies branch exists on remote before allowing start
- [ ] Returns GateResult with passed=True if concurrency limit not exceeded and branch exists

## Files to Modify
- /Users/kit/Code/buildspec/epic/gates.py
