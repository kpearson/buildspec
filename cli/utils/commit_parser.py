"""Utility functions for parsing ticket names from git commit messages."""

import re
from typing import Optional


def parse_ticket_name_from_commit(commit_message: str, fallback_sha: Optional[str] = None) -> str:
    """Extract ticket name from git commit message.

    This function attempts to extract a ticket name from various commit message formats:
    1. Branch-like patterns: "ticket/ticket-name" or "branch: ticket/ticket-name"
    2. Completion patterns: "Completed ticket: ticket-name"
    3. Conventional commits: "feat(ticket-name):", "fix(ticket-name):", etc.
    4. Conventional commits with scope: "feat: ticket-name" or "fix: ticket-name"
    5. Ticket references in body: "ticket: ticket-name" or "Ticket: ticket-name"

    If no ticket name is found, returns the fallback SHA or "unknown".

    Args:
        commit_message: Full git commit message (subject + body)
        fallback_sha: Optional commit SHA to use as fallback if no ticket found

    Returns:
        Extracted ticket name, fallback SHA (if provided), or "unknown"

    Examples:
        >>> parse_ticket_name_from_commit("ticket/add-feature")
        'add-feature'

        >>> parse_ticket_name_from_commit("feat(add-feature): implement new API")
        'add-feature'

        >>> parse_ticket_name_from_commit("fix: resolve bug\\n\\nticket: bug-fix-123")
        'bug-fix-123'

        >>> parse_ticket_name_from_commit("Completed ticket: update-docs")
        'update-docs'

        >>> parse_ticket_name_from_commit("Random commit", "abc123")
        'abc123'
    """
    if not commit_message:
        return fallback_sha or "unknown"

    # Try to extract ticket name from branch-like patterns
    # Matches: "ticket/ticket-name" or "branch: ticket/ticket-name"
    match = re.search(r"ticket/([a-z0-9-]+)", commit_message, re.IGNORECASE)
    if match:
        return match.group(1)

    # Try to extract from "Completed ticket:" pattern
    # Matches: "Completed ticket: ticket-name"
    match = re.search(r"completed\s+ticket:\s*([a-z0-9-]+)", commit_message, re.IGNORECASE)
    if match:
        return match.group(1)

    # Try to extract from conventional commit format with scope
    # Matches: "feat(ticket-name):", "fix(ticket-name):", "chore(ticket-name):", etc.
    match = re.search(
        r"^(?:feat|fix|docs|style|refactor|perf|test|chore|build|ci)\(([a-z0-9-]+)\):",
        commit_message,
        re.IGNORECASE | re.MULTILINE
    )
    if match:
        return match.group(1)

    # Try to extract from conventional commit body with scope
    # Matches: "feat: ticket-name" or "fix: ticket-name" (ticket name at start after colon)
    match = re.search(
        r"^(?:feat|fix|docs|style|refactor|perf|test|chore|build|ci):\s*([a-z0-9-]+)",
        commit_message,
        re.IGNORECASE | re.MULTILINE
    )
    if match:
        # Ensure it looks like a ticket name (contains hyphens or is multi-word)
        ticket_candidate = match.group(1)
        if "-" in ticket_candidate or len(ticket_candidate) > 15:
            return ticket_candidate

    # Try to extract from commit body with "ticket:" or "Ticket:" prefix
    # Matches: "ticket: ticket-name" or "Ticket: ticket-name"
    match = re.search(r"^ticket:\s*([a-z0-9-]+)", commit_message, re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1)

    # No ticket name found, return fallback
    return fallback_sha or "unknown"


def extract_ticket_name(commit_message: str) -> Optional[str]:
    """Extract ticket name from commit message (returns None if not found).

    This is a convenience wrapper around parse_ticket_name_from_commit that
    returns None instead of a fallback value when no ticket is found.

    Args:
        commit_message: Git commit message

    Returns:
        Ticket name if found, None otherwise

    Examples:
        >>> extract_ticket_name("ticket/add-feature")
        'add-feature'

        >>> extract_ticket_name("Random commit")
        None
    """
    result = parse_ticket_name_from_commit(commit_message, fallback_sha=None)
    return None if result == "unknown" else result
