"""Unit tests for create-tickets validation and archiving."""

import time
from pathlib import Path

import pytest

from cli.commands.create_tickets import _archive_tickets, _validate_ticket_filenames


class TestValidateTicketFilenames:
    """Test ticket filename validation against epic YAML."""

    def test_validates_successfully_with_matching_filenames(self, tmp_path):
        """Should return valid when all ticket filenames match epic IDs."""
        epic_file = tmp_path / "test.epic.yaml"
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()

        epic_file.write_text("""
tickets:
  - id: data-models-1
    title: Test
  - id: database-schema-1
    title: Test
""")

        (tickets_dir / "data-models-1.md").write_text("# Ticket")
        (tickets_dir / "database-schema-1.md").write_text("# Ticket")

        is_valid, mismatches = _validate_ticket_filenames(epic_file, tickets_dir)

        assert is_valid is True
        assert mismatches == []

    def test_validates_nested_epic_structure(self, tmp_path):
        """Should validate tickets nested under epic: key."""
        epic_file = tmp_path / "test.epic.yaml"
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()

        epic_file.write_text("""
epic:
  name: Test Epic
  tickets:
    - id: ticket-1
      title: Test
    - id: ticket-2
      title: Test
""")

        (tickets_dir / "ticket-1.md").write_text("# Ticket")
        (tickets_dir / "ticket-2.md").write_text("# Ticket")

        is_valid, mismatches = _validate_ticket_filenames(epic_file, tickets_dir)

        assert is_valid is True
        assert mismatches == []

    def test_detects_mismatched_filenames(self, tmp_path):
        """Should detect when filenames don't match ticket IDs."""
        epic_file = tmp_path / "test.epic.yaml"
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()

        epic_file.write_text("""
tickets:
  - id: data-models-1
    title: Test
  - id: database-schema-1
    title: Test
""")

        (tickets_dir / "ticket-001-data-models.md").write_text("# Ticket")
        (tickets_dir / "ticket-002-database.md").write_text("# Ticket")

        is_valid, mismatches = _validate_ticket_filenames(epic_file, tickets_dir)

        assert is_valid is False
        assert len(mismatches) == 2
        assert mismatches[0]["ticket_id"] == "data-models-1"
        assert mismatches[0]["expected_file"] == "data-models-1.md"
        assert "ticket-001-data-models.md" in mismatches[0]["found_files"]

    def test_finds_similar_files_for_mismatches(self, tmp_path):
        """Should list similar files that might be misnamed."""
        epic_file = tmp_path / "test.epic.yaml"
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()

        epic_file.write_text("""
tickets:
  - id: user-auth-api
    title: Test
""")

        (tickets_dir / "001-user-auth-api.md").write_text("# Ticket")
        (tickets_dir / "user-auth-something.md").write_text("# Ticket")

        is_valid, mismatches = _validate_ticket_filenames(epic_file, tickets_dir)

        assert is_valid is False
        assert len(mismatches) == 1
        # Should find both similar files
        similar_files = mismatches[0]["found_files"]
        assert "001-user-auth-api.md" in similar_files
        assert "user-auth-something.md" in similar_files

    def test_handles_empty_tickets_list(self, tmp_path):
        """Should return valid when no tickets to validate."""
        epic_file = tmp_path / "test.epic.yaml"
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()

        epic_file.write_text("tickets: []")

        is_valid, mismatches = _validate_ticket_filenames(epic_file, tickets_dir)

        assert is_valid is True
        assert mismatches == []

    def test_handles_missing_ticket_id(self, tmp_path):
        """Should skip tickets without ID field."""
        epic_file = tmp_path / "test.epic.yaml"
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()

        epic_file.write_text("""
tickets:
  - title: Test without ID
  - id: valid-ticket
    title: Test
""")

        (tickets_dir / "valid-ticket.md").write_text("# Ticket")

        is_valid, mismatches = _validate_ticket_filenames(epic_file, tickets_dir)

        assert is_valid is True

    def test_handles_invalid_yaml(self, tmp_path):
        """Should return error for invalid YAML."""
        epic_file = tmp_path / "test.epic.yaml"
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()

        epic_file.write_text("invalid: yaml: [unclosed")

        is_valid, mismatches = _validate_ticket_filenames(epic_file, tickets_dir)

        assert is_valid is False
        assert "error" in mismatches[0]


class TestArchiveTickets:
    """Test ticket directory archiving."""

    def test_archives_tickets_directory_with_timestamp(self, tmp_path):
        """Should move tickets directory to artifacts with unix timestamp."""
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "ticket-1.md").write_text("# Ticket 1")
        (tickets_dir / "ticket-2.md").write_text("# Ticket 2")

        artifacts_dir = tmp_path / "artifacts"

        # Get current time for comparison
        before_timestamp = int(time.time())

        _archive_tickets(tickets_dir, artifacts_dir)

        after_timestamp = int(time.time())

        # Tickets directory should be gone
        assert not tickets_dir.exists()

        # Archive should exist in artifacts
        assert artifacts_dir.exists()
        archives = list(artifacts_dir.glob("*-tickets"))
        assert len(archives) == 1

        # Archive name should be timestamp-tickets
        archive_name = archives[0].name
        timestamp_str = archive_name.replace("-tickets", "")
        timestamp = int(timestamp_str)
        assert before_timestamp <= timestamp <= after_timestamp

        # Archive should contain original files
        archived_tickets = archives[0]
        assert (archived_tickets / "ticket-1.md").exists()
        assert (archived_tickets / "ticket-2.md").exists()

    def test_creates_artifacts_directory_if_missing(self, tmp_path):
        """Should create artifacts directory if it doesn't exist."""
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "ticket-1.md").write_text("# Ticket")

        artifacts_dir = tmp_path / "artifacts"
        assert not artifacts_dir.exists()

        _archive_tickets(tickets_dir, artifacts_dir)

        assert artifacts_dir.exists()
        assert not tickets_dir.exists()

    def test_does_nothing_when_tickets_dir_missing(self, tmp_path):
        """Should do nothing when tickets directory doesn't exist."""
        tickets_dir = tmp_path / "tickets"
        artifacts_dir = tmp_path / "artifacts"

        # Should not raise error
        _archive_tickets(tickets_dir, artifacts_dir)

        # Should not create anything
        assert not tickets_dir.exists()
        assert not artifacts_dir.exists()

    def test_preserves_all_files_and_subdirectories(self, tmp_path):
        """Should archive entire tickets directory structure."""
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "ticket-1.md").write_text("# Ticket 1")

        subdir = tickets_dir / "notes"
        subdir.mkdir()
        (subdir / "notes.txt").write_text("Notes")

        artifacts_dir = tmp_path / "artifacts"

        _archive_tickets(tickets_dir, artifacts_dir)

        # Find archive
        archives = list(artifacts_dir.glob("*-tickets"))
        archived_tickets = archives[0]

        # Check structure preserved
        assert (archived_tickets / "ticket-1.md").exists()
        assert (archived_tickets / "notes").is_dir()
        assert (archived_tickets / "notes" / "notes.txt").exists()
