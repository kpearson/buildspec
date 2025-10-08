# Create Epic CLI Commands

## Description
Create CLI commands for state machine API (status, start-ticket, complete-ticket, fail-ticket, finalize)

## Dependencies
- implement-get-epic-status-api
- implement-get-ready-tickets-api
- implement-start-ticket-api
- implement-complete-ticket-api
- implement-fail-ticket-api
- implement-finalize-epic-api

## Acceptance Criteria
- [ ] Click command group 'buildspec epic' with subcommands
- [ ] epic status <epic_file> shows epic status JSON
- [ ] epic status <epic_file> --ready shows ready tickets JSON
- [ ] epic start-ticket <epic_file> <ticket_id> creates branch and returns info JSON
- [ ] epic complete-ticket <epic_file> <ticket_id> --final-commit --test-status --acceptance-criteria validates and returns result JSON
- [ ] epic fail-ticket <epic_file> <ticket_id> --reason marks ticket failed
- [ ] epic finalize <epic_file> collapses tickets and pushes epic branch
- [ ] All commands output JSON for LLM consumption
- [ ] Error handling with clear messages and non-zero exit codes
- [ ] Commands are in buildspec/cli/epic_commands.py

## Files to Modify
- /Users/kit/Code/buildspec/cli/epic_commands.py
