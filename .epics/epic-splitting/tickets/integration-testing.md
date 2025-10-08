# integration-testing

## Description

Create integration tests for epic splitting workflow to validate the entire
split process works correctly.

This test suite validates all coordination contracts work together correctly
across the scenarios defined in the specification, ensuring epic splitting
preserves quality and independence.

## Acceptance Criteria

- Test epic with 12 tickets: should NOT split
- Test epic with 13 independent tickets: should split into 2 independent epics
- Test epic with 25 independent tickets: should split into 2-3 independent epics
- Test epic with 20 tickets in dependency chain: should NOT split (warn user)
- Test epic with 40 tickets: should split into 3+ independent epics
- Verify each split epic is fully independent (no cross-epic dependencies)
- Verify dependencies preserved within each epic
- Verify ticket quality maintained after split
- Verify original epic is archived correctly
- Verify --no-split flag bypasses workflow
- All tests use pytest framework
- Tests create temporary epic files in test fixtures
- Clean up all test artifacts after completion

## Files to Modify

- /Users/kit/Code/buildspec/tests/integration/test_epic_splitting.py (NEW FILE)

## Dependencies

- create-epic-split-workflow
- subdirectory-creation-logic
- archive-original-epic
- split-result-display
- split-edge-case-handling

## Implementation Notes

### Test Structure

```python
# tests/integration/test_epic_splitting.py

import pytest
from pathlib import Path
from cli.commands.create_epic import handle_split_workflow
from cli.utils.epic_validator import parse_epic_yaml, validate_ticket_count

@pytest.fixture
def temp_epics_dir(tmp_path):
    """Create temporary .epics directory for testing."""
    epics_dir = tmp_path / ".epics"
    epics_dir.mkdir()
    return epics_dir

@pytest.fixture
def sample_epic_12_tickets(temp_epics_dir):
    """Create sample epic with exactly 12 tickets."""
    # Create YAML file with 12 independent tickets
    # Return path to epic file
    pass

class TestEpicSplitting:

    def test_no_split_for_12_tickets(self, sample_epic_12_tickets):
        """Epic with 12 tickets should NOT trigger split."""
        epic_data = parse_epic_yaml(sample_epic_12_tickets)
        assert not validate_ticket_count(epic_data['ticket_count'])
        # Verify no split occurred

    def test_split_13_independent_tickets(self, temp_epics_dir):
        """Epic with 13 independent tickets should split into 2 epics."""
        # Create epic with 13 independent tickets
        epic_path = create_test_epic(temp_epics_dir, ticket_count=13, dependencies=False)

        # Trigger split
        handle_split_workflow(epic_path, spec_path, 13)

        # Verify split results
        split_epics = list((temp_epics_dir / "test-epic").glob("*/test-epic.epic.yaml"))
        assert len(split_epics) == 2
        assert all(count_tickets(e) <= 12 for e in split_epics)

    def test_split_25_independent_tickets(self, temp_epics_dir):
        """Epic with 25 independent tickets should split into 2-3 epics."""
        epic_path = create_test_epic(temp_epics_dir, ticket_count=25, dependencies=False)

        handle_split_workflow(epic_path, spec_path, 25)

        split_epics = list((temp_epics_dir / "test-epic").glob("*/test-epic.epic.yaml"))
        assert 2 <= len(split_epics) <= 3
        assert all(count_tickets(e) <= 15 for e in split_epics)

    def test_dependency_chain_not_split(self, temp_epics_dir):
        """Epic with long dependency chain should NOT split."""
        # Create epic with 20 tickets in single dependency chain
        epic_path = create_test_epic(temp_epics_dir, ticket_count=20, dependency_chain=True)

        # Should detect chain and refuse to split
        with pytest.raises(Exception, match="dependency chain"):
            handle_split_workflow(epic_path, spec_path, 20)

    def test_40_tickets_split_into_multiple(self, temp_epics_dir):
        """Epic with 40 tickets should split into 3+ epics."""
        epic_path = create_test_epic(temp_epics_dir, ticket_count=40, dependencies=False)

        handle_split_workflow(epic_path, spec_path, 40)

        split_epics = list((temp_epics_dir / "test-epic").glob("*/test-epic.epic.yaml"))
        assert len(split_epics) >= 3
        assert all(count_tickets(e) <= 15 for e in split_epics)

    def test_split_independence(self, temp_epics_dir):
        """Verify split epics have no cross-epic dependencies."""
        epic_path = create_test_epic(temp_epics_dir, ticket_count=20, dependencies=True)

        handle_split_workflow(epic_path, spec_path, 20)

        split_epics = list((temp_epics_dir / "test-epic").glob("*/test-epic.epic.yaml"))

        # Verify no cross-epic dependencies
        for epic in split_epics:
            assert_no_cross_epic_dependencies(epic, split_epics)

    def test_dependencies_preserved_within_epic(self, temp_epics_dir):
        """Verify dependencies are preserved within each split epic."""
        epic_path = create_test_epic(temp_epics_dir, ticket_count=15, dependencies=True)

        handle_split_workflow(epic_path, spec_path, 15)

        split_epics = list((temp_epics_dir / "test-epic").glob("*/test-epic.epic.yaml"))

        # Verify all dependencies still exist within their epic
        for epic in split_epics:
            assert_dependencies_preserved(epic)

    def test_original_epic_archived(self, temp_epics_dir):
        """Verify original epic is archived with .original suffix."""
        epic_path = create_test_epic(temp_epics_dir, ticket_count=13, dependencies=False)
        original_content = Path(epic_path).read_text()

        handle_split_workflow(epic_path, spec_path, 13)

        # Verify original archived
        archived_path = Path(str(epic_path) + ".original")
        assert archived_path.exists()
        assert archived_path.read_text() == original_content

    def test_no_split_flag(self, temp_epics_dir):
        """Verify --no-split flag bypasses workflow."""
        epic_path = create_test_epic(temp_epics_dir, ticket_count=20, dependencies=False)

        # Call with no_split=True
        # Should skip split workflow
        # Verify no split occurred
        pass

    def test_ticket_quality_maintained(self, temp_epics_dir):
        """Verify split tickets maintain same quality as original."""
        epic_path = create_test_epic(temp_epics_dir, ticket_count=15, dependencies=False)
        original_data = parse_epic_yaml(epic_path)

        handle_split_workflow(epic_path, spec_path, 15)

        split_epics = list((temp_epics_dir / "test-epic").glob("*/test-epic.epic.yaml"))

        # Verify all original tickets exist in split epics
        all_split_tickets = []
        for epic in split_epics:
            epic_data = parse_epic_yaml(epic)
            all_split_tickets.extend(epic_data['tickets'])

        assert len(all_split_tickets) == len(original_data['tickets'])
        # Verify ticket content matches original
```

### Test Utilities

```python
def create_test_epic(base_dir: Path, ticket_count: int, dependencies: bool = False, dependency_chain: bool = False) -> str:
    """Create test epic YAML file with specified characteristics."""
    pass

def count_tickets(epic_path: Path) -> int:
    """Count tickets in an epic file."""
    pass

def assert_no_cross_epic_dependencies(epic_path: Path, all_epics: list[Path]) -> None:
    """Assert epic has no dependencies on tickets in other epics."""
    pass

def assert_dependencies_preserved(epic_path: Path) -> None:
    """Assert all ticket dependencies exist within the epic."""
    pass
```

### Running Tests

```bash
# Run all integration tests
uv run pytest tests/integration/test_epic_splitting.py -v

# Run specific test
uv run pytest tests/integration/test_epic_splitting.py::TestEpicSplitting::test_split_13_independent_tickets -v

# Run with coverage
uv run pytest tests/integration/test_epic_splitting.py --cov=cli.commands.create_epic --cov-report=term-missing
```

### Coordination Role

Validates end-to-end coordination and integration contracts, ensuring all
components work together correctly to produce valid, independent split epics.
