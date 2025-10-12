# GitOperations wrapper for git subprocess commands

**Ticket ID:** create-git-operations

**Critical:** true

**Dependencies:** None

**Coordination Role:** Provides git operations to state machine and validation gates

## Description

As a state machine developer, I want a GitOperations wrapper that encapsulates all git subprocess commands so that git logic is isolated, testable, and reusable across the state machine and validation gates.

This ticket creates git_operations.py with the GitOperations class that wraps subprocess git commands for branch management, merging, and validation. The state machine (ticket: core-state-machine) calls these methods for branch operations during ticket execution, and validation gates (tickets: implement-branch-creation-gate, implement-validation-gate) call these for git validation checks. All operations must be idempotent to support retries and resumption. Key functions to implement:
- create_branch(branch_name: str, base_commit: str): Creates git branch from specified commit using subprocess "git checkout -b {branch} {commit}"
- push_branch(branch_name: str): Pushes branch to remote using "git push -u origin {branch}"
- branch_exists_remote(branch_name: str) -> bool: Checks if branch exists on remote via "git ls-remote --heads origin {branch}"
- get_commits_between(base: str, head: str) -> List[str]: Gets commit SHAs via "git rev-list {base}..{head}"
- commit_exists(commit: str) -> bool: Validates commit SHA via "git cat-file -t {commit}"
- commit_on_branch(commit: str, branch: str) -> bool: Checks commit ancestry via "git merge-base --is-ancestor {commit} {branch}"
- find_most_recent_commit(commits: List[str]) -> str: Finds newest via "git log --no-walk --date-order --format=%H" on commit list
- merge_branch(source: str, target: str, strategy: str, message: str) -> str: Merges with "git merge --squash" or "git merge --no-ff", returns merge commit SHA from "git rev-parse HEAD"
- delete_branch(branch_name: str, remote: bool): Deletes via "git branch -D {branch}" or "git push origin --delete {branch}"

## Acceptance Criteria

- All git operations implemented using subprocess with proper error handling
- Operations are idempotent (safe to call multiple times)
- GitError exception raised with clear messages for git failures
- All operations validated against real git repository in tests
- Subprocess calls use list-form arguments (no shell=True)

## Testing

Unit tests with mocked subprocess.run for each operation to verify correct git commands and error handling. Integration tests with real git repository to verify operations work end-to-end. Coverage: 90% minimum.

## Non-Goals

No async operations, no git object parsing, no direct libgit2 bindings, no worktree support, no git hooks - only subprocess-based plumbing commands.
