# implement-git-operations-wrapper

## Description
Create GitOperations class wrapping git commands with error handling

## Epic Context
This ticket implements the git operations layer that enforces the epic's git strategy: stacked branches with final collapse. The GitOperations class provides a clean, tested interface for all git operations needed by the state machine.

**Git Strategy Summary**:
- Tickets execute synchronously (one at a time)
- Each ticket branches from previous ticket's final commit (true stacking)
- Epic branch stays at baseline during execution
- After all tickets complete, collapse all branches into epic branch (squash merge)
- Push epic branch to remote for human review

**Key Objectives**:
- Git Strategy Enforcement: Stacked branch creation, base commit calculation, and merge order handled by code
- Auditable Execution: State machine logs all transitions and gate checks for debugging

**Key Constraints**:
- Git operations (branch creation, base commit calculation, merging) are deterministic and tested
- Epic execution produces identical git structure on every run (given same tickets)
- Squash merge strategy for clean epic branch history

## Acceptance Criteria
- GitOperations class with methods: create_branch, push_branch, delete_branch, get_commits_between, commit_exists, commit_on_branch, find_most_recent_commit, merge_branch
- All git operations use subprocess with proper error handling
- GitError exception class for git operation failures
- Methods return clean data (SHAs, branch names, commit info)
- Merge operations support squash strategy
- Git operations are in buildspec/epic/git_operations.py
- Unit tests for git operations with mock git commands

## Dependencies
None

## Files to Modify
- /Users/kit/Code/buildspec/epic/git_operations.py

## Additional Notes
This class abstracts all git operations needed by the state machine. Key methods:

- create_branch: Creates a new branch from a specific base commit
- find_most_recent_commit: For tickets with multiple dependencies, finds the most recent commit via git log
- merge_branch: Squash merges a ticket branch into the epic branch
- commit_exists, commit_on_branch: Validation helpers for gates

All methods should raise GitError on failures with clear error messages. The wrapper should handle git's stderr output and parse it appropriately.
