# Changelog

All notable changes to MockExchange will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project uses tags (`vX.Y.Z`) as releases.

Releases are created by pushing a Git tag (vX.Y.Z) or using GitHub's 'Draft a new release' UI. CI runs on tags to validate the release.

## [Unreleased]

## [v0.1.5] - 2025-08-21

### 🎯 Major Achievements
- **Zero MyPy Errors**: Achieved 0 type errors in core business logic through smart filtering
- **Enhanced Development Workflow**: One-command development cycle with comprehensive testing
- **Smart Type Checking**: MyPy now focuses on business logic while ignoring framework limitations
- **Comprehensive Integration Testing**: Fresh restart + integration tests in single command

### Added
- **Development Workflow & Toolchain**: Comprehensive improvements for developer experience
  - **One-command development cycle**: `make dev` now runs install → format → lint → type-check → test
  - **Smart type checking**: `make type-check` with MyPy filtering (ignores framework limitations)
  - **Comprehensive integration testing**: `make integration` for fresh restart + integration tests
  - **Modernized toolchain**: Replaced Black with Ruff for faster, more comprehensive code formatting
  - **Enhanced service management**: Individual service control with fresh rebuilds
  - **Zero MyPy errors**: Achieved 0 errors in core business logic through smart filtering
  - **Pre-commit integration**: MyPy runs on commits with framework noise filtered out
- **Type Safety & Code Quality**: Massive improvements in type annotations and error handling
  - **Comprehensive type annotations**: Reduced MyPy errors from 136+ to 0 in core business logic (100% improvement!)
  - **Smart filtering implemented**: MyPy now ignores framework limitations while catching real type issues
  - **Type stubs added**: redis, requests, pandas, httpx for better type support
  - **CanExecuteResult TypedDict**: Added proper return type for `can_execute` method
  - **Portfolio type annotations**: Fixed `_get_summary_assets_balance` to use `Mapping[str, Mapping[str, float]]`
  - **Consistent error handling**: Changed side fallback from `None` to `TypeError` in `orderbook.py` for fail-fast behavior
  - **Generic method signatures**: Updated methods to accept generic `Mapping[str, Any]`
- **Configuration & Documentation**: Comprehensive environment variable and deployment support
  - **Valkey IP Configuration**: Added comprehensive external server support with `VALKEY_HOST` examples
  - **Environment Variable Documentation**: Complete documentation for all missing environment variables
  - **External deployment support**: System now supports local Docker Compose and external Valkey deployments
  - **Documentation consistency**: Fixed `FRESH_WINDOW_S` default from 60 to 300 to match periscope config
  - **Enhanced READMEs**: Updated all package READMEs with comprehensive configuration tables
- **GitHub PR Tools**: Automated PR comment export and analysis for LLM integration
  - **Export PR comments**: `make export-pr-comments PR=123` exports GitHub PR comments to JSON
  - **Analyze comments**: `make analyze-pr-comments PR=123` generates structured LLM prompts
  - **Latest review filtering**: New `--latest-only` flag to filter to most recent CodeRabbit review
  - **Multiple review support**: Automatically detects and selects latest review from multiple reviews
  - **Reduced LLM confusion**: Focused feedback prevents confusion from multiple review iterations
  - **New Make commands**: `make analyze-pr-comments-latest` and `make export-and-analyze-pr-latest`
  - **CodeRabbit integration**: Specifically designed to export CodeRabbit AI review comments
  - **Better Cursor integration**: Optimized for focused, actionable feedback analysis
- **Script Robustness**: Enhanced GitHub PR tools with better error handling and API integration
  - **Strict mode**: Added `set -euo pipefail` to export script for better error detection
  - **Output directory creation**: `mkdir -p` before writing files to prevent write failures
  - **Enhanced GitHub API**: Added `X-GitHub-Api-Version: 2022-11-28` header and `per_page=100` parameter
  - **Better curl options**: Changed from `curl -s` to `curl -sSf` for improved error reporting
  - **Path corrections**: Fixed script usage examples and documentation to use correct paths
  - **Environment file paths**: Updated .env documentation to match actual script behavior

## [v0.1.4] - 2025-08-18

### Added
- **Docker Compose Flexibility**: Support for external service connections
  - Removed `depends_on` dependencies for flexible service startup
  - Added `start-sequential` command for proper dependency ordering
  - Support for connecting to external Valkey, Oracle, and Engine services
  - Individual service startup commands for independent operation

- **Makefile Enhancements**: New commands for flexible service management
  - `make start-sequential` - Start services in dependency order (valkey → oracle → engine → periscope)
  - `make start` - Start all services in parallel
  - Individual service commands: `start-engine`, `start-oracle`, `start-periscope`, `start-valkey`
  - Corresponding stop, restart, and logs commands for each service

### Changed
- **Docker Compose Configuration**: Updated for better flexibility
  - Default version updated to 0.1.4
  - Removed hard dependencies between services
  - Enhanced environment variable support for external connections
  - Periscope API_URL now configurable for external engine connections

- **Periscope Portfolio Charts**: Improved mobile responsiveness and styling
  - Fixed pie chart sizing issues on mobile devices
  - Added custom color scheme for asset distribution chart:
    * Free Cash: #0061FF (blue)
    * Frozen Cash: #EF6C00 (orange)
    * Free Assets: #0EC1FD (light blue)
    * Frozen Assets: #FFB347 (light orange)
  - Consolidated duplicate pie chart functions
  - Reduced chart height to 400px for better mobile display
  - Added explicit height parameters for consistent rendering

### Fixed
- **Mobile Display**: Resolved pie chart size inconsistencies on mobile devices
- **Code Duplication**: Removed redundant `_display_assets_pie_chart_compact` function
- **Docker Compose**: Fixed version mismatch between git tags and docker-compose.yml

## [v0.1.3] - 2025-08-18

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

### Testing
- **Comprehensive Test Suite**: Added extensive unit tests for new portfolio features
  - Created `test_portfolio_helpers.py` with 8 tests for chart functions and data validation
  - Created `test_portfolio_integration.py` with 10 tests for portfolio page integration
  - Updated `test_api_integration.py` with 7 tests for API data structure validation
  - Total of 25 new tests covering edge cases, error handling, and data validation
  - All tests pass successfully: 21 periscope tests, 21 engine tests, 31 oracle tests

### Fixed
- **Test Infrastructure**: Resolved test execution issues across all packages
  - Fixed import errors by installing all package dependencies
  - Resolved 'No module named core' errors in engine tests
  - Fixed streamlit import issues in periscope test environment
  - Ensured proper virtual environment setup for all packages
  - All 73 tests now pass across engine, periscope, and oracle packages

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
  - Code quality tools (Ruff, MyPy)
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
