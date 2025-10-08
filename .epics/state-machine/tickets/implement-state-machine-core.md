# Implement State Machine Core

## Description
Implement EpicStateMachine core with state transitions and ticket lifecycle management

## Dependencies
- create-state-enums-and-models
- implement-state-file-persistence

## Acceptance Criteria
- [ ] EpicStateMachine class with __init__ accepting epic_file and resume flag
- [ ] Loads state from epic-state.json if resume=True
- [ ] Initializes new epic if resume=False
- [ ] Private _transition_ticket method with validation
- [ ] Private _run_gate method to execute gates and log results
- [ ] Private _is_valid_transition to validate state transitions
- [ ] Private _update_epic_state to update epic-level state based on ticket states
- [ ] Transition logging with timestamps
- [ ] State persistence on every transition

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py
