"""Git operations wrapper using subprocess for branch management and validation.

This module provides a GitOperations class that wraps all git subprocess commands
needed by the epic state machine and validation gates. All operations are
idempotent to support retries and resumption.
"""

from __future__ import annotations

import subprocess
from typing import List, Optional


class GitError(Exception):
    """Exception raised when git operations fail."""

    pass


class GitOperations:
    """Wrapper for git subprocess commands with proper error handling."""

    def __init__(self, repo_path: Optional[str] = None):
        """Initialize GitOperations.

        Args:
            repo_path: Path to git repository. If None, uses current directory.
        """
        self.repo_path = repo_path

    def _run_git_command(
        self, args: List[str], check: bool = True, capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a git command with proper error handling.

        Args:
            args: Git command arguments (e.g., ["git", "status"])
            check: Whether to raise exception on non-zero exit code
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess object with command results

        Raises:
            GitError: If command fails and check=True
        """
        try:
            result = subprocess.run(
                args,
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                check=False,
            )
            if check and result.returncode != 0:
                raise GitError(
                    f"Git command failed: {' '.join(args)}\n"
                    f"Exit code: {result.returncode}\n"
                    f"stdout: {result.stdout}\n"
                    f"stderr: {result.stderr}"
                )
            return result
        except FileNotFoundError as e:
            raise GitError(f"Git executable not found: {e}")
        except Exception as e:
            raise GitError(f"Unexpected error running git command: {e}")

    def create_branch(self, branch_name: str, base_commit: str) -> None:
        """Create a new branch from a specified commit.

        This operation is idempotent - if the branch already exists and points
        to the correct commit, it succeeds silently. If it exists but points to
        a different commit, it raises GitError.

        Args:
            branch_name: Name of the branch to create
            base_commit: Commit SHA to create the branch from

        Raises:
            GitError: If branch creation fails or branch exists with different base
        """
        # Check if branch already exists
        result = self._run_git_command(
            ["git", "rev-parse", "--verify", branch_name], check=False
        )

        if result.returncode == 0:
            # Branch exists, verify it points to the correct commit
            existing_commit = result.stdout.strip()
            if existing_commit != base_commit:
                raise GitError(
                    f"Branch '{branch_name}' already exists but points to "
                    f"different commit: {existing_commit} != {base_commit}"
                )
            # Branch exists with correct commit, idempotent success
            return

        # Create the branch
        self._run_git_command(["git", "checkout", "-b", branch_name, base_commit])

    def push_branch(self, branch_name: str) -> None:
        """Push branch to remote with upstream tracking.

        This operation is idempotent - if the branch is already pushed and
        up-to-date, it succeeds silently.

        Args:
            branch_name: Name of the branch to push

        Raises:
            GitError: If push fails
        """
        self._run_git_command(["git", "push", "-u", "origin", branch_name])

    def branch_exists_remote(self, branch_name: str) -> bool:
        """Check if a branch exists on remote.

        Args:
            branch_name: Name of the branch to check

        Returns:
            True if branch exists on remote, False otherwise
        """
        result = self._run_git_command(
            ["git", "ls-remote", "--heads", "origin", branch_name], check=False
        )
        return bool(result.stdout.strip())

    def get_commits_between(self, base: str, head: str) -> List[str]:
        """Get list of commit SHAs between base and head.

        Args:
            base: Base commit SHA
            head: Head commit SHA

        Returns:
            List of commit SHAs from base to head (exclusive base, inclusive head)

        Raises:
            GitError: If commits are invalid or unreachable
        """
        result = self._run_git_command(["git", "rev-list", f"{base}..{head}"])
        commits = result.stdout.strip().split("\n")
        return [c for c in commits if c]  # Filter out empty strings

    def commit_exists(self, commit: str) -> bool:
        """Check if a commit exists in the repository.

        Args:
            commit: Commit SHA to check

        Returns:
            True if commit exists, False otherwise
        """
        result = self._run_git_command(
            ["git", "cat-file", "-t", commit], check=False
        )
        return result.returncode == 0 and result.stdout.strip() == "commit"

    def commit_on_branch(self, commit: str, branch: str) -> bool:
        """Check if a commit is an ancestor of a branch.

        Args:
            commit: Commit SHA to check
            branch: Branch name to check against

        Returns:
            True if commit is on branch (is ancestor), False otherwise
        """
        result = self._run_git_command(
            ["git", "merge-base", "--is-ancestor", commit, branch], check=False
        )
        return result.returncode == 0

    def find_most_recent_commit(self, commits: List[str]) -> str:
        """Find the most recent commit from a list of commit SHAs.

        Args:
            commits: List of commit SHAs

        Returns:
            SHA of the most recent commit

        Raises:
            GitError: If no commits provided or commits are invalid
        """
        if not commits:
            raise GitError("Cannot find most recent commit: empty commit list")

        # Use git log with --no-walk and --date-order to sort commits by date
        result = self._run_git_command(
            ["git", "log", "--no-walk", "--date-order", "--format=%H"] + commits
        )

        # First line is the most recent
        most_recent = result.stdout.strip().split("\n")[0]
        if not most_recent:
            raise GitError("Failed to find most recent commit")

        return most_recent

    def merge_branch(
        self, source: str, target: str, strategy: str, message: str
    ) -> str:
        """Merge source branch into target branch.

        Args:
            source: Source branch name
            target: Target branch name
            strategy: Merge strategy ("squash" or "no-ff")
            message: Commit message for merge

        Returns:
            SHA of the merge commit

        Raises:
            GitError: If merge fails or strategy is invalid
        """
        if strategy not in ("squash", "no-ff"):
            raise GitError(f"Invalid merge strategy: {strategy}. Use 'squash' or 'no-ff'")

        # Checkout target branch
        self._run_git_command(["git", "checkout", target])

        # Perform merge based on strategy
        if strategy == "squash":
            self._run_git_command(["git", "merge", "--squash", source])
            # Squash merge requires explicit commit
            self._run_git_command(["git", "commit", "-m", message])
        else:  # no-ff
            self._run_git_command(["git", "merge", "--no-ff", "-m", message, source])

        # Get the merge commit SHA
        result = self._run_git_command(["git", "rev-parse", "HEAD"])
        return result.stdout.strip()

    def delete_branch(self, branch_name: str, remote: bool = False) -> None:
        """Delete a branch locally or remotely.

        This operation is idempotent - if the branch doesn't exist, it succeeds
        silently.

        Args:
            branch_name: Name of the branch to delete
            remote: If True, delete from remote; if False, delete locally

        Raises:
            GitError: If deletion fails (except for non-existent branch)
        """
        if remote:
            # Delete remote branch
            result = self._run_git_command(
                ["git", "push", "origin", "--delete", branch_name], check=False
            )
            # Ignore error if branch doesn't exist on remote
            if result.returncode != 0 and "remote ref does not exist" not in result.stderr:
                raise GitError(
                    f"Failed to delete remote branch '{branch_name}': {result.stderr}"
                )
        else:
            # Delete local branch
            result = self._run_git_command(
                ["git", "branch", "-D", branch_name], check=False
            )
            # Ignore error if branch doesn't exist locally
            if result.returncode != 0 and "not found" not in result.stderr:
                raise GitError(
                    f"Failed to delete local branch '{branch_name}': {result.stderr}"
                )
