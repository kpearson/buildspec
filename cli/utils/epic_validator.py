"""Utility functions for validating epic YAML files and detecting oversized epics."""

import os
from typing import Dict

import yaml


def parse_epic_yaml(epic_file_path: str) -> Dict:
    """
    Parse epic YAML file and extract ticket count for validation.

    Args:
        epic_file_path: Absolute path to epic YAML file

    Returns:
        dict with keys: 'ticket_count', 'epic', 'tickets'

    Raises:
        FileNotFoundError: If epic file doesn't exist
        yaml.YAMLError: If YAML is malformed
        KeyError: If required fields missing

    Examples:
        >>> parse_epic_yaml("/path/to/epic.yaml")
        {'ticket_count': 15, 'epic': 'My Epic', 'tickets': [...]}
    """
    if not os.path.exists(epic_file_path):
        raise FileNotFoundError(f"Epic file does not exist: {epic_file_path}")

    try:
        with open(epic_file_path) as f:
            epic_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML file {epic_file_path}: {e}")

    if epic_data is None:
        raise ValueError(f"Epic file is empty: {epic_file_path}")

    # Validate required fields exist
    required_fields = ['ticket_count', 'epic', 'tickets']
    missing_fields = [field for field in required_fields if field not in epic_data]

    if missing_fields:
        raise KeyError(f"Missing required fields in epic YAML: {', '.join(missing_fields)}")

    return {
        'ticket_count': epic_data['ticket_count'],
        'epic': epic_data['epic'],
        'tickets': epic_data['tickets']
    }


def validate_ticket_count(ticket_count: int) -> bool:
    """
    Check if ticket count exceeds threshold and needs splitting.

    Args:
        ticket_count: Number of tickets in epic

    Returns:
        True if ticket_count >= 13 (needs split), False otherwise

    Examples:
        >>> validate_ticket_count(12)
        False

        >>> validate_ticket_count(13)
        True

        >>> validate_ticket_count(25)
        True
    """
    return ticket_count >= 13
