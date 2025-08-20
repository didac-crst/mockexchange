# MockExchange Release Template

## 🚀 Release Summary

Brief description of what this release accomplishes and its key highlights.

## 📋 What's New

### ✨ New Features
-
-
-

### 🐛 Bug Fixes
-
-
-

### 🔧 Improvements
-
-
-

### 📚 Documentation
-
-
-

### 🧪 Testing & Quality
-
-
-

## 🔄 Breaking Changes

> **⚠️ Important**: If this release includes breaking changes, document them here.

### What Changed
-

### Why It Changed
-

### Migration Guide
```python
# Before (old version)
# Your old code here

# After (new version)
# Your new code here
```

## 📦 Installation

### From GitHub (Recommended)
```bash
# Engine
pip install "git+https://github.com/didac-crst/mockexchange.git@vVERSION#subdirectory=packages/engine"

# Oracle
pip install "git+https://github.com/didac-crst/mockexchange.git@vVERSION#subdirectory=packages/oracle"

# Periscope
pip install "git+https://github.com/didac-crst/mockexchange.git@vVERSION#subdirectory=packages/periscope"
```

### With Poetry
```bash
git clone --depth 1 --branch vVERSION git@github.com:didac-crst/mockexchange.git
cd mockexchange/packages/engine && poetry install
cd ../oracle && poetry install
cd ../periscope && poetry install
```

### Docker Compose
```bash
VERSION=VERSION docker-compose up -d
```

## 🧪 Testing

### Unit Tests
```bash
make test
```

### Integration Tests
```bash
make test-integration
```

### All Quality Checks
```bash
make dev
```

### Type Checking
```bash
poetry run mypy packages/engine/src/core/
```

## 📊 Compatibility

### Python Versions
- ✅ Python 3.12+
- ✅ Python 3.13+

### Redis Compatibility
- ✅ Valkey (Redis-compatible) support
- ✅ Standard Redis support
- ✅ Connection pooling and error handling

### MockExchange Components
- ✅ MockExchange Engine compatibility
- ✅ MockExchange Oracle compatibility
- ✅ MockExchange Periscope compatibility
- ✅ Cross-component communication verified

## 🔗 Dependencies

### Required
- **Redis/Valkey**: For data persistence
- **Python**: 3.12+
- **Docker**: For containerized deployment

### Development
- **Poetry**: For dependency management
- **Ruff**: Code formatting and linting
- **MyPy**: Type checking (with smart filtering)
- **Pytest**: Testing framework
- **Pre-commit**: Quality hooks

## 📈 Performance

### Benchmarks
-
-
-

### Memory Usage
-
-

## 🔒 Security

### Security Improvements
-
-

### Known Issues
-
-

## 🐛 Known Issues

> List any known issues that users should be aware of.

-
-

## 🚧 Deprecations

> List any deprecated features that will be removed in future versions.

-
-

## 📝 Changelog

### Full Changelog
See [CHANGELOG.md](https://github.com/didac-crst/mockexchange/blob/main/CHANGELOG.md) for the complete list of changes.

### Key Changes
-
-
-

## 🙏 Contributors

Thanks to all contributors who made this release possible:

-
-

## 📞 Support

### Getting Help
- 📖 [Documentation](https://github.com/didac-crst/mockexchange#readme)
- 🐛 [Bug Reports](https://github.com/didac-crst/mockexchange/issues)
- 💡 [Feature Requests](https://github.com/didac-crst/mockexchange/issues)
- 💬 [Discussions](https://github.com/didac-crst/mockexchange/discussions)

### MockExchange Suite
- 🔗 [MockExchange Engine](https://github.com/didac-crst/mockexchange/tree/main/packages/engine)
- 🔗 [MockExchange Oracle](https://github.com/didac-crst/mockexchange/tree/main/packages/oracle)
- 🔗 [MockExchange Periscope](https://github.com/didac-crst/mockexchange/tree/main/packages/periscope)
- 📚 [MockExchange Documentation](https://github.com/didac-crst/mockexchange#readme)

## 🔮 What's Next

### Upcoming Features
-
-

### Roadmap
-
-

---

**Release Date**: DATE
**Version**: VERSION
**Commit**: COMMIT_HASH

---

## 📋 Release Checklist

### Pre-Release
- [ ] All tests pass (`make test`)
- [ ] Integration tests pass (`make test-integration`)
- [ ] Type checking passes (`poetry run mypy packages/engine/src/core/`)
- [ ] Linting passes (`make lint`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated with new entries under [Unreleased]
- [ ] Version bumped in all packages
- [ ] Docker images build successfully

### Release
- [ ] Create release branch (`git checkout -b release/vX.Y.Z`)
- [ ] Update version numbers
- [ ] Update CHANGELOG.md
- [ ] Create pull request
- [ ] Merge to main
- [ ] Create Git tag (`git tag -a vX.Y.Z -m "Release vX.Y.Z"`)
- [ ] Push tag (`git push origin vX.Y.Z`)
- [ ] Create GitHub release with this template

### Post-Release
- [ ] Verify Docker images are available
- [ ] Test installation from GitHub tags
- [ ] Update documentation if needed
- [ ] Announce release
