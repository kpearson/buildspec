# Comprehensive Testing Specification

## Overview

Establish >90% test coverage for the buildspec codebase with fast, reliable unit and integration tests. All Claude CLI interactions must be mocked with responses captured from real LLM runs to ensure mock accuracy.

## Problem Statement

The codebase currently has virtually no tests - the `tests/` directory is just lip service. This is unacceptable for a tool that orchestrates complex multi-agent workflows. We need:

- **Unit tests** for all modules, functions, and classes
- **Integration tests** for component collaboration
- **No async/await/sleep antipatterns** - tests must be fast and deterministic
- **Real LLM response mocks** - capture actual Claude responses, use as test fixtures

## Goals

1. Achieve >90% code coverage (unit + integration)
2. All tests run in <30 seconds total
3. Zero sleeps, zero waiting - fully synchronous or properly mocked
4. Mock Claude CLI responses using real LLM output as fixtures
5. Test all critical paths and edge cases
6. Integration tests for all component collaborations
7. Fast, reliable CI/CD pipeline

## Non-Goals

- End-to-end tests with real Claude (too slow, non-deterministic)
- Manual testing (must be automated)
- Coverage theater (high coverage of trivial code)

## Testing Strategy

### Coverage Target Breakdown

**Unit Tests (>85% coverage):**
- `cli/commands/` - All command modules
- `cli/core/` - Context, config, validation, prompts, claude runner
- `cli/utils/` - Path resolver, epic validator, commit parser
- Edge cases, error handling, validation logic

**Integration Tests (>90% coverage of interactions):**
- Command → Claude runner → subprocess
- Path resolution → context → file operations  
- Epic creation → validation → splitting
- Ticket execution → git operations → commit parsing

### Test Framework Stack

**Testing tools:**
- `pytest` - Test runner and fixtures
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking and spying
- `responses` or `requests-mock` - HTTP mocking (if needed)
- `freezegun` - Time mocking for timestamps
- `pyfakefs` - Filesystem mocking

**No sleeps, no async antipatterns:**
- All subprocess calls mocked
- All file I/O uses pyfakefs or tmpdir
- All time-based logic uses freezegun
- Zero `time.sleep()` in tests
- No real Claude CLI invocations

### LLM Response Fixture Strategy

**Capture real responses:**
1. Run actual Claude commands with various inputs
2. Capture stdout/stderr/exit codes
3. Store as JSON fixtures in `tests/fixtures/claude_responses/`
4. Use fixtures to mock subprocess responses

**Fixture structure:**
```json
{
  "command": ["claude", "-p", "prompt...", "--session-id", "abc123"],
  "input": "prompt text here",
  "stdout": "actual Claude JSON response",
  "stderr": "",
  "returncode": 0,
  "session_id": "abc123"
}
```

**Mock subprocess with fixtures:**
```python
def test_create_epic_success(mocker, claude_fixture):
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = Mock(
        returncode=claude_fixture['returncode'],
        stdout=claude_fixture['stdout'],
        stderr=claude_fixture['stderr']
    )
    # Test logic here
```

## Test Organization

### Directory Structure

```
tests/
├── unit/
│   ├── commands/
│   │   ├── test_create_epic.py
│   │   ├── test_create_tickets.py
│   │   ├── test_execute_epic.py
│   │   └── test_execute_ticket.py
│   ├── core/
│   │   ├── test_claude.py
│   │   ├── test_config.py
│   │   ├── test_context.py
│   │   ├── test_prompts.py
│   │   └── test_validation.py
│   └── utils/
│       ├── test_path_resolver.py
│       ├── test_epic_validator.py
│       └── test_commit_parser.py
├── integration/
│   ├── test_create_epic_workflow.py
│   ├── test_execute_epic_workflow.py
│   ├── test_epic_splitting_workflow.py
│   └── test_path_resolution_workflow.py
├── fixtures/
│   ├── claude_responses/
│   │   ├── create_epic_success.json
│   │   ├── create_epic_failure.json
│   │   ├── execute_ticket_success.json
│   │   └── ...
│   ├── sample_specs/
│   │   ├── simple_spec.md
│   │   └── complex_spec.md
│   └── sample_epics/
│       ├── simple.epic.yaml
│       └── complex.epic.yaml
├── conftest.py              # Shared fixtures
└── pytest.ini               # Pytest configuration
```

### Key Test Files

**tests/conftest.py** - Shared fixtures:
```python
import pytest
import json
from pathlib import Path

@pytest.fixture
def mock_project_context(tmp_path):
    """Mock ProjectContext with temp directories"""
    
@pytest.fixture  
def claude_response_fixture():
    """Load Claude response fixtures"""
    
@pytest.fixture
def mock_subprocess(mocker, claude_response_fixture):
    """Mock subprocess.run with Claude fixtures"""
```

## Critical Test Cases

### Unit Tests

**cli/commands/create_epic.py:**
- ✅ Successfully creates epic from spec
- ✅ Handles missing spec file
- ✅ Validates epic filename (.epic.yaml)
- ✅ Renames incorrectly named epics
- ✅ Invokes split workflow when ticket_count >= 13
- ✅ Displays session ID on success
- ✅ Handles subprocess failures

**cli/core/claude.py:**
- ✅ Generates session_id if not provided
- ✅ Pipes prompt via stdin correctly
- ✅ Returns exit_code and session_id tuple
- ✅ Handles Claude CLI not found
- ✅ Passes console for spinner display
- ✅ Redirects stdout/stderr properly

**cli/core/prompts.py:**
- ✅ Builds create-epic prompt correctly
- ✅ Builds create-tickets prompt correctly
- ✅ Builds execute-epic prompt with session_id
- ✅ Builds execute-ticket prompt with context
- ✅ Reads command files from context.claude_dir
- ✅ Includes naming requirements in prompts

**cli/utils/path_resolver.py:**
- ✅ Strips line number notation (file.md:123)
- ✅ Returns file if it exists
- ✅ Infers file from directory with pattern
- ✅ Raises error if multiple matches
- ✅ Raises error if no matches
- ✅ Handles directory without pattern

**cli/utils/epic_validator.py:**
- ✅ Parses YAML and extracts ticket_count
- ✅ Validates ticket count limits
- ✅ Detects circular dependencies
- ✅ Validates epic structure

**cli/utils/commit_parser.py:**
- ✅ Extracts session_id from commit messages
- ✅ Handles commits without session_id
- ✅ Parses git log output correctly

### Integration Tests

**test_create_epic_workflow.py:**
- ✅ End-to-end epic creation from spec
- ✅ Context resolution → prompt building → subprocess → validation
- ✅ Epic splitting workflow when oversized
- ✅ File operations and path handling

**test_execute_epic_workflow.py:**
- ✅ Epic parsing → ticket orchestration → Task spawning
- ✅ Dependency management and ordering
- ✅ Session ID propagation through workflow
- ✅ Epic state tracking

**test_epic_splitting_workflow.py:**
- ✅ Detection of oversized epic
- ✅ Specialist agent invocation
- ✅ Subdirectory creation
- ✅ Original epic archival

**test_path_resolution_workflow.py:**
- ✅ Directory inference → file resolution → context resolution
- ✅ Line number stripping → validation
- ✅ Error handling across components

## Mock Strategy

### Subprocess Mocking

**Always mock subprocess.run:**
```python
def test_claude_execution(mocker):
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = Mock(
        returncode=0,
        stdout='{"session_id": "test123"}',
        stderr=''
    )
    
    runner = ClaudeRunner(context)
    exit_code, session_id = runner.execute("test prompt")
    
    assert exit_code == 0
    assert session_id == "test123"
    mock_run.assert_called_once()
```

### Filesystem Mocking

**Use pyfakefs or tmp_path:**
```python
def test_file_operations(tmp_path):
    spec_file = tmp_path / "spec.md"
    spec_file.write_text("content")
    
    # Test code uses tmp_path
    result = resolve_file_argument(str(spec_file))
    assert result == spec_file
```

### Time Mocking

**Use freezegun for deterministic timestamps:**
```python
@freeze_time("2025-01-01 12:00:00")
def test_timestamped_operation():
    # Time is frozen, tests are deterministic
    assert get_timestamp() == "2025-01-01T12:00:00"
```

## LLM Response Fixture Creation

### Capture Process

**Script to capture real Claude responses:**
```python
# tests/fixtures/capture_claude_responses.py
import subprocess
import json
from pathlib import Path

def capture_response(prompt, name):
    result = subprocess.run(
        ["claude", "--session-id", f"fixture-{name}"],
        input=prompt,
        capture_output=True,
        text=True
    )
    
    fixture = {
        "name": name,
        "prompt": prompt,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "session_id": f"fixture-{name}"
    }
    
    fixture_path = Path(f"tests/fixtures/claude_responses/{name}.json")
    fixture_path.write_text(json.dumps(fixture, indent=2))

# Capture various scenarios
capture_response("Create epic from spec...", "create_epic_success")
capture_response("Invalid prompt...", "create_epic_failure")
```

### Using Fixtures in Tests

```python
@pytest.fixture
def load_fixture(request):
    def _load(name):
        path = Path(f"tests/fixtures/claude_responses/{name}.json")
        return json.loads(path.read_text())
    return _load

def test_with_fixture(load_fixture, mocker):
    fixture = load_fixture("create_epic_success")
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = Mock(
        returncode=fixture['returncode'],
        stdout=fixture['stdout']
    )
    # Test uses real Claude response
```

## CI/CD Integration

### pytest.ini Configuration

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --cov=cli
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=90
    -v
    --tb=short
    --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests (if needed)
```

### Coverage Configuration

**.coveragerc:**
```ini
[run]
source = cli
omit = 
    */tests/*
    */__pycache__/*
    */site-packages/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
```

### Makefile Targets

```makefile
test:
	pytest

test-unit:
	pytest tests/unit -m unit

test-integration:
	pytest tests/integration -m integration

test-cov:
	pytest --cov=cli --cov-report=html --cov-report=term

test-watch:
	pytest-watch
```

## Success Criteria

1. ✅ >90% code coverage (verified by pytest-cov)
2. ✅ All tests run in <30 seconds
3. ✅ Zero sleeps, zero async antipatterns
4. ✅ All subprocess calls mocked with real LLM fixtures
5. ✅ All file I/O mocked or uses temp directories
6. ✅ All critical paths tested (happy + error cases)
7. ✅ Integration tests cover all component collaborations
8. ✅ CI/CD pipeline fails if coverage drops below 90%
9. ✅ Tests are deterministic (no flakes)

## Testing Edge Cases

**Path Resolution:**
- File with line notation: `file.md:123`
- Directory with single matching file
- Directory with multiple matching files
- Directory with no matching files
- Non-existent paths

**Epic Validation:**
- Missing ticket_count field
- Circular dependencies
- Invalid YAML structure
- Oversized epic (>12 tickets)
- Dependency chains

**Subprocess Errors:**
- Claude CLI not found
- Non-zero exit codes
- Empty stdout/stderr
- Malformed JSON output

**File Operations:**
- Permission errors
- Missing directories
- File already exists
- Invalid file names

## Implementation Plan

### Phase 1: Infrastructure (Test Framework Setup)
1. Add pytest and dependencies to pyproject.toml
2. Create conftest.py with shared fixtures
3. Create pytest.ini and .coveragerc
4. Set up fixture capture script

### Phase 2: Unit Tests (Core Components)
1. cli/core/claude.py - ClaudeRunner tests
2. cli/core/prompts.py - PromptBuilder tests
3. cli/core/context.py - ProjectContext tests
4. cli/utils/path_resolver.py - Path resolution tests
5. cli/utils/epic_validator.py - Validation tests

### Phase 3: Unit Tests (Commands)
1. cli/commands/create_epic.py
2. cli/commands/create_tickets.py
3. cli/commands/execute_epic.py
4. cli/commands/execute_ticket.py

### Phase 4: Integration Tests
1. Create epic workflow (end-to-end)
2. Execute epic workflow
3. Epic splitting workflow
4. Path resolution workflow

### Phase 5: Coverage & CI
1. Achieve >90% coverage
2. Set up CI/CD pipeline
3. Add coverage badges
4. Documentation

## Related Work

- Epic splitting implementation (depends on epic_validator tests)
- Code review agent (depends on robust testing foundation)
- Performance optimization (needs benchmarks/profiling tests)
