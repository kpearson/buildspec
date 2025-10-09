# create-gate-interface-and-protocol

## Description

Define TransitionGate protocol and GateResult for validation gates

## Epic Context

This ticket establishes the validation gate system that enforces deterministic
state transitions. Gates are the mechanism by which the state machine validates
conditions before allowing ticket state transitions.

**Key Objectives**:

- Validation Gates: Automated checks before allowing state transitions (branch
  exists, tests pass, etc.)
- LLM Interface Boundary: Clear contract between state machine (coordinator) and
  LLM (worker)
- Auditable Execution: State machine logs all transitions and gate checks for
  debugging

**Key Constraints**:

- LLM agents interact with state machine via CLI commands only (no direct state
  file manipulation)
- Validation gates automatically verify LLM work before accepting state
  transitions

## Acceptance Criteria

- TransitionGate protocol with check() method signature
- GateResult dataclass with passed, reason, metadata fields
- Clear documentation on gate contract
- Base gate implementation for testing
- Gates are in buildspec/epic/gates.py

## Dependencies

- create-state-enums-and-models

## Files to Modify

- /Users/kit/Code/buildspec/epic/gates.py

## Additional Notes

The TransitionGate protocol defines the contract for all validation gates. Each
gate implements the check() method which returns a GateResult indicating whether
the gate passed and why.

GateResult should include:

- passed: boolean indicating success/failure
- reason: human-readable explanation of the result
- metadata: dict of additional information (e.g., branch_name, base_commit)

This protocol enables the state machine to run validation checks in a
consistent, testable manner before allowing state transitions.
