# Happy path integration test for 3-ticket sequential epic

**Ticket ID:** add-happy-path-integration-test

**Critical:** true

**Dependencies:** core-state-machine, create-git-operations, implement-dependency-gate, implement-branch-creation-gate, implement-llm-start-gate, implement-validation-gate, implement-finalization-logic

**Coordination Role:** Validates core execution flow with real git operations

## Description

As a developer, I want an integration test for the happy path (3-ticket sequential epic completing successfully) so that I can verify the core execution flow works end-to-end with real git operations.

This ticket creates tests/integration/epic/test_happy_path.py that tests complete epic execution with the state machine (ticket: core-state-machine). The test creates a fixture epic with 3 sequential tickets (A, B depends on A, C depends on B), runs execute(), and verifies stacked branches, ticket execution order, final collapse, and epic branch push. Uses real git repository (temporary directory) and mocked ClaudeTicketBuilder to simulate ticket implementation. Key test scenarios:
- test_happy_path_3_sequential_tickets(): Create fixture epic YAML with 3 tickets, create ticket markdown files, mock ClaudeTicketBuilder to return success with fake commits, initialize real git repo, run EpicStateMachine.execute(), verify branches created (ticket/A, ticket/B, ticket/C), verify ticket/B branched from A's final commit, verify ticket/C branched from B's final commit, verify all tickets transitioned to COMPLETED, verify epic branch contains all changes, verify ticket branches deleted, verify epic branch pushed to remote, verify state file persisted

## Acceptance Criteria

- Test creates fixture epic YAML and ticket files programmatically
- Test uses real git operations (temporary git repository)
- Test verifies stacked branch structure (B from A, C from B)
- Test verifies final epic branch contains all ticket changes
- Test verifies state file persisted correctly
- Test passes consistently (no flakiness)

## Testing

This IS the integration test. Run it to verify core flow. Expected runtime: <5 seconds.

## Non-Goals

No failure scenarios in this test, no complex dependencies (diamond), no resume testing, no validation gate failure testing.
