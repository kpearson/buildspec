"""Unit tests for GitOperations with mocked subprocess calls."""

from unittest.mock import MagicMock, call, patch
import subprocess

import pytest

from cli.epic.git_operations import GitError, GitOperations


class TestGitOperations:
    """Test GitOperations class."""

    def test_initialization_default(self):
        """Test default initialization."""
        ops = GitOperations()
        assert ops.repo_path is None

    def test_initialization_with_path(self):
        """Test initialization with repo path."""
        ops = GitOperations(repo_path="/path/to/repo")
        assert ops.repo_path == "/path/to/repo"


class TestRunGitCommand:
    """Test _run_git_command helper method."""

    @patch("subprocess.run")
    def test_successful_command(self, mock_run):
        """Test successful git command execution."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "status"],
            returncode=0,
            stdout="output",
            stderr="",
        )

        ops = GitOperations()
        result = ops._run_git_command(["git", "status"])

        assert result.returncode == 0
        assert result.stdout == "output"
        mock_run.assert_called_once_with(
            ["git", "status"],
            cwd=None,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_command_with_repo_path(self, mock_run):
        """Test command execution with repo path."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "status"],
            returncode=0,
            stdout="",
            stderr="",
        )

        ops = GitOperations(repo_path="/path/to/repo")
        ops._run_git_command(["git", "status"])

        mock_run.assert_called_once_with(
            ["git", "status"],
            cwd="/path/to/repo",
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_failed_command_with_check(self, mock_run):
        """Test that failed command raises GitError when check=True."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "invalid"],
            returncode=1,
            stdout="",
            stderr="fatal: invalid command",
        )

        ops = GitOperations()
        with pytest.raises(GitError) as exc_info:
            ops._run_git_command(["git", "invalid"], check=True)

        assert "Git command failed" in str(exc_info.value)
        assert "fatal: invalid command" in str(exc_info.value)

    @patch("subprocess.run")
    def test_failed_command_without_check(self, mock_run):
        """Test that failed command does not raise when check=False."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "invalid"],
            returncode=1,
            stdout="",
            stderr="error",
        )

        ops = GitOperations()
        result = ops._run_git_command(["git", "invalid"], check=False)
        assert result.returncode == 1

    @patch("subprocess.run")
    def test_git_not_found(self, mock_run):
        """Test error when git executable is not found."""
        mock_run.side_effect = FileNotFoundError("git not found")

        ops = GitOperations()
        with pytest.raises(GitError) as exc_info:
            ops._run_git_command(["git", "status"])

        assert "Git executable not found" in str(exc_info.value)

    @patch("subprocess.run")
    def test_unexpected_exception(self, mock_run):
        """Test handling of unexpected exceptions."""
        mock_run.side_effect = RuntimeError("unexpected error")

        ops = GitOperations()
        with pytest.raises(GitError) as exc_info:
            ops._run_git_command(["git", "status"])

        assert "Unexpected error running git command" in str(exc_info.value)


class TestCreateBranch:
    """Test create_branch method."""

    @patch("subprocess.run")
    def test_create_new_branch(self, mock_run):
        """Test creating a new branch."""
        # First call: branch doesn't exist (rev-parse fails)
        # Second call: checkout succeeds
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=["git", "rev-parse", "--verify", "new-branch"],
                returncode=1,
                stdout="",
                stderr="fatal: Needed a single revision",
            ),
            subprocess.CompletedProcess(
                args=["git", "checkout", "-b", "new-branch", "abc123"],
                returncode=0,
                stdout="",
                stderr="",
            ),
        ]

        ops = GitOperations()
        ops.create_branch("new-branch", "abc123")

        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "rev-parse", "--verify", "new-branch"],
            cwd=None,
            capture_output=True,
            text=True,
            check=False,
        )
        mock_run.assert_any_call(
            ["git", "checkout", "-b", "new-branch", "abc123"],
            cwd=None,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_create_branch_idempotent(self, mock_run):
        """Test that creating existing branch with same commit is idempotent."""
        # Branch exists and points to correct commit
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--verify", "existing-branch"],
            returncode=0,
            stdout="abc123\n",
            stderr="",
        )

        ops = GitOperations()
        ops.create_branch("existing-branch", "abc123")

        # Should only check if branch exists, not try to create
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_create_branch_conflict(self, mock_run):
        """Test error when branch exists with different commit."""
        # Branch exists but points to different commit
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "rev-parse", "--verify", "existing-branch"],
            returncode=0,
            stdout="def456\n",
            stderr="",
        )

        ops = GitOperations()
        with pytest.raises(GitError) as exc_info:
            ops.create_branch("existing-branch", "abc123")

        assert "already exists but points to different commit" in str(exc_info.value)
        assert "def456" in str(exc_info.value)
        assert "abc123" in str(exc_info.value)


class TestPushBranch:
    """Test push_branch method."""

    @patch("subprocess.run")
    def test_push_branch(self, mock_run):
        """Test pushing a branch."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "push", "-u", "origin", "my-branch"],
            returncode=0,
            stdout="",
            stderr="",
        )

        ops = GitOperations()
        ops.push_branch("my-branch")

        mock_run.assert_called_once_with(
            ["git", "push", "-u", "origin", "my-branch"],
            cwd=None,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_push_branch_failure(self, mock_run):
        """Test error when push fails."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "push", "-u", "origin", "my-branch"],
            returncode=1,
            stdout="",
            stderr="fatal: remote error",
        )

        ops = GitOperations()
        with pytest.raises(GitError):
            ops.push_branch("my-branch")


class TestBranchExistsRemote:
    """Test branch_exists_remote method."""

    @patch("subprocess.run")
    def test_branch_exists(self, mock_run):
        """Test checking if branch exists on remote."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "ls-remote", "--heads", "origin", "my-branch"],
            returncode=0,
            stdout="abc123\trefs/heads/my-branch\n",
            stderr="",
        )

        ops = GitOperations()
        result = ops.branch_exists_remote("my-branch")

        assert result is True
        mock_run.assert_called_once_with(
            ["git", "ls-remote", "--heads", "origin", "my-branch"],
            cwd=None,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_branch_does_not_exist(self, mock_run):
        """Test checking if branch does not exist on remote."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "ls-remote", "--heads", "origin", "missing-branch"],
            returncode=0,
            stdout="",
            stderr="",
        )

        ops = GitOperations()
        result = ops.branch_exists_remote("missing-branch")

        assert result is False


class TestGetCommitsBetween:
    """Test get_commits_between method."""

    @patch("subprocess.run")
    def test_get_commits_between(self, mock_run):
        """Test getting commits between base and head."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "rev-list", "base123..head456"],
            returncode=0,
            stdout="commit3\ncommit2\ncommit1\n",
            stderr="",
        )

        ops = GitOperations()
        commits = ops.get_commits_between("base123", "head456")

        assert commits == ["commit3", "commit2", "commit1"]
        mock_run.assert_called_once_with(
            ["git", "rev-list", "base123..head456"],
            cwd=None,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_get_commits_between_empty(self, mock_run):
        """Test getting commits when there are none."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "rev-list", "base123..head456"],
            returncode=0,
            stdout="\n",
            stderr="",
        )

        ops = GitOperations()
        commits = ops.get_commits_between("base123", "head456")

        assert commits == []

    @patch("subprocess.run")
    def test_get_commits_between_failure(self, mock_run):
        """Test error when getting commits fails."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "rev-list", "invalid..commits"],
            returncode=1,
            stdout="",
            stderr="fatal: bad revision",
        )

        ops = GitOperations()
        with pytest.raises(GitError):
            ops.get_commits_between("invalid", "commits")


class TestCommitExists:
    """Test commit_exists method."""

    @patch("subprocess.run")
    def test_commit_exists(self, mock_run):
        """Test checking if commit exists."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "cat-file", "-t", "abc123"],
            returncode=0,
            stdout="commit\n",
            stderr="",
        )

        ops = GitOperations()
        result = ops.commit_exists("abc123")

        assert result is True
        mock_run.assert_called_once_with(
            ["git", "cat-file", "-t", "abc123"],
            cwd=None,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_commit_does_not_exist(self, mock_run):
        """Test checking if commit does not exist."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "cat-file", "-t", "invalid"],
            returncode=1,
            stdout="",
            stderr="fatal: Not a valid object name",
        )

        ops = GitOperations()
        result = ops.commit_exists("invalid")

        assert result is False

    @patch("subprocess.run")
    def test_commit_wrong_type(self, mock_run):
        """Test checking object that is not a commit."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "cat-file", "-t", "tree123"],
            returncode=0,
            stdout="tree\n",
            stderr="",
        )

        ops = GitOperations()
        result = ops.commit_exists("tree123")

        assert result is False


class TestCommitOnBranch:
    """Test commit_on_branch method."""

    @patch("subprocess.run")
    def test_commit_on_branch(self, mock_run):
        """Test checking if commit is on branch."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "merge-base", "--is-ancestor", "abc123", "main"],
            returncode=0,
            stdout="",
            stderr="",
        )

        ops = GitOperations()
        result = ops.commit_on_branch("abc123", "main")

        assert result is True
        mock_run.assert_called_once_with(
            ["git", "merge-base", "--is-ancestor", "abc123", "main"],
            cwd=None,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_commit_not_on_branch(self, mock_run):
        """Test checking if commit is not on branch."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "merge-base", "--is-ancestor", "abc123", "main"],
            returncode=1,
            stdout="",
            stderr="",
        )

        ops = GitOperations()
        result = ops.commit_on_branch("abc123", "main")

        assert result is False


class TestFindMostRecentCommit:
    """Test find_most_recent_commit method."""

    @patch("subprocess.run")
    def test_find_most_recent_commit(self, mock_run):
        """Test finding most recent commit from list."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "log", "--no-walk", "--date-order", "--format=%H", "abc", "def", "ghi"],
            returncode=0,
            stdout="def\nghi\nabc\n",
            stderr="",
        )

        ops = GitOperations()
        result = ops.find_most_recent_commit(["abc", "def", "ghi"])

        assert result == "def"
        mock_run.assert_called_once_with(
            ["git", "log", "--no-walk", "--date-order", "--format=%H", "abc", "def", "ghi"],
            cwd=None,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_find_most_recent_commit_single(self, mock_run):
        """Test finding most recent commit with single commit."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "log", "--no-walk", "--date-order", "--format=%H", "abc123"],
            returncode=0,
            stdout="abc123\n",
            stderr="",
        )

        ops = GitOperations()
        result = ops.find_most_recent_commit(["abc123"])

        assert result == "abc123"

    def test_find_most_recent_commit_empty_list(self):
        """Test error when commit list is empty."""
        ops = GitOperations()
        with pytest.raises(GitError) as exc_info:
            ops.find_most_recent_commit([])

        assert "empty commit list" in str(exc_info.value)

    @patch("subprocess.run")
    def test_find_most_recent_commit_failure(self, mock_run):
        """Test error when git log fails."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "log", "--no-walk", "--date-order", "--format=%H", "invalid"],
            returncode=1,
            stdout="",
            stderr="fatal: bad object",
        )

        ops = GitOperations()
        with pytest.raises(GitError):
            ops.find_most_recent_commit(["invalid"])


class TestMergeBranch:
    """Test merge_branch method."""

    @patch("subprocess.run")
    def test_merge_branch_squash(self, mock_run):
        """Test merging with squash strategy."""
        mock_run.side_effect = [
            # Checkout target
            subprocess.CompletedProcess(
                args=["git", "checkout", "main"],
                returncode=0,
                stdout="",
                stderr="",
            ),
            # Merge squash
            subprocess.CompletedProcess(
                args=["git", "merge", "--squash", "feature"],
                returncode=0,
                stdout="",
                stderr="",
            ),
            # Commit
            subprocess.CompletedProcess(
                args=["git", "commit", "-m", "Merge feature"],
                returncode=0,
                stdout="",
                stderr="",
            ),
            # Get merge commit SHA
            subprocess.CompletedProcess(
                args=["git", "rev-parse", "HEAD"],
                returncode=0,
                stdout="merge123\n",
                stderr="",
            ),
        ]

        ops = GitOperations()
        result = ops.merge_branch("feature", "main", "squash", "Merge feature")

        assert result == "merge123"
        assert mock_run.call_count == 4

    @patch("subprocess.run")
    def test_merge_branch_no_ff(self, mock_run):
        """Test merging with no-ff strategy."""
        mock_run.side_effect = [
            # Checkout target
            subprocess.CompletedProcess(
                args=["git", "checkout", "main"],
                returncode=0,
                stdout="",
                stderr="",
            ),
            # Merge no-ff
            subprocess.CompletedProcess(
                args=["git", "merge", "--no-ff", "-m", "Merge feature", "feature"],
                returncode=0,
                stdout="",
                stderr="",
            ),
            # Get merge commit SHA
            subprocess.CompletedProcess(
                args=["git", "rev-parse", "HEAD"],
                returncode=0,
                stdout="merge456\n",
                stderr="",
            ),
        ]

        ops = GitOperations()
        result = ops.merge_branch("feature", "main", "no-ff", "Merge feature")

        assert result == "merge456"
        assert mock_run.call_count == 3

    def test_merge_branch_invalid_strategy(self):
        """Test error with invalid merge strategy."""
        ops = GitOperations()
        with pytest.raises(GitError) as exc_info:
            ops.merge_branch("feature", "main", "invalid", "Merge")

        assert "Invalid merge strategy" in str(exc_info.value)

    @patch("subprocess.run")
    def test_merge_branch_conflict(self, mock_run):
        """Test error when merge has conflicts."""
        mock_run.side_effect = [
            # Checkout target
            subprocess.CompletedProcess(
                args=["git", "checkout", "main"],
                returncode=0,
                stdout="",
                stderr="",
            ),
            # Merge fails with conflict
            subprocess.CompletedProcess(
                args=["git", "merge", "--no-ff", "-m", "Merge", "feature"],
                returncode=1,
                stdout="",
                stderr="CONFLICT: merge conflict",
            ),
        ]

        ops = GitOperations()
        with pytest.raises(GitError):
            ops.merge_branch("feature", "main", "no-ff", "Merge")


class TestDeleteBranch:
    """Test delete_branch method."""

    @patch("subprocess.run")
    def test_delete_local_branch(self, mock_run):
        """Test deleting local branch."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "branch", "-D", "feature"],
            returncode=0,
            stdout="",
            stderr="",
        )

        ops = GitOperations()
        ops.delete_branch("feature", remote=False)

        mock_run.assert_called_once_with(
            ["git", "branch", "-D", "feature"],
            cwd=None,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_delete_remote_branch(self, mock_run):
        """Test deleting remote branch."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "push", "origin", "--delete", "feature"],
            returncode=0,
            stdout="",
            stderr="",
        )

        ops = GitOperations()
        ops.delete_branch("feature", remote=True)

        mock_run.assert_called_once_with(
            ["git", "push", "origin", "--delete", "feature"],
            cwd=None,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("subprocess.run")
    def test_delete_local_branch_idempotent(self, mock_run):
        """Test deleting non-existent local branch is idempotent."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "branch", "-D", "feature"],
            returncode=1,
            stdout="",
            stderr="error: branch 'feature' not found",
        )

        ops = GitOperations()
        # Should not raise error
        ops.delete_branch("feature", remote=False)

    @patch("subprocess.run")
    def test_delete_remote_branch_idempotent(self, mock_run):
        """Test deleting non-existent remote branch is idempotent."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "push", "origin", "--delete", "feature"],
            returncode=1,
            stdout="",
            stderr="error: remote ref does not exist",
        )

        ops = GitOperations()
        # Should not raise error
        ops.delete_branch("feature", remote=True)

    @patch("subprocess.run")
    def test_delete_local_branch_failure(self, mock_run):
        """Test error when local branch deletion fails for other reasons."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "branch", "-D", "feature"],
            returncode=1,
            stdout="",
            stderr="fatal: some other error",
        )

        ops = GitOperations()
        with pytest.raises(GitError) as exc_info:
            ops.delete_branch("feature", remote=False)

        assert "Failed to delete local branch" in str(exc_info.value)

    @patch("subprocess.run")
    def test_delete_remote_branch_failure(self, mock_run):
        """Test error when remote branch deletion fails for other reasons."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "push", "origin", "--delete", "feature"],
            returncode=1,
            stdout="",
            stderr="fatal: authentication failed",
        )

        ops = GitOperations()
        with pytest.raises(GitError) as exc_info:
            ops.delete_branch("feature", remote=True)

        assert "Failed to delete remote branch" in str(exc_info.value)
