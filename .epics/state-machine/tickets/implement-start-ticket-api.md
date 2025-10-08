# Implement Start Ticket API

## Description
Implement start_ticket() public API method in state machine

## Dependencies
- implement-state-machine-core
- implement-create-branch-gate
- implement-llm-start-gate

## Acceptance Criteria
- [ ] start_ticket(ticket_id) transitions ticket READY → BRANCH_CREATED → IN_PROGRESS
- [ ] Runs CreateBranchGate to create branch from base commit
- [ ] Runs LLMStartGate to enforce concurrency
- [ ] Updates ticket.git_info with branch_name and base_commit
- [ ] Returns dict with branch_name, base_commit, ticket_file, epic_file
- [ ] Raises StateTransitionError if gates fail
- [ ] Marks ticket.started_at timestamp

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py
