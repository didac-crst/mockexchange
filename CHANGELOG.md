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
4. **Docker**: Build versioned images locally
5. **Deployment**: Deploy using versioned Docker images
6. **Documentation**: Update changelog and release notes

## Docker Image Tags

Each release creates multiple Docker image tags for reproducibility:

- `mockx-engine:0.3.0` - Version tag
- `mockx-engine:0.3.0-abc1234` - Version + short SHA
- `mockx-engine:latest` - Latest stable

This ensures you can always deploy the exact code that was tested and tagged.

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
