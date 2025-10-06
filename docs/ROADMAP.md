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

### Paralle builds

Assigning ticketed work that can be executed in Paralle presents several
substantial challenges. I see two optential options

1. launch containers

2. git worktrees
