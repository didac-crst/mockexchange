# Docker Version Pinning

This document lists all pinned Docker image versions used in MockExchange for reproducibility and security.

## Base Images

| Service             | Base Image      | Version       | Reason                                |
| ------------------- | --------------- | ------------- | ------------------------------------- |
| **Engine**          | `python`        | `3.12.4-slim` | Python 3.12, slim for smaller size    |
| **Oracle**          | `python`        | `3.12.4-slim` | Python 3.12, slim for smaller size    |
| **Periscope**       | `python`        | `3.12.4-slim` | Python 3.12, slim for smaller size    |
| **Order Generator** | `python`        | `3.12.4-slim` | Python 3.12, slim for smaller size    |
| **Valkey**          | `valkey/valkey` | `7-alpine`    | Redis-compatible, Alpine for security |

## Build Tools

| Tool       | Version | Location        |
| ---------- | ------- | --------------- |
| **Poetry** | `1.8.2` | All Dockerfiles |

## Custom Images

| Service             | Default Tag | Environment Variable |
| ------------------- | ----------- | -------------------- |
| **mockx-engine**    | `0.1.0`     | `VERSION`            |
| **mockx-oracle**    | `0.1.0`     | `VERSION`            |
| **mockx-periscope** | `0.1.0`     | `VERSION`            |

## Version Management

### For Development
```bash
# Use default version (0.1.0)
docker-compose up -d

# Use specific version
VERSION=0.1.0 docker-compose up -d
```

### For Production
```bash
# Always specify version for production
VERSION=0.1.0 docker-compose up -d
```

## Security Benefits

1. **Reproducibility**: Same code always builds the same image
2. **Security**: Known-good base images, no surprise updates
3. **Stability**: No breaking changes from base image updates
4. **Auditability**: Clear version history for compliance

## Update Process

When updating versions:

1. **Base Images**: Update in Dockerfiles, test thoroughly
2. **Poetry**: Update in all Dockerfiles simultaneously
3. **Custom Images**: Update default version in docker-compose.yml
4. **Document**: Update this file with new versions
5. **Test**: Verify all services work with new versions

## Current Versions (as of 2025-08-12)

- **Python**: 3.12.4 (all services)
- **Poetry**: 1.8.2
- **Valkey**: 7-alpine
- **MockExchange**: 0.1.0
