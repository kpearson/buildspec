# Implement Finalize Epic API

## Description
Implement finalize_epic() public API method to collapse tickets into epic branch

## Dependencies
- implement-complete-ticket-api
- implement-git-operations-wrapper

## Acceptance Criteria
- [ ] finalize_epic() verifies all tickets are COMPLETED, BLOCKED, or FAILED
- [ ] Transitions epic state to MERGING
- [ ] Gets tickets in topological order (dependencies first)
- [ ] Squash merges each COMPLETED ticket into epic branch sequentially
- [ ] Uses merge_branch with strategy="squash"
- [ ] Generates commit message: "feat: {ticket.title}\n\nTicket: {ticket.id}"
- [ ] Deletes ticket branches after successful merge
- [ ] Pushes epic branch to remote
- [ ] Transitions epic state to FINALIZED
- [ ] Returns dict with success, epic_branch, merge_commits, pushed
- [ ] Handles merge conflicts and returns error if merge fails

## Files to Modify
- /Users/kit/Code/buildspec/epic/state_machine.py
