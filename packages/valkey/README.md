# MockX Valkey

**MockX Valkey** is the data persistence layer for the MockExchange suite, providing a Redis-compatible in-memory database for storing market data, orders, and portfolio information.

## Overview

Valkey is a Redis fork that provides the same API and functionality as Redis, but with improved performance and memory efficiency. In the MockExchange ecosystem, it serves as:

- **Market Data Store**: Real-time price feeds from exchanges
- **Order Book Storage**: Active orders and order history
- **Portfolio Database**: Asset balances and transaction history
- **Trade Statistics**: Aggregated trading metrics and performance data
- **Deposit/Withdrawal Tracking**: Asset movement history

**Note**: MockExchange is designed as a single-user system, so all data is stored without user-specific prefixes.

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

The following Redis keys are used by MockExchange (based on actual implementation):

### Market Data
- `tickers:{SYMBOL}` - Hash containing price data for a trading pair
  - `price` - Last traded price
  - `timestamp` - Unix timestamp
  - `bid` - Best bid price (optional)
  - `ask` - Best ask price (optional)
  - `bidVolume` - Bid volume (optional)
  - `askVolume` - Ask volume (optional)

### Portfolio & Balances
- `balances` - Hash containing all asset balances (single-user system)
  - `{ASSET}` - JSON string with balance data
    - `asset` - Asset symbol (e.g., "BTC", "USDT")
    - `free` - Available balance
    - `used` - Reserved balance (in open orders)
    - `total` - Total balance (free + used)

### Orders
- `orders` - Hash containing all orders (single-user system)
  - `{ORDER_ID}` - JSON string with order data
    - `id` - Unique order identifier
    - `symbol` - Trading pair (e.g., "BTC/USDT")
    - `side` - Order side ("BUY" or "SELL")
    - `type` - Order type ("MARKET" or "LIMIT")
    - `amount` - Order amount in base currency
    - `price` - Limit price (for limit orders)
    - `status` - Order status
    - `timestamp` - Creation timestamp
    - `history` - Array of order state changes (when include_history=True)

### Order Indexes
- `open:set` - Set containing IDs of all open orders
- `open:{SYMBOL}` - Set containing IDs of open orders for a specific symbol

### Trade Statistics
- `trades:{SIDE}:{BASE}:count` - Hash with trade count per quote currency
- `trades:{SIDE}:{BASE}:amount` - Hash with total amount traded per quote currency
- `trades:{SIDE}:{BASE}:notional` - Hash with total notional value per quote currency
- `trades:{SIDE}:{BASE}:fee` - Hash with total fees per fee asset

### Trade Indexes
- `trades:index:count` - Set containing all trade count hash keys
- `trades:index:amount` - Set containing all trade amount hash keys
- `trades:index:notional` - Set containing all trade notional hash keys
- `trades:index:fee` - Set containing all trade fee hash keys

### Deposits & Withdrawals
- `deposits:{ASSET}` - Hash containing deposit data for an asset
  - `ref_symbol` - Reference currency (usually "USDT")
  - `asset_quantity` - Total deposited amount
  - `ref_value` - Value in reference currency
- `withdrawals:{ASSET}` - Hash containing withdrawal data for an asset
  - `ref_symbol` - Reference currency (usually "USDT")
  - `asset_quantity` - Total withdrawn amount
  - `ref_value` - Value in reference currency

### Deposit & Withdrawal Indexes
- `deposits:index` - Set containing all deposit hash keys
- `withdrawals:index` - Set containing all withdrawal hash keys

### Engine Management
- `engine:leader` - String containing the current engine leader identifier

## Data Access Patterns

The MockX Engine uses specific patterns to access this data:

### Order Management
- **Add Order**: `HSET orders {ORDER_ID} {JSON}` + `SADD open:set {ORDER_ID}` + `SADD open:{SYMBOL} {ORDER_ID}`
- **Update Order**: `HSET orders {ORDER_ID} {JSON}` (with history)
- **Get Order**: `HGET orders {ORDER_ID}`
- **List Open Orders**: `SMEMBERS open:{SYMBOL}` then `HMGET orders {ID1} {ID2} ...`
- **Close Order**: `SREM open:set {ORDER_ID}` + `SREM open:{SYMBOL} {ORDER_ID}`

### Balance Management
- **Get Balance**: `HGET balances {ASSET}`
- **Set Balance**: `HSET balances {ASSET} {JSON}`
- **All Balances**: `HGETALL balances`

### Market Data
- **Set Ticker**: `HSET tickers:{SYMBOL} {FIELDS}`
- **Get Ticker**: `HGETALL tickers:{SYMBOL}`
- **List Tickers**: `SCAN tickers:*`

### Trade Statistics
- **Update Stats**: `HINCRBY/HINCRBYFLOAT` on trade hashes + `SADD` to indexes
- **Get Stats**: `SMEMBERS` on indexes then `HGETALL` on hashes

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
