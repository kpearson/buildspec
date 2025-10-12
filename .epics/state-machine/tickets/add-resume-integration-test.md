# Resume integration test for crash recovery

**Ticket ID:** add-resume-integration-test

**Critical:** false

**Dependencies:** add-happy-path-integration-test, implement-resume-from-state

**Coordination Role:** Validates resumability and state persistence

## Description

As a developer, I want an integration test for crash recovery (epic stops mid-execution and resumes from state file) so that I can verify resumability and state persistence work correctly.

This ticket creates tests/integration/epic/test_resume.py that tests state machine resumption (tickets: core-state-machine, implement-resume-from-state). The test simulates interruption by running state machine twice: first session executes one ticket then stops, second session resumes from state file and completes remaining tickets. Uses real git operations and state file. Key test scenario:
- test_resume_after_partial_execution(): Create 3-ticket epic (A → B → C), first session: execute state machine, let A complete, stop execution, verify state file saved with A=COMPLETED; second session: create new state machine with resume=True, call execute(), verify A skipped (already COMPLETED), verify B and C execute, verify final epic completion, verify state file updated

## Acceptance Criteria

- Test simulates interruption by running state machine in two separate sessions
- Test verifies state file persistence after first ticket
- Test verifies completed tickets skipped on resume (not re-executed)
- Test verifies remaining tickets execute normally
- Test verifies final epic completion after resume
- Test passes consistently

## Testing

This IS the integration test. Run it to verify resumability. Expected runtime: <5 seconds.

## Non-Goals

No state file corruption testing, no concurrent resume attempts, no state migration.
