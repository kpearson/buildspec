#!/bin/bash
# epic-paths.sh - Extract paths for epic file creation
# Usage: epic-paths.sh <planning-doc-path>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <planning-doc-path>"
    echo "Example: $0 planning/user-auth-spec.md"
    exit 1
fi

PLANNING_DOC="$1"

# Clean the path - remove any trailing line numbers (e.g., :38)
CLEAN_PLANNING_DOC=$(echo "$PLANNING_DOC" | sed 's/:[0-9]*$//')

# Validate input file exists
if [ ! -f "$CLEAN_PLANNING_DOC" ]; then
    echo "SPEC_EXISTS=false"
    echo "ERROR_MESSAGE=Planning document '$CLEAN_PLANNING_DOC' not found"
    exit 0  # Don't fail the script, let agent handle it
fi

echo "SPEC_EXISTS=true"
PLANNING_DOC="$CLEAN_PLANNING_DOC"

# Extract paths using absolute path resolution
TARGET_DIR=$(dirname "$(realpath "$PLANNING_DOC")")
BASE_NAME=$(basename "$PLANNING_DOC" .md)
EPIC_FILE="$TARGET_DIR/$BASE_NAME.epic.yaml"

# Output variables for use in other scripts or tools
echo "TARGET_DIR=$TARGET_DIR"
echo "BASE_NAME=$BASE_NAME"
echo "EPIC_FILE=$EPIC_FILE"

# Check if epic file already exists
if [ -f "$EPIC_FILE" ]; then
    echo "EPIC_EXISTS=true"
    echo "EPIC_SIZE=$(wc -c < "$EPIC_FILE")"
    echo "EPIC_MODIFIED=$(stat -f %Sm -t '%Y-%m-%d %H:%M:%S' "$EPIC_FILE" 2>/dev/null || stat -c '%y' "$EPIC_FILE" 2>/dev/null)"
else
    echo "EPIC_EXISTS=false"
fi