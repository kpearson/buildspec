#!/bin/bash

# validate-epic.sh - Pre-flight validation for epic and ticket execution
# Usage: ./validate-epic.sh <epic-file-path> [--ticket <ticket-path>]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() { echo -e "${RED}❌ ERROR: $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  WARNING: $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }

# Function to extract TOML config from markdown
extract_toml_config() {
    local file="$1"
    # Find lines between ```toml and ```
    awk '/^```toml$/,/^```$/ {if (!/^```/) print}' "$file"
}

# Function to parse TOML and extract ticket info
parse_tickets() {
    local toml_content="$1"

    # Extract ticket IDs and paths using grep and sed
    echo "$toml_content" | grep -E '^\[\[tickets\]\]|^id\s*=|^path\s*=' | \
    while IFS= read -r line; do
        if [[ "$line" == "[[tickets]]" ]]; then
            echo "TICKET_START"
        elif [[ "$line" =~ ^id[[:space:]]*=[[:space:]]*\"(.*)\" ]]; then
            echo "ID:${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^path[[:space:]]*=[[:space:]]*\"(.*)\" ]]; then
            echo "PATH:${BASH_REMATCH[1]}"
        fi
    done
}

# Function to validate epic file format
validate_epic_format() {
    local epic_file="$1"

    print_info "Validating epic file format: $epic_file"

    # Check if file exists
    if [[ ! -f "$epic_file" ]]; then
        print_error "Epic file does not exist: $epic_file"
        return 1
    fi

    # Check if file contains TOML config block
    if ! grep -q '^```toml$' "$epic_file"; then
        print_error "Epic file missing TOML configuration block (\`\`\`toml)"
        return 1
    fi

    # Extract TOML config
    local toml_config
    toml_config=$(extract_toml_config "$epic_file")

    if [[ -z "$toml_config" ]]; then
        print_error "Empty TOML configuration in epic file"
        return 1
    fi

    # Check required epic fields
    if ! echo "$toml_config" | grep -q '^\[epic\]'; then
        print_error "Missing [epic] section in TOML config"
        return 1
    fi

    if ! echo "$toml_config" | grep -q '^name\s*='; then
        print_error "Missing epic name in TOML config"
        return 1
    fi

    # Check for tickets
    if ! echo "$toml_config" | grep -q '^\[\[tickets\]\]'; then
        print_error "No tickets defined in epic file"
        return 1
    fi

    print_success "Epic file format is valid"
    return 0
}

# Function to validate all ticket files exist
validate_ticket_files() {
    local epic_file="$1"
    local epic_dir
    epic_dir=$(dirname "$epic_file")

    print_info "Validating ticket file existence..."

    # Skip if epic file doesn't exist (already reported)
    if [[ ! -f "$epic_file" ]]; then
        return 1
    fi

    local toml_config
    toml_config=$(extract_toml_config "$epic_file")

    local current_id=""
    local current_path=""
    local ticket_count=0
    local missing_count=0

    # Parse tickets and check each file
    while IFS= read -r line; do
        case "$line" in
            "TICKET_START")
                # Process previous ticket if we have both id and path
                if [[ -n "$current_id" && -n "$current_path" ]]; then
                    ((ticket_count++))
                    # Resolve path relative to epic file
                    local full_path
                    if [[ "$current_path" = /* ]]; then
                        full_path="$current_path"
                    else
                        full_path="$epic_dir/$current_path"
                    fi

                    if [[ -f "$full_path" ]]; then
                        print_success "Ticket file exists: $current_id -> $full_path"
                    else
                        print_error "Ticket file missing: $current_id -> $full_path"
                        ((missing_count++))
                    fi
                fi
                current_id=""
                current_path=""
                ;;
            ID:*)
                current_id="${line#ID:}"
                ;;
            PATH:*)
                current_path="${line#PATH:}"
                ;;
        esac
    done < <(parse_tickets "$toml_config")

    # Handle last ticket
    if [[ -n "$current_id" && -n "$current_path" ]]; then
        ((ticket_count++))
        local full_path
        if [[ "$current_path" = /* ]]; then
            full_path="$current_path"
        else
            full_path="$epic_dir/$current_path"
        fi

        if [[ -f "$full_path" ]]; then
            print_success "Ticket file exists: $current_id -> $full_path"
        else
            print_error "Ticket file missing: $current_id -> $full_path"
            ((missing_count++))
        fi
    fi

    print_info "Found $ticket_count ticket(s), $missing_count missing"

    if [[ $missing_count -gt 0 ]]; then
        return 1
    fi

    return 0
}

# Function to validate single ticket file format
validate_ticket_format() {
    local ticket_file="$1"

    print_info "Validating ticket file format: $ticket_file"

    # Check if file exists
    if [[ ! -f "$ticket_file" ]]; then
        print_error "Ticket file does not exist: $ticket_file"
        return 1
    fi

    # Check required sections
    local required_sections=(
        "Issue Summary"
        "Story"
        "Acceptance Criteria"
        "Technical Details"
        "Implementation Details"
        "Definition of Done"
    )

    local missing_sections=()
    for section in "${required_sections[@]}"; do
        if ! grep -q "## $section" "$ticket_file"; then
            missing_sections+=("$section")
        fi
    done

    if [[ ${#missing_sections[@]} -gt 0 ]]; then
        print_error "Missing required sections in ticket file:"
        for section in "${missing_sections[@]}"; do
            print_error "  - $section"
        done
        return 1
    fi

    print_success "Ticket file format is valid"
    return 0
}

# Function to check git repository state
validate_git_state() {
    print_info "Validating git repository state..."

    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository"
        return 1
    fi

    # Check for uncommitted changes
    if ! git diff --quiet || ! git diff --cached --quiet; then
        print_warning "Working directory has uncommitted changes"
        print_info "Consider committing or stashing changes before running epic"
    fi

    # Check if we're on a reasonable branch (not detached HEAD)
    local current_branch
    current_branch=$(git branch --show-current)
    if [[ -z "$current_branch" ]]; then
        print_error "Currently in detached HEAD state"
        return 1
    fi

    print_success "Git repository state is valid (on branch: $current_branch)"
    return 0
}

# Function to check for existing epic/ticket branches
validate_branch_conflicts() {
    local epic_file="$1"
    local epic_name

    print_info "Checking for branch conflicts..."

    # Skip if epic file doesn't exist (already reported)
    if [[ ! -f "$epic_file" ]]; then
        return 1
    fi

    # Extract epic name from file
    local toml_config
    toml_config=$(extract_toml_config "$epic_file")
    epic_name=$(echo "$toml_config" | grep '^name\s*=' | sed 's/^name\s*=\s*"\(.*\)"/\1/')

    if [[ -z "$epic_name" ]]; then
        print_error "Could not extract epic name for branch validation"
        return 1
    fi

    # Convert epic name to branch name (lowercase, replace spaces with dashes)
    local epic_branch_name="epic/$(echo "$epic_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"

    # Check if epic branch already exists
    if git rev-parse --verify "$epic_branch_name" > /dev/null 2>&1; then
        print_error "Epic branch already exists: $epic_branch_name"
        print_info "Either checkout existing branch or delete it: git branch -D $epic_branch_name"
        return 1
    fi

    # Check for ticket branches (this is more complex, would need to parse all ticket IDs)
    # For now, just check if there are any ticket/ branches
    local existing_ticket_branches
    existing_ticket_branches=$(git branch --list 'ticket/*' | wc -l)
    if [[ $existing_ticket_branches -gt 0 ]]; then
        print_warning "Found existing ticket branches:"
        git branch --list 'ticket/*' | sed 's/^/  /'
        print_info "These may conflict with new epic execution"
    fi

    print_success "No branch conflicts detected for epic: $epic_branch_name"
    return 0
}

# Function to validate workspace setup
validate_workspace() {
    local epic_file="$1"
    local epic_dir
    epic_dir=$(dirname "$epic_file")

    print_info "Validating workspace setup..."

    # Check if artifacts directory already exists
    if [[ -d "$epic_dir/artifacts" ]]; then
        print_warning "Artifacts directory already exists: $epic_dir/artifacts"
        print_info "Existing artifacts may be overwritten"
    fi

    # Check write permissions
    if [[ ! -w "$epic_dir" ]]; then
        print_error "No write permission in epic directory: $epic_dir"
        return 1
    fi

    print_success "Workspace is ready"
    return 0
}

# Main validation function
main() {
    local epic_file=""
    local ticket_file=""
    local exit_code=0

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --ticket)
                ticket_file="$2"
                shift 2
                ;;
            -*)
                print_error "Unknown option: $1"
                exit 1
                ;;
            *)
                if [[ -z "$epic_file" ]]; then
                    epic_file="$1"
                else
                    print_error "Too many arguments"
                    exit 1
                fi
                shift
                ;;
        esac
    done

    if [[ -z "$epic_file" ]]; then
        echo "Usage: $0 <epic-file-path> [--ticket <ticket-path>]"
        echo ""
        echo "Validates epic file format, ticket file existence, and git state"
        echo "before running execute-epic or execute-ticket commands."
        echo ""
        echo "Options:"
        echo "  --ticket <path>  Also validate specific ticket file format"
        echo ""
        echo "Examples:"
        echo "  $0 epics/user-auth.md"
        echo "  $0 epics/user-auth.md --ticket tickets/auth-base.md"
        exit 1
    fi

    echo "🚀 Starting pre-flight validation..."
    echo ""

    # Run all validation checks
    validate_git_state || exit_code=1
    validate_epic_format "$epic_file" || exit_code=1
    validate_ticket_files "$epic_file" || exit_code=1
    validate_branch_conflicts "$epic_file" || exit_code=1
    validate_workspace "$epic_file" || exit_code=1

    # Validate specific ticket if requested
    if [[ -n "$ticket_file" ]]; then
        validate_ticket_format "$ticket_file" || exit_code=1
    fi

    echo ""
    if [[ $exit_code -eq 0 ]]; then
        print_success "✨ All pre-flight checks passed! Ready for epic execution."
    else
        print_error "❌ Pre-flight validation failed. Please fix the issues above."
    fi

    exit $exit_code
}

# Run main function with all arguments
main "$@"