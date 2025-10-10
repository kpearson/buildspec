"""Utility functions for validating epic YAML files and detecting oversized epics."""

import os
from typing import Dict

import yaml


def parse_epic_yaml(epic_file_path: str) -> Dict:
    """
    Parse epic YAML file and extract ticket count for validation.

    Supports two epic formats:
    1. Original format: epic, description, ticket_count, tickets
    2. Rich format: id, title, description, goals, success_criteria, coordination_requirements, tickets

    Args:
        epic_file_path: Absolute path to epic YAML file

    Returns:
        dict with keys: 'ticket_count', 'epic', 'tickets'
        - epic: epic title (from 'epic' or 'title' field)
        - ticket_count: number of tickets (explicit or len(tickets))
        - tickets: list of ticket dicts

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

    # Check if this is the rich format (has 'id' and 'title') or original format (has 'epic')
    if 'id' in epic_data and 'title' in epic_data:
        # Rich format
        epic_title = epic_data.get('title', epic_data.get('id', 'Unknown Epic'))
        tickets = epic_data.get('tickets', [])
        ticket_count = epic_data.get('ticket_count', len(tickets))
    elif 'epic' in epic_data:
        # Original format
        epic_title = epic_data['epic']
        tickets = epic_data.get('tickets', [])
        ticket_count = epic_data.get('ticket_count', len(tickets))
    else:
        raise KeyError("Epic file must have either 'epic' field (original format) or 'id'+'title' fields (rich format)")

    # Validate tickets exist
    if not tickets:
        raise ValueError(f"Epic file has no tickets: {epic_file_path}")

    return {
        'ticket_count': ticket_count,
        'epic': epic_title,
        'tickets': tickets
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
