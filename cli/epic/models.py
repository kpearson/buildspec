"""Type-safe data models and state enums for the epic state machine.

This module provides the foundational type system for the entire state machine,
including ticket and epic lifecycle states, and all associated data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TicketState(str, Enum):
    """Ticket lifecycle states."""

    PENDING = "PENDING"
    READY = "READY"
    BRANCH_CREATED = "BRANCH_CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_VALIDATION = "AWAITING_VALIDATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class EpicState(str, Enum):
    """Epic lifecycle states."""

    INITIALIZING = "INITIALIZING"
    EXECUTING = "EXECUTING"
    MERGING = "MERGING"
    FINALIZED = "FINALIZED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass(frozen=True)
class GitInfo:
    """Git information for a ticket."""

    branch_name: Optional[str] = None
    base_commit: Optional[str] = None
    final_commit: Optional[str] = None


@dataclass
class AcceptanceCriterion:
    """Acceptance criterion with validation status."""

    criterion: str
    met: bool = False


@dataclass(frozen=True)
class GateResult:
    """Result of a gate check."""

    passed: bool
    reason: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BuilderResult:
    """Result of a ticket builder execution."""

    success: bool
    final_commit: Optional[str] = None
    test_status: Optional[str] = None
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    error: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


@dataclass
class Ticket:
    """Ticket data model with full lifecycle tracking."""

    id: str
    path: str
    title: str
    depends_on: list[str] = field(default_factory=list)
    critical: bool = False
    state: TicketState = TicketState.PENDING
    git_info: GitInfo = field(default_factory=GitInfo)
    test_suite_status: Optional[str] = None
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    failure_reason: Optional[str] = None
    blocking_dependency: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
