# implement-start-ticket-api

## Description
Implement start_ticket() public API method in state machine

## Epic Context
This public API method starts a ticket, transitioning it through BRANCH_CREATED to IN_PROGRESS. It creates the git branch using the stacked branch strategy and enforces synchronous execution.

**Git Strategy Context**:
- Each ticket branches from previous ticket's final commit (true stacking)
- Branch created with format "ticket/{ticket-id}"
- Branch pushed to remote for LLM worker access

**Key Objectives**:
- Git Strategy Enforcement: Stacked branch creation handled by code
- Deterministic State Transitions: Gates enforce rules before transitions
- LLM Interface Boundary: Clear contract for starting work

**Key Constraints**:
- LLM agents interact with state machine via CLI commands only
- Synchronous execution enforced (concurrency = 1)
- Git operations are deterministic

## Acceptance Criteria
- start_ticket(ticket_id) transitions ticket READY → BRANCH_CREATED → IN_PROGRESS
- Runs CreateBranchGate to create branch from base commit
- Runs LLMStartGate to enforce concurrency
- Updates ticket.git_info with branch_name and base_commit
- Returns dict with branch_name, base_commit, ticket_file, epic_file
- Raises StateTransitionError if gates fail
- Marks ticket.started_at timestamp

## Dependencies
- implement-state-machine-core
- implement-create-branch-gate
- implement-llm-start-gate

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py

## Additional Notes
This method orchestrates the ticket start process:

1. **Validate State**: Ensure ticket is in READY state
2. **Create Branch** (READY → BRANCH_CREATED):
   - Run CreateBranchGate to create branch from correct base commit
   - Update ticket.git_info with branch_name and base_commit from gate metadata
   - Persist state
3. **Start Work** (BRANCH_CREATED → IN_PROGRESS):
   - Run LLMStartGate to enforce concurrency and verify branch exists
   - Mark ticket.started_at timestamp
   - Persist state
4. **Return Info**: Return dict with all info LLM needs to start work:
   - branch_name: the git branch to work on
   - base_commit: the starting commit
   - ticket_file: path to ticket markdown file
   - epic_file: path to epic YAML file

The two-step transition (READY → BRANCH_CREATED → IN_PROGRESS) ensures the branch creation and LLM start are separate, auditable steps.
