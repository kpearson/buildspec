"""Review feedback configuration and dependency injection.

This module provides the ReviewTargets dataclass, which serves as a
dependency injection container for review feedback application workflows.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal


@dataclass
class ReviewTargets:
    """Dependency injection container for review feedback configuration.

    This dataclass encapsulates all file paths, directories, and metadata
    required to apply review feedback to an epic or epic-file. It serves
    as a contract between callers (create_epic.py, create_tickets.py) and
    the review feedback application logic.

    Usage Pattern:
        Instantiate ReviewTargets with specific paths and configuration,
        then pass to apply_review_feedback() for processing. This allows
        the same review feedback logic to work for different review types
        (epic-file-review, epic-review) by varying the configuration.

    Example:
        targets = ReviewTargets(
            primary_file=Path(".epics/my-epic/my-epic.epic.yaml"),
            additional_files=[],
            editable_directories=[Path(".epics/my-epic")],
            artifacts_dir=Path(".epics/my-epic/artifacts"),
            updates_doc_name="epic-file-review-updates.md",
            log_file_name="epic-file-review.log",
            error_file_name="epic-file-review-errors.log",
            epic_name="my-epic",
            reviewer_session_id="550e8400-e29b-41d4-a716-446655440000",
            review_type="epic-file"
        )

    Fields:
        primary_file: Path to the main target file (typically epic YAML).
        additional_files: List of additional files to edit (e.g., ticket
            markdown files for epic-review).
        editable_directories: List of directories where files can be
            modified during review feedback application.
        artifacts_dir: Directory where review artifacts and logs are
            written.
        updates_doc_name: Filename for the documentation of changes made
            during review feedback application.
        log_file_name: Filename for stdout logs from the review feedback
            session.
        error_file_name: Filename for stderr logs from the review feedback
            session.
        epic_name: Name of the epic being reviewed (for documentation).
        reviewer_session_id: Session ID of the review session that
            generated the feedback.
        review_type: Type of review - "epic-file" for epic YAML only, or
            "epic" for epic YAML plus all ticket files.

    Note:
        No validation is performed in this dataclass. Validation happens
        at call sites before instantiating ReviewTargets.
    """

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
