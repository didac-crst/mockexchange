# Changelog

All notable changes to MockExchange will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-08-12

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

---

## Versioning Strategy

MockExchange uses **unified versioning** across all packages (Engine, Oracle, Periscope, Valkey) since they are typically deployed together.

- **Major (x.0.0)**: Breaking changes, major features
- **Minor (x.y.0)**: New features, enhancements
- **Patch (x.y.z)**: Bug fixes, minor improvements

## Release Process

1. **Development**: Features developed on feature branches
2. **Testing**: All tests must pass before release
3. **Tagging**: Create annotated git tag with version
4. **Docker**: Build and push versioned images
5. **Deployment**: Deploy using versioned Docker images
6. **Documentation**: Update changelog and release notes

## Docker Image Tags

Each release creates multiple Docker image tags for reproducibility:

- `mockx-engine:0.1.0` - Version tag
- `mockx-engine:0.1.0-abc1234` - Version + short SHA
- `mockx-engine:latest` - Latest stable

This ensures you can always deploy the exact code that was tested and tagged.
