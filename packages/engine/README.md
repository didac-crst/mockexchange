# MockX Engine

**MockX Engine** is the core trading engine of the MockExchange suite, providing a complete order matching system with REST API and CLI interface.

## Overview

MockX Engine provides:

- **Order Matching Engine** - Processes market and limit orders
- **Portfolio Management** - Tracks balances and positions
- **REST API** - HTTP interface for trading operations
- **CLI Tool** - Command-line interface (`mockx`)
- **Trade Statistics** - Aggregated metrics and performance data
- **Single-User System** - Designed for individual trading simulation

## Architecture

The engine consists of two main components:

### **Core Engine** (`src/core/`)
- `engine_actors.py` - Pykka-based order matching engine
- `orderbook.py` - Redis-backed order storage and indexing
- `portfolio.py` - Balance management and asset tracking
- `market.py` - Market data interface
- `_types.py` - Data structures and enums

### **API Layer** (`src/api/`)
- `server.py` - FastAPI REST server
- `cli.py` - Command-line interface (`mockx`)

## Quick Start

The engine is part of the full MockExchange stack. See the [main README](../../README.md) for complete setup instructions.

### **Individual Service Management**
```bash
# Start just the engine (requires Valkey and Oracle)
make start-engine

# View engine logs
make logs-engine

# Check engine status
make status
```

### **API Documentation**
When running with `TEST_ENV=true`, the API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Configuration

The engine uses environment variables from the root `.env` file. Key variables include:

| Variable        | Default       | Description                             |
| --------------- | ------------- | --------------------------------------- |
| `ENGINE_PORT`   | `8000`        | API server port                         |
| `API_KEY`       | `invalid-key` | Authentication key for API requests     |
| `COMMISSION`    | `0.00075`     | Trading fee rate (0.075%)               |
| `CASH_ASSET`    | `USDT`        | Reference currency for PnL calculations |
| `TICK_LOOP_SEC` | `10`          | Price tick processing interval          |
| `TEST_ENV`      | `false`       | Enable API docs and disable auth        |

See the [main README](../../README.md#-environment-configuration) for the complete configuration guide.

## Authentication

Production containers require the `x-api-key` header for all requests:

```http
x-api-key: your-api-key
```

Set `TEST_ENV=true` to disable authentication for development.

## REST Endpoints

### Market Data
- `GET /tickers` - List all available symbols
- `GET /tickers/{symbol}` - Get latest ticker data

### Portfolio
- `GET /balance` - Full portfolio snapshot
- `GET /balance/list` - List of all assets
- `GET /balance/{asset}` - Specific asset balance
- `POST /balance/{asset}/deposit` - Deposit funds
- `POST /balance/{asset}/withdrawal` - Withdraw funds

### Orders
- `GET /orders` - List orders with filters
- `GET /orders/{oid}` - Get specific order
- `POST /orders` - Create market/limit order
- `POST /orders/can_execute` - Dry-run order execution
- `POST /orders/{oid}/cancel` - Cancel open order

### Overview
- `GET /overview/assets` - Portfolio summary
- `GET /overview/trades` - Trade statistics

### Admin
- `PATCH /admin/tickers/{symbol}/price` - Set ticker price
- `PATCH /admin/balance/{asset}` - Set balance
- `POST /admin/fund` - Quick funding
- `DELETE /admin/data` - Reset all data
- `GET /admin/health` - Health check

## CLI Usage

The `mockx` CLI provides convenient access to the API:

```bash
# Portfolio management
mockx balance                    # Show all balances
mockx fund USDT 100000          # Fund account

# Market data
mockx ticker BTC/USDT           # Get ticker data

# Order management
mockx order BTC/USDT buy 0.05   # Place market order
mockx order BTC/USDT sell 0.01 --type limit --price 50000  # Place limit order
mockx orders --status filled    # List filled orders
mockx cancel <ORDER_ID>         # Cancel order

# Admin operations
mockx set-price BTC/USDT 50000  # Set price manually
mockx reset-data                # Clear all data
```

## Development

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run specific test
poetry run pytest src/tests/test_03_market_orders_property.py -v
```

### Code Quality
```bash
# Format code
poetry run black src/
poetry run ruff check --fix src/

# Type checking
poetry run mypy src/
```

## Data Flow

1. **Price Feeds** - Oracle writes to `tickers:{SYMBOL}` in Valkey
2. **Order Processing** - Engine reads prices and matches orders
3. **State Updates** - Orders and balances updated in Valkey
4. **API Access** - REST API and CLI read from Valkey

## Dependencies

- **Valkey** - Data persistence (Redis-compatible)
- **Oracle** - Price feed service
- **Pykka** - Actor framework for concurrency
- **FastAPI** - REST API framework
- **CCXT** - Exchange integration (via Oracle)

## Examples

See the [order generator example](../../examples/order-generator/) for a complete trading simulation.

## License

MIT License - see [LICENSE](LICENSE) for details.