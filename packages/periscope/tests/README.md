# Periscope Tests

This directory contains tests for the MockX Periscope dashboard package.

## Test Structure

```
tests/
├── test_api_integration.py  # API integration tests
└── conftest.py              # Shared fixtures
```

## Test Coverage

### API Integration Tests (`test_api_integration.py`)
- **Balance Retrieval**: Test fetching portfolio balances
- **Order History**: Test fetching order data
- **Ticker Data**: Test fetching market prices
- **Error Handling**: Test API errors, timeouts, connection issues

## Running Tests

```bash
# Run all tests
make test-periscope

# Run with coverage
cd packages/periscope && poetry run pytest --cov=app
```

## Test Data

- **Fixtures**: Mock API responses, Streamlit components
- **Sample Data**: Portfolio balances, orders, market data
- **Error Scenarios**: Network failures, API errors

## Best Practices

1. **Mock External APIs**: Engine API endpoints
2. **Test Error Scenarios**: Network failures, invalid responses
3. **Validate Data Processing**: Ensure correct data transformation
4. **Test UI Components**: Mock Streamlit for component testing

## Future Test Areas

- **Dashboard Components**: Individual Streamlit components
- **Data Visualization**: Chart rendering and updates
- **User Interactions**: Form submissions, button clicks
- **Real-time Updates**: Auto-refresh functionality
