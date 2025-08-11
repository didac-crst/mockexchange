# Engine Tests

This directory contains tests for the MockX Engine package.

## Test Structure

```
tests/
├── unit/           # Unit tests for core business logic
│   ├── test_market.py
│   └── test_orderbook.py
├── integration/    # Integration tests via API
│   ├── test_00_normal_example.py
│   ├── test_01_reset_and_edit_balance.py
│   └── ...
└── conftest.py     # Shared fixtures
```

## Test Types

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual functions and classes in isolation
- **Dependencies**: Mocked external dependencies (Redis, etc.)
- **Speed**: Fast execution
- **Coverage**: Core business logic, edge cases, error handling

### Integration Tests (`tests/integration/`)
- **Purpose**: Test the full system via API endpoints
- **Dependencies**: Real Redis backend, HTTP client
- **Speed**: Slower execution
- **Coverage**: End-to-end workflows, API contracts

## Running Tests

```bash
# Run all tests
make test-engine

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run with coverage
cd packages/engine && poetry run pytest --cov=core --cov=api
```

## Test Data

- **Fixtures**: Defined in `conftest.py`
- **Sample Data**: Mock orders, tickers, balances
- **Test Helpers**: API client utilities in `integration/helpers.py`

## Best Practices

1. **Unit Tests**: Mock external dependencies, test one thing at a time
2. **Integration Tests**: Use real dependencies, test complete workflows
3. **Naming**: Use descriptive test names that explain the scenario
4. **Coverage**: Aim for high coverage of business logic
5. **Speed**: Keep unit tests fast, integration tests can be slower
