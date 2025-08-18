# Changelog

All notable changes to MockExchange will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project uses tags (`vX.Y.Z`) as releases.

Releases are created by pushing a Git tag (vX.Y.Z) or using GitHub's 'Draft a new release' UI. CI runs on tags to validate the release.

## [Unreleased]
- (Add new entries under here in PRs)

## [v0.1.4] - 2025-08-18

### Added
- **Portfolio Dashboard Enhancement**: Added second pie chart for asset distribution analysis
  - New pie chart showing frozen vs free cash and assets values
  - Side-by-side layout with harmonized styling for both charts
  - Optimized API calls by fetching assets overview data once
  - Clean, professional labels without currency clutter
  - Consistent donut chart styling with 40% hole and percentage labels
  - Enhanced user experience with better visual organization

### Changed
- **Portfolio Page Layout**: Improved chart presentation and performance
  - Refactored to avoid duplicate API calls to `get_assets_overview()`
  - Added subheaders for better chart identification
  - Harmonized chart styling (height, margins, text positioning)
  - Streamlined function structure for better maintainability

## [v0.1.2] - 2025-08-18

### Added
- **Release Branch Script**: Automated release branch creation with version calculation
  - Automatic version bumping (patch, minor, major)
  - Git validation and safety checks
  - Dry-run mode and interactive usage
  - Makefile integration with `make release-branch`
  - Comprehensive error handling and user-friendly output

### Changed
- **Release Process**: Simplified to use Git tags instead of complex local scripts
  - Removed `scripts/release.sh` and all references to it
  - Updated CI to run on Git tags (`v*.*.*`) for release validation
  - Streamlined workflow to `git tag -a vX.Y.Z && git push origin vX.Y.Z`
  - Added GitHub Releases UI as recommended approach

### Fixed
- **Documentation**: Updated README badges (Python version 3.11+ → 3.12+)
- **Documentation**: Removed outdated README.md.backup file
- **Release Script**: Fixed version calculation bug that caused incorrect branch names
- **Release Script**: Resolved output pollution issue in version detection

### Documentation
- **README**: Added "How we ship" and "Install from GitHub tags" sections
- **README**: Added comprehensive release branch script documentation
- **README**: Updated monorepo structure and development setup
- **CHANGELOG**: Simplified to follow Keep a Changelog format
- **PR Template**: Added comprehensive checklist for contributions

## [v0.1.1] - 2025-08-12

### Fixed
- **Documentation**: Updated README badges to accurately reflect current project state
  - Fixed Python version badge from 3.11+ to 3.12+ to match actual requirements
  - Removed outdated README.md.backup file
  - All badges now correctly represent current project configuration

---

## [v0.1.0] - 2025-08-12

### Added
- **MockX Engine**: Complete trading engine with order matching, portfolio tracking, and REST API
  - Order book management with limit and market orders
  - Real-time portfolio balance tracking
  - Commission calculation and fee handling
  - Comprehensive REST API with FastAPI
  - CLI tools for management and testing
  - Full test coverage with unit and integration tests

- **MockX Oracle**: Market data service with price validation
  - Real-time price feeds via CCXT integration
  - Support for multiple exchanges (Binance, Coinbase, etc.)
  - Price validation to ensure data integrity
  - Automatic discovery of trading pairs
  - Redis/Valkey integration for data persistence
  - Configurable update intervals and symbols

- **MockX Periscope**: Streamlit-based dashboard for monitoring
  - Real-time portfolio visualization
  - Order history and status tracking
  - Performance metrics and analytics
  - Interactive charts and data tables
  - Auto-refresh capabilities
  - Responsive design for different screen sizes

- **MockX Valkey**: Redis-compatible database layer
  - Optimized data structures for trading data
  - Efficient storage for market data, orders, and balances
  - Indexed access patterns for fast queries
  - Data persistence and recovery

- **Order Generator**: Example tool for testing and demonstration
  - Dockerized random order generation
  - Configurable trading parameters
  - Reset capabilities for clean testing
  - Management scripts for easy deployment

- **Development Infrastructure**:
  - Comprehensive test suite with pytest
  - Code quality tools (Black, Ruff, MyPy)
  - Pre-commit hooks for automated formatting
  - Docker Compose for easy deployment
  - Poetry for dependency management
  - CodeRabbit integration for AI-powered code reviews

### Changed
- Unified versioning across all packages for consistent releases
- Centralized environment configuration via `.env` file
- Improved error handling and logging across all services
- Enhanced Docker configurations for production readiness

### Fixed
- Docker Compose compatibility issues
- Price fallback logic for handling edge cases
- Test assertion errors in integration tests
- Environment variable handling across services


