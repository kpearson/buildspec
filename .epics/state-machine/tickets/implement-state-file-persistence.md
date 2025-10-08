# Implement State File Persistence

## Description
Add state file loading and atomic saving to state machine

## Dependencies
- create-state-enums-and-models

## Acceptance Criteria
- [ ] State machine can save epic-state.json atomically (write to temp, then rename)
- [ ] State machine can load state from epic-state.json for resumption
- [ ] State file includes epic metadata (id, branch, baseline_commit, started_at)
- [ ] State file includes all ticket states with git_info
- [ ] JSON schema validation on load
- [ ] Proper error handling for corrupted state files
- [ ] State file created in epic_dir/artifacts/epic-state.json

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py
