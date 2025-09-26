#!/bin/bash
# validate-epic-creation.sh - PreToolUse hook for create-epic agent validation
# This hook runs before Task tool use - exits fast for non-epic tasks

set -euo pipefail

# Read the tool call from stdin
TOOL_CALL=$(cat)

# FAST EXIT: Check if this looks like epic creation
# Look for epic-related keywords in the prompt first
if ! echo "$TOOL_CALL" | grep -q "epic\|planning.*document\|coordination\|\.md"; then
    # Not epic-related, pass through immediately
    echo "$TOOL_CALL"
    exit 0
fi

# Extract the prompt to look for planning document paths
PROMPT=$(echo "$TOOL_CALL" | jq -r '.prompt // ""')

# Look for planning document paths in the prompt
PLANNING_DOC_PATH=$(echo "$PROMPT" | grep -oE '/[^[:space:]]+\.md(:[0-9]+)?' | head -1 || echo "")

# If no .md file path found, this isn't epic creation
if [ -z "$PLANNING_DOC_PATH" ]; then
    echo "$TOOL_CALL"
    exit 0
fi

echo "🔍 Validating epic creation for: $PLANNING_DOC_PATH" >&2

# Run our validation script
VALIDATION_OUTPUT=$(/Users/kit/.claude/scripts/epic-paths.sh "$PLANNING_DOC_PATH" 2>&1)

# Check if validation passed
if echo "$VALIDATION_OUTPUT" | grep -q "SPEC_EXISTS=false"; then
    ERROR_MSG=$(echo "$VALIDATION_OUTPUT" | grep "ERROR_MESSAGE=" | cut -d'=' -f2-)
    echo "❌ VALIDATION FAILED: $ERROR_MSG" >&2
    echo "🛑 Blocking create-epic agent execution to prevent token waste" >&2
    exit 1
fi

if echo "$VALIDATION_OUTPUT" | grep -q "EPIC_EXISTS=true"; then
    EPIC_FILE=$(echo "$VALIDATION_OUTPUT" | grep "EPIC_FILE=" | cut -d'=' -f2-)
    echo "❌ VALIDATION FAILED: Epic file already exists at $EPIC_FILE" >&2
    echo "🛑 Remove existing file or use --force flag" >&2
    exit 1
fi

echo "✅ Validation passed - proceeding with epic creation" >&2

# If we get here, validation passed - allow the tool call
echo "$TOOL_CALL"