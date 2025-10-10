"""Agent configuration loader for Claude CLI."""

import json
from pathlib import Path
from typing import Dict, Optional


def load_agent_config(agent_file: Path) -> Dict:
    """Load agent configuration from JSON file.

    Args:
        agent_file: Path to agent JSON file

    Returns:
        Dict containing agent configuration

    Raises:
        FileNotFoundError: If agent file doesn't exist
        json.JSONDecodeError: If agent file is invalid JSON
    """
    if not agent_file.exists():
        raise FileNotFoundError(f"Agent file not found: {agent_file}")

    with open(agent_file, 'r') as f:
        return json.load(f)


def merge_agent_configs(*agent_files: Path) -> str:
    """Merge multiple agent config files into single JSON string for Claude CLI.

    Args:
        *agent_files: Variable number of agent config file paths

    Returns:
        JSON string containing merged agent configurations

    Example:
        If agent1.json contains {"reviewer": {...}}
        and agent2.json contains {"tester": {...}}
        Returns: '{"reviewer": {...}, "tester": {...}}'
    """
    merged = {}

    for agent_file in agent_files:
        config = load_agent_config(agent_file)
        merged.update(config)

    return json.dumps(merged)


def load_builtin_agent(agent_name: str, claude_dir: Optional[Path] = None) -> Optional[str]:
    """Load a built-in agent from claude_files/agents directory.

    Args:
        agent_name: Name of agent (without .json extension)
        claude_dir: Optional claude directory path (defaults to ~/.claude)

    Returns:
        JSON string of agent config, or None if not found
    """
    if claude_dir is None:
        claude_dir = Path.home() / ".claude"

    agent_file = claude_dir / "agents" / f"{agent_name}.json"

    if not agent_file.exists():
        return None

    config = load_agent_config(agent_file)
    return json.dumps(config)
