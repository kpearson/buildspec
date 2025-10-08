# Implement Get Epic Status API

## Description
Implement get_epic_status() public API method to return current epic state

## Dependencies
- implement-state-machine-core

## Acceptance Criteria
- [ ] get_epic_status() returns dict with epic_state, tickets, stats
- [ ] Tickets dict includes state, critical, git_info for each ticket
- [ ] Stats include total, completed, in_progress, failed, blocked counts
- [ ] JSON serializable output

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py
