"""Tests for commit message parser utility."""

import pytest

from cli.utils.commit_parser import extract_ticket_name, parse_ticket_name_from_commit


class TestExtractTicketName:
    """Test cases for extract_ticket_name function."""

    def test_extracts_from_ticket_branch_pattern(self):
        """Should extract ticket name from 'ticket/ticket-name' pattern."""
        assert extract_ticket_name("ticket/add-feature") == "add-feature"
        assert extract_ticket_name("Update ticket/fix-bug component") == "fix-bug"
        assert extract_ticket_name("TICKET/UPDATE-DOCS") == "UPDATE-DOCS"

    def test_extracts_from_completed_ticket_pattern(self):
        """Should extract ticket name from 'Completed ticket:' pattern."""
        assert extract_ticket_name("Completed ticket: add-feature") == "add-feature"
        assert extract_ticket_name("completed ticket: fix-bug") == "fix-bug"
        assert extract_ticket_name("COMPLETED TICKET: update-docs") == "update-docs"

    def test_extracts_from_conventional_commit_with_scope(self):
        """Should extract ticket name from conventional commit scope."""
        assert extract_ticket_name("feat(add-feature): implement new API") == "add-feature"
        assert extract_ticket_name("fix(bug-fix-123): resolve memory leak") == "bug-fix-123"
        assert extract_ticket_name("chore(update-deps): upgrade packages") == "update-deps"
        assert extract_ticket_name("docs(api-docs): update documentation") == "api-docs"
        assert extract_ticket_name("test(add-tests): add unit tests") == "add-tests"
        assert extract_ticket_name("refactor(cleanup-code): simplify logic") == "cleanup-code"
        assert extract_ticket_name("perf(optimize-query): improve performance") == "optimize-query"
        assert extract_ticket_name("style(format-code): fix linting") == "format-code"
        assert extract_ticket_name("build(ci-config): update build") == "ci-config"
        assert extract_ticket_name("ci(github-actions): add workflow") == "github-actions"

    def test_extracts_from_conventional_commit_without_scope(self):
        """Should extract ticket name from conventional commit subject."""
        # Should match ticket-like names (with hyphens)
        assert extract_ticket_name("feat: add-new-feature") == "add-new-feature"
        assert extract_ticket_name("fix: bug-fix-critical") == "bug-fix-critical"

        # Should NOT match simple words (too short, no hyphens)
        assert extract_ticket_name("feat: simple") is None
        assert extract_ticket_name("fix: bug") is None

        # Should match long single words (likely ticket names)
        assert extract_ticket_name("feat: implement-authentication-system") == "implement-authentication-system"

    def test_extracts_from_commit_body_ticket_field(self):
        """Should extract ticket name from 'ticket:' in commit body."""
        commit_msg = """fix: resolve critical bug

This is a detailed description of the fix.

ticket: bug-fix-123
"""
        assert extract_ticket_name(commit_msg) == "bug-fix-123"

        commit_msg_capital = """feat: add new feature

Ticket: add-new-feature
"""
        assert extract_ticket_name(commit_msg_capital) == "add-new-feature"

    def test_multiline_commit_messages(self):
        """Should handle multiline commit messages correctly."""
        commit_msg = """feat(add-feature): implement new API

This is a longer description that explains
what the feature does and why it's needed.

Breaking changes:
- API endpoint changed
"""
        assert extract_ticket_name(commit_msg) == "add-feature"

    def test_returns_none_when_no_ticket_found(self):
        """Should return None when no ticket pattern is found."""
        assert extract_ticket_name("Random commit message") is None
        assert extract_ticket_name("Update README") is None
        assert extract_ticket_name("Merge branch 'main'") is None
        assert extract_ticket_name("") is None

    def test_case_insensitive_matching(self):
        """Should match patterns case-insensitively."""
        assert extract_ticket_name("TICKET/add-feature") == "add-feature"
        assert extract_ticket_name("Ticket/add-feature") == "add-feature"
        assert extract_ticket_name("COMPLETED TICKET: add-feature") == "add-feature"
        assert extract_ticket_name("Completed Ticket: add-feature") == "add-feature"

    def test_handles_ticket_names_with_numbers(self):
        """Should handle ticket names containing numbers."""
        assert extract_ticket_name("ticket/add-feature-v2") == "add-feature-v2"
        assert extract_ticket_name("feat(bug-fix-123): fix issue") == "bug-fix-123"
        assert extract_ticket_name("Completed ticket: update-api-v3") == "update-api-v3"

    def test_handles_empty_and_whitespace(self):
        """Should handle empty and whitespace-only messages."""
        assert extract_ticket_name("") is None
        assert extract_ticket_name("   ") is None
        assert extract_ticket_name("\n\n") is None

    def test_prioritizes_patterns_correctly(self):
        """Should prioritize ticket/ pattern over other patterns."""
        # ticket/ pattern should be found first
        commit_msg = "ticket/add-feature - feat(other-ticket): something"
        assert extract_ticket_name(commit_msg) == "add-feature"

        # If no ticket/ pattern, should use conventional commit
        commit_msg = "feat(add-feature): implement new API"
        assert extract_ticket_name(commit_msg) == "add-feature"


class TestParseTicketNameFromCommit:
    """Test cases for parse_ticket_name_from_commit function."""

    def test_returns_fallback_sha_when_no_ticket_found(self):
        """Should return fallback SHA when no ticket pattern is found."""
        assert parse_ticket_name_from_commit("Random commit", "abc123") == "abc123"
        assert parse_ticket_name_from_commit("Update README", "def456") == "def456"

    def test_returns_unknown_when_no_ticket_and_no_fallback(self):
        """Should return 'unknown' when no ticket and no fallback provided."""
        assert parse_ticket_name_from_commit("Random commit") == "unknown"
        assert parse_ticket_name_from_commit("Update README", None) == "unknown"

    def test_prefers_ticket_name_over_fallback(self):
        """Should return ticket name even when fallback is provided."""
        assert parse_ticket_name_from_commit("ticket/add-feature", "abc123") == "add-feature"
        assert parse_ticket_name_from_commit("feat(bug-fix): fix", "def456") == "bug-fix"

    def test_handles_empty_message_with_fallback(self):
        """Should return fallback for empty message."""
        assert parse_ticket_name_from_commit("", "abc123") == "abc123"
        assert parse_ticket_name_from_commit("", None) == "unknown"

    def test_all_patterns_with_fallback(self):
        """Should extract ticket name from all supported patterns even with fallback."""
        # All these should return ticket name, not fallback
        assert parse_ticket_name_from_commit("ticket/add-feature", "sha") == "add-feature"
        assert parse_ticket_name_from_commit("Completed ticket: fix-bug", "sha") == "fix-bug"
        assert parse_ticket_name_from_commit("feat(update-docs): docs", "sha") == "update-docs"
        assert parse_ticket_name_from_commit("fix: critical-bug-fix", "sha") == "critical-bug-fix"

        body_msg = "feat: something\n\nticket: body-ticket"
        assert parse_ticket_name_from_commit(body_msg, "sha") == "body-ticket"


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_handles_special_characters_in_ticket_names(self):
        """Should handle hyphens and numbers but not other special chars."""
        # Valid: hyphens and numbers
        assert extract_ticket_name("ticket/add-feature-123") == "add-feature-123"

        # The regex only allows [a-z0-9-], so underscores and dots act as delimiters
        # It will match the part before the special character
        assert extract_ticket_name("ticket/add_feature") == "add"  # matches up to underscore
        assert extract_ticket_name("ticket/add.feature") == "add"  # matches up to dot

    def test_handles_very_long_ticket_names(self):
        """Should handle very long ticket names."""
        long_name = "implement-very-long-ticket-name-with-many-parts-123"
        assert extract_ticket_name(f"ticket/{long_name}") == long_name
        assert extract_ticket_name(f"feat({long_name}): description") == long_name

    def test_handles_ticket_name_at_different_positions(self):
        """Should find ticket pattern regardless of position in message."""
        # At start
        assert extract_ticket_name("ticket/add-feature - initial commit") == "add-feature"

        # In middle
        assert extract_ticket_name("Update ticket/fix-bug component") == "fix-bug"

        # At end
        assert extract_ticket_name("Initial commit for ticket/update-docs") == "update-docs"

    def test_conventional_commit_with_description_and_body(self):
        """Should handle conventional commits with full structure."""
        commit_msg = """feat(add-auth): implement authentication system

This commit adds a complete authentication system with:
- JWT token support
- User registration
- Login/logout functionality

Breaking changes:
- Old auth system removed

ticket: add-auth
"""
        # Should match from scope, not body (scope is checked first)
        assert extract_ticket_name(commit_msg) == "add-auth"

    def test_conventional_commit_body_only_ticket_field(self):
        """Should extract from body when no other pattern matches."""
        commit_msg = """Update documentation

This commit updates the API documentation
with the latest endpoint changes.

ticket: update-docs-123
"""
        assert extract_ticket_name(commit_msg) == "update-docs-123"

    def test_multiple_ticket_patterns_uses_first_match(self):
        """Should use the first matching pattern found."""
        # ticket/ pattern is checked first, so it wins
        commit_msg = "ticket/first-ticket feat(second-ticket): something"
        assert extract_ticket_name(commit_msg) == "first-ticket"

        # If no ticket/, completed ticket is checked next
        commit_msg = "Completed ticket: first-ticket feat(second-ticket): something"
        assert extract_ticket_name(commit_msg) == "first-ticket"
