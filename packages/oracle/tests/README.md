# Oracle Tests

This directory contains tests for the MockX Oracle package.

## Test Structure

```
tests/
├── test_discovery.py        # Symbol discovery functionality
├── test_ticker_processing.py # Ticker data processing
└── conftest.py              # Shared fixtures
```

## Test Coverage

### Discovery Tests (`test_discovery.py`)
- **CSV Parsing**: Parse comma-separated quote assets
- **Symbol Discovery**: Find trading pairs by quote asset
- **Limit Handling**: Respect discovery limits
- **Deduplication**: Remove duplicate symbols across quotes

### Ticker Processing Tests (`test_ticker_processing.py`)
- **Timestamp Normalization**: Convert between seconds/milliseconds
- **Price Extraction**: Handle different price sources (last, close, mid)
- **Data Validation**: Ensure required fields are present
- **Error Handling**: Graceful handling of invalid data

## Running Tests

```bash
# Run all tests
make test-oracle

# Run with coverage
cd packages/oracle && poetry run pytest --cov=oracle
```

## Test Data

- **Fixtures**: Mock CCXT exchange, Redis client
- **Sample Data**: Market data, ticker information
- **Edge Cases**: Invalid timestamps, missing prices, empty markets

## Best Practices

1. **Mock External Dependencies**: CCXT exchanges, Redis
2. **Test Edge Cases**: Invalid data, network errors
3. **Validate Data Processing**: Ensure correct normalization
4. **Test Discovery Logic**: Verify symbol filtering and limits
