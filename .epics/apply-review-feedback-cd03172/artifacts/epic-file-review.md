---
date: 2025-10-11
epic: apply-review-feedback
ticket_count: 10
builder_session_id: a7858952-ac4e-4592-82b5-e5f0c383204f
reviewer_session_id: f55a05f2-78ce-4124-a728-d9e6f1b8ca9b
---

# Epic Review Report

## Executive Summary

This is a well-structured refactoring epic that extracts a reusable abstraction
for applying review feedback. The epic has clear objectives, logical ticket
granularity, and proper dependency chains. However, it lacks concrete function
signatures in ticket descriptions (Paragraph 2) and needs more specific
coordination requirements around the ReviewTargets interface contract.

## Critical Issues

### 1. Missing Function Examples in Ticket Descriptions

**Every ticket's Paragraph 2 should contain concrete function signatures**, but
currently tickets only describe what should exist without showing the actual
interfaces:

- **ARF-001**: Should show `ReviewTargets` dataclass with exact field types and
  defaults

  ```python
  @dataclass
  class ReviewTargets:
      primary_file: Path
      additional_files: List[Path]
      editable_directories: List[Path]
      artifacts_dir: Path
      updates_doc_name: str
      log_file_name: str
      error_file_name: str
      epic_name: str
      reviewer_session_id: str
      review_type: Literal["epic-file", "epic"]
  ```

- **ARF-002**: Should show `_build_feedback_prompt()` signature:

  ```python
  def _build_feedback_prompt(review_content: str, targets: ReviewTargets, builder_session_id: str) -> str
  ```

- **ARF-003**: Should show `_create_template_doc()` signature:

  ```python
  def _create_template_doc(targets: ReviewTargets, builder_session_id: str) -> None
  ```

- **ARF-004**: Should show `_create_fallback_updates_doc()` signature:

  ```python
  def _create_fallback_updates_doc(targets: ReviewTargets, stdout: str, stderr: str, builder_session_id: str) -> None
  ```

- **ARF-005**: Should show `apply_review_feedback()` signature:
  ```python
  def apply_review_feedback(
      review_artifact_path: Path,
      builder_session_id: str,
      context: ClaudeContext,
      targets: ReviewTargets,
      console: Console
  ) -> None
  ```

**Impact**: Without concrete signatures, implementers must guess at parameter
orders, return types, and exception handling contracts.

### 2. Incomplete Coordination Requirements

The epic lacks explicit coordination requirements that define the integration
contract. Add a `coordination_requirements` section that specifies:

```yaml
coordination_requirements:
  - ReviewTargets dataclass must be the single source of truth for all file
    paths and configuration
  - All helper functions (_build_feedback_prompt, _create_template_doc,
    _create_fallback_updates_doc) must accept ReviewTargets as parameter
  - apply_review_feedback() must not hardcode any file paths or names - all must
    come from ReviewTargets
  - Prompt template must vary based on targets.review_type ("epic-file" vs
    "epic")
  - Template document must use frontmatter with "status:
      in_progress" before Claude runs
  - Fallback documentation must be created when template status remains
    "in_progress"
  - Both create_epic.py and create_tickets.py must instantiate ReviewTargets
    differently but call same function
  - Module must have minimal external dependencies (pathlib, dataclasses, typing
    only)
```

**Impact**: Without these explicit contracts, tickets might be implemented in
ways that don't compose correctly.

## Major Improvements

### 3. Testing Gaps in ARF-009

While ARF-009 specifies 8 test cases, it's missing critical test scenarios:

**Add these test cases:**

- `test_review_targets_validation()` - Test that ReviewTargets validates
  required fields
- `test_build_feedback_prompt_special_chars()` - Test prompt building with
  special characters in review content
- `test_create_template_doc_directory_exists()` - Test when artifacts directory
  doesn't exist
- `test_apply_review_feedback_partial_success()` - Test when some files update
  but others fail
- `test_concurrent_review_feedback()` - Test thread safety if multiple reviews
  run in parallel

### 4. Integration Testing Insufficient in ARF-010

ARF-010 lists 5 integration tests but doesn't specify:

- **Pass criteria**: What constitutes success? Should there be assertions on
  specific file changes?
- **Test data**: What sample epic/tickets should be used?
- **Rollback strategy**: What happens if integration tests reveal bugs?
- **Performance**: Should there be timing constraints (e.g., review application
  should complete in < 30s)?

**Recommendation**: Add a test fixture epic specifically for integration testing
(e.g., `.epics/test-fixtures/simple-epic/`) with known inputs and expected
outputs.

### 5. Error Handling Not Specified

While ARF-005 mentions "proper error handling with try/except blocks", the epic
doesn't specify:

- What exceptions should be caught?
- Should errors fail fast or continue gracefully?
- Should errors be logged to error_file_name or stderr?
- Should partial failures (e.g., epic updates but ticket files don't) be
  considered success or failure?

**Recommendation**: Add specific error handling requirements to ARF-005
acceptance criteria.

### 6. Missing Non-Goals

The epic should explicitly state what is NOT included:

**Non-Goals:**

- Applying review feedback for review types beyond "epic-file" and "epic"
- Validating review artifact structure (assumed correct)
- Retrying failed Claude sessions (assumed single attempt)
- Preserving backup copies of files before editing
- Concurrent review feedback application
- CLI command changes (only internal refactoring)

### 7. Backwards Compatibility Not Addressed

The epic doesn't specify whether existing session logs, artifacts, or
documentation from the old implementation should remain compatible.

**Recommendation**: Add to ARF-007 acceptance criteria: "Existing
epic-file-review artifacts directory structure remains unchanged."

## Minor Issues

### 8. LOC Estimates in Tickets

ARF-007 mentions "Net LOC reduction of ~272 lines" and ARF-008 mentions "Net LOC
increase of ~27 lines" - these are helpful but should be in acceptance criteria
consistently across all tickets that modify existing files.

### 9. Import Organization

ARF-006 mentions updating `__init__.py` but doesn't specify import style. Should
it be:

- `from cli.utils.review_feedback import ReviewTargets, apply_review_feedback`
- `from .review_feedback import ReviewTargets, apply_review_feedback`

**Recommendation**: Specify relative imports for consistency.

### 10. Directory Structure Ambiguity

The epic mentions `cli/utils/review_feedback.py` but doesn't specify if this
follows an existing pattern.

**Recommendation**: Verify that `cli/utils/` is the correct location (not
`buildspec/utils/` or similar).

### 11. Console Output Not Specified

The epic doesn't specify what user-facing messages should be shown during review
feedback application. Should there be:

- "Applying review feedback..." progress message?
- Success/failure summary?
- File change summary?

**Recommendation**: Add console output requirements to ARF-005.

### 12. Documentation Frontmatter Schema

The epic mentions frontmatter with "status" field but doesn't specify the
complete schema. Should include:

```yaml
---
date: YYYY-MM-DD
epic: epic-name
builder_session_id: uuid
reviewer_session_id: uuid
status: in_progress | completed | completed_with_errors
---
```

This should be explicit in ARF-003.

## Strengths

1. **Clear Abstraction Boundary**: The ReviewTargets dataclass is an excellent
   dependency injection pattern
2. **Logical Decomposition**: Tickets are well-scoped and follow natural
   implementation order
3. **Proper Dependencies**: Dependency chain is linear and sensible (no circular
   dependencies)
4. **Testing Included**: ARF-009 ensures quality before integration
5. **Real-World Validation**: ARF-010 validates the abstraction actually works
6. **Two Integration Points**: Epic demonstrates reusability by integrating into
   both create_epic.py and create_tickets.py
7. **Preservation of Behavior**: ARF-007 explicitly states behavior should
   remain identical
8. **Helper Function Extraction**: Breaking down into \_build_feedback_prompt,
   \_create_template_doc, etc. makes code testable

## Recommendations

### Priority 1 (Must Fix)

1. **Add function signatures to Paragraph 2 of each ticket** (ARF-001 through
   ARF-005)
2. **Add explicit coordination_requirements section** to epic YAML
3. **Specify error handling contracts** in ARF-005

### Priority 2 (Should Fix)

4. **Expand test cases** in ARF-009 to cover edge cases
5. **Add specific integration test criteria** to ARF-010 with test fixtures
6. **Add non-goals section** to epic description
7. **Specify backwards compatibility** in ARF-007

### Priority 3 (Nice to Have)

8. **Add LOC estimates** consistently across all refactoring tickets
9. **Specify import style** in ARF-006
10. **Add console output requirements** to ARF-005
11. **Document complete frontmatter schema** in ARF-003
12. **Verify directory structure** matches existing patterns

## Overall Assessment

This is a **high-quality refactoring epic** with clear objectives and good
decomposition. The main gaps are:

- Missing concrete function signatures (coordination contract)
- Underspecified error handling
- Integration testing needs more detail

With the Priority 1 fixes, this epic is ready for ticket generation. The
abstraction design is sound and the implementation plan is logical.

**Estimated effort**: 8-12 hours for implementation + testing **Risk level**:
Low (refactoring with existing behavior preservation) **Recommended action**:
Apply Priority 1 fixes, then proceed with ticket generation
