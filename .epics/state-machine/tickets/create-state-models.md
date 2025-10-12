# Well-defined type-safe data models and state enums

**Ticket ID:** create-state-models

**Critical:** true

**Dependencies:** None

**Coordination Role:** Provides type system for all state machine components

## Description

As a developer implementing the state machine, I want well-defined type-safe data models and state enums so that all components share a consistent type system and state definitions, enabling type checking and preventing runtime errors.

This ticket creates the foundational data models and state enums in cli/epic/models.py that define ticket and epic lifecycle states. These models form the type system for the entire state machine, ensuring type safety and clear state definitions. All other components (state machine, gates, builder, CLI) consume these types. Key models to implement:
- TicketState enum: PENDING, READY, BRANCH_CREATED, IN_PROGRESS, AWAITING_VALIDATION, COMPLETED, FAILED, BLOCKED
- EpicState enum: INITIALIZING, EXECUTING, MERGING, FINALIZED, FAILED, ROLLED_BACK
- Ticket dataclass: id, path, title, depends_on, critical, state, git_info, test_suite_status, acceptance_criteria, failure_reason, blocking_dependency, started_at, completed_at
- GitInfo dataclass: branch_name, base_commit, final_commit
- AcceptanceCriterion dataclass: criterion, met
- GateResult dataclass: passed, reason, metadata
- BuilderResult dataclass: success, final_commit, test_status, acceptance_criteria, error, stdout, stderr

## Acceptance Criteria

- All enums defined with correct state values
- All dataclasses defined with complete type hints
- Models pass mypy strict type checking
- Appropriate dataclasses are immutable (frozen=True)
- All fields have sensible defaults where applicable

## Testing

Unit tests verify enum values are correct, dataclass initialization works with various field combinations, type validation catches errors, immutability constraints are enforced for frozen dataclasses. Coverage: 100% (data models are small and fully testable).

## Non-Goals

No state transition logic, no validation rules, no persistence serialization, no business logic - this ticket is purely data structures.
