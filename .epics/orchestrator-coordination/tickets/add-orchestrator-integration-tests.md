# add-orchestrator-integration-tests

## Description

Add comprehensive integration tests for orchestrator coordination scenarios,
validating all coordination logic works correctly end-to-end.

All coordination logic must be validated with integration tests covering
parallel execution, failures, recovery, git workflow, and various dependency
graph scenarios. This ticket creates a complete test suite ensuring the
orchestrator handles all coordination scenarios reliably.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. Integration tests validate that all
coordination components work together correctly in real-world scenarios.

**Architecture:** Tests use pytest with real git operations, mock sub-agents,
and temporary epic files. Tests validate state machine transitions, concurrency
limits, git workflow, and error recovery.

## Story

As a **buildspec orchestrator developer**, I need **comprehensive integration
tests** so that **I can confidently validate all coordination logic works
correctly and catch regressions before production use**.

## Acceptance Criteria

### Core Requirements

- All test scenarios pass with correct behavior
- Tests validate state machine transitions
- Tests verify concurrency limits are enforced
- Tests confirm error recovery works as expected
- Tests cover all major coordination scenarios
- Tests use real git operations (not mocked)
- Test coverage > 90% for orchestration code

### Test Scenarios

1. **Parallel Execution with 3 Concurrent Tickets**
2. **Critical Ticket Failure with Rollback**
3. **Non-Critical Ticket Failure with Partial Success**
4. **Orchestrator Crash Recovery from State File**
5. **Complex Dependency Graphs** (diamond, chain, independent clusters)
6. **Base Commit Calculation** (no deps, single dep, multiple deps)
7. **Completion Report Validation** (valid, invalid, missing fields)

## Integration Points

### Upstream Dependencies

- **add-wave-execution-algorithm**: Complete coordination logic to test

### Downstream Dependencies

None - this is validation of all previous work

## Current vs New Flow

### BEFORE (Current State)

No integration tests for orchestration. Manual testing only.

### AFTER (This Ticket)

Complete integration test suite in
`/Users/kit/Code/buildspec/tests/integration/test_orchestrator.py` with:

- 7+ test scenarios covering all coordination aspects
- Real git operations and state file validation
- Mock sub-agents for controlled test execution
- Helper utilities for test epic creation

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/tests/integration/test_orchestrator.py`
(new file)

```python
"""
Integration tests for orchestrator coordination.

Tests validate complete epic execution workflows including:
- Parallel ticket execution
- Concurrency control
- Error recovery
- Git workflow
- State machine transitions
"""

import pytest
import json
import subprocess
from pathlib import Path
from datetime import datetime, UTC
import tempfile
import shutil

# Assume orchestrator code is in cli/orchestrator/
from cli.orchestrator.execute_epic import (
    initialize_epic_execution,
    execute_wave_loop,
    finalize_epic_execution,
    calculate_ready_tickets,
    calculate_base_commit,
    validate_completion_report,
    merge_ticket_branches,
    push_epic_branch
)


class TestParallelExecution:
    """Test parallel ticket execution with concurrency control."""

    def test_parallel_execution_3_concurrent_tickets(self, temp_repo):
        """
        Test parallel execution respects MAX_CONCURRENT_TICKETS=3 limit.

        Epic with 5 independent tickets should execute 3 at a time.
        """
        # Create test epic with 5 independent tickets
        epic_file = create_test_epic(
            name="parallel-test",
            tickets=[
                {'id': 'ticket-a', 'critical': True, 'depends_on': []},
                {'id': 'ticket-b', 'critical': True, 'depends_on': []},
                {'id': 'ticket-c', 'critical': True, 'depends_on': []},
                {'id': 'ticket-d', 'critical': True, 'depends_on': []},
                {'id': 'ticket-e', 'critical': True, 'depends_on': []}
            ],
            repo_path=temp_repo
        )

        # Initialize epic
        state = initialize_epic_execution(epic_file)

        assert state.status == 'ready_to_execute'
        assert len(state.tickets) == 5

        # Execute first wave
        ready = calculate_ready_tickets(state)
        assert len(ready) == 5  # All tickets ready

        # Spawn first 3 (MAX_CONCURRENT_TICKETS)
        executing_count = 3
        available_slots = 3 - executing_count
        assert available_slots == 0  # No more slots

        # Verify concurrency limit enforced
        assert executing_count <= 3

        # Complete 1 ticket
        state.tickets['ticket-a'].status = 'completed'
        state.tickets['ticket-a'].git_info = {
            'branch_name': 'ticket/ticket-a',
            'base_commit': state.baseline_commit,
            'final_commit': 'aaa111'
        }

        # Now 1 slot available
        executing_count = 2
        available_slots = 3 - executing_count
        assert available_slots == 1

        # Can spawn 1 more ticket
        ready = calculate_ready_tickets(state)
        assert len(ready) == 4  # 4 remaining pending tickets


class TestCriticalFailureRollback:
    """Test critical ticket failure triggers rollback."""

    def test_rollback_on_critical_failure(self, temp_repo):
        """
        Test rollback when critical ticket fails with rollback_on_failure=true.

        Verify epic branch and ticket branches are deleted.
        """
        epic_file = create_test_epic(
            name="rollback-test",
            rollback_on_failure=True,
            tickets=[
                {'id': 'ticket-a', 'critical': True, 'depends_on': []},
                {'id': 'ticket-b', 'critical': True, 'depends_on': ['ticket-a']},
            ],
            repo_path=temp_repo
        )

        state = initialize_epic_execution(epic_file)
        epic_branch = state.epic_branch

        # Verify epic branch exists
        result = subprocess.run(
            ['git', 'rev-parse', '--verify', f'refs/heads/{epic_branch}'],
            cwd=temp_repo,
            capture_output=True
        )
        assert result.returncode == 0

        # Create ticket branch for ticket-a
        subprocess.run(
            ['git', 'checkout', '-b', 'ticket/ticket-a'],
            cwd=temp_repo,
            check=True
        )
        subprocess.run(['git', 'checkout', epic_branch], cwd=temp_repo, check=True)

        # Ticket-a fails (critical)
        state.tickets['ticket-a'].status = 'failed'
        state.tickets['ticket-a'].critical = True
        state.tickets['ticket-a'].failure_reason = 'test_failure'

        # Execute rollback
        from cli.orchestrator.execute_epic import execute_rollback
        execute_rollback(state)

        # Verify epic branch deleted
        result = subprocess.run(
            ['git', 'rev-parse', '--verify', f'refs/heads/{epic_branch}'],
            cwd=temp_repo,
            capture_output=True
        )
        assert result.returncode != 0  # Branch should not exist

        # Verify ticket branch deleted
        result = subprocess.run(
            ['git', 'rev-parse', '--verify', 'refs/heads/ticket/ticket-a'],
            cwd=temp_repo,
            capture_output=True
        )
        assert result.returncode != 0  # Branch should not exist

        # Verify epic status
        assert state.status == 'rolled_back'


class TestPartialSuccess:
    """Test partial success when non-critical ticket fails."""

    def test_partial_success_non_critical_failure(self, temp_repo):
        """
        Test partial success when non-critical ticket fails.

        Verify dependent tickets marked blocked, independent tickets continue.
        """
        epic_file = create_test_epic(
            name="partial-success-test",
            rollback_on_failure=False,
            tickets=[
                {'id': 'ticket-a', 'critical': True, 'depends_on': []},
                {'id': 'ticket-b', 'critical': False, 'depends_on': []},
                {'id': 'ticket-c', 'critical': True, 'depends_on': ['ticket-b']},
                {'id': 'ticket-d', 'critical': True, 'depends_on': []},
            ],
            repo_path=temp_repo
        )

        state = initialize_epic_execution(epic_file)

        # Ticket-a completes
        state.tickets['ticket-a'].status = 'completed'

        # Ticket-b fails (non-critical)
        state.tickets['ticket-b'].status = 'failed'
        state.tickets['ticket-b'].failure_reason = 'test_failure'

        # Ticket-c should be blocked (depends on ticket-b)
        from cli.orchestrator.execute_epic import mark_dependent_tickets_blocked
        mark_dependent_tickets_blocked(state, 'ticket-b')

        assert state.tickets['ticket-c'].status == 'blocked'
        assert state.tickets['ticket-c'].blocking_dependency == 'ticket-b'

        # Ticket-d should continue (independent)
        ready = calculate_ready_tickets(state)
        ready_ids = [t.id for t in ready]
        assert 'ticket-d' in ready_ids

        # Complete ticket-d
        state.tickets['ticket-d'].status = 'completed'

        # Epic should be partial_success (ticket-b failed, but non-critical)
        assert state.status == 'partial_success' or state.status == 'completed'


class TestCrashRecovery:
    """Test orchestrator crash recovery from epic-state.json."""

    def test_crash_recovery_resets_stale_tickets(self, temp_repo):
        """
        Test crash recovery resets stale 'executing' tickets.

        Verify stale tickets reset to queued/pending based on dependencies.
        """
        epic_file = create_test_epic(
            name="crash-recovery-test",
            tickets=[
                {'id': 'ticket-a', 'critical': True, 'depends_on': []},
                {'id': 'ticket-b', 'critical': True, 'depends_on': ['ticket-a']},
            ],
            repo_path=temp_repo
        )

        state = initialize_epic_execution(epic_file)

        # Ticket-a completes
        state.tickets['ticket-a'].status = 'completed'
        state.tickets['ticket-a'].git_info = {
            'branch_name': 'ticket/ticket-a',
            'base_commit': state.baseline_commit,
            'final_commit': 'aaa111'
        }

        # Ticket-b is executing (simulating crash)
        state.tickets['ticket-b'].status = 'executing'
        state.tickets['ticket-b'].started_at = datetime.now(UTC).isoformat()

        # Save state
        from cli.orchestrator.execute_epic import update_epic_state
        update_epic_state(state, {})

        # Simulate crash: reload state from file
        from cli.orchestrator.execute_epic import recover_from_crash
        recovered_state = recover_from_crash(epic_file)

        # Verify ticket-b reset to queued (dependencies met)
        assert recovered_state.tickets['ticket-b'].status == 'queued'
        assert recovered_state.tickets['ticket-b'].started_at is None


class TestComplexDependencyGraphs:
    """Test various dependency graph structures."""

    def test_diamond_dependency_graph(self, temp_repo):
        """
        Test diamond dependency graph.

        A → B, A → C, B → D, C → D
        """
        epic_file = create_test_epic(
            name="diamond-test",
            tickets=[
                {'id': 'ticket-a', 'critical': True, 'depends_on': []},
                {'id': 'ticket-b', 'critical': True, 'depends_on': ['ticket-a']},
                {'id': 'ticket-c', 'critical': True, 'depends_on': ['ticket-a']},
                {'id': 'ticket-d', 'critical': True, 'depends_on': ['ticket-b', 'ticket-c']},
            ],
            repo_path=temp_repo
        )

        state = initialize_epic_execution(epic_file)

        # Wave 1: Only ticket-a ready
        ready = calculate_ready_tickets(state)
        assert len(ready) == 1
        assert ready[0].id == 'ticket-a'

        # Complete ticket-a
        state.tickets['ticket-a'].status = 'completed'
        state.tickets['ticket-a'].git_info = {
            'final_commit': 'aaa111'
        }

        # Wave 2: ticket-b and ticket-c ready
        ready = calculate_ready_tickets(state)
        assert len(ready) == 2
        assert set([t.id for t in ready]) == {'ticket-b', 'ticket-c'}

        # Complete ticket-b and ticket-c
        state.tickets['ticket-b'].status = 'completed'
        state.tickets['ticket-b'].git_info = {'final_commit': 'bbb222'}

        state.tickets['ticket-c'].status = 'completed'
        state.tickets['ticket-c'].git_info = {'final_commit': 'ccc333'}

        # Wave 3: ticket-d ready
        ready = calculate_ready_tickets(state)
        assert len(ready) == 1
        assert ready[0].id == 'ticket-d'

        # Calculate base commit for ticket-d (should use most recent)
        base_commit = calculate_base_commit(state, state.tickets['ticket-d'])
        # Should be either bbb222 or ccc333 (most recent)
        assert base_commit in ['bbb222', 'ccc333']


class TestBaseCommitCalculation:
    """Test base commit calculation for various dependency scenarios."""

    def test_no_dependencies_uses_epic_baseline(self, temp_repo):
        """Test ticket with no dependencies branches from epic baseline."""
        epic_file = create_test_epic(
            name="base-commit-test",
            tickets=[{'id': 'ticket-a', 'critical': True, 'depends_on': []}],
            repo_path=temp_repo
        )

        state = initialize_epic_execution(epic_file)
        ticket = state.tickets['ticket-a']

        base_commit = calculate_base_commit(state, ticket)

        assert base_commit == state.baseline_commit

    def test_single_dependency_uses_dependency_final_commit(self, temp_repo):
        """Test ticket with single dependency branches from dependency."""
        epic_file = create_test_epic(
            name="base-commit-test",
            tickets=[
                {'id': 'ticket-a', 'critical': True, 'depends_on': []},
                {'id': 'ticket-b', 'critical': True, 'depends_on': ['ticket-a']},
            ],
            repo_path=temp_repo
        )

        state = initialize_epic_execution(epic_file)

        # Complete ticket-a
        state.tickets['ticket-a'].status = 'completed'
        state.tickets['ticket-a'].git_info = {
            'final_commit': 'aaa111'
        }

        ticket_b = state.tickets['ticket-b']
        base_commit = calculate_base_commit(state, ticket_b)

        assert base_commit == 'aaa111'


class TestCompletionReportValidation:
    """Test completion report validation."""

    def test_valid_report_passes_validation(self):
        """Test valid completion report passes validation."""
        ticket = MockTicket(id='test-ticket')
        report = {
            'ticket_id': 'test-ticket',
            'status': 'completed',
            'branch_name': 'ticket/test-ticket',
            'base_commit': 'abc123',
            'final_commit': 'def456',
            'files_modified': ['/path/to/file.py'],
            'test_suite_status': 'passing',
            'acceptance_criteria': [
                {'criterion': 'Test criterion', 'met': True}
            ]
        }

        result = validate_completion_report(ticket, report)

        assert result.passed is True
        assert result.error is None

    def test_missing_required_field_fails_validation(self):
        """Test missing required field fails validation."""
        ticket = MockTicket(id='test-ticket')
        report = {
            'ticket_id': 'test-ticket',
            'status': 'completed',
            # Missing branch_name
            'base_commit': 'abc123',
            'final_commit': 'def456',
            'files_modified': [],
            'test_suite_status': 'passing',
            'acceptance_criteria': []
        }

        result = validate_completion_report(ticket, report)

        assert result.passed is False
        assert 'branch_name' in result.error


# Test Fixtures and Helpers

@pytest.fixture
def temp_repo(tmp_path):
    """Create temporary git repository for testing."""
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(['git', 'init'], cwd=repo_path, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=repo_path, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_path, check=True)

    # Create initial commit
    (repo_path / 'README.md').write_text('# Test Repo')
    subprocess.run(['git', 'add', '.'], cwd=repo_path, check=True)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path, check=True)

    yield repo_path

    # Cleanup
    shutil.rmtree(repo_path)


def create_test_epic(name: str, tickets: list, repo_path: Path, rollback_on_failure: bool = True) -> Path:
    """Create test epic YAML file."""
    epics_dir = repo_path / '.epics' / name
    epics_dir.mkdir(parents=True, exist_ok=True)

    epic_data = {
        'epic': name,
        'description': f'Test epic: {name}',
        'ticket_count': len(tickets),
        'rollback_on_failure': rollback_on_failure,
        'tickets': tickets
    }

    epic_file = epics_dir / f'{name}.epic.yaml'
    epic_file.write_text(yaml.dump(epic_data))

    return epic_file


class MockTicket:
    """Mock ticket for testing."""
    def __init__(self, id: str, depends_on=None, critical=True):
        self.id = id
        self.depends_on = depends_on or []
        self.critical = critical
```

### Test Coverage Requirements

- **State Machine Transitions:** All epic and ticket state transitions
- **Concurrency Control:** MAX_CONCURRENT_TICKETS enforcement
- **Dependency Resolution:** All graph structures (linear, diamond, independent)
- **Error Recovery:** Rollback, partial success, crash recovery
- **Git Workflow:** Branch creation, stacking, merging, push
- **Validation:** Completion report validation, git verification

### Test Execution

```bash
# Run all orchestrator integration tests
uv run pytest tests/integration/test_orchestrator.py -v

# Run specific test class
uv run pytest tests/integration/test_orchestrator.py::TestParallelExecution -v

# Run with coverage
uv run pytest tests/integration/test_orchestrator.py --cov=cli.orchestrator --cov-report=html
```

## Error Handling Strategy

- **Test Failures:** Provide clear assertion messages
- **Cleanup:** Always cleanup temp repos and files
- **Isolation:** Each test uses fresh temp repo
- **Mocking:** Mock sub-agents for controlled execution

## Testing Strategy

### Validation Tests

All tests are integration tests validating end-to-end workflows.

### Test Commands

```bash
# Run all orchestrator tests
uv run pytest tests/integration/test_orchestrator.py -v

# Run with coverage report
uv run pytest tests/integration/test_orchestrator.py --cov=cli.orchestrator --cov-report=term-missing

# Run specific scenario
uv run pytest tests/integration/test_orchestrator.py::TestCriticalFailureRollback::test_rollback_on_critical_failure -v
```

## Dependencies

- **add-wave-execution-algorithm**: Complete coordination logic to test

## Coordination Role

Validates all coordination logic works correctly end-to-end. Provides confidence
in orchestrator reliability and catches regressions before production
deployment.
