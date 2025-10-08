# Buildspec CLI Test Checklist

Comprehensive test plan to verify buildspec CLI functionality and behavior.

## Test Categories

### 1. Installation & Setup Tests

#### 1.1 Fresh Installation
- [ ] Clone repo to `~/tools/buildspec` or custom location
- [ ] Run `make install` from repo directory
- [ ] Verify `buildspec` command available in PATH
- [ ] Check symlinks created in `~/.claude/`
  - [ ] `~/.claude/agents/*.md` exist
  - [ ] `~/.claude/commands/*.md` exist
  - [ ] `~/.claude/scripts/*.sh` exist and executable
  - [ ] `~/.claude/hooks/*.sh` exist and executable
  - [ ] `~/.claude/mcp-servers/*.py` exist and executable
- [ ] Run `buildspec --help` → shows all commands
- [ ] Run `make test` → confirms installation

#### 1.2 Configuration Initialization
- [ ] Run `buildspec init` → creates `~/.config/buildspec/config.toml`
- [ ] Run `buildspec init --show` → displays default config without creating
- [ ] Run `buildspec init` when config exists → error with helpful message
- [ ] Run `buildspec init --force` → overwrites existing config
- [ ] Verify XDG directories created:
  - [ ] `~/.config/buildspec/`
  - [ ] `~/.config/buildspec/templates/`
  - [ ] `~/.local/state/buildspec/`
  - [ ] `~/.cache/buildspec/`

#### 1.3 Uninstallation
- [ ] Run `make uninstall`
- [ ] Verify `buildspec` command removed
- [ ] Verify symlinks removed from `~/.claude/`
- [ ] Config files remain (manual cleanup)

#### 1.4 Reinstallation
- [ ] Run `make reinstall`
- [ ] Verify complete uninstall + install cycle
- [ ] All functionality works after reinstall

---

### 2. Context Detection Tests

#### 2.1 Project Root Detection
- [ ] **Test from project root** (contains `.git/`)
  - Run `buildspec --help` → detects correct project root
- [ ] **Test from subdirectory** (e.g., `src/components/`)
  - Run `buildspec create-epic ../../planning/spec.md` → works correctly
- [ ] **Test from non-git directory**
  - Falls back to cwd as project root
- [ ] **Test with local `.claude/` directory**
  - Prefers local over global `~/.claude/`

#### 2.2 Path Resolution
- [ ] **Absolute paths**: `buildspec create-epic /full/path/to/spec.md`
- [ ] **Relative paths**: `buildspec create-epic planning/spec.md`
- [ ] **Paths with spaces**: `buildspec create-epic "planning docs/my spec.md"`
- [ ] **Paths from different directories**:
  ```bash
  cd ~/Code/project/src
  buildspec create-epic ../planning/spec.md
  ```

---

### 3. Create Epic Tests

#### 3.1 Basic Epic Creation (CLI)
- [ ] **Minimal input**: `buildspec create-epic planning/feature-spec.md`
  - Input: Planning doc with Related Issues section
  - Output: `planning/feature.epic.yaml` in same directory
  - Verify: Epic YAML structure valid
  - Verify: Coordination requirements extracted
  - Verify: Tickets with dependencies
- [ ] **Custom output path**: `buildspec create-epic planning/spec.md -o epics/custom.epic.yaml`
  - Output: Epic at specified location
- [ ] **Project directory override**: `buildspec create-epic spec.md -p ~/Code/other-project`
  - Context detected from specified directory


#### 3.3 Epic Content Validation
- [ ] **Required fields present**:
  - [ ] `epic:` name
  - [ ] `description:`
  - [ ] `acceptance_criteria:` list
  - [ ] `rollback_on_failure:`
  - [ ] `coordination_requirements:` section
  - [ ] `tickets:` list
- [ ] **Coordination requirements extracted**:
  - [ ] `function_profiles` with arity and intent
  - [ ] `directory_structure` with paths
  - [ ] `integration_contracts` for each ticket
  - [ ] `architectural_decisions` when present
  - [ ] `breaking_changes_prohibited` when specified
- [ ] **Ticket structure valid**:
  - [ ] Each ticket has `id`, `description`, `depends_on`, `critical`
  - [ ] Inline descriptions (not separate files)
  - [ ] `coordination_role` specified

#### 3.4 Dependency Graph
- [ ] **No dependencies**: Tickets can run in parallel
- [ ] **Linear dependencies**: Sequential execution order
- [ ] **Diamond dependencies**: Complex graph handled correctly
- [ ] **No circular dependencies**: Validation catches cycles

#### 3.5 Epic Creation Edge Cases
- [ ] **Planning doc missing**: Error with helpful message
- [ ] **Planning doc not .md**: Error about file extension
- [ ] **Epic file already exists**: Warning or error
- [ ] **Planning doc with no Related Issues section**: Handles gracefully
- [ ] **Planning doc with line numbers** (e.g., `spec.md:38`): Strips line numbers
- [ ] **Empty planning doc**: Error or minimal epic

#### 3.6 Filtering Implementation Noise
- [ ] **Brainstorming text filtered out**: "we could", "maybe" statements
- [ ] **Pseudo-code removed**: Only coordination essentials remain
- [ ] **Planning discussions excluded**: Focus on decisions, not discussions
- [ ] **Coordination essentials retained**: Function signatures, interfaces preserved

---

### 4. Create Tickets Tests

#### 4.1 Basic Ticket Creation (CLI)
- [ ] **From epic**: `buildspec create-tickets planning/feature.epic.yaml`
  - Input: Epic YAML with tickets
  - Output: Individual `.md` files for each ticket
  - Default location: `tickets/` directory relative to epic
- [ ] **Custom output dir**: `buildspec create-tickets epic.yaml -d custom-tickets/`
  - Output: Tickets in specified directory
- [ ] **Project directory override**: `buildspec create-tickets epic.yaml -p ~/other-project`


#### 4.3 Ticket Content Validation
- [ ] **All tickets created**: One file per ticket in epic
- [ ] **Ticket structure**: Follows planning-ticket-template format
  - [ ] Issue Summary
  - [ ] Story (As a/I want/So that)
  - [ ] Acceptance Criteria
  - [ ] Technical Details
  - [ ] Implementation Details
  - [ ] Testing Strategy
  - [ ] Definition of Done
- [ ] **Epic context included**: Each ticket references epic goals
- [ ] **Dependencies documented**: Upstream/downstream tickets listed
- [ ] **No placeholders**: All `[COMPONENT]`, `xtest` patterns replaced
- [ ] **Project-specific details**: Actual framework names, commands, paths

#### 4.4 Ticket Creation Edge Cases
- [ ] **Epic file missing**: Error with helpful message
- [ ] **Epic file not YAML**: Error about format
- [ ] **Malformed epic YAML**: Validation error
- [ ] **Output directory doesn't exist**: Creates directory
- [ ] **Output directory not writable**: Permission error
- [ ] **Ticket file already exists**: Overwrite or skip?

---

### 5. Execute Ticket Tests

#### 5.1 Basic Ticket Execution (CLI)
- [ ] **Single ticket**: `buildspec execute-ticket tickets/auth-base.md`
  - Pre-flight: Runs full test suite
  - Creates branch: `ticket/auth-base`
  - Implements changes
  - Runs tests
  - Commits work
  - Reports: base commit, branch name, final commit
- [ ] **With epic context**: `buildspec execute-ticket tickets/auth-base.md -e planning/auth.epic.yaml`
  - Reads epic for coordination context
- [ ] **With base commit**: `buildspec execute-ticket tickets/auth-api.md -b abc123`
  - Creates branch from specified commit
- [ ] **All options**: `buildspec execute-ticket tickets/ui.md -e epic.yaml -b def456 -p ~/project`


#### 5.3 Pre-flight Validation
- [ ] **All tests passing**: Ticket proceeds normally
- [ ] **Tests failing**: Ticket blocked immediately
  - Status: "blocked - pre-flight test failures"
  - Lists failing tests
  - Shows error messages
  - Does not proceed

#### 5.4 Ticket Execution Workflow
- [ ] **Git branch created**: Correct naming convention
- [ ] **Base commit recorded**: For dependency tracking
- [ ] **All file modifications**: As specified in ticket
- [ ] **Tests created/updated**: Following Testing Strategy
- [ ] **Full test suite runs**: After implementation
- [ ] **All tests pass**: Before completion
- [ ] **Work committed**: To ticket branch
- [ ] **Final commit SHA recorded**: For reporting

#### 5.5 Ticket Execution Report
- [ ] **Ticket identification**: ID and summary
- [ ] **Changes summary**: What was done
- [ ] **Files modified**: With line counts
- [ ] **Tests created/updated**: List of test files
- [ ] **Acceptance criteria**: ✓/✗ for each
- [ ] **Test suite status**: All passing
- [ ] **Git information**:
  - [ ] Base commit SHA
  - [ ] Branch name
  - [ ] Final commit SHA
- [ ] **Status**: "completed"

#### 5.6 Ticket Execution Edge Cases
- [ ] **Ticket file missing**: Error
- [ ] **Ticket file not .md**: Error
- [ ] **Malformed ticket**: Validation error
- [ ] **Epic file specified but missing**: Error
- [ ] **Base commit doesn't exist**: Git error
- [ ] **Tests fail after implementation**: Ticket not marked complete
- [ ] **File modification blocked**: Permission error
- [ ] **Merge conflicts**: Reported to user

---

### 6. Execute Epic Tests

#### 6.1 Basic Epic Execution (CLI)
- [ ] **Simple sequential epic**: `buildspec execute-epic planning/feature.epic.yaml`
  - Pre-flight validation
  - Creates epic branch
  - Creates artifacts directory
  - Initializes epic-state.json
  - Executes tickets sequentially
  - Creates PRs
  - Reports completion
- [ ] **Parallel execution enabled**: Default behavior
  - Tickets with no dependencies run in parallel
- [ ] **Sequential execution**: `buildspec execute-epic epic.yaml -s` or `--no-parallel`
  - One ticket at a time
- [ ] **Dry run**: `buildspec execute-epic epic.yaml -n` or `--dry-run`
  - Shows execution plan
  - Does not execute tickets


#### 6.3 Epic Branch Strategy
- [ ] **Epic branch created**: `epic/<epic-name>` from main
- [ ] **Epic branch pushed**: To remote
- [ ] **Epic PR created**: Draft status initially
- [ ] **Baseline commit recorded**: Epic branch HEAD SHA
- [ ] **Tickets branch from baseline**: For no dependencies
- [ ] **Tickets branch from final commit**: For dependent tickets
- [ ] **Stacked branches**: Correct dependency chain

#### 6.4 State Management
- [ ] **artifacts/ directory created**: Alongside epic file
- [ ] **epic-state.json created**: With initial structure
- [ ] **State updated after each ticket**: Git info, status, timestamps
- [ ] **Ticket artifacts created**: `artifacts/tickets/<id>-<sha>.md`
- [ ] **State persisted**: Survives interruptions
- [ ] **Resume capability**: Can continue from partial state

#### 6.5 Parallel Execution
- [ ] **Independent tickets start together**: No dependencies
- [ ] **Multiple Task agents spawned**: Simultaneous execution
- [ ] **Dependencies respected**: Tickets wait for prerequisites
- [ ] **Execution phases tracked**: not-started → completed
- [ ] **Diamond dependencies**: Correct synchronization
  ```
  Phase 1: A
  Phase 2: B, C (both depend on A, run in parallel)
  Phase 3: D (depends on B and C, waits for both)
  ```

#### 6.6 Critical vs Non-Critical Tickets
- [ ] **Critical ticket fails**: Epic stops immediately
- [ ] **Non-critical ticket fails**: Epic continues
- [ ] **Dependent tickets skip**: If prerequisite fails
- [ ] **Final status**: Success/partial/failed

#### 6.7 PR Creation
- [ ] **Epic PR**: `epic/name → main` (draft initially)
- [ ] **Ticket PRs numbered**: `[1] Title`, `[2] Title`
- [ ] **PR targets epic branch**: Not main
- [ ] **Sequential merge order**: Based on dependency graph
- [ ] **Epic PR updated**: To ready for review at end
- [ ] **PR descriptions**: Include ticket summary

#### 6.8 Artifacts Finalization
- [ ] **All artifacts committed**: To epic branch
- [ ] **Commit message**: "Add artifacts for <epic-name>"
- [ ] **Artifacts pushed**: With epic branch
- [ ] **Artifacts include**:
  - [ ] epic-state.json
  - [ ] tickets/*.md (one per ticket)

#### 6.9 Epic Execution Report
- [ ] **Epic summary**: Success/partial/failed
- [ ] **Execution timeline**: Parallel execution visualization
- [ ] **Ticket statuses**: ✅/❌/⏭️ for each
- [ ] **Acceptance criteria**: Checklist
- [ ] **Total execution time**: Duration
- [ ] **Recommendations**: Follow-up actions
- [ ] **PR URLs**: Epic and ticket PRs

#### 6.10 Epic Execution Edge Cases
- [ ] **Epic file missing**: Error
- [ ] **Epic file not YAML**: Error
- [ ] **Malformed epic**: Validation error
- [ ] **Circular dependencies**: Detected and reported
- [ ] **Missing ticket files**: Error before execution
- [ ] **Git not clean**: Warning
- [ ] **Epic branch exists**: Error or continue?
- [ ] **Interrupted execution**: State allows resume
- [ ] **All critical tickets fail**: Epic marked failed
- [ ] **Test suite fails**: Epic stops

---

### 7. Validation Tests

#### 7.1 Pre-flight Validation Script
- [ ] **Run directly**: `~/.claude/scripts/validate-epic.sh epic.yaml`
  - Validates epic format
  - Checks ticket files exist
  - Validates git state
  - Checks branch conflicts
  - Validates workspace
- [ ] **With ticket**: `~/.claude/scripts/validate-epic.sh epic.yaml --ticket ticket.md`
  - Additionally validates ticket format
- [ ] **All checks pass**: Exit 0
- [ ] **Any check fails**: Exit 1 with error details

#### 7.2 Epic Path Extraction
- [ ] **Run directly**: `~/.claude/scripts/epic-paths.sh planning/spec.md`
  - Outputs: TARGET_DIR, BASE_NAME, EPIC_FILE
  - Outputs: SPEC_EXISTS, EPIC_EXISTS
- [ ] **With line numbers**: `~/.claude/scripts/epic-paths.sh spec.md:38`
  - Strips line numbers correctly

#### 7.3 Epic Creation Hook
- [ ] **Valid planning doc**: Hook passes, allows Task agent
- [ ] **Missing planning doc**: Hook fails, blocks agent
- [ ] **Epic already exists**: Hook fails, blocks agent
- [ ] **Non-epic task**: Hook fast-exits immediately

#### 7.4 MCP Validation Tool
- [ ] **Tool available**: Listed in MCP tools
- [ ] **Valid input**: Returns validation success
- [ ] **Invalid input**: Returns validation failure
- [ ] **Helpful messages**: Clear error explanations

---

### 8. Configuration Tests

#### 8.1 Config File Loading
- [ ] **Default config**: Works without config file
- [ ] **Custom config**: Reads from `~/.config/buildspec/config.toml`
- [ ] **Dot notation**: `config.get('claude.cli_command')`
- [ ] **Missing keys**: Returns default value
- [ ] **Invalid TOML**: Error with helpful message

#### 8.2 Config Options
- [ ] **Claude CLI command**: Override `claude` with custom path
- [ ] **CLI flags**: Additional flags for Claude
- [ ] **Epic extension**: Custom `.epic.yaml` or `.epic.yml`
- [ ] **Rollback on failure**: Default behavior
- [ ] **Tickets directory**: Custom location
- [ ] **Git branch prefixes**: Custom `epic/` and `ticket/`
- [ ] **Auto-push**: Enable/disable remote push
- [ ] **Auto-create PRs**: Enable/disable PR creation

---

### 9. Error Handling Tests

#### 9.1 Graceful Failures
- [ ] **Claude CLI not installed**: Helpful error message
- [ ] **Git not installed**: Error with context
- [ ] **GitHub CLI not installed**: Error when PRs requested
- [ ] **Permission denied**: Clear error about file/directory
- [ ] **Network issues**: Timeout or connection errors
- [ ] **Disk full**: Storage error
- [ ] **Invalid YAML**: Parse error with line number

#### 9.2 Recovery Scenarios
- [ ] **Interrupted epic execution**: Resume from state file
- [ ] **Failed ticket**: Skip or retry
- [ ] **Test failures**: Block until fixed
- [ ] **Merge conflicts**: Report and pause
- [ ] **Branch already exists**: Offer to continue or abort

---

### 10. Integration Tests

#### 10.1 End-to-End Workflow
- [ ] **Full workflow**:
  1. Create planning doc
  2. `buildspec create-epic planning/spec.md`
  3. Verify epic YAML created
  4. `buildspec create-tickets planning/spec.epic.yaml`
  5. Verify ticket files created
  6. `buildspec execute-epic planning/spec.epic.yaml`
  7. Verify all tickets executed
  8. Verify PRs created
  9. Verify artifacts committed
  10. Verify epic-state.json complete

#### 10.2 Multi-Project Support
- [ ] **Project A**: Create and execute epic
- [ ] **Switch to Project B**: Create and execute different epic
- [ ] **Context isolated**: No cross-contamination

#### 10.3 Concurrent Execution
- [ ] **Multiple epics**: In different terminals
- [ ] **State isolation**: Each has own artifacts
- [ ] **No interference**: Independent execution

---

### 11. Documentation Tests

#### 11.1 Help Output
- [ ] `buildspec --help` → Shows all commands
- [ ] `buildspec create-epic --help` → Shows options and examples
- [ ] `buildspec create-tickets --help` → Complete documentation
- [ ] `buildspec execute-epic --help` → All flags explained
- [ ] `buildspec execute-ticket --help` → Parameter details
- [ ] `buildspec init --help` → Config initialization help

#### 11.2 Error Messages
- [ ] **Missing arguments**: Suggest correct usage
- [ ] **Invalid paths**: Show expected format
- [ ] **Validation failures**: Explain what's wrong and how to fix
- [ ] **Pre-flight failures**: List specific failing tests

---

### 12. Performance Tests

#### 12.1 Scalability
- [ ] **Large planning doc** (10k lines): Epic created successfully
- [ ] **Many tickets** (50+): All executed correctly
- [ ] **Deep dependencies** (10 levels): Correct execution order
- [ ] **Wide parallelism** (20 independent tickets): All run in parallel

#### 12.2 Resource Usage
- [ ] **Memory usage**: Reasonable for large epics
- [ ] **Disk usage**: Artifacts don't explode in size
- [ ] **Token usage**: Coordination requirements compress effectively

---

### 13. Portability Tests

#### 13.1 Cross-Platform
- [ ] **macOS**: All features work
- [ ] **Linux**: All features work
- [ ] **Different shells**: bash, zsh compatibility
- [ ] **Python 3.8**: Minimum version works
- [ ] **Python 3.11+**: tomllib works
- [ ] **Python 3.13**: Latest version works

#### 13.2 Path Handling
- [ ] **Home directory**: `~` expansion works
- [ ] **XDG variables**: Respects XDG_CONFIG_HOME, etc.
- [ ] **Spaces in paths**: Quoted paths work
- [ ] **Symlinks**: Resolved correctly
- [ ] **Relative paths**: Work from any directory

---

## Test Execution Strategy

### Priority 1 (Critical Path)
1. Installation & setup
2. Create epic (basic)
3. Execute ticket (basic)
4. Execute epic (sequential)

### Priority 2 (Core Features)
5. Create tickets
6. Epic execution (parallel)
7. Pre-flight validation
8. Context detection

### Priority 3 (Advanced Features)
9. Configuration customization
10. Error handling
11. PR creation
12. State management

### Priority 4 (Edge Cases)
13. All edge cases and error scenarios
14. Performance tests
15. Portability tests

---

## Testing Notes

- Run tests in isolated environments when possible
- Document any failures with reproduction steps
- Track test coverage and update checklist as features evolve
- Prioritize critical path tests before each release
