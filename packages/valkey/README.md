# MockX Valkey

**MockX Valkey** is the data persistence layer for the MockExchange suite, providing a Redis-compatible in-memory database for storing market data, orders, and portfolio information.

## Overview

Valkey is a Redis fork that provides the same API and functionality as Redis, but with improved performance and memory efficiency. In the MockExchange ecosystem, it serves as:

- **Market Data Store**: Real-time price feeds from exchanges
- **Order Book Storage**: Active orders and order history
- **Portfolio Database**: User balances and transaction history
- **Session Management**: Temporary data and caching

## Configuration

Valkey is configured through environment variables in the root `.env` file:

| Variable          | Default           | Description                         |
| ----------------- | ----------------- | ----------------------------------- |
| `VALKEY_PASSWORD` | `SuperSecretPass` | Authentication password             |
| `VALKEY_PORT`     | `6379`            | Port to bind to                     |
| `VALKEY_HOST`     | `valkey`          | Hostname for internal communication |

## Usage

Valkey is automatically started as part of the full stack:

```bash
# Start everything including Valkey
make start

# Or start just Valkey
make start-valkey
```

## Data Structure

The following Redis keys are used by MockExchange:

### Market Data
- `tickers:{SYMBOL}` - Hash containing price data for a trading pair
  - `price` - Last traded price
  - `timestamp` - Unix timestamp
  - `bid` - Best bid price
  - `ask` - Best ask price
  - `bidVolume` - Bid volume
  - `askVolume` - Ask volume

### Orders
- `orders:{USER_ID}` - List of active orders
- `fills:{USER_ID}` - List of completed fills
- `orderbook:{SYMBOL}` - Order book for a symbol

### Portfolio
- `balances:{USER_ID}` - Hash of user balances
- `portfolio:{USER_ID}` - Portfolio summary

## Development

For local development, you can connect to Valkey using any Redis client:

```bash
# Using redis-cli
redis-cli -h localhost -p 6379 -a SuperSecretPass

# Using Python
import redis
r = redis.Redis(host='localhost', port=6379, password='SuperSecretPass')
```

## Monitoring

Check Valkey status and logs:

```bash
# Service status
make status

# Valkey logs
make logs-valkey
```
