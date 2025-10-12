"""Integration tests for GitOperations with real git repository."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from cli.epic.git_operations import GitError, GitOperations


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

    return {
        "path": str(repo_path),
        "initial_commit": initial_commit,
    }


class TestGitOperationsIntegration:
    """Integration tests for GitOperations with real git operations."""

    def test_create_branch(self, git_repo):
        """Test creating a new branch in real repo."""
        ops = GitOperations(repo_path=git_repo["path"])

        # Create a new branch
        ops.create_branch("test-branch", git_repo["initial_commit"])

        # Verify branch exists
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "test-branch"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == git_repo["initial_commit"]

    def test_create_branch_idempotent(self, git_repo):
        """Test that creating same branch twice is idempotent."""
        ops = GitOperations(repo_path=git_repo["path"])

        # Create branch first time
        ops.create_branch("test-branch", git_repo["initial_commit"])

        # Create same branch again - should succeed
        ops.create_branch("test-branch", git_repo["initial_commit"])

    def test_create_branch_conflict(self, git_repo):
        """Test error when branch exists with different commit."""
        ops = GitOperations(repo_path=git_repo["path"])

        # Create a second commit
        test_file = Path(git_repo["path"]) / "test.txt"
        test_file.write_text("test content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Second commit"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
        )
        second_commit = result.stdout.strip()

        # Create branch pointing to first commit
        ops.create_branch("test-branch", git_repo["initial_commit"])

        # Try to create same branch pointing to second commit - should fail
        with pytest.raises(GitError) as exc_info:
            ops.create_branch("test-branch", second_commit)
        assert "already exists but points to different commit" in str(exc_info.value)

    def test_commit_exists(self, git_repo):
        """Test checking if commit exists."""
        ops = GitOperations(repo_path=git_repo["path"])

        # Check valid commit
        assert ops.commit_exists(git_repo["initial_commit"]) is True

        # Check invalid commit
        assert ops.commit_exists("0000000000000000000000000000000000000000") is False

    def test_get_commits_between(self, git_repo):
        """Test getting commits between two points."""
        ops = GitOperations(repo_path=git_repo["path"])

        # Create second and third commits
        commits = []
        for i in range(2):
            test_file = Path(git_repo["path"]) / f"test{i}.txt"
            test_file.write_text(f"content {i}")
            subprocess.run(
                ["git", "add", f"test{i}.txt"],
                cwd=git_repo["path"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i + 2}"],
                cwd=git_repo["path"],
                check=True,
                capture_output=True,
            )
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=git_repo["path"],
                capture_output=True,
                text=True,
            )
            commits.append(result.stdout.strip())

        # Get commits between initial and HEAD
        result_commits = ops.get_commits_between(git_repo["initial_commit"], commits[1])

        # Should have exactly 2 commits
        assert len(result_commits) == 2
        # They should be in reverse chronological order
        assert result_commits[0] == commits[1]
        assert result_commits[1] == commits[0]

    def test_commit_on_branch(self, git_repo):
        """Test checking if commit is on a branch."""
        ops = GitOperations(repo_path=git_repo["path"])

        # Create a branch
        subprocess.run(
            ["git", "checkout", "-b", "test-branch"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        # Create a commit on test-branch
        test_file = Path(git_repo["path"]) / "branch.txt"
        test_file.write_text("branch content")
        subprocess.run(
            ["git", "add", "branch.txt"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Branch commit"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
        )
        branch_commit = result.stdout.strip()

        # Initial commit should be on test-branch (ancestor)
        assert ops.commit_on_branch(git_repo["initial_commit"], "test-branch") is True

        # Branch commit should be on test-branch
        assert ops.commit_on_branch(branch_commit, "test-branch") is True

        # Branch commit should NOT be on master/main (it's ahead)
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )
        assert ops.commit_on_branch(branch_commit, "master") is False

    def test_find_most_recent_commit(self, git_repo):
        """Test finding most recent commit from a list."""
        ops = GitOperations(repo_path=git_repo["path"])

        # Create multiple commits with explicit dates to ensure different timestamps
        commits = []
        base_timestamp = 1609459200  # 2021-01-01 00:00:00
        for i in range(4):
            test_file = Path(git_repo["path"]) / f"file{i}.txt"
            test_file.write_text(f"content {i}")
            subprocess.run(
                ["git", "add", f"file{i}.txt"],
                cwd=git_repo["path"],
                check=True,
                capture_output=True,
            )
            # Set both author and committer date via environment variables
            commit_date = str(base_timestamp + (i + 1) * 3600)  # Each commit 1 hour apart
            env = os.environ.copy()
            env["GIT_COMMITTER_DATE"] = commit_date
            env["GIT_AUTHOR_DATE"] = commit_date
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i + 2}"],
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
            )
            commits.append(result.stdout.strip())

        # Most recent should be the last one (highest timestamp)
        most_recent = ops.find_most_recent_commit(commits)
        assert most_recent == commits[-1]

        # Try with shuffled list
        import random
        shuffled = commits.copy()
        random.shuffle(shuffled)
        most_recent = ops.find_most_recent_commit(shuffled)
        assert most_recent == commits[-1]

    def test_merge_branch_squash(self, git_repo):
        """Test merging with squash strategy."""
        ops = GitOperations(repo_path=git_repo["path"])

        # Create a feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        # Create commits on feature branch
        for i in range(2):
            test_file = Path(git_repo["path"]) / f"feature{i}.txt"
            test_file.write_text(f"feature content {i}")
            subprocess.run(
                ["git", "add", f"feature{i}.txt"],
                cwd=git_repo["path"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Feature commit {i + 1}"],
                cwd=git_repo["path"],
                check=True,
                capture_output=True,
            )

        # Merge with squash
        merge_commit = ops.merge_branch("feature", "master", "squash", "Squash merge feature")

        # Verify merge commit exists
        assert ops.commit_exists(merge_commit)

        # Verify we're on master
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "master"

        # Verify changes are merged
        assert (Path(git_repo["path"]) / "feature0.txt").exists()
        assert (Path(git_repo["path"]) / "feature1.txt").exists()

    def test_merge_branch_no_ff(self, git_repo):
        """Test merging with no-ff strategy."""
        ops = GitOperations(repo_path=git_repo["path"])

        # Create a feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        # Create a commit on feature branch
        test_file = Path(git_repo["path"]) / "feature.txt"
        test_file.write_text("feature content")
        subprocess.run(
            ["git", "add", "feature.txt"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        # Merge with no-ff
        merge_commit = ops.merge_branch("feature", "master", "no-ff", "No-FF merge feature")

        # Verify merge commit exists
        assert ops.commit_exists(merge_commit)

        # Verify we're on master
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "master"

        # Verify it's a merge commit (has 2 parents)
        result = subprocess.run(
            ["git", "rev-list", "--parents", "-n", "1", merge_commit],
            cwd=git_repo["path"],
            capture_output=True,
            text=True,
        )
        parents = result.stdout.strip().split()
        assert len(parents) == 3  # commit SHA + 2 parent SHAs

    def test_delete_branch_local(self, git_repo):
        """Test deleting a local branch."""
        ops = GitOperations(repo_path=git_repo["path"])

        # Create a branch
        subprocess.run(
            ["git", "checkout", "-b", "to-delete"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        # Switch back to master
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        # Delete the branch
        ops.delete_branch("to-delete", remote=False)

        # Verify branch is deleted
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "to-delete"],
            cwd=git_repo["path"],
            capture_output=True,
        )
        assert result.returncode != 0

    def test_delete_branch_idempotent(self, git_repo):
        """Test that deleting non-existent branch is idempotent."""
        ops = GitOperations(repo_path=git_repo["path"])

        # Delete a branch that doesn't exist - should not raise error
        ops.delete_branch("nonexistent", remote=False)

    def test_branch_exists_remote_no_remote(self, git_repo):
        """Test checking remote branch when no remote is configured."""
        ops = GitOperations(repo_path=git_repo["path"])

        # This should return False when no remote is configured
        # Git will return empty output for ls-remote without error
        result = ops.branch_exists_remote("any-branch")
        assert result is False

    def test_find_most_recent_commit_empty_list(self, git_repo):
        """Test error when trying to find most recent from empty list."""
        ops = GitOperations(repo_path=git_repo["path"])

        with pytest.raises(GitError) as exc_info:
            ops.find_most_recent_commit([])
        assert "empty commit list" in str(exc_info.value)

    def test_merge_invalid_strategy(self, git_repo):
        """Test error with invalid merge strategy."""
        ops = GitOperations(repo_path=git_repo["path"])

        with pytest.raises(GitError) as exc_info:
            ops.merge_branch("feature", "master", "invalid-strategy", "Merge")
        assert "Invalid merge strategy" in str(exc_info.value)

    def test_operations_with_nonexistent_repo(self):
        """Test that operations fail gracefully with nonexistent repo."""
        ops = GitOperations(repo_path="/nonexistent/repo/path")

        with pytest.raises(GitError):
            ops.commit_exists("abc123")

    def test_multiple_operations_sequence(self, git_repo):
        """Test a realistic sequence of git operations."""
        ops = GitOperations(repo_path=git_repo["path"])

        # 1. Create a branch
        ops.create_branch("feature-branch", git_repo["initial_commit"])

        # 2. Verify commit exists
        assert ops.commit_exists(git_repo["initial_commit"])

        # 3. Switch to feature branch and make changes
        subprocess.run(
            ["git", "checkout", "feature-branch"],
            cwd=git_repo["path"],
            check=True,
            capture_output=True,
        )

        # Create multiple commits with explicit dates to ensure different timestamps
        commits = []
        base_timestamp = 1609459200  # 2021-01-01 00:00:00
        for i in range(3):
            test_file = Path(git_repo["path"]) / f"feature{i}.txt"
            test_file.write_text(f"content {i}")
            subprocess.run(
                ["git", "add", f"feature{i}.txt"],
                cwd=git_repo["path"],
                check=True,
                capture_output=True,
            )
            # Set both author and committer date via environment variables
            commit_date = str(base_timestamp + (i + 1) * 3600)  # Each commit 1 hour apart
            env = os.environ.copy()
            env["GIT_COMMITTER_DATE"] = commit_date
            env["GIT_AUTHOR_DATE"] = commit_date
            subprocess.run(
                ["git", "commit", "-m", f"Feature commit {i + 1}"],
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
            )
            commits.append(result.stdout.strip())

        # 4. Get commits between base and HEAD
        branch_commits = ops.get_commits_between(git_repo["initial_commit"], commits[-1])
        assert len(branch_commits) == 3

        # 5. Find most recent commit
        most_recent = ops.find_most_recent_commit(commits)
        assert most_recent == commits[-1]

        # 6. Verify commits are on branch
        for commit in commits:
            assert ops.commit_on_branch(commit, "feature-branch")

        # 7. Merge branch
        merge_commit = ops.merge_branch("feature-branch", "master", "squash", "Merge feature")
        assert ops.commit_exists(merge_commit)

        # 8. Delete the feature branch
        ops.delete_branch("feature-branch", remote=False)

        # Verify branch is deleted
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "feature-branch"],
            cwd=git_repo["path"],
            capture_output=True,
        )
        assert result.returncode != 0
