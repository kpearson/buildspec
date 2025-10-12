# Epic Creation Prompt Construction Guide

## Purpose

This document outlines the systematic approach to constructing a prompt for a
headless Claude Code instance that transforms a comprehensive feature
specification (1k-2k lines) into an actionable Epic document with breakdown into
implementable tickets.

## Discovery Phase

### 1. Analyze the Input Format

- Study several example feature specs to understand their structure
- Identify common patterns (sections, headings, terminology)
- Note variations in how requirements are expressed
- Document the typical information architecture of specs

#### Answers

Spec docs are unstuctured by design. They do have hierarchiy. The main purpose
of Spec docs is to allow a feature Planning session to go where ever it needs
to. Spec files are the place where product managers, engineers, and other stake
holder bring all there ides for a feature or feature set together.

**Making asumptions about the spec will cause problmes as the are some times
structured, sometimes not, and the structure varries widly. It's a feature not a
bug**

### 2. Analyze the Desired Output Format

- Examine existing epics in your codebase/workflow
- Understand the epic schema (what fields are required vs optional)
- Study how tickets are typically structured and linked to epics
- Review completed epics to understand what "done" looks like

#### Answers

YAML. We can set datetime them. But lets say there will be a list of tickets
with there attributes.

Review completed epics: **We're green field buddy.** If I wanted more of the
sub-par work from before I'd stick with the original prompt

### 3. Identify the Transformation Rules

- Map spec sections → epic sections
- Define what makes a feature "ticket-worthy" vs part of another ticket
- Establish criteria for ticket sizing and dependencies
- Document how to handle different types of requirements (functional,
  non-functional, technical)

#### Answers

Map spec sections: Can't

Define what makes a feature "ticket-worthy" vs part of another ticket: This is
what makes this tricky and why it's worth giving to a state or the art LLM.
Infact this is the biggest quetion I have. Would it be work it to create a
claude agent for this purpose?

I keep going back and forth on the value of creating a deadicated agent for
ticket creation. on thing going for an proper agent is Multi-turn capability. If
the ticket abent can't iterate, sketch out the breakdown of the epic into
tickets, review it's own work, and make improvments, I'd say that would be about
the best we could. Thoughts?

Document how to handle different types of requirements (functional,
non-functional, technical): yes, but how?

## Prompt Architecture Planning

### 4. Define the Core Objective

- Be explicit about the transformation goal
- Specify the completeness criterion (all tickets done = spec implemented)
- Clarify the relationship between spec and epic
- State quality expectations

#### Answers

**Yes to all of that**

### 5. Establish Output Structure Requirements

- Epic metadata (title, description, goals)
- Implementation considerations section
- Gotchas/warnings section
- Ticket breakdown with clear acceptance criteria
- Dependencies and ordering
- Testing strategy overview

### 6. Create Extraction Heuristics

- How to identify "features" vs "implementation details": Feature add value,
  implementation is how that value is delivered. (User uses app not aws)
- How to spot dependencies between work items: the llm doing this work should be
  taking in the spec as whole and determining for it's self what work items are.
- How to recognize technical risks/gotchas
- How to infer appropriate ticket granularity
- How to distinguish must-have from nice-to-have
- How to identify cross-cutting concerns

#### Answers: fucntion names and directory structure should be keeped. Implementation should not. the psudo code in fuctions should be replaced with a 1-3 sententses about intent.

### 7. Define Ticket Decomposition Strategy

- Vertical slicing principles (user-facing value): to a point. sometimes value
  will need to be below the api. Ticket need to be testable. Units, public apis,
  integrations.
- Technical dependency ordering: do you mean the order of Ticket execution. Yes
  tickets will need tickst dependency and thet will be in keeped in the epic.
- Testing/validation considerations
- Integration points: need to be carfully articulated in the epic and tickets.
- Ticket size guidelines (avoid too large or too small): Small as possible will
  being testable and adding value(user, developer, or system)
- When to split vs combine work items

## Validation Strategy

### 8. Build in Quality Checks

- **Completeness**: does epic capture all spec requirements?
- **Actionability**: can a developer start work from a ticket alone?
- **Traceability**: can you map each spec requirement to ticket(s)?
- **Clarity**: are acceptance criteria unambiguous?
- **Testability**: can each ticket be verified independently?

> Answers:

### 9. Handle Edge Cases

- Ambiguous requirements in spec
- Cross-cutting concerns (logging, error handling, etc.)
- Infrastructure/setup work
- Documentation requirements
- Migration or backwards compatibility needs
- Performance requirements
- Security considerations

## Iterative Refinement

> Answers:

### 10. Test with Examples

- Start with a small spec section: nope. Thats not hard to build.
- Evaluate output quality: because this requirements judment, maybe we ceate a
  deadicated agent for thins?
- Identify what's missing or unclear
- Refine the prompt instructions
- Test with varied spec styles

### 11. Add Constraints and Guidelines

- Ticket size limits (story points, complexity)
- Naming conventions
- Required fields for tickets
- Format specifications (markdown, YAML, etc.)
- Standard sections for each ticket
- How to reference related tickets
- How to indicate priority/ordering

## Implementation Considerations

### Prompt Structure Elements

- **Context setting**: What is the agent's role?
- **Input description**: What will it receive?
- **Output specification**: What should it produce?
- **Process instructions**: How should it analyze and transform?
- **Quality criteria**: How to self-evaluate?
- **Examples**: Reference examples of good transformations

### Agent Capabilities to Leverage

- File reading and analysis
- Pattern recognition across large documents
- Structured output generation
- Multi-step reasoning
- Dependency analysis

> Answers:

### Potential Challenges

- Maintaining context across 1k-2k line document
- Ensuring no requirements are missed
- Appropriate ticket granularity
- Handling ambiguity in specs
- Balancing detail with readability

## Next Steps

1. Gather example feature specs
2. Gather example epics and tickets
3. Define epic/ticket schema formally
4. Create transformation rules document
5. Draft initial prompt
6. Test with sample specs
7. Iterate based on results

I have a spec ready to test with. I don't what yuou to see it becuse I don't
want to contamiate your creative process.
