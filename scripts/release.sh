#!/bin/bash

# MockExchange Release Script
# This script automates the release process for MockExchange

set -e  # Exit on any error

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
    echo "MockExchange Release Script"
    echo ""
    echo "Usage: $0 [OPTIONS] VERSION"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -p, --patch         Auto-increment patch version"
    echo "  -m, --minor         Auto-increment minor version"
    echo "  -d, --dry-run       Show what would be done without executing"
    echo "  --no-docker         Skip Docker image building/pushing"
    echo "  --no-tag            Skip git tagging"
    echo "  --registry REGISTRY Docker registry (default: didac)"
    echo ""
    echo "Examples:"
    echo "  $0 v0.3.0                    # Release specific version"
    echo "  $0 -p                        # Auto-increment patch version"
    echo "  $0 -m                        # Auto-increment minor version"
    echo "  $0 --dry-run v0.3.0          # Show what would be done"
    echo "  $0 --registry myregistry v0.3.0  # Use custom registry"
    echo ""
    echo "Environment Variables:"
    echo "  DOCKER_USERNAME     Docker Hub username"
    echo "  DOCKER_PASSWORD     Docker Hub password"
    echo "  DOCKER_REGISTRY     Docker registry (default: didac)"
}

# Parse command line arguments
DRY_RUN=false
PATCH=false
MINOR=false
NO_DOCKER=false
NO_TAG=false
DOCKER_REGISTRY=${DOCKER_REGISTRY:-didac}
VERSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -p|--patch)
            PATCH=true
            shift
            ;;
        -m|--minor)
            MINOR=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-docker)
            NO_DOCKER=true
            shift
            ;;
        --no-tag)
            NO_TAG=true
            shift
            ;;
        --registry)
            DOCKER_REGISTRY="$2"
            shift 2
            ;;
        -*)
            print_error "Unknown option $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$VERSION" ]]; then
                VERSION="$1"
            else
                print_error "Multiple versions specified: $VERSION and $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate version format
validate_version() {
    local version=$1
    if [[ ! $version =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Invalid version format: $version"
        print_error "Version must be in format: vX.Y.Z (e.g., v0.3.0)"
        exit 1
    fi
}

# Get current version from git tags
get_current_version() {
    local current_version
    current_version=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
    echo "$current_version"
}

# Calculate next version
calculate_next_version() {
    local current_version=$1
    local increment_type=$2
    
    if [[ $increment_type == "patch" ]]; then
        echo "$current_version" | awk -F. '{print $1"."$2"."$3+1}'
    elif [[ $increment_type == "minor" ]]; then
        echo "$current_version" | awk -F. '{print $1"."$2+1".0"}'
    else
        echo "$current_version"
    fi
}

# Check if we're on main branch
check_branch() {
    local current_branch
    current_branch=$(git branch --show-current)
    if [[ $current_branch != "main" ]]; then
        print_warning "You're not on the main branch (current: $current_branch)"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Check for uncommitted changes
check_clean_working_directory() {
    if [[ -n $(git status --porcelain) ]]; then
        print_error "Working directory is not clean. Please commit or stash changes."
        git status --short
        exit 1
    fi
}

# Run tests
run_tests() {
    print_info "Running tests..."
    if [[ $DRY_RUN == false ]]; then
        make test
        print_success "Tests passed"
    else
        print_info "DRY RUN: Would run tests"
    fi
}

# Create git tag
create_tag() {
    local version=$1
    print_info "Creating git tag: $version"
    
    if [[ $DRY_RUN == false ]]; then
        if git tag -l | grep -q "^$version$"; then
            print_error "Tag $version already exists"
            exit 1
        fi
        
        git tag -a "$version" -m "MockExchange $version"
        git push origin "$version"
        print_success "Tag $version created and pushed"
    else
        print_info "DRY RUN: Would create tag $version"
    fi
}

# Build Docker images locally
build_docker_images() {
    local version=$1
    local sha
    sha=$(git rev-parse --short HEAD)
    
    print_info "Building Docker images for $version..."
    
    if [[ $DRY_RUN == false ]]; then
        # Build each service locally
        local services=("engine" "oracle" "periscope")
        for service in "${services[@]}"; do
            print_info "Building $service..."
            docker build -t "mockx-$service:$version" \
                        -t "mockx-$service:$version-$sha" \
                        -t "mockx-$service:latest" \
                        "packages/$service"
        done
        
        print_success "Docker images built locally"
    else
        print_info "DRY RUN: Would build Docker images locally"
        print_info "  - mockx-engine:$version"
        print_info "  - mockx-oracle:$version"
        print_info "  - mockx-periscope:$version"
    fi
}

# Update changelog
update_changelog() {
    local version=$1
    local date
    date=$(date +%Y-%m-%d)
    
    print_info "Updating CHANGELOG.md..."
    
    if [[ $DRY_RUN == false ]]; then
        # Replace the placeholder date in the changelog
        sed -i.bak "s/## \[$version\] - 2025-01-XX/## [$version] - $date/" CHANGELOG.md
        rm -f CHANGELOG.md.bak
        
        # Move unreleased changes to the new version
        sed -i.bak "/## \[Unreleased\]/,/## \[$version\]/ { /## \[Unreleased\]/d; /## \[$version\]/d; s/^/  /; }" CHANGELOG.md
        rm -f CHANGELOG.md.bak
        
        print_success "CHANGELOG.md updated"
    else
        print_info "DRY RUN: Would update CHANGELOG.md with date $date"
    fi
}

# Main release process
main() {
    print_info "🚀 Starting MockExchange release process..."
    
    # Determine version
    if [[ $PATCH == true ]]; then
        local current_version
        current_version=$(get_current_version)
        VERSION=$(calculate_next_version "$current_version" "patch")
        print_info "Auto-incrementing patch version: $current_version → $VERSION"
    elif [[ $MINOR == true ]]; then
        local current_version
        current_version=$(get_current_version)
        VERSION=$(calculate_next_version "$current_version" "minor")
        print_info "Auto-incrementing minor version: $current_version → $VERSION"
    fi
    
    # Validate version
    if [[ -z "$VERSION" ]]; then
        print_error "No version specified"
        show_usage
        exit 1
    fi
    
    validate_version "$VERSION"
    
    # Pre-flight checks
    check_branch
    check_clean_working_directory
    
    print_info "Release version: $VERSION"
    print_info "Docker registry: $DOCKER_REGISTRY"
    print_info "Dry run: $DRY_RUN"
    
    if [[ $DRY_RUN == true ]]; then
        print_warning "DRY RUN MODE - No changes will be made"
    fi
    
    # Run the release steps
    run_tests
    
    if [[ $NO_TAG == false ]]; then
        create_tag "$VERSION"
    fi
    
    if [[ $NO_DOCKER == false ]]; then
        build_docker_images "$VERSION"
    fi
    
    update_changelog "$VERSION"
    
    # Success message
    print_success "🎉 Release $VERSION completed successfully!"
    
    if [[ $DRY_RUN == false ]]; then
        echo ""
        print_info "📋 Next steps:"
        echo "  1. Deploy using: VERSION=$VERSION docker-compose up -d"
        echo "  2. Monitor deployment and verify functionality"
        echo "  3. Update CHANGELOG.md with release date"
    fi
}

# Run main function
main "$@"
