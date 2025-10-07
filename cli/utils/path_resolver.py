"""Path resolution utilities for CLI arguments."""

from pathlib import Path
from typing import Optional


class PathResolutionError(Exception):
    """Raised when path resolution fails."""
    pass


def resolve_file_argument(
    arg: str,
    expected_pattern: Optional[str] = None,
    arg_name: str = "file"
) -> Path:
    """Resolve file path from CLI argument with smart handling.
    
    Handles:
    1. Line number notation (e.g., "file.md:123" -> "file.md")
    2. Directory inference (if dir contains exactly one file matching pattern)
    
    Args:
        arg: Raw argument string from CLI
        expected_pattern: Optional substring to look for when inferring from directory
                         (e.g., "spec" for planning docs, "epic" for epic files)
        arg_name: Name of the argument for error messages
    
    Returns:
        Resolved Path object
        
    Raises:
        PathResolutionError: If path cannot be resolved
    """
    # Strip line number notation
    if ":" in arg:
        arg = arg.split(":", 1)[0]
    
    path = Path(arg)
    
    # If it's a file that exists, return it
    if path.is_file():
        return path
    
    # If it's a directory and we have a pattern, try to infer the file
    if path.is_dir() and expected_pattern:
        matching_files = [
            f for f in path.iterdir()
            if f.is_file() and expected_pattern.lower() in f.name.lower()
        ]
        
        if len(matching_files) == 0:
            raise PathResolutionError(
                f"{arg_name.capitalize()} not found: No files containing '{expected_pattern}' in directory: {path}"
            )
        elif len(matching_files) > 1:
            files_list = "\n  ".join(f.name for f in matching_files)
            raise PathResolutionError(
                f"{arg_name.capitalize()} ambiguous: Multiple files containing '{expected_pattern}' found in {path}:\n  {files_list}\n"
                f"Please specify the exact file."
            )
        
        return matching_files[0]
    
    # If it's a directory but no pattern provided
    if path.is_dir():
        raise PathResolutionError(
            f"{arg_name.capitalize()} is a directory: {path}\n"
            f"Please specify the exact file."
        )
    
    # Path doesn't exist
    raise PathResolutionError(
        f"{arg_name.capitalize()} not found: {path}"
    )
