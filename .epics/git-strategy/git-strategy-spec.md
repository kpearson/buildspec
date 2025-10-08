# Git Strategy Standardization Spec

## Overview

Standardize git operations in epic/ticket execution by implementing a scripted
git strategy layer. This removes ambiguity from LLM-driven git operations while
preserving flexibility where needed.

## Problem Statement

Current git strategy is entirely LLM-driven through prompt instructions. This
leads to:

- **Inconsistent commit messages** - Session IDs suggested but not enforced
- **Branch naming variations** - LLMs may interpret ticket names differently
- **Manual PR creation errors** - Complex gh CLI commands in prompts
- **No branch cleanup** - Merged ticket branches accumulate
- **Unclear merge strategy** - No defined approach for epic → main merges
- **Git operation failures** - LLMs make git mistakes (wrong base commits, push
  errors)

## Goals

1. **Enforce consistency** in branch naming, commit format, PR creation
2. **Reduce LLM error surface** by scripting complex git operations
3. **Maintain flexibility** in commit frequency and descriptive content
4. **Enable traceability** with mandatory session IDs and structured metadata
5. **Automate cleanup** of merged branches

## Non-Goals

- Changing the epic branch model (stacked tickets remain)
- Removing LLM autonomy in deciding when to commit
- Adding git hooks or pre-commit checks
- Implementing custom git workflows beyond epic/ticket model

## Solution: Git Strategy Script Layer

Create `~/.claude/scripts/epic-git.sh` with standardized functions that:

- Enforce naming conventions
- Structure commit metadata
- Handle PR creation
- Manage branch lifecycle

### Script Functions

#### 1. `create_epic_branch()`

**Purpose:** Create epic branch from main and push to remote

**Usage:**

```bash
source ~/.claude/scripts/epic-git.sh
create_epic_branch "user-authentication" "feat/add-user-auth"
```

**Parameters:**

- `epic_name` - Epic identifier (kebab-case)
- `description` - Brief epic description for PR

**Behavior:**

- Validates on `main` branch
- Creates `epic/{epic_name}` branch
- Pushes to origin with `-u` flag
- Creates draft PR: `epic/{epic_name} → main`
- Returns epic branch name and PR URL

**Output:**

```json
{
  "branch": "epic/user-authentication",
  "pr_url": "https://github.com/org/repo/pull/123",
  "base_commit": "abc123def"
}
```

#### 2. `create_ticket_branch()`

**Purpose:** Create ticket branch from specified base commit

**Usage:**

```bash
create_ticket_branch "auth-base-models" "abc123def" "epic/user-authentication"
```

**Parameters:**

- `ticket_id` - Exact ticket ID from epic YAML
- `base_commit` - SHA to branch from (epic baseline or dependency commit)
- `epic_branch` - Epic branch name (for validation)

**Behavior:**

- Validates base commit exists
- Creates `ticket/{ticket_id}` branch from base commit
- Does NOT push (ticket work happens before push)
- Returns branch name and base commit

**Output:**

```json
{
  "branch": "ticket/auth-base-models",
  "base_commit": "abc123def"
}
```

#### 3. `commit_ticket_work()`

**Purpose:** Commit ticket work with enforced metadata

**Usage:**

```bash
commit_ticket_work "Add user authentication models" "auth-base-models" "session-uuid-here"
```

**Parameters:**

- `message` - Commit message (LLM-provided, descriptive)
- `ticket_id` - Ticket identifier
- `session_id` - Session UUID for traceability

**Behavior:**

- Stages all changes (`git add -A`)
- Creates commit with structured message:

  ```
  [ticket-id] message

  ticket_id: auth-base-models
  session_id: uuid-here
  ```

- Returns commit SHA

**Output:**

```json
{
  "commit_sha": "def456abc",
  "branch": "ticket/auth-base-models"
}
```

#### 4. `create_ticket_pr()`

**Purpose:** Create numbered PR for ticket targeting epic branch

**Usage:**

```bash
create_ticket_pr "ticket/auth-base-models" "epic/user-authentication" "1" "Add base authentication models"
```

**Parameters:**

- `ticket_branch` - Ticket branch name
- `epic_branch` - Epic branch to target
- `sequence` - PR number in merge order (from topological sort)
- `title` - PR title (without number prefix)

**Behavior:**

- Pushes ticket branch to origin
- Creates PR: `ticket/name → epic/name`
- Title format: `[{sequence}] {title}`
- Adds body with ticket metadata
- Returns PR URL

**Output:**

```json
{
  "pr_url": "https://github.com/org/repo/pull/124",
  "number": 124,
  "title": "[1] Add base authentication models"
}
```

#### 5. `finalize_epic_pr()`

**Purpose:** Update epic PR from draft to ready with summary

**Usage:**

```bash
finalize_epic_pr "epic/user-authentication" "summary text" "pr-url-1,pr-url-2,pr-url-3"
```

**Parameters:**

- `epic_branch` - Epic branch name
- `summary` - Epic summary (LLM-generated)
- `ticket_pr_urls` - Comma-separated ticket PR URLs in merge order

**Behavior:**

- Commits artifacts to epic branch
- Pushes epic branch
- Updates PR from draft to ready
- Updates PR body with:
  - Epic summary
  - Ticket PRs in merge order
  - Merge instructions
- Returns updated PR URL

#### 6. `cleanup_merged_branch()`

**Purpose:** Delete ticket branch after successful merge

**Usage:**

```bash
cleanup_merged_branch "ticket/auth-base-models"
```

**Parameters:**

- `branch_name` - Branch to delete

**Behavior:**

- Verifies branch is merged to epic branch
- Deletes local branch
- Deletes remote branch
- Returns confirmation

### Integration with Commands

#### execute-epic Command Changes

**Current:** LLM receives prompt with git instructions **New:** LLM calls git
strategy functions

```markdown
2. Initialize epic branch and state tracking:
   - Source git strategy: source ~/.claude/scripts/epic-git.sh
   - Create epic branch: result=$(create_epic_branch "{epic_name}"
     "{description}")
   - Extract epic branch, PR URL, baseline commit from result JSON
   - Record in epic-state.json
```

**Advantages:**

- Consistent branch naming
- Automatic PR creation
- No gh CLI syntax errors
- Validated git operations

#### execute-ticket Command Changes

**Current:** LLM creates branch, commits, with flexible approach **New:** LLM
uses scripted functions for structure, flexibility for content

```markdown
2. Set up git environment:
   - Source git strategy: source ~/.claude/scripts/epic-git.sh
   - Create ticket branch: result=$(create_ticket_branch "{ticket_id}"
     "{base_commit}" "{epic_branch}")
3. Commit all changes:
   - Commit work: result=$(commit_ticket_work "{descriptive message}"
     "{ticket_id}" "{session_id}")
   - Record final commit SHA from result JSON
```

### Commit Message Format

**Enforced structure:**

```
[ticket-id] Short descriptive message (LLM writes this)

Long description of changes if needed (LLM writes this)
Can be multiple paragraphs.

ticket_id: exact-ticket-id
session_id: uuid-session-id
epic_id: epic-name
```

**Benefits:**

- Machine-parseable metadata
- Human-readable descriptions
- Traceability to sessions
- Searchable by ticket/epic

### Branch Naming Convention

**Epic branches:**

```
epic/{epic-name}
```

Example: `epic/user-authentication`

**Ticket branches:**

```
ticket/{ticket-id}
```

Example: `ticket/auth-base-models`

**Enforced by script** - No LLM variation possible

### PR Creation Strategy

**Ticket PRs:**

- Created after ticket completion
- Title: `[{sequence}] {descriptive title}`
- Target: Epic branch
- Body includes:
  - Ticket file link
  - Base commit
  - Final commit
  - Session ID
  - Acceptance criteria checklist

**Epic PR:**

- Created at epic start (draft)
- Updated at epic completion (ready)
- Title: `{Epic Name}`
- Body includes:
  - Epic summary
  - Ticket PRs in merge order with instructions
  - Artifacts summary

### Branch Cleanup Strategy

**When:** After ticket PR is merged to epic branch **How:**
`cleanup_merged_branch()` called by orchestrator **Scope:** Both local and
remote branches deleted

**Epic branch cleanup:**

- After epic PR merged to main
- Delete epic branch local and remote
- Ticket branches already cleaned up

## Implementation Plan

### Phase 1: Create Git Strategy Script

**Deliverables:**

- `~/.claude/scripts/epic-git.sh` with all 6 functions
- JSON output format for programmatic parsing
- Error handling and validation
- Unit tests for git functions

### Phase 2: Update Command Prompts

**Deliverables:**

- Updated `execute-epic.md` with function calls
- Updated `execute-ticket.md` with function calls
- Updated `create-epic.md` with function calls

### Phase 3: Update Python Commands

**Deliverables:**

- Install script copies `epic-git.sh` to `~/.claude/scripts/`
- Validation that script exists before execution
- Error messages if script missing

## Testing Strategy

**Unit Tests:**

- Test each git function in isolation
- Mock git commands
- Validate JSON output format
- Test error conditions

**Integration Tests:**

- Full epic execution with git strategy
- Verify branch creation
- Verify PR creation
- Verify commit format
- Verify cleanup

**Fixtures:**

- Sample epic YAML files
- Mock git repositories
- Mock gh CLI responses

## Success Criteria

1. ✅ All epic executions use consistent branch naming
2. ✅ All commits include session_id and ticket_id
3. ✅ All PRs follow numbering convention
4. ✅ Merged branches are automatically cleaned up
5. ✅ Git errors reduced by >80% (measured by epic execution logs)
6. ✅ LLMs can parse git function output reliably

## Risks & Mitigations

**Risk:** Script errors break epic execution **Mitigation:** Comprehensive error
handling, exit codes, validation

**Risk:** LLMs ignore script functions and use raw git **Mitigation:** Strong
prompt language, validation in orchestrator

**Risk:** JSON parsing failures **Mitigation:** Strict JSON schema, jq
validation in script

**Risk:** gh CLI version incompatibility **Mitigation:** Version check in
script, clear error messages

## Future Enhancements

- Git hook integration for commit message validation
- Automatic rebase of epic branch on main
- Conflict detection and resolution guidance
- Branch protection rule suggestions
- Merge strategy options (squash vs merge commit)

## Dependencies

- `git` >= 2.30
- `gh` CLI >= 2.0
- `jq` >= 1.6 (for JSON output)
- Bash >= 4.0

## Open Questions

1. **Merge strategy for epic → main:** Squash all or preserve commits?
   - **Recommendation:** Merge commit (preserves ticket commits for history)

2. **Concurrent epic executions:** Multiple epics in parallel?
   - **Recommendation:** Supported - epics isolated by branch

3. **Failed ticket cleanup:** Delete branch on failure or keep for debugging?
   - **Recommendation:** Keep on failure, manual cleanup

4. **Session ID format:** UUID4 or timestamp-based?
   - **Current:** UUID4 (already implemented)

## Acceptance Criteria

- [ ] `epic-git.sh` script implements all 6 functions
- [ ] All functions output valid JSON
- [ ] All functions validate inputs and return error codes
- [ ] Command prompts updated to use script functions
- [ ] Install script deploys git strategy script
- [ ] Integration tests pass with script
- [ ] Documentation updated with git strategy
- [ ] Existing epics can be executed with new strategy

## Definition of Done

- Script written and tested
- Commands updated to use script
- Tests passing (unit + integration)
- Documentation complete
- Deployed via install script
- Successfully executed test epic with new strategy
