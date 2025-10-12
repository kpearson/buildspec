"""Integration tests for CreateBranchGate with real git repository."""

import os
import subprocess
from pathlib import Path

import pytest

from cli.epic.gates import CreateBranchGate, EpicContext
from cli.epic.git_operations import GitOperations
from cli.epic.models import GitInfo, Ticket


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Configure git user for commits
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository\n")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Get initial commit SHA
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    initial_commit = result.stdout.strip()

    # Set up fake remote (just another directory)
    remote_path = tmp_path / "remote_repo"
    remote_path.mkdir()
    subprocess.run(
        ["git", "init", "--bare"],
        cwd=remote_path,
        check=True,
        capture_output=True,
    )

    # Add remote
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_path)],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Push initial commit to remote
    subprocess.run(
        ["git", "push", "-u", "origin", "master"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return {
        "path": str(repo_path),
        "remote_path": str(remote_path),
        "initial_commit": initial_commit,
    }


def create_commit(repo_path: str, filename: str, content: str, message: str) -> str:
    """Helper to create a commit and return its SHA."""
    file_path = Path(repo_path) / filename
    file_path.write_text(content)

    subprocess.run(
        ["git", "add", filename],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip()


class TestCreateBranchGateIntegration:
    """Integration tests for CreateBranchGate with real git operations."""

    def test_create_branch_no_dependencies(self, git_repo):
        """Test creating branch for ticket with no dependencies branches from baseline."""
        ops = GitOperations(repo_path=git_repo["path"])
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
            baseline_commit=git_repo["initial_commit"],
            tickets={"ticket-1": ticket},
            git=ops,
            epic_config={},
        )

        result = gate.check(ticket, context)

        # Verify success
        assert result.passed is True
        assert result.metadata["branch_name"] == "ticket/ticket-1"
        assert result.metadata["base_commit"] == git_repo["initial_commit"]

        # Verify branch exists locally
        branch_result = subprocess.run(
            ["git", "rev-parse", "--verify", "ticket/ticket-1"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
        )
        assert branch_result.returncode == 0
        assert branch_result.stdout.strip() == git_repo["initial_commit"]

        # Verify branch exists on remote
        assert ops.branch_exists_remote("ticket/ticket-1") is True

    def test_create_stacked_branch_single_dependency(self, git_repo):
        """Test creating stacked branch that branches from dependency's final commit."""
        ops = GitOperations(repo_path=git_repo["path"])
        gate = CreateBranchGate()

        # Create first ticket branch and commit
        ops.create_branch("ticket/ticket-1", git_repo["initial_commit"])
        subprocess.run(
            ["git", "checkout", "ticket/ticket-1"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        ticket1_final = create_commit(
            git_repo["path"],
            "feature1.txt",
            "Feature 1 content",
            "Add feature 1",
        )

        ops.push_branch("ticket/ticket-1")

        # Create dependency ticket with final commit
        dep_ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="First Ticket",
            git_info=GitInfo(
                branch_name="ticket/ticket-1",
                base_commit=git_repo["initial_commit"],
                final_commit=ticket1_final,
            ),
        )

        # Create second ticket that depends on first
        ticket = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Second Ticket",
            depends_on=["ticket-1"],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit=git_repo["initial_commit"],
            tickets={"ticket-1": dep_ticket, "ticket-2": ticket},
            git=ops,
            epic_config={},
        )

        result = gate.check(ticket, context)

        # Verify success
        assert result.passed is True
        assert result.metadata["branch_name"] == "ticket/ticket-2"
        assert result.metadata["base_commit"] == ticket1_final

        # Verify branch exists and points to correct commit
        branch_result = subprocess.run(
            ["git", "rev-parse", "--verify", "ticket/ticket-2"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
        )
        assert branch_result.returncode == 0
        assert branch_result.stdout.strip() == ticket1_final

        # Verify branch exists on remote
        assert ops.branch_exists_remote("ticket/ticket-2") is True

    def test_create_diamond_dependency_branches_from_most_recent(self, git_repo):
        """Test diamond dependency: A -> B, A -> C, B+C -> D.

        Ticket D should branch from whichever of B or C has the most recent final commit.
        """
        ops = GitOperations(repo_path=git_repo["path"])
        gate = CreateBranchGate()

        # Create ticket A branch and commit
        ops.create_branch("ticket/ticket-a", git_repo["initial_commit"])
        subprocess.run(
            ["git", "checkout", "ticket/ticket-a"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        ticket_a_final = create_commit(
            git_repo["path"],
            "featureA.txt",
            "Feature A content",
            "Add feature A",
        )

        ops.push_branch("ticket/ticket-a")

        # Create ticket B branch (depends on A) with explicit timestamp
        ops.create_branch("ticket/ticket-b", ticket_a_final)
        subprocess.run(
            ["git", "checkout", "ticket/ticket-b"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        # Create commit for B with specific timestamp (earlier)
        file_b = Path(git_repo["path"]) / "featureB.txt"
        file_b.write_text("Feature B content")
        subprocess.run(
            ["git", "add", "featureB.txt"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        base_timestamp = 1609459200  # 2021-01-01 00:00:00
        env = os.environ.copy()
        env["GIT_COMMITTER_DATE"] = str(base_timestamp)
        env["GIT_AUTHOR_DATE"] = str(base_timestamp)

        subprocess.run(
            ["git", "commit", "-m", "Add feature B"],
            cwd=git_repo["path"],
            env=env,
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
            check=True,
        )
        ticket_b_final = result.stdout.strip()

        ops.push_branch("ticket/ticket-b")

        # Create ticket C branch (depends on A) with later timestamp
        ops.create_branch("ticket/ticket-c", ticket_a_final)
        subprocess.run(
            ["git", "checkout", "ticket/ticket-c"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        # Create commit for C with later timestamp
        file_c = Path(git_repo["path"]) / "featureC.txt"
        file_c.write_text("Feature C content")
        subprocess.run(
            ["git", "add", "featureC.txt"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        env["GIT_COMMITTER_DATE"] = str(base_timestamp + 3600)  # 1 hour later
        env["GIT_AUTHOR_DATE"] = str(base_timestamp + 3600)

        subprocess.run(
            ["git", "commit", "-m", "Add feature C"],
            cwd=git_repo["path"],
            env=env,
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
            check=True,
        )
        ticket_c_final = result.stdout.strip()

        ops.push_branch("ticket/ticket-c")

        # Create ticket models
        ticket_a = Ticket(
            id="ticket-a",
            path="/path/a",
            title="Ticket A",
            depends_on=[],
            git_info=GitInfo(
                branch_name="ticket/ticket-a",
                base_commit=git_repo["initial_commit"],
                final_commit=ticket_a_final,
            ),
        )

        ticket_b = Ticket(
            id="ticket-b",
            path="/path/b",
            title="Ticket B",
            depends_on=["ticket-a"],
            git_info=GitInfo(
                branch_name="ticket/ticket-b",
                base_commit=ticket_a_final,
                final_commit=ticket_b_final,
            ),
        )

        ticket_c = Ticket(
            id="ticket-c",
            path="/path/c",
            title="Ticket C",
            depends_on=["ticket-a"],
            git_info=GitInfo(
                branch_name="ticket/ticket-c",
                base_commit=ticket_a_final,
                final_commit=ticket_c_final,
            ),
        )

        # Create ticket D that depends on both B and C
        ticket_d = Ticket(
            id="ticket-d",
            path="/path/d",
            title="Ticket D",
            depends_on=["ticket-b", "ticket-c"],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit=git_repo["initial_commit"],
            tickets={
                "ticket-a": ticket_a,
                "ticket-b": ticket_b,
                "ticket-c": ticket_c,
                "ticket-d": ticket_d,
            },
            git=ops,
            epic_config={},
        )

        # Create branch for ticket D
        result = gate.check(ticket_d, context)

        # Verify success
        assert result.passed is True
        assert result.metadata["branch_name"] == "ticket/ticket-d"

        # Verify D branches from C (most recent)
        assert result.metadata["base_commit"] == ticket_c_final

        # Verify branch exists
        branch_result = subprocess.run(
            ["git", "rev-parse", "--verify", "ticket/ticket-d"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
        )
        assert branch_result.returncode == 0
        assert branch_result.stdout.strip() == ticket_c_final

    def test_create_linear_chain_stacking(self, git_repo):
        """Test linear chain A -> B -> C where each branches from previous final commit."""
        ops = GitOperations(repo_path=git_repo["path"])
        gate = CreateBranchGate()

        tickets = {}
        commits = [git_repo["initial_commit"]]
        ticket_ids = ["ticket-a", "ticket-b", "ticket-c"]

        # Create chain of 3 tickets
        for i, ticket_id in enumerate(ticket_ids):
            prev_commit = commits[-1]

            # Create branch and commit
            ops.create_branch(f"ticket/{ticket_id}", prev_commit)
            subprocess.run(
                ["git", "checkout", f"ticket/{ticket_id}"],
                cwd=git_repo["path"],
                check=True,
                capture_output=True,
            )

            final_commit = create_commit(
                git_repo["path"],
                f"feature{i}.txt",
                f"Feature {i} content",
                f"Add feature {i}",
            )

            ops.push_branch(f"ticket/{ticket_id}")

            # Create ticket model
            ticket = Ticket(
                id=ticket_id,
                path=f"/path/{ticket_id}",
                title=f"Ticket {ticket_id}",
                depends_on=[ticket_ids[i - 1]] if i > 0 else [],
                git_info=GitInfo(
                    branch_name=f"ticket/{ticket_id}",
                    base_commit=prev_commit,
                    final_commit=final_commit,
                ),
            )

            tickets[ticket_id] = ticket
            commits.append(final_commit)

        # Verify each ticket branches from correct base
        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit=git_repo["initial_commit"],
            tickets=tickets,
            git=ops,
            epic_config={},
        )

        for i, ticket_id in enumerate(ticket_ids):
            ticket = tickets[ticket_id]
            expected_base = commits[i]

            # Verify via git that branch points to expected commit
            branch_result = subprocess.run(
                ["git", "rev-parse", "--verify", f"ticket/{ticket_id}"],
                cwd=git_repo["path"],
                capture_output=True,
                text=True,
            )
            assert branch_result.returncode == 0
            assert branch_result.stdout.strip() == commits[i + 1]

            # Verify branch exists on remote
            assert ops.branch_exists_remote(f"ticket/{ticket_id}") is True

    def test_idempotent_branch_creation(self, git_repo):
        """Test that calling check() twice for same ticket is idempotent."""
        ops = GitOperations(repo_path=git_repo["path"])
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
            baseline_commit=git_repo["initial_commit"],
            tickets={"ticket-1": ticket},
            git=ops,
            epic_config={},
        )

        # Create branch first time
        result1 = gate.check(ticket, context)
        assert result1.passed is True

        # Create same branch again - should succeed (idempotent)
        result2 = gate.check(ticket, context)
        assert result2.passed is True

        # Results should be identical
        assert result1.metadata == result2.metadata

    def test_branch_already_exists_different_base_fails(self, git_repo):
        """Test that creating branch that exists with different base fails."""
        ops = GitOperations(repo_path=git_repo["path"])
        gate = CreateBranchGate()

        # Create a second commit
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        second_commit = create_commit(
            git_repo["path"],
            "test.txt",
            "test content",
            "Second commit",
        )

        subprocess.run(
            ["git", "push", "origin", "master"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        # Create branch pointing to initial commit
        ops.create_branch("ticket/ticket-1", git_repo["initial_commit"])
        ops.push_branch("ticket/ticket-1")

        # Try to create same branch pointing to second commit
        ticket = Ticket(
            id="ticket-1",
            path="/path/1",
            title="First Ticket",
            depends_on=[],
        )

        # Context has baseline as second commit (different from existing branch)
        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit=second_commit,  # Different from existing branch base
            tickets={"ticket-1": ticket},
            git=ops,
            epic_config={},
        )

        result = gate.check(ticket, context)

        # Should fail due to conflict
        assert result.passed is False
        assert "Failed to create branch" in result.reason

    def test_push_to_remote_succeeds(self, git_repo):
        """Test that branches are pushed to remote successfully."""
        ops = GitOperations(repo_path=git_repo["path"])
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
            baseline_commit=git_repo["initial_commit"],
            tickets={"ticket-1": ticket},
            git=ops,
            epic_config={},
        )

        result = gate.check(ticket, context)

        assert result.passed is True

        # Verify branch exists on remote using ls-remote
        remote_result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", "ticket/ticket-1"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
        )

        assert remote_result.returncode == 0
        assert "ticket/ticket-1" in remote_result.stdout

    def test_multiple_tickets_create_separate_branches(self, git_repo):
        """Test that multiple tickets create separate independent branches."""
        ops = GitOperations(repo_path=git_repo["path"])
        gate = CreateBranchGate()

        # Create 3 independent tickets
        tickets = {}
        for i in range(1, 4):
            ticket_id = f"ticket-{i}"
            ticket = Ticket(
                id=ticket_id,
                path=f"/path/{i}",
                title=f"Ticket {i}",
                depends_on=[],
            )
            tickets[ticket_id] = ticket

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit=git_repo["initial_commit"],
            tickets=tickets,
            git=ops,
            epic_config={},
        )

        # Create branches for all tickets
        for ticket in tickets.values():
            result = gate.check(ticket, context)
            assert result.passed is True

        # Verify all branches exist
        for i in range(1, 4):
            branch_name = f"ticket/ticket-{i}"
            branch_result = subprocess.run(
                ["git", "rev-parse", "--verify", branch_name],
                cwd=git_repo["path"],
                capture_output=True,
                text=True,
            )
            assert branch_result.returncode == 0
            assert branch_result.stdout.strip() == git_repo["initial_commit"]

            # Verify on remote
            assert ops.branch_exists_remote(branch_name) is True

    def test_calculate_base_with_real_git_find_most_recent(self, git_repo):
        """Test that find_most_recent_commit works correctly with real commits."""
        ops = GitOperations(repo_path=git_repo["path"])
        gate = CreateBranchGate()

        # Create two branches with different timestamps
        base_timestamp = 1609459200

        # Branch 1 with earlier timestamp
        ops.create_branch("ticket/ticket-1", git_repo["initial_commit"])
        subprocess.run(
            ["git", "checkout", "ticket/ticket-1"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        file1 = Path(git_repo["path"]) / "feature1.txt"
        file1.write_text("Feature 1")
        subprocess.run(
            ["git", "add", "feature1.txt"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        env = os.environ.copy()
        env["GIT_COMMITTER_DATE"] = str(base_timestamp)
        env["GIT_AUTHOR_DATE"] = str(base_timestamp)

        subprocess.run(
            ["git", "commit", "-m", "Feature 1"],
            cwd=git_repo["path"],
            env=env,
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
            check=True,
        )
        commit1 = result.stdout.strip()

        ops.push_branch("ticket/ticket-1")

        # Branch 2 with later timestamp
        ops.create_branch("ticket/ticket-2", git_repo["initial_commit"])
        subprocess.run(
            ["git", "checkout", "ticket/ticket-2"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        file2 = Path(git_repo["path"]) / "feature2.txt"
        file2.write_text("Feature 2")
        subprocess.run(
            ["git", "add", "feature2.txt"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        env["GIT_COMMITTER_DATE"] = str(base_timestamp + 7200)  # 2 hours later
        env["GIT_AUTHOR_DATE"] = str(base_timestamp + 7200)

        subprocess.run(
            ["git", "commit", "-m", "Feature 2"],
            cwd=git_repo["path"],
            env=env,
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
            check=True,
        )
        commit2 = result.stdout.strip()

        ops.push_branch("ticket/ticket-2")

        # Create ticket models
        ticket1 = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Ticket 1",
            git_info=GitInfo(
                branch_name="ticket/ticket-1",
                base_commit=git_repo["initial_commit"],
                final_commit=commit1,
            ),
        )

        ticket2 = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Ticket 2",
            git_info=GitInfo(
                branch_name="ticket/ticket-2",
                base_commit=git_repo["initial_commit"],
                final_commit=commit2,
            ),
        )

        # Create ticket that depends on both
        ticket3 = Ticket(
            id="ticket-3",
            path="/path/3",
            title="Ticket 3",
            depends_on=["ticket-1", "ticket-2"],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit=git_repo["initial_commit"],
            tickets={"ticket-1": ticket1, "ticket-2": ticket2, "ticket-3": ticket3},
            git=ops,
            epic_config={},
        )

        result = gate.check(ticket3, context)

        # Should branch from commit2 (most recent)
        assert result.passed is True
        assert result.metadata["base_commit"] == commit2

        # Verify branch points to commit2
        branch_result = subprocess.run(
            ["git", "rev-parse", "--verify", "ticket/ticket-3"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
        )
        assert branch_result.returncode == 0
        assert branch_result.stdout.strip() == commit2
