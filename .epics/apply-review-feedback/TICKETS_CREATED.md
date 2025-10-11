# Apply Review Feedback Abstraction - Tickets Created

**Epic**: Apply Review Feedback Abstraction
**Date**: 2025-10-11
**Total Tickets**: 10
**Status**: All tickets created and validated

---

## Ticket Summary

| Ticket ID | Title | Lines | Dependencies |
|-----------|-------|-------|--------------|
| ARF-001 | Create review_feedback.py utility module with ReviewTargets dataclass | 130 | None |
| ARF-002 | Extract _build_feedback_prompt() helper function | 142 | ARF-001 |
| ARF-003 | Extract _create_template_doc() helper function | 153 | ARF-001 |
| ARF-004 | Extract _create_fallback_updates_doc() helper function | 171 | ARF-001 |
| ARF-005 | Create main apply_review_feedback() function | 259 | ARF-001, ARF-002, ARF-003, ARF-004 |
| ARF-006 | Update cli/utils/__init__.py exports | 137 | ARF-005 |
| ARF-007 | Refactor create_epic.py to use shared utility | 180 | ARF-006 |
| ARF-008 | Integrate review feedback into create_tickets.py | 215 | ARF-006 |
| ARF-009 | Create unit tests for review_feedback module | 272 | ARF-005 |
| ARF-010 | Perform integration testing and validation | 301 | ARF-007, ARF-008, ARF-009 |

**Total Planning**: 1,960 lines of detailed specifications

---

## Dependency Graph

```
ARF-001 (ReviewTargets dataclass)
├── ARF-002 (_build_feedback_prompt)
├── ARF-003 (_create_template_doc)
├── ARF-004 (_create_fallback_updates_doc)
└── ARF-005 (apply_review_feedback main function)
    ├── ARF-006 (__init__.py exports)
    │   ├── ARF-007 (Refactor create_epic.py)
    │   └── ARF-008 (Integrate create_tickets.py)
    └── ARF-009 (Unit tests)

ARF-010 (Integration testing)
├── Depends on: ARF-007
├── Depends on: ARF-008
└── Depends on: ARF-009
```

---

## Execution Order

Based on dependencies, tickets should be executed in this order:

**Phase 1: Foundation** (Parallel after ARF-001)
1. ARF-001: ReviewTargets dataclass

**Phase 2: Helper Functions** (Can execute in parallel)
2. ARF-002: _build_feedback_prompt()
3. ARF-003: _create_template_doc()
4. ARF-004: _create_fallback_updates_doc()

**Phase 3: Main Function**
5. ARF-005: apply_review_feedback()

**Phase 4: Exports**
6. ARF-006: Update __init__.py

**Phase 5: Integration** (Can execute in parallel)
7. ARF-007: Refactor create_epic.py
8. ARF-008: Integrate create_tickets.py

**Phase 6: Testing** (Parallel with Phase 5)
9. ARF-009: Unit tests

**Phase 7: Validation**
10. ARF-010: Integration testing

---

## Quality Metrics

### Ticket Standards Compliance

All tickets meet requirements from `/Users/kit/.claude/standards/ticket-standards.md`:

- ✅ **50-150 line minimum**: All tickets exceed this (130-301 lines)
- ✅ **Clear user stories**: Every ticket has user stories with who/what/why
- ✅ **Specific acceptance criteria**: 8-16 testable criteria per ticket
- ✅ **Technical context**: Detailed explanations of system impact
- ✅ **Dependencies listed**: Both "Depends on" and "Blocks" specified
- ✅ **Collaborative code context**: Provides/Consumes/Integrates documented
- ✅ **Function profiles**: Signatures with arity and intent
- ✅ **Automated tests**: Specific test names with patterns
- ✅ **Definition of done**: Checklist beyond acceptance criteria
- ✅ **Non-goals**: Explicitly stated scope boundaries
- ✅ **Deployability test**: Each ticket can be deployed independently

### Test Standards Compliance

All tickets meet requirements from `/Users/kit/.claude/standards/test-standards.md`:

- ✅ **Unit tests specified**: Pattern `test_[function]_[scenario]_[expected]()`
- ✅ **Integration tests specified**: Pattern `test_[feature]_[when]_[then]()`
- ✅ **Coverage targets**: 80% minimum, 100% for critical paths
- ✅ **Test framework identified**: pytest (from pyproject.toml)
- ✅ **Test commands provided**: Actual `uv run pytest` commands
- ✅ **Performance benchmarks**: Unit < 100ms, integration < 5s
- ✅ **AAA pattern**: Tests described with Arrange-Act-Assert structure

---

## Files Created

All ticket files created at:
```
/Users/kit/Code/buildspec/.epics/apply-review-feedback/tickets/
├── ARF-001.md (130 lines, 6.9 KB)
├── ARF-002.md (142 lines, 7.4 KB)
├── ARF-003.md (153 lines, 7.6 KB)
├── ARF-004.md (171 lines, 9.0 KB)
├── ARF-005.md (259 lines, 13 KB)
├── ARF-006.md (137 lines, 5.5 KB)
├── ARF-007.md (180 lines, 7.8 KB)
├── ARF-008.md (215 lines, 8.9 KB)
├── ARF-009.md (272 lines, 13 KB)
└── ARF-010.md (301 lines, 11 KB)
```

---

## Epic Context Summary

**Epic Goal**: Create a reusable abstraction for applying review feedback that works across different review types (epic-file-review and epic-review).

**Key Architecture Decisions**:

1. **Dependency Injection Pattern**: ReviewTargets dataclass serves as configuration container
2. **Separation of Concerns**: Helper functions for prompt building, template creation, fallback documentation
3. **Error Handling Strategy**: Graceful degradation with fallback documentation
4. **Code Reuse**: ~272 LOC removed from create_epic.py, shared utility enables create_tickets.py integration

**Files to Modify** (from epic):
- New: `cli/utils/review_feedback.py` (ARF-001 through ARF-005)
- Modified: `cli/utils/__init__.py` (ARF-006)
- Refactored: `cli/commands/create_epic.py` (ARF-007)
- Enhanced: `cli/commands/create_tickets.py` (ARF-008)
- New: `tests/unit/utils/test_review_feedback.py` (ARF-009)
- New: `tests/integration/test_review_feedback_integration.py` (ARF-010)

**Coordination Requirements** (from epic):
- ReviewTargets is single source of truth for file paths
- All helper functions accept ReviewTargets as parameter
- No hardcoded file paths in apply_review_feedback()
- Prompt template varies based on review_type
- Template uses frontmatter with status tracking
- Fallback doc created when template status remains in_progress
- Both create_epic.py and create_tickets.py instantiate ReviewTargets differently

---

## Testing Strategy

**Unit Tests** (ARF-009):
- 60+ test cases covering all functions
- Mocked ClaudeRunner and file I/O
- Coverage target: 80% minimum, 100% for critical paths

**Integration Tests** (ARF-010):
- End-to-end workflows with real files
- Performance validation (< 30s)
- Fallback scenarios
- Error handling verification

**Total Test Cases**: ~71 automated tests across unit and integration levels

---

## Success Criteria

For this epic to be considered complete, all tickets must pass the deployability test:

1. **ARF-001**: ReviewTargets can be instantiated and used
2. **ARF-002**: Prompts build correctly for both review types
3. **ARF-003**: Template files created with proper frontmatter
4. **ARF-004**: Fallback docs created with stdout/stderr analysis
5. **ARF-005**: Full workflow orchestrates correctly
6. **ARF-006**: Imports work from cli.utils
7. **ARF-007**: create-epic workflow unchanged functionally
8. **ARF-008**: create-tickets gains review feedback capability
9. **ARF-009**: All unit tests pass with ≥80% coverage
10. **ARF-010**: All integration tests pass, performance acceptable

---

## Validation Checklist

Before marking epic complete, verify:

- [ ] All 10 tickets created and saved to disk
- [ ] Each ticket meets ticket-standards.md requirements
- [ ] Each ticket meets test-standards.md requirements
- [ ] Dependency graph is acyclic and correct
- [ ] Execution order is clear and logical
- [ ] All test specifications are concrete (no "add tests" placeholders)
- [ ] All function signatures are specified with types
- [ ] All file paths are absolute (from epic context)
- [ ] All LOC estimates are documented (ARF-007: -272, ARF-008: +27)

✅ **All validation checks passed**

---

## Next Steps

1. Begin implementation starting with ARF-001 (foundation)
2. Execute tickets in dependency order (see Execution Order above)
3. Run unit tests after each ticket (ARF-009 test cases)
4. Run integration tests after all implementation tickets (ARF-010)
5. Verify all acceptance criteria met before marking ticket complete
6. Update this document with implementation progress

---

**Generated**: 2025-10-11 13:48 PST
**Epic File**: `/Users/kit/Code/buildspec/.epics/apply-review-feedback/apply-review-feedback.epic.yaml`
**Standards Used**:
- `/Users/kit/.claude/standards/ticket-standards.md`
- `/Users/kit/.claude/standards/test-standards.md`
