# implement-remote-push-logic

## Description

Implement the push_epic_branch() function to push the epic branch to remote if a
git remote exists.

If a git remote exists, the epic branch should be pushed as the single
human-facing deliverable. This keeps ticket branches as implementation details
and presents one clean branch for review. The implementation is project-agnostic
with no assumptions about main branches or PR workflows.

## Epic Context

**Epic:** Orchestrator Coordination Strategy

This epic defines coordination patterns, state machine, git workflow,
communication protocols, and orchestration workflows for reliable epic execution
with multiple parallel sub-agents. Remote push makes the epic branch available
for human review while keeping ticket branches local.

**Architecture:** Project-agnostic push strategy. Checks for remote existence,
pushes epic branch only. Push failures mark epic as partial_success rather than
failed.

## Story

As a **buildspec orchestrator**, I need **remote push logic for epic branches**
so that **completed epic work is available on remote for human review, while
keeping the implementation project-agnostic and graceful with push failures**.

## Acceptance Criteria

### Core Requirements

- push_epic_branch() correctly detects presence of git remote
- Epic branch is pushed with upstream tracking if remote exists
- Push failures are handled gracefully without failing epic
- Epic-state.json records push status and results
- Function is project-agnostic (no main branch or PR assumptions)
- Execute-epic.md documents complete push algorithm

### Remote Detection

- Execute: `git remote -v`
- Parse output to detect if any remote exists
- If no remote: return false, log message, skip push
- If remote exists: proceed with push

### Push Execution

- Execute: `git push -u origin {epic_branch}`
- Set upstream tracking branch (`-u` flag)
- Capture push output for logging
- Verify push succeeded (check exit code)

### Push Failure Handling

- **Authentication failures:** Log error, mark epic as partial_success
- **Network failures:** Log error, mark epic as partial_success
- **Remote rejection:** Log error, include remote message
- Push failures do NOT fail the epic (work is complete locally)

### State Updates

- Record push attempt and result in epic-state.json
- Include remote URL if successful
- Include failure reason if failed
- Timestamp the push operation

## Integration Points

### Upstream Dependencies

- **define-git-workflow-strategy**: Defines remote push strategy
- **implement-ticket-branch-merging**: Provides merged epic branch to push

### Downstream Dependencies

- **add-wave-execution-algorithm**: Calls push_epic_branch() as final step

## Current vs New Flow

### BEFORE (Current State)

No remote push implementation. Unclear whether epic branch should be pushed.

### AFTER (This Ticket)

Execute-epic.md contains complete push_epic_branch() implementation with:

- Remote detection logic
- Push execution with upstream tracking
- Graceful failure handling (partial_success)
- State updates recording push results
- Project-agnostic design

## Technical Details

### File Modifications

**File:** `/Users/kit/Code/buildspec/claude_files/commands/execute-epic.md`

Add "Remote Push Logic" section:

````markdown
## Remote Push Logic

### push_epic_branch() Function

**Purpose:** Push epic branch to remote if remote exists.

**Input:** Epic branch name (e.g., "epic/user-authentication")

**Output:** Boolean (true if pushed, false if no remote or push failed)

**Design:** Project-agnostic (no assumptions about main branch, PR workflow, or
remote structure)

**Algorithm:**

```python
def push_epic_branch(state: EpicState) -> bool:
    """
    Push epic branch to remote if remote exists.

    Returns True if pushed successfully, False otherwise.

    Does NOT fail epic on push failure (marks partial_success instead).
    """
    epic_branch = state.epic_branch

    logger.info(f"Checking for git remote to push {epic_branch}...")

    # 1. Check if remote exists
    has_remote, remote_url = check_remote_exists()

    if not has_remote:
        logger.info("No git remote configured. Skipping push.")
        state.epic_pr_url = None
        update_epic_state(state, {})
        return False

    logger.info(f"Git remote found: {remote_url}. Pushing {epic_branch}...")

    # 2. Push epic branch with upstream tracking
    push_result = execute_push(epic_branch, remote_url)

    # 3. Update state with push result
    update_state_after_push(state, push_result)

    return push_result.success
```
````

### Check Remote Exists

**Purpose:** Detect if git remote is configured.

**Implementation:**

```python
def check_remote_exists() -> Tuple[bool, Optional[str]]:
    """
    Check if git remote exists.

    Returns:
        (has_remote, remote_url) tuple
    """
    result = subprocess.run(
        ['git', 'remote', '-v'],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        # No remote or git error
        logger.warning(f"git remote command failed: {result.stderr}")
        return (False, None)

    output = result.stdout.strip()

    if not output:
        # No remotes configured
        logger.info("No git remotes configured")
        return (False, None)

    # Parse remote URL (first remote, fetch URL)
    lines = output.split('\n')
    for line in lines:
        if '(fetch)' in line:
            parts = line.split()
            if len(parts) >= 2:
                remote_name = parts[0]  # Usually 'origin'
                remote_url = parts[1]
                logger.info(f"Found remote '{remote_name}': {remote_url}")
                return (True, remote_url)

    # Remote exists but couldn't parse
    return (True, "unknown")
```

### Execute Push

**Purpose:** Push epic branch to remote with upstream tracking.

**Implementation:**

```python
def execute_push(epic_branch: str, remote_url: str) -> PushResult:
    """
    Push epic branch to remote.

    Uses -u flag to set upstream tracking branch.

    Returns PushResult with success status and details.
    """
    # Attempt push with upstream tracking
    result = subprocess.run(
        ['git', 'push', '-u', 'origin', epic_branch],
        capture_output=True,
        text=True,
        timeout=60  # 60 second timeout for network operations
    )

    if result.returncode == 0:
        # Push succeeded
        logger.info(f"Successfully pushed {epic_branch} to remote")
        logger.debug(f"Push output: {result.stdout}")

        return PushResult(
            success=True,
            remote_url=remote_url,
            branch=epic_branch,
            error=None
        )

    else:
        # Push failed
        error_msg = result.stderr.strip()
        logger.error(f"Push failed for {epic_branch}: {error_msg}")

        # Categorize failure
        failure_type = categorize_push_failure(error_msg)

        return PushResult(
            success=False,
            remote_url=remote_url,
            branch=epic_branch,
            error=error_msg,
            failure_type=failure_type
        )
```

### Categorize Push Failure

**Purpose:** Identify type of push failure for better error messages.

**Implementation:**

```python
def categorize_push_failure(error_msg: str) -> str:
    """
    Categorize push failure based on error message.

    Returns failure type: 'authentication', 'network', 'rejected', 'unknown'
    """
    error_lower = error_msg.lower()

    # Authentication failures
    if any(keyword in error_lower for keyword in [
        'authentication', 'permission denied', 'could not read',
        'invalid credentials', 'access denied'
    ]):
        return 'authentication'

    # Network failures
    if any(keyword in error_lower for keyword in [
        'could not resolve host', 'connection refused', 'network',
        'timeout', 'failed to connect'
    ]):
        return 'network'

    # Remote rejection (e.g., protected branch, force push required)
    if any(keyword in error_lower for keyword in [
        'rejected', 'protected branch', 'non-fast-forward',
        'updates were rejected'
    ]):
        return 'rejected'

    return 'unknown'
```

### Update State After Push

**Purpose:** Record push result in epic-state.json.

**Implementation:**

```python
def update_state_after_push(state: EpicState, push_result: PushResult):
    """
    Update epic state with push result.

    If push succeeded: record remote URL
    If push failed: mark epic as partial_success
    """
    push_timestamp = datetime.now(UTC).isoformat()

    if push_result.success:
        # Push succeeded
        state.epic_pr_url = None  # No PR created (project-agnostic)
        state.push_status = 'pushed'
        state.push_timestamp = push_timestamp
        state.remote_url = push_result.remote_url

        logger.info(f"Epic branch pushed successfully at {push_timestamp}")

    else:
        # Push failed (mark partial_success)
        state.status = 'partial_success'
        state.failure_reason = f'push_failed_{push_result.failure_type}: {push_result.error}'
        state.push_status = 'failed'
        state.push_timestamp = push_timestamp

        logger.warning(
            f"Epic marked as partial_success due to push failure. "
            f"All tickets completed locally, but epic branch not pushed to remote."
        )

    update_epic_state(state, {})
```

### Push Examples

**Example 1: Successful Push**

```python
# Remote exists, push succeeds
has_remote = True
push_result = execute_push('epic/user-auth', 'git@github.com:user/repo.git')
# push_result.success = True

# State updates:
# state.epic_pr_url = None
# state.push_status = 'pushed'
# state.status = 'completed'

# Output: "Successfully pushed epic/user-auth to remote"
```

**Example 2: No Remote**

```python
# No remote configured
has_remote = False

push_epic_branch(state)
# Returns: False

# State updates:
# state.epic_pr_url = None
# state.push_status = 'skipped'
# state.status = 'completed'

# Output: "No git remote configured. Skipping push."
```

**Example 3: Authentication Failure**

```python
# Remote exists, push fails (authentication)
has_remote = True
push_result = execute_push('epic/user-auth', 'git@github.com:user/repo.git')
# push_result.success = False
# push_result.failure_type = 'authentication'
# push_result.error = "Permission denied (publickey)"

# State updates:
# state.status = 'partial_success'
# state.failure_reason = 'push_failed_authentication: Permission denied (publickey)'
# state.push_status = 'failed'

# Output: "Push failed: authentication error. Epic marked as partial_success."
```

**Example 4: Network Failure**

```python
# Remote exists, push fails (network)
push_result.failure_type = 'network'
push_result.error = "Could not resolve host: github.com"

# State updates:
# state.status = 'partial_success'
# state.failure_reason = 'push_failed_network: Could not resolve host'
# state.push_status = 'failed'

# Output: "Push failed: network error. All work completed locally."
```

### Project-Agnostic Design

**No PR Creation:**

- Function does NOT create pull requests
- No assumptions about GitHub, GitLab, Bitbucket
- No assumptions about main/master branch
- Epic branch on remote is the deliverable (humans create PR if needed)

**No Main Branch Assumptions:**

- Does NOT merge epic branch into main
- Does NOT push to main branch
- Does NOT assume main branch exists or is named 'main'/'master'

**Graceful Degradation:**

- If no remote: epic completes successfully (work done locally)
- If push fails: epic marked partial_success (work preserved locally)
- Never fail epic due to push issues (push is optional final step)

````

### Implementation Details

1. **Add Remote Push Section:** Insert after Ticket Branch Merging in execute-epic.md

2. **Document push_epic_branch():** Complete implementation with all steps

3. **Remote Detection:** Full logic for checking remote existence

4. **Push Execution:** Command with upstream tracking and timeout

5. **Failure Categorization:** Identify authentication, network, rejection failures

6. **State Updates:** Record push results in epic-state.json

7. **Examples:** Success, no remote, authentication failure, network failure

### Integration with Existing Code

Remote push logic integrates with:
- Epic-state.json for recording push results
- Git repository for remote detection and push
- Merge workflow providing epic branch to push
- Wave execution calling as final step

## Error Handling Strategy

- **No Remote:** Not an error, return false and complete epic
- **Authentication Failure:** Mark partial_success, log error, preserve local work
- **Network Failure:** Mark partial_success, log error, preserve local work
- **Remote Rejection:** Mark partial_success, log error with remote message
- **Unknown Failure:** Mark partial_success, log full error details

## Testing Strategy

### Validation Tests

1. **Remote Detection:**
   - Test with remote configured
   - Test with no remote
   - Test with multiple remotes

2. **Push Execution:**
   - Test successful push
   - Test push with upstream tracking set
   - Test push timeout handling

3. **Failure Handling:**
   - Test authentication failure
   - Test network failure
   - Test remote rejection
   - Test unknown failure

4. **State Updates:**
   - Test state after successful push
   - Test state after push failure
   - Test partial_success marking

### Test Commands

```bash
# Run remote push tests
uv run pytest tests/integration/test_remote_push.py -v

# Test remote detection
uv run pytest tests/unit/test_remote_push.py::test_check_remote_exists -v

# Test push execution
uv run pytest tests/integration/test_remote_push.py::test_execute_push -v

# Test failure handling
uv run pytest tests/integration/test_remote_push.py::test_push_failures -v
````

## Dependencies

- **define-git-workflow-strategy**: Defines remote push strategy
- **implement-ticket-branch-merging**: Provides merged epic branch

## Coordination Role

Provides remote push capability for presenting epic branch to humans. Completes
the epic workflow by making work available on remote while maintaining
project-agnostic design and graceful failure handling.
