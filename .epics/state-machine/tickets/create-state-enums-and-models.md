# Create State Enums and Models

## Description
Define TicketState and EpicState enums, plus core data classes (Ticket, GitInfo, EpicContext)

## Dependencies
None

## Acceptance Criteria
- [ ] TicketState enum with states: PENDING, READY, BRANCH_CREATED, IN_PROGRESS, AWAITING_VALIDATION, COMPLETED, FAILED, BLOCKED
- [ ] EpicState enum with states: INITIALIZING, EXECUTING, MERGING, FINALIZED, FAILED, ROLLED_BACK
- [ ] Ticket dataclass with all required fields (id, path, title, depends_on, critical, state, git_info, etc.)
- [ ] GitInfo dataclass with branch_name, base_commit, final_commit
- [ ] AcceptanceCriterion dataclass for tracking acceptance criteria
- [ ] GateResult dataclass for gate check results
- [ ] All classes use dataclasses with proper type hints
- [ ] Models are in buildspec/epic/models.py

## Files to Modify
- /Users/kit/Code/buildspec/epic/models.py
