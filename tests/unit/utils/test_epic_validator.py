"""Tests for epic validator utility."""

import os
import tempfile

import pytest
import yaml

from cli.utils.epic_validator import parse_epic_yaml, validate_ticket_count


class TestParseEpicYaml:
    """Test cases for parse_epic_yaml function."""

    def test_parses_valid_epic_yaml(self):
        """Should parse valid epic YAML and extract required fields."""
        epic_data = {
            'epic': 'Test Epic',
            'ticket_count': 15,
            'tickets': [
                {'id': 'ticket-1', 'description': 'First ticket'},
                {'id': 'ticket-2', 'description': 'Second ticket'}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(epic_data, f)
            temp_path = f.name

        try:
            result = parse_epic_yaml(temp_path)
            assert result['ticket_count'] == 15
            assert result['epic'] == 'Test Epic'
            assert len(result['tickets']) == 2
            assert result['tickets'][0]['id'] == 'ticket-1'
        finally:
            os.unlink(temp_path)

    def test_raises_file_not_found_for_missing_file(self):
        """Should raise FileNotFoundError if epic file doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            parse_epic_yaml('/nonexistent/path/to/epic.yaml')

        assert 'Epic file does not exist' in str(exc_info.value)
        assert '/nonexistent/path/to/epic.yaml' in str(exc_info.value)

    def test_raises_yaml_error_for_malformed_yaml(self):
        """Should raise yaml.YAMLError if YAML is malformed."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('invalid: yaml: content:\n  - broken\n  indentation')
            temp_path = f.name

        try:
            with pytest.raises(yaml.YAMLError) as exc_info:
                parse_epic_yaml(temp_path)

            assert 'Failed to parse YAML file' in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_parses_epic_without_explicit_ticket_count(self):
        """Should derive ticket_count from len(tickets) if not provided."""
        epic_data = {
            'epic': 'Test Epic',
            'tickets': [{'id': 'ticket-1'}]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(epic_data, f)
            temp_path = f.name

        try:
            result = parse_epic_yaml(temp_path)
            assert result['ticket_count'] == 1  # Derived from len(tickets)
            assert result['epic'] == 'Test Epic'
        finally:
            os.unlink(temp_path)

    def test_raises_key_error_for_missing_epic_field(self):
        """Should raise KeyError if neither epic nor id+title fields present."""
        epic_data = {
            'ticket_count': 15,
            'tickets': [{'id': 'ticket-1'}]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(epic_data, f)
            temp_path = f.name

        try:
            with pytest.raises(KeyError) as exc_info:
                parse_epic_yaml(temp_path)

            error_msg = str(exc_info.value)
            assert 'Epic file must have either' in error_msg
            assert 'epic' in error_msg or 'title' in error_msg
        finally:
            os.unlink(temp_path)

    def test_raises_value_error_for_missing_tickets_field(self):
        """Should raise ValueError if tickets field is missing or empty."""
        epic_data = {
            'epic': 'Test Epic',
            'ticket_count': 15
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(epic_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                parse_epic_yaml(temp_path)

            assert 'Epic file has no tickets' in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_raises_key_error_for_multiple_missing_fields(self):
        """Should raise KeyError when required epic identification fields missing."""
        epic_data = {
            'description': 'Some description'
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(epic_data, f)
            temp_path = f.name

        try:
            with pytest.raises(KeyError) as exc_info:
                parse_epic_yaml(temp_path)

            error_msg = str(exc_info.value)
            assert 'Epic file must have either' in error_msg
            # Should mention either epic or id+title requirement
            assert 'epic' in error_msg or 'title' in error_msg
        finally:
            os.unlink(temp_path)

    def test_raises_value_error_for_empty_file(self):
        """Should raise ValueError if epic file is empty."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Write empty content
            f.write('')
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                parse_epic_yaml(temp_path)

            assert 'Epic file is empty' in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_parses_epic_with_additional_fields(self):
        """Should parse epic with additional fields beyond required ones."""
        epic_data = {
            'epic': 'Test Epic',
            'ticket_count': 10,
            'tickets': [{'id': 'ticket-1'}],
            'description': 'Additional description',
            'acceptance_criteria': ['Criteria 1', 'Criteria 2'],
            'custom_field': 'custom value'
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(epic_data, f)
            temp_path = f.name

        try:
            result = parse_epic_yaml(temp_path)
            # Should only return the required fields
            assert set(result.keys()) == {'ticket_count', 'epic', 'tickets'}
            assert result['ticket_count'] == 10
            assert result['epic'] == 'Test Epic'
        finally:
            os.unlink(temp_path)

    def test_raises_value_error_for_zero_tickets(self):
        """Should raise ValueError for epic with zero tickets."""
        epic_data = {
            'epic': 'Empty Epic',
            'ticket_count': 0,
            'tickets': []
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(epic_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                parse_epic_yaml(temp_path)

            assert 'Epic file has no tickets' in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_parses_epic_with_large_ticket_count(self):
        """Should parse epic with large ticket count."""
        epic_data = {
            'epic': 'Large Epic',
            'ticket_count': 100,
            'tickets': [{'id': f'ticket-{i}'} for i in range(100)]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(epic_data, f)
            temp_path = f.name

        try:
            result = parse_epic_yaml(temp_path)
            assert result['ticket_count'] == 100
            assert len(result['tickets']) == 100
        finally:
            os.unlink(temp_path)


class TestValidateTicketCount:
    """Test cases for validate_ticket_count function."""

    def test_returns_false_for_count_below_threshold(self):
        """Should return False for ticket counts below 13."""
        assert validate_ticket_count(0) is False
        assert validate_ticket_count(1) is False
        assert validate_ticket_count(5) is False
        assert validate_ticket_count(10) is False
        assert validate_ticket_count(12) is False

    def test_returns_true_for_count_at_threshold(self):
        """Should return True for ticket count exactly at 13."""
        assert validate_ticket_count(13) is True

    def test_returns_true_for_count_above_threshold(self):
        """Should return True for ticket counts above 13."""
        assert validate_ticket_count(14) is True
        assert validate_ticket_count(15) is True
        assert validate_ticket_count(20) is True
        assert validate_ticket_count(50) is True
        assert validate_ticket_count(100) is True

    def test_boundary_value_12(self):
        """Should return False for boundary value 12 (just below threshold)."""
        assert validate_ticket_count(12) is False

    def test_boundary_value_13(self):
        """Should return True for boundary value 13 (exactly at threshold)."""
        assert validate_ticket_count(13) is True


class TestIntegration:
    """Integration tests combining parse_epic_yaml and validate_ticket_count."""

    def test_parses_and_validates_oversized_epic(self):
        """Should parse epic and correctly identify it needs splitting."""
        epic_data = {
            'epic': 'Oversized Epic',
            'ticket_count': 15,
            'tickets': [{'id': f'ticket-{i}'} for i in range(15)]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(epic_data, f)
            temp_path = f.name

        try:
            result = parse_epic_yaml(temp_path)
            needs_split = validate_ticket_count(result['ticket_count'])
            assert needs_split is True
        finally:
            os.unlink(temp_path)

    def test_parses_and_validates_normal_epic(self):
        """Should parse epic and correctly identify it doesn't need splitting."""
        epic_data = {
            'epic': 'Normal Epic',
            'ticket_count': 10,
            'tickets': [{'id': f'ticket-{i}'} for i in range(10)]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(epic_data, f)
            temp_path = f.name

        try:
            result = parse_epic_yaml(temp_path)
            needs_split = validate_ticket_count(result['ticket_count'])
            assert needs_split is False
        finally:
            os.unlink(temp_path)

    def test_parses_and_validates_boundary_epic(self):
        """Should correctly handle boundary case of 13 tickets."""
        epic_data = {
            'epic': 'Boundary Epic',
            'ticket_count': 13,
            'tickets': [{'id': f'ticket-{i}'} for i in range(13)]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(epic_data, f)
            temp_path = f.name

        try:
            result = parse_epic_yaml(temp_path)
            needs_split = validate_ticket_count(result['ticket_count'])
            # 13 tickets should trigger split
            assert needs_split is True
        finally:
            os.unlink(temp_path)
