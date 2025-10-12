# Testing Standards for Clean Tickets

**Version:** 1.0
**Last Updated:** 2025-10-08

## How to Use This Document

**When defining tests for a ticket:**
1. Read the ticket's acceptance criteria from `ticket-standards.md`
2. For each acceptance criterion, define at least one test
3. Apply the test organization standards for naming and structure
4. Ensure coverage requirements are met (minimum 80%)
5. Use validation prompts (below) to verify test quality

**When reviewing test specifications:**
1. Verify each acceptance criterion has corresponding tests
2. Check tests follow naming conventions and AAA pattern
3. Ensure coverage meets minimum thresholds
4. Review against Common Mistakes section

---

## Core Testing Principles

1. **Test Coverage Must Match Acceptance Criteria** - Every acceptance criterion
   from the ticket (defined in `ticket-standards.md`) must have at least one
   automated test that verifies it

2. **Tests Must Be Runnable in Isolation** - Each test should pass independently
   without relying on execution order

3. **Tests Must Be Deterministic** - Same input always produces same output; no
   flaky tests

4. **Tests Must Be Fast** - Unit tests should run in milliseconds, integration
   tests in seconds

5. **Tests Must Be Readable** - Test names and structure should clearly
   communicate intent and expected behavior

## Required Test Types

### Unit Tests

- **MUST** test individual functions and methods in isolation
- **MUST** use mocks/stubs for external dependencies
- **MUST** cover:
  - Happy path (expected behavior)
  - Edge cases (boundary conditions)
  - Error conditions (invalid inputs, failure scenarios)
- **MUST** achieve minimum 80% code coverage for new code
- **Example**:
  ```python
  test_validate_email_valid_format_returns_true()
  test_validate_email_missing_at_symbol_returns_false()
  test_validate_email_empty_string_returns_false()
  ```

### Integration Tests

- **MUST** test interactions between components
- **MUST** verify that collaborative code works together (see
  "Collaborative Code Context" in `ticket-standards.md`)
- **MUST** test against real dependencies where practical (databases, APIs, file
  systems)
- **SHOULD** use test fixtures or factories for consistent test data
- **Example**:
  ```python
  test_user_login_valid_credentials_returns_auth_token()
  test_user_login_invalid_password_returns_unauthorized()
  test_user_login_nonexistent_user_returns_not_found()
  ```

### End-to-End Tests (When Applicable)

- **SHOULD** include if ticket affects user-facing functionality
- **MUST** verify complete user workflows
- **MUST** test critical paths only (avoid exhaustive E2E coverage)
- **Example**:
  ```python
  test_complete_checkout_valid_cart_creates_order()
  ```

## Test Organization Standards

### Naming Conventions

- **MUST** use descriptive test names following pattern:
  - `test_[function_name]_[scenario]_[expected_result]()`
  - OR `test_[feature]_[when]_[then]()`
- **Examples**:
  ```python
  test_validate_email_valid_format_returns_true()
  test_validate_email_missing_at_symbol_returns_false()
  test_checkout_when_cart_is_empty_then_returns_validation_error()
  ```

### Test Structure

- **MUST** follow Arrange-Act-Assert (AAA) pattern:
  ```
  // Arrange - set up test data and conditions
  // Act - execute the function/behavior being tested
  // Assert - verify expected outcomes
  ```

### Test Data

- **MUST** use meaningful test data that reflects real-world scenarios
- **MUST NOT** use production data in tests
- **SHOULD** use factories or builders for complex objects
- **SHOULD** make test data obvious (avoid magic numbers)

## Coverage Requirements

### Minimum Coverage

- **MUST** achieve 80% line coverage for new code
- **MUST** achieve 100% coverage for critical paths (authentication, payment,
  data loss scenarios)
- **MUST** cover all acceptance criteria with at least one test

### What Must Be Tested

- **All public APIs and interfaces** - every public function must have tests
- **All error handling paths** - verify errors are caught and handled correctly
- **All state transitions** - in state machines or workflow systems
- **All boundary conditions** - min/max values, empty collections, null values
- **All integration points** - interactions with other tickets' code

### What Should NOT Be Tested

- **Third-party library internals** - trust external dependencies
- **Language/framework features** - don't test that Python's `dict` works
- **Generated code** - unless business logic is embedded
- **Trivial getters/setters** - without logic

## Test Quality Standards

### Tests Must Be Maintainable

- **MUST** be easy to understand 6 months from now
- **MUST** fail with clear, actionable error messages
- **MUST** be updated when implementation changes
- **MUST NOT** duplicate implementation logic in assertions

### Tests Must Be Independent

- **MUST** clean up after themselves (teardown fixtures)
- **MUST NOT** share mutable state between tests
- **MUST** be runnable in any order
- **MUST** be runnable in parallel (where framework supports it)

### Tests Must Be Trustworthy

- **MUST** fail when code is broken
- **MUST** pass when code is correct
- **MUST NOT** have false positives (passing when they should fail)
- **MUST NOT** have false negatives (failing when they should pass)

## Performance Benchmarks

- **Unit tests**: < 100ms per test
- **Integration tests**: < 5 seconds per test
- **E2E tests**: < 30 seconds per test
- **Full test suite**: Should run in < 5 minutes for CI/CD

## Test Documentation

### Test Comments

- **SHOULD** include comments only when test intent is not obvious from name
- **MUST** explain WHY a test exists if testing a subtle bug or edge case
- **Example**:
  ```python
  # This tests the fix for issue #123 where concurrent requests
  # could cause race condition in cache invalidation
  def test_cache_invalidation_concurrent_requests_maintains_consistency():
      ...
  ```

### Test Coverage Reports

- **MUST** be generated on every test run
- **MUST** identify untested code paths
- **SHOULD** be reviewed before marking ticket complete

## Ticket Mergability Criteria

A ticket is **only mergable** when (must also meet criteria in
`ticket-standards.md`):

1. All tests pass
2. Coverage meets minimum thresholds (80% line coverage)
3. All acceptance criteria have corresponding tests
4. No flaky tests (tests pass consistently)
5. Tests follow naming and organization standards
6. Tests are documented where necessary

## Anti-Patterns to Avoid

❌ **Testing implementation details** - Test behavior, not internal
structure

❌ **Overly coupled tests** - Tests should not break when refactoring

❌ **Testing everything through UI** - Use appropriate test level

❌ **Ignoring test failures** - Fix or remove, never skip

❌ **Copy-paste test code** - Use helpers and fixtures

❌ **Sleeping in tests** - Use proper synchronization mechanisms

❌ **Testing multiple things in one test** - One concern per test

---

## Common Mistakes

### Coverage Issues
❌ **Not testing acceptance criteria** - Writing tests that don't match
the ticket's acceptance criteria
✅ **Criteria-driven tests** - Each acceptance criterion has at least one
corresponding test

❌ **Low coverage** - Achieving < 80% line coverage for new code
✅ **Adequate coverage** - Meeting 80% minimum, 100% for critical paths

❌ **Testing only happy path** - Ignoring edge cases and error conditions
✅ **Comprehensive testing** - Happy path + edge cases + error handling

### Test Organization
❌ **Generic test names** - `test_function1()`, `test_case_2()`
✅ **Descriptive names** -
`test_validate_email_missing_at_symbol_returns_false()`

❌ **Ignoring AAA pattern** - Mixing setup, execution, and assertions
✅ **Clear structure** - Separate Arrange, Act, Assert sections

❌ **Magic values** - `assert result == 42` without explanation
✅ **Clear test data** - `expected_discount = 0.15  # 15% member
discount`

### Test Independence
❌ **Shared mutable state** - Tests failing when run in different order
✅ **Independent tests** - Each test sets up and tears down its own data

❌ **Test interdependence** - Test B requires Test A to run first
✅ **Isolated tests** - Any test can run alone and pass

❌ **No cleanup** - Leaving test data/files/connections open
✅ **Proper teardown** - Tests clean up all resources they create

### Test Quality
❌ **Flaky tests** - Randomly failing due to timing, randomness, or
external factors
✅ **Deterministic tests** - Same input always produces same result

❌ **Slow tests** - Unit tests taking seconds, integration tests taking
minutes
✅ **Fast tests** - Unit < 100ms, integration < 5s, full suite < 5min

❌ **Testing implementation** - Tests break when refactoring internal
structure
✅ **Testing behavior** - Tests verify outcomes, not how they're achieved

### Integration Testing
❌ **Skipping integration tests** - Only unit testing collaborative code
✅ **Testing integration points** - Verifying code from multiple tickets
works together

❌ **Testing third-party internals** - Verifying how libraries work
✅ **Testing our usage** - Verifying we use libraries correctly

### Missing Error Cases
❌ **Only testing success** - Not verifying error handling paths
✅ **Testing failures** - Invalid input, missing data, external failures
all tested

❌ **No boundary testing** - Missing min/max values, empty collections,
null handling
✅ **Edge case coverage** - All boundaries and special cases tested

## Validation Prompts

Before finalizing test specifications, answer these questions:

### Coverage & Completeness
- [ ] Does every acceptance criterion have at least one test?
- [ ] Have I covered happy path, edge cases, and error conditions?
- [ ] Does the test coverage meet 80% minimum for new code?
- [ ] Are critical paths (auth, payments, data loss) at 100% coverage?

### Test Quality
- [ ] Are test names descriptive and follow naming conventions?
- [ ] Does each test follow the Arrange-Act-Assert pattern?
- [ ] Will these tests fail when the code is broken?
- [ ] Will these tests pass when the code is correct?
- [ ] Are the tests deterministic (no random failures)?

### Independence & Maintainability
- [ ] Can each test run independently in any order?
- [ ] Do tests clean up after themselves?
- [ ] Will someone understand these tests in 6 months?
- [ ] Do tests have clear, actionable error messages?

### Performance
- [ ] Do unit tests run in < 100ms each?
- [ ] Do integration tests run in < 5 seconds each?
- [ ] Will the full test suite complete in < 5 minutes?

### Integration
- [ ] Do integration tests verify collaborative code from other tickets?
- [ ] Are all integration points with other tickets tested?
- [ ] Have I avoided testing third-party library internals?

---

## Summary

Tests are not optional documentation—they are the executable specification of
the ticket's behavior. Every acceptance criterion must be verified by automated
tests. When tests pass and coverage thresholds are met, the code is mergable.
Tests must be fast, isolated, deterministic, and maintainable. Poor tests are
worse than no tests because they create false confidence and maintenance burden.
