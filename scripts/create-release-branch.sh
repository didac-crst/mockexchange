#!/bin/bash

# MockExchange Release Branch Creator
# Usage: ./scripts/create-release-branch.sh [patch|minor|major] [--dry-run]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [patch|minor|major] [--dry-run]"
    echo ""
    echo "Creates a new release branch with automatic version bumping."
    echo ""
    echo "Arguments:"
    echo "  patch    - Increment patch version (0.1.0 → 0.1.1)"
    echo "  minor    - Increment minor version (0.1.0 → 0.2.0)"
    echo "  major    - Increment major version (0.1.0 → 1.0.0)"
    echo "  --dry-run - Show what would be done without executing"
    echo ""
    echo "Examples:"
    echo "  $0 patch        # Create release/0.1.1 branch"
    echo "  $0 minor        # Create release/0.2.0 branch"
    echo "  $0 major        # Create release/1.0.0 branch"
    echo "  $0 patch --dry-run  # Show what would happen"
}

# Function to get the latest version from git tags
get_latest_version() {
    local silent=${1:-false}
    
    # Fetch latest tags from remote
    if [ "$silent" != "true" ]; then
        print_info "Fetching latest tags from remote..."
    fi
    git fetch --tags --quiet
    
    # Get the latest version tag
    local latest_tag=$(git tag --sort=-version:refname | grep '^v[0-9]\+\.[0-9]\+\.[0-9]\+$' | head -1)
    
    if [ -z "$latest_tag" ]; then
        print_error "No version tags found. Please create an initial tag first:"
        echo "  git tag -a v0.1.0 -m 'Initial release'"
        echo "  git push origin v0.1.0"
        exit 1
    fi
    
    # Remove 'v' prefix
    echo "${latest_tag#v}"
}

# Function to calculate new version
calculate_new_version() {
    local current_version=$1
    local bump_type=$2
    
    # Parse current version
    IFS='.' read -r major minor patch <<< "$current_version"
    
    case $bump_type in
        patch)
            patch=$((patch + 1))
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        *)
            print_error "Invalid bump type: $bump_type"
            show_usage
            exit 1
            ;;
    esac
    
    echo "$major.$minor.$patch"
}

# Function to validate git status
validate_git_status() {
    # Check if we're on main branch
    local current_branch=$(git branch --show-current)
    if [ "$current_branch" != "main" ]; then
        print_warning "You're not on the main branch (currently on: $current_branch)"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Aborted."
            exit 1
        fi
    fi
    
    # Check if working directory is clean
    if [ -n "$(git status --porcelain)" ]; then
        print_error "Working directory is not clean. Please commit or stash your changes first."
        git status --short
        exit 1
    fi
    
    # Check if main is up to date
    print_info "Checking if main is up to date..."
    git fetch origin main --quiet
    local local_commit=$(git rev-parse HEAD)
    local remote_commit=$(git rev-parse origin/main)
    
    if [ "$local_commit" != "$remote_commit" ]; then
        print_warning "Local main is not up to date with remote main"
        print_info "Local:  $local_commit"
        print_info "Remote: $remote_commit"
        read -p "Pull latest changes? (Y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            print_info "Pulling latest changes..."
            git pull origin main --ff-only
        else
            print_warning "Continuing with outdated main branch..."
        fi
    fi
}

# Function to create release branch
create_release_branch() {
    local new_version=$1
    local dry_run=$2
    
    # Debug: Check if new_version is empty
    if [ -z "$new_version" ]; then
        print_error "Error: new_version is empty!"
        print_error "This should not happen. Please check the script."
        exit 1
    fi
    
    local branch_name="release/v$new_version"
    
    print_info "Creating release branch: $branch_name"
    
    if [ "$dry_run" = "true" ]; then
        print_info "[DRY RUN] Would execute:"
        echo "  git checkout -b $branch_name"
        echo "  git push -u origin $branch_name"
        return
    fi
    
    # Create and checkout new branch
    git checkout -b "$branch_name"
    print_success "Created and checked out branch: $branch_name"
    
    # Push to remote and set upstream
    git push -u origin "$branch_name"
    print_success "Pushed branch to remote and set upstream"
    
    print_success "Release branch '$branch_name' is ready!"
    print_info "Next steps:"
    echo "  1. Make any necessary changes on this branch"
    echo "  2. Test thoroughly"
    echo "  3. Create tag: git tag -a v$new_version -m 'Release v$new_version'"
    echo "  4. Push tag: git push origin v$new_version"
    echo "  5. Merge back to main when ready"
}

# Main script logic
main() {
    local bump_type=""
    local dry_run=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            patch|minor|major)
                bump_type=$1
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown argument: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Validate required argument
    if [ -z "$bump_type" ]; then
        print_error "Bump type is required"
        show_usage
        exit 1
    fi
    
    print_info "MockExchange Release Branch Creator"
    echo "========================================"
    print_info "Bump type: $bump_type"
    print_info "Dry run: $dry_run"
    echo ""
    
    # Validate git status
    validate_git_status
    
    # Get current version
    local current_version=$(get_latest_version true)
    print_info "Current version: v$current_version"
    
    # Calculate new version
    local new_version=$(calculate_new_version "$current_version" "$bump_type")
    print_info "New version: v$new_version"
    
    # Debug: Check if new_version is empty
    if [ -z "$new_version" ]; then
        print_error "Error: Failed to calculate new version!"
        print_error "Current version: $current_version"
        print_error "Bump type: $bump_type"
        exit 1
    fi
    
    echo ""
    
    # Confirm action
    if [ "$dry_run" != "true" ]; then
        print_warning "This will create a new release branch: release/v$new_version"
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Aborted."
            exit 1
        fi
    fi
    
    # Create release branch
    create_release_branch "$new_version" "$dry_run"
}

# Run main function with all arguments
main "$@"
