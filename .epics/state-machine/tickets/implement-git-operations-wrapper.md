# Implement Git Operations Wrapper

## Description
Create GitOperations class wrapping git commands with error handling

## Dependencies
None

## Acceptance Criteria
- [ ] GitOperations class with methods: create_branch, push_branch, delete_branch, get_commits_between, commit_exists, commit_on_branch, find_most_recent_commit, merge_branch
- [ ] All git operations use subprocess with proper error handling
- [ ] GitError exception class for git operation failures
- [ ] Methods return clean data (SHAs, branch names, commit info)
- [ ] Merge operations support squash strategy
- [ ] Git operations are in buildspec/epic/git_operations.py
- [ ] Unit tests for git operations with mock git commands

## Files to Modify
- /Users/kit/Code/buildspec/epic/git_operations.py
