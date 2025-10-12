# TransitionGate protocol for validation gates

**Ticket ID:** create-gate-interface

**Critical:** true

**Dependencies:** create-state-models

**Coordination Role:** Provides gate interface implemented by all validation gates and consumed by state machine

## Description

As a state machine developer, I want a clear TransitionGate protocol that defines how validation gates work so that all gates follow a consistent interface and the state machine can use them uniformly.

This ticket creates gates.py with the TransitionGate protocol defining the check() interface that all validation gates must implement. This establishes the gate pattern used throughout the state machine for enforcing invariants before state transitions. The protocol is implemented by all concrete gates (tickets: implement-dependency-gate, implement-branch-creation-gate, implement-llm-start-gate, implement-validation-gate) and consumed by the state machine (ticket: core-state-machine) in the _run_gate() method. Key components to implement:
- TransitionGate: Protocol with check(ticket: Ticket, context: EpicContext) -> GateResult signature
- EpicContext: Dataclass containing epic_id, epic_branch, baseline_commit, tickets dict, git operations instance, epic config
- Protocol documentation explaining gate contract and usage pattern

## Acceptance Criteria

- TransitionGate protocol defined with clear type hints
- EpicContext dataclass contains all state needed by gates (epic metadata, tickets, git operations, config)
- Protocol can be type-checked with mypy as a structural type
- Documentation explains gate pattern and how to implement new gates
- GateResult model (from ticket: create-state-models) properly used

## Testing

Unit tests verify protocol structure and EpicContext initialization. Mock gate implementations test that protocol interface is correctly defined and type-checkable. Coverage: 100% (protocol and context dataclass).

## Non-Goals

No concrete gate implementations (those are separate tickets), no gate registry or factory, no gate orchestration logic, no gate caching - this is purely interface definition.
