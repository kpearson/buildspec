"""Unit tests for CreateBranchGate."""

from unittest.mock import MagicMock, Mock

import pytest

from cli.epic.gates import CreateBranchGate, EpicContext
from cli.epic.git_operations import GitError, GitOperations
from cli.epic.models import GateResult, GitInfo, Ticket


class TestCalculateBaseCommit:
    """Test _calculate_base_commit method with various dependency graphs."""

    def test_no_dependencies_returns_baseline(self):
        """Test that ticket with no dependencies branches from epic baseline."""
        gate = CreateBranchGate()
        ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="First Ticket",
            depends_on=[],
        )
        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"ticket-1": ticket},
            git=GitOperations(),
            epic_config={},
        )

        result = gate._calculate_base_commit(ticket, context)

        assert result == "baseline123"

    def test_single_dependency_returns_dep_final_commit(self):
        """Test that ticket with single dependency branches from dependency's final commit."""
        gate = CreateBranchGate()

        # Create dependency ticket with final commit
        dep_ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Dependency",
            git_info=GitInfo(
                branch_name="ticket/ticket-1",
                base_commit="baseline123",
                final_commit="dep_final_abc",
            ),
        )

        # Create ticket that depends on first ticket
        ticket = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Second Ticket",
            depends_on=["ticket-1"],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"ticket-1": dep_ticket, "ticket-2": ticket},
            git=GitOperations(),
            epic_config={},
        )

        result = gate._calculate_base_commit(ticket, context)

        assert result == "dep_final_abc"

    def test_single_dependency_missing_final_commit_raises_error(self):
        """Test that missing final_commit raises ValueError."""
        gate = CreateBranchGate()

        # Create dependency ticket WITHOUT final commit
        dep_ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Dependency",
            git_info=GitInfo(
                branch_name="ticket/ticket-1",
                base_commit="baseline123",
                final_commit=None,  # Missing!
            ),
        )

        ticket = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Second Ticket",
            depends_on=["ticket-1"],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"ticket-1": dep_ticket, "ticket-2": ticket},
            git=GitOperations(),
            epic_config={},
        )

        with pytest.raises(ValueError) as exc_info:
            gate._calculate_base_commit(ticket, context)

        assert "ticket-1" in str(exc_info.value)
        assert "missing final_commit" in str(exc_info.value)

    def test_single_dependency_missing_git_info_raises_error(self):
        """Test that missing git_info raises ValueError."""
        gate = CreateBranchGate()

        # Create dependency ticket WITHOUT git_info
        dep_ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Dependency",
            git_info=None,  # Missing!
        )

        ticket = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Second Ticket",
            depends_on=["ticket-1"],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"ticket-1": dep_ticket, "ticket-2": ticket},
            git=GitOperations(),
            epic_config={},
        )

        with pytest.raises(ValueError) as exc_info:
            gate._calculate_base_commit(ticket, context)

        assert "ticket-1" in str(exc_info.value)
        assert "missing final_commit" in str(exc_info.value)

    def test_multiple_dependencies_finds_most_recent(self):
        """Test that ticket with multiple dependencies branches from most recent final commit."""
        gate = CreateBranchGate()

        # Create two dependency tickets with different final commits
        dep_ticket1 = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Dependency 1",
            git_info=GitInfo(
                branch_name="ticket/ticket-1",
                base_commit="baseline123",
                final_commit="commit_abc",
            ),
        )

        dep_ticket2 = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Dependency 2",
            git_info=GitInfo(
                branch_name="ticket/ticket-2",
                base_commit="baseline123",
                final_commit="commit_def",
            ),
        )

        # Create ticket that depends on both
        ticket = Ticket(
            id="ticket-3",
            path="/path/3",
            title="Diamond Ticket",
            depends_on=["ticket-1", "ticket-2"],
        )

        # Mock git operations to return commit_def as most recent
        mock_git = Mock(spec=GitOperations)
        mock_git.find_most_recent_commit.return_value = "commit_def"

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={
                "ticket-1": dep_ticket1,
                "ticket-2": dep_ticket2,
                "ticket-3": ticket,
            },
            git=mock_git,
            epic_config={},
        )

        result = gate._calculate_base_commit(ticket, context)

        # Verify it called find_most_recent_commit with both commits
        mock_git.find_most_recent_commit.assert_called_once_with(
            ["commit_abc", "commit_def"]
        )
        assert result == "commit_def"

    def test_multiple_dependencies_one_missing_final_commit_raises_error(self):
        """Test that if any dependency is missing final_commit, raises ValueError."""
        gate = CreateBranchGate()

        # Create one complete and one incomplete dependency
        dep_ticket1 = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Dependency 1",
            git_info=GitInfo(
                branch_name="ticket/ticket-1",
                base_commit="baseline123",
                final_commit="commit_abc",
            ),
        )

        dep_ticket2 = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Dependency 2",
            git_info=GitInfo(
                branch_name="ticket/ticket-2",
                base_commit="baseline123",
                final_commit=None,  # Missing!
            ),
        )

        ticket = Ticket(
            id="ticket-3",
            path="/path/3",
            title="Diamond Ticket",
            depends_on=["ticket-1", "ticket-2"],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={
                "ticket-1": dep_ticket1,
                "ticket-2": dep_ticket2,
                "ticket-3": ticket,
            },
            git=GitOperations(),
            epic_config={},
        )

        with pytest.raises(ValueError) as exc_info:
            gate._calculate_base_commit(ticket, context)

        assert "ticket-2" in str(exc_info.value)
        assert "missing final_commit" in str(exc_info.value)

    def test_diamond_dependency_pattern(self):
        """Test diamond dependency: A -> B, A -> C, B+C -> D.

        This tests the scenario where:
        - Ticket A has no dependencies (branches from baseline)
        - Tickets B and C both depend on A (branch from A's final)
        - Ticket D depends on both B and C (branch from most recent of B or C)
        """
        gate = CreateBranchGate()

        # A: no dependencies
        ticket_a = Ticket(
            id="ticket-a",
            path="/path/a",
            title="Ticket A",
            depends_on=[],
            git_info=GitInfo(
                branch_name="ticket/ticket-a",
                base_commit="baseline123",
                final_commit="commit_a",
            ),
        )

        # B: depends on A
        ticket_b = Ticket(
            id="ticket-b",
            path="/path/b",
            title="Ticket B",
            depends_on=["ticket-a"],
            git_info=GitInfo(
                branch_name="ticket/ticket-b",
                base_commit="commit_a",
                final_commit="commit_b",
            ),
        )

        # C: depends on A
        ticket_c = Ticket(
            id="ticket-c",
            path="/path/c",
            title="Ticket C",
            depends_on=["ticket-a"],
            git_info=GitInfo(
                branch_name="ticket/ticket-c",
                base_commit="commit_a",
                final_commit="commit_c",
            ),
        )

        # D: depends on B and C
        ticket_d = Ticket(
            id="ticket-d",
            path="/path/d",
            title="Ticket D",
            depends_on=["ticket-b", "ticket-c"],
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.find_most_recent_commit.return_value = "commit_c"

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={
                "ticket-a": ticket_a,
                "ticket-b": ticket_b,
                "ticket-c": ticket_c,
                "ticket-d": ticket_d,
            },
            git=mock_git,
            epic_config={},
        )

        # Test A branches from baseline
        result_a = gate._calculate_base_commit(ticket_a, context)
        assert result_a == "baseline123"

        # Test B branches from A's final
        result_b = gate._calculate_base_commit(ticket_b, context)
        assert result_b == "commit_a"

        # Test C branches from A's final
        result_c = gate._calculate_base_commit(ticket_c, context)
        assert result_c == "commit_a"

        # Test D branches from most recent of B and C
        result_d = gate._calculate_base_commit(ticket_d, context)
        mock_git.find_most_recent_commit.assert_called_once_with(
            ["commit_b", "commit_c"]
        )
        assert result_d == "commit_c"

    def test_linear_chain_dependency(self):
        """Test linear chain: A -> B -> C -> D."""
        gate = CreateBranchGate()

        tickets = {}
        commits = ["baseline123"]

        # Create chain of 4 tickets
        for i in range(4):
            ticket_id = f"ticket-{i}"
            prev_commit = commits[-1]
            current_commit = f"commit_{i}"

            ticket = Ticket(
                id=ticket_id,
                path=f"/path/{i}",
                title=f"Ticket {i}",
                depends_on=[f"ticket-{i-1}"] if i > 0 else [],
                git_info=GitInfo(
                    branch_name=f"ticket/{ticket_id}",
                    base_commit=prev_commit,
                    final_commit=current_commit,
                ),
            )

            tickets[ticket_id] = ticket
            commits.append(current_commit)

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets=tickets,
            git=GitOperations(),
            epic_config={},
        )

        # Test each ticket branches from previous final commit
        for i in range(4):
            ticket = tickets[f"ticket-{i}"]
            result = gate._calculate_base_commit(ticket, context)
            expected = commits[i]  # Previous commit in chain
            assert result == expected


class TestCreateBranchGateCheck:
    """Test check() method with mocked git operations."""

    def test_successful_branch_creation_no_dependencies(self):
        """Test successful branch creation for ticket with no dependencies."""
        gate = CreateBranchGate()

        ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="First Ticket",
            depends_on=[],
        )

        # Mock git operations
        mock_git = Mock(spec=GitOperations)
        mock_git.create_branch = Mock()
        mock_git.push_branch = Mock()

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"ticket-1": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        # Verify success
        assert result.passed is True
        assert result.reason == "Branch created successfully"
        assert result.metadata["branch_name"] == "ticket/ticket-1"
        assert result.metadata["base_commit"] == "baseline123"

        # Verify git operations called correctly
        mock_git.create_branch.assert_called_once_with("ticket/ticket-1", "baseline123")
        mock_git.push_branch.assert_called_once_with("ticket/ticket-1")

    def test_successful_branch_creation_with_single_dependency(self):
        """Test successful branch creation for ticket with single dependency."""
        gate = CreateBranchGate()

        dep_ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Dependency",
            git_info=GitInfo(
                branch_name="ticket/ticket-1",
                base_commit="baseline123",
                final_commit="commit_abc",
            ),
        )

        ticket = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Second Ticket",
            depends_on=["ticket-1"],
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.create_branch = Mock()
        mock_git.push_branch = Mock()

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"ticket-1": dep_ticket, "ticket-2": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        # Verify success with dependency's final commit
        assert result.passed is True
        assert result.metadata["branch_name"] == "ticket/ticket-2"
        assert result.metadata["base_commit"] == "commit_abc"

        mock_git.create_branch.assert_called_once_with("ticket/ticket-2", "commit_abc")
        mock_git.push_branch.assert_called_once_with("ticket/ticket-2")

    def test_successful_branch_creation_with_multiple_dependencies(self):
        """Test successful branch creation for ticket with multiple dependencies."""
        gate = CreateBranchGate()

        dep_ticket1 = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Dependency 1",
            git_info=GitInfo(
                branch_name="ticket/ticket-1",
                base_commit="baseline123",
                final_commit="commit_abc",
            ),
        )

        dep_ticket2 = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Dependency 2",
            git_info=GitInfo(
                branch_name="ticket/ticket-2",
                base_commit="baseline123",
                final_commit="commit_def",
            ),
        )

        ticket = Ticket(
            id="ticket-3",
            path="/path/3",
            title="Diamond Ticket",
            depends_on=["ticket-1", "ticket-2"],
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.create_branch = Mock()
        mock_git.push_branch = Mock()
        mock_git.find_most_recent_commit.return_value = "commit_def"

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={
                "ticket-1": dep_ticket1,
                "ticket-2": dep_ticket2,
                "ticket-3": ticket,
            },
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        # Verify success with most recent commit
        assert result.passed is True
        assert result.metadata["branch_name"] == "ticket/ticket-3"
        assert result.metadata["base_commit"] == "commit_def"

        mock_git.find_most_recent_commit.assert_called_once_with(
            ["commit_abc", "commit_def"]
        )
        mock_git.create_branch.assert_called_once_with("ticket/ticket-3", "commit_def")
        mock_git.push_branch.assert_called_once_with("ticket/ticket-3")

    def test_git_error_during_create_branch(self):
        """Test that GitError during create_branch is caught and returned as failure."""
        gate = CreateBranchGate()

        ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="First Ticket",
            depends_on=[],
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.create_branch.side_effect = GitError("Branch already exists")

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"ticket-1": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        # Verify failure
        assert result.passed is False
        assert "Failed to create branch" in result.reason
        assert "Branch already exists" in result.reason

    def test_git_error_during_push_branch(self):
        """Test that GitError during push_branch is caught and returned as failure."""
        gate = CreateBranchGate()

        ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="First Ticket",
            depends_on=[],
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.create_branch = Mock()  # Succeeds
        mock_git.push_branch.side_effect = GitError("Failed to push to remote")

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"ticket-1": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        # Verify failure
        assert result.passed is False
        assert "Failed to create branch" in result.reason
        assert "Failed to push to remote" in result.reason

    def test_branch_naming_format(self):
        """Test that branches are created with correct naming format."""
        gate = CreateBranchGate()

        # Test with various ticket IDs
        ticket_ids = [
            "simple-ticket",
            "ticket-with-dashes",
            "ticket_with_underscores",
            "ticket123",
        ]

        for ticket_id in ticket_ids:
            ticket = Ticket(
                id=ticket_id,
                path=f"/path/{ticket_id}",
                title=f"Ticket {ticket_id}",
                depends_on=[],
            )

            mock_git = Mock(spec=GitOperations)
            mock_git.create_branch = Mock()
            mock_git.push_branch = Mock()

            context = EpicContext(
                epic_id="test-epic",
                epic_branch="epic/test",
                baseline_commit="baseline123",
                tickets={ticket_id: ticket},
                git=mock_git,
                epic_config={},
            )

            result = gate.check(ticket, context)

            expected_branch = f"ticket/{ticket_id}"
            assert result.metadata["branch_name"] == expected_branch
            mock_git.create_branch.assert_called_once_with(
                expected_branch, "baseline123"
            )

    def test_metadata_includes_branch_and_base_commit(self):
        """Test that result metadata includes both branch_name and base_commit."""
        gate = CreateBranchGate()

        ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="First Ticket",
            depends_on=[],
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.create_branch = Mock()
        mock_git.push_branch = Mock()

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline_abc123",
            tickets={"ticket-1": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        # Verify metadata structure
        assert "branch_name" in result.metadata
        assert "base_commit" in result.metadata
        assert result.metadata["branch_name"] == "ticket/ticket-1"
        assert result.metadata["base_commit"] == "baseline_abc123"
        assert len(result.metadata) == 2  # Only these two fields

    def test_dependency_missing_final_commit_fails(self):
        """Test that missing final_commit in dependency causes check to fail."""
        gate = CreateBranchGate()

        dep_ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Dependency",
            git_info=GitInfo(
                branch_name="ticket/ticket-1",
                base_commit="baseline123",
                final_commit=None,  # Missing!
            ),
        )

        ticket = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Second Ticket",
            depends_on=["ticket-1"],
        )

        mock_git = Mock(spec=GitOperations)

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"ticket-1": dep_ticket, "ticket-2": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        # Verify failure due to missing final_commit
        assert result.passed is False
        assert "Failed to create branch" in result.reason
        assert "ticket-1" in result.reason
        assert "missing final_commit" in result.reason

        # Verify git operations were never called
        mock_git.create_branch.assert_not_called()
        mock_git.push_branch.assert_not_called()
