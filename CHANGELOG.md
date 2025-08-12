# Changelog

All notable changes to MockExchange will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Oracle price validation to ensure only positive prices are stored
- Order generator with Docker management script
- Comprehensive test coverage for all packages
- CodeRabbit integration for AI-powered code reviews
- Release management and tagging system

### Changed
- Oracle now skips tickers with non-positive prices instead of storing them
- Order generator uses environment variables instead of file flags for reset control
- Improved error handling and logging across all services

### Fixed
- Docker Compose compatibility issues in order generator
- Price fallback logic in Oracle for handling None values
- Test assertion errors in integration tests

## [0.3.0] - 2025-01-XX

### Added
- **Oracle**: Price validation system to filter out non-positive prices
- **Order Generator**: Complete example application with Docker management
- **Engine**: Enhanced order matching with partial fills
- **Periscope**: Improved portfolio visualization and PnL charts
- **CodeRabbit**: AI-powered code review integration

### Changed
- **Oracle**: Modified ticker processing to skip invalid prices while preserving existing data
- **Order Generator**: Switched from file-based to environment variable reset control
- **API**: Enhanced order response format with additional metadata
- **Documentation**: Comprehensive README updates across all packages

### Fixed
- **Oracle**: Rate limiting and error handling for exchange API calls
- **Engine**: Precision handling in quote calculations
- **Docker**: Compatibility issues with different Docker Compose versions
- **Tests**: Integration test reliability and assertion accuracy

### Security
- Enhanced input validation across all API endpoints
- Improved error handling to prevent information leakage

## [0.2.3] - 2025-01-XX

### Fixed
- **Engine**: Rounding bug on quote precision calculations
- **Oracle**: Binance fetch_tickers rate-limit backoff implementation
- **Periscope**: Chart rendering issues with empty datasets

### Changed
- **API**: `/orders` response now includes `avg_price` field
- **Documentation**: Updated deployment instructions

## [0.2.2] - 2025-01-XX

### Added
- **Engine**: Commission model hooks for flexible fee calculation
- **Periscope**: Real-time portfolio balance tracking
- **Oracle**: Support for additional cryptocurrency exchanges

### Fixed
- **Engine**: Order cancellation edge cases
- **Oracle**: Memory usage optimization for large ticker sets

## [0.2.1] - 2025-01-XX

### Added
- **Periscope**: Basic portfolio dashboard
- **Engine**: Order history endpoint
- **Oracle**: Configurable exchange selection

### Fixed
- **Engine**: Order matching race conditions
- **Docker**: Service startup ordering issues

## [0.2.0] - 2025-01-XX

### Added
- **Engine**: Complete order matching engine with REST API
- **Oracle**: Price feed service with CCXT integration
- **Periscope**: Streamlit-based dashboard
- **Valkey**: Redis-compatible data store
- **Docker**: Complete containerization setup

### Changed
- **Architecture**: Microservices design with centralized configuration
- **API**: RESTful endpoints for orders, portfolio, and tickers

## [0.1.0] - 2025-01-XX

### Added
- Initial project structure
- Basic order matching logic
- Docker Compose setup
- Development environment configuration

---

## Versioning Strategy

MockExchange uses **unified versioning** across all packages (Engine, Oracle, Periscope, Valkey) since they are typically deployed together.

- **Major (0.x.y)**: Breaking changes, major features
- **Minor (0.x.y)**: New features, enhancements
- **Patch (0.x.y)**: Bug fixes, minor improvements

## Release Process

1. **Development**: Features developed on feature branches
2. **Testing**: All tests must pass before release
3. **Tagging**: Create annotated git tag with version
4. **Docker**: Build and push versioned images
5. **Deployment**: Deploy using versioned Docker images
6. **Documentation**: Update changelog and release notes

## Docker Image Tags

Each release creates multiple Docker image tags for reproducibility:

- `mockx-engine:0.3.0` - Version tag
- `mockx-engine:0.3.0-abc1234` - Version + short SHA
- `mockx-engine:latest` - Latest stable

This ensures you can always deploy the exact code that was tested and tagged.
