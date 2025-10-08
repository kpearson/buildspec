# CLI Modificaitons

- [x] Flatten dir hiearchy
- [x] add makefile to stremline install - initial system install and uninstall.
      build symlinks and add executable
- [x] add init command - setup config.toml
- [x] add uv
- [x] Ruff - Lint and auto-formatter
- [x] add short args -h --help
- [x] add orchistraation agent prompt
- [ ] make install or buildspec init needs to add .buildspec to .gitignore
- [ ] init needs to create sub directories for each project
      ~/.confib/buildspec/[project]/config.toml
- [ ] Add progress indicators (spinner/status) while CLI commands are running
      - Show spinner while waiting for Claude CLI to respond
      - Display status messages: "Analyzing epic...", "Executing ticket...", etc.
      - Use rich.spinner or rich.progress for visual feedback
      - Especially important for long-running commands (execute-epic, execute-ticket)

## Features

### Orchistraation agent

The top most agent must be an orchistrator and not attempt to execute any units
of work. Delegating to sub-agents is critical for two key reasons.

1. To preserve the contex window. If the top level agent is handed an epic with
   2-3 ticket and it attemptes to execute the work it's self, it's context
   window will fill up, and it will have to exit before it can complet the epic.

2. An orchistraation agent creates the opportunity for code-review agents(code
   quality and adherence to ticket, test quality, securety) and refinemens
   before calling the work done.

### Code review agent

Creating a code review agent focusing on a critical anallisis on the work
product of the builder agent. This agent will have specialized tools and context
to scrutenize the the new code and offer improvments.

Promot elements:

- Use git to understand the code in question.
- The code under review was written by a differernt member of the team and we
  (the prompt author) are not sure about it. This enoculates agenst claude being
  favorable to it's own code.
- include a pass fail assessment. Tell us whether changes are required

Prompt example "A member of the team turned this is in for review. I'd like you
to evaluate it for:

- adherence to the ticketed work
- How well it fits within the exsisting codebase. conforms to exsisting
  conventions
- Performance
- idomatic

You review need to include an assessment as to wether the code should be given
back to the engineer to make changes.

Create a code review md document artifact in {epic artifacts dir}. Print to std
out a summary of your review with a pass or fail including the full path to the
code-review file"

### State management - ~/.config/buildspec/

This is happening through prompting alone (I think in the epic prompt). We need
to formalize this so that it can be relyed on by the orchistraation agent and
when the orchistraation agent stops early or headless execution is interupted.

This will need an id (uuid) which means each "execute epic" run will need an id.
Create new if not attaching to an exsisting (what should we call this? run,
session, ... Im thinking session)

This can be keept in the target project in .buildspec/

If we keep this outside of the project

### Epic branches - currently in config.toml

### Git Branch Creation Issue

- [ ] **CRITICAL**: Investigate why execute-epic doesn't create epic branch
  - Test: Run execute-epic and verify epic branch is created
  - Check: execute-epic.md instructions for epic branch creation
  - Check: Orchestrator agent is following branch creation instructions
  - Fix: Ensure epic branch is created as first step in epic execution
  - Test: Verify epic branch and ticket branches are created correctly
  - Document: Branch creation flow in execute-epic command

### CLI Progress Indicators

- [ ] Add spinners/progress indicators to long-running CLI commands
  - Implement spinner in ClaudeRunner.execute() using rich.spinner
  - Add contextual status messages:
    - "Analyzing epic..." (execute-epic)
    - "Generating epic file..." (create-epic)
    - "Executing ticket..." (execute-ticket)
    - "Creating tickets..." (create-tickets)
  - Use Live context manager to show spinner during Claude execution
  - Test on all commands (create-epic, execute-epic, execute-ticket, create-tickets)
  - Ensure spinner stops cleanly on success/error

### One-Command Installation (Option 3 from DISTRIBUTION.md)

- [ ] Implement one-command curl-based installation
  - Create `install.sh` script in repo root
    - Detect OS and architecture (macOS ARM/x86_64, Linux x86_64/ARM64)
    - Download pre-built binary from GitHub Releases
    - Verify SHA256 checksum
    - Install to ~/.local/bin/buildspec
    - Download and install Claude Code files to ~/.claude/
    - Verify installation and show next steps
  - Create `.github/workflows/release.yml` for multi-platform builds
    - Build matrix: macOS (ARM64, x86_64), Linux (x86_64, ARM64)
    - Use PyInstaller to build binaries on each platform
    - Generate SHA256 checksums for each binary
    - Package claude_files/ as tar.gz
    - Create GitHub Release with all artifacts
  - Test installation on all platforms
  - Update README.md with one-command install as primary method
  - Document release process (tagging, building, publishing)

### Paralle builds

Assigning ticketed work that can be executed in Paralle presents several
substantial challenges. I see two optential options

1. launch containers

2. git worktrees
