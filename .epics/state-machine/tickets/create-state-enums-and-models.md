# create-state-enums-and-models

## Description
Define TicketState and EpicState enums, plus core data classes (Ticket, GitInfo, EpicContext)

## Epic Context
This ticket is foundational to the state machine epic, which replaces LLM-driven coordination with a Python state machine for deterministic epic execution. The state machine enforces structured execution, precise git strategies, and state transitions while the LLM focuses solely on implementing ticket requirements.

**Core Insight**: LLMs are excellent at creative problem-solving (implementing features, fixing bugs) but poor at following strict procedural rules consistently. This architecture inverts that: the state machine handles procedures, the LLM handles problems.

**Key Objectives**:
- Deterministic State Transitions: Python code enforces state machine rules, LLM cannot bypass gates
- Auditable Execution: State machine logs all transitions and gate checks for debugging
- Resumability: State machine can resume from epic-state.json after crashes

**Key Constraints**:
- State machine written in Python with explicit state classes and transition rules
- Epic execution produces identical git structure on every run (given same tickets)
- State file (epic-state.json) is private to state machine

## Acceptance Criteria
- TicketState enum with states: PENDING, READY, BRANCH_CREATED, IN_PROGRESS, AWAITING_VALIDATION, COMPLETED, FAILED, BLOCKED
- EpicState enum with states: INITIALIZING, EXECUTING, MERGING, FINALIZED, FAILED, ROLLED_BACK
- Ticket dataclass with all required fields (id, path, title, depends_on, critical, state, git_info, etc.)
- GitInfo dataclass with branch_name, base_commit, final_commit
- AcceptanceCriterion dataclass for tracking acceptance criteria
- GateResult dataclass for gate check results
- All classes use dataclasses with proper type hints
- Models are in buildspec/epic/models.py

## Dependencies
None

## Files to Modify
- /Users/kit/Code/buildspec/epic/models.py

## Additional Notes
These models form the foundation of the state machine's type system. The TicketState enum must capture all possible states a ticket can be in throughout its lifecycle. The EpicState enum tracks the overall execution state. The dataclasses should be immutable where possible and use proper type hints for type safety.

GitInfo tracks the git metadata for each ticket's branch, enabling the stacked branch strategy where each ticket branches from the previous ticket's final commit.
