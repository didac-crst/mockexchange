# MockX Oracle

**MockX Oracle** is the price feed service for the MockExchange suite, fetching live market data from exchanges and providing it to the trading engine.

---

## Overview

The Oracle service:

- **Fetches live prices** from exchanges via CCXT
- **Writes to Valkey** in the format expected by the engine
- **Supports multiple exchanges** (Binance, Coinbase, etc.)
- **Configurable symbols** and update intervals
- **Auto-discovery mode** for finding available markets

## Quick Start

The Oracle is part of the full MockExchange stack. See the [main README](../../README.md) for complete setup instructions.

### **Individual Service Management**
```bash
# Start just the Oracle (requires Valkey)
make start-oracle

# View Oracle logs
make logs-oracle

# Check Oracle status
make status
```

---

## Configuration

The Oracle uses environment variables from the root `.env` file. Key variables include:

| Variable          | Default             | Description                               |
| ----------------- | ------------------- | ----------------------------------------- |
| `EXCHANGE`        | `binance`           | Exchange to fetch data from               |
| `SYMBOLS`         | `BTC/USDT,ETH/USDT` | Trading pairs to monitor                  |
| `QUOTES`          | `USDT`              | Quote assets for discovery                |
| `QUOTE`           | `USDT`              | Fallback quote asset (if QUOTES is empty) |
| `INTERVAL_SEC`    | `10`                | Price update frequency                    |
| `DISCOVER_QUOTES` | `false`             | Enable discovery mode (`true`/`false`)    |
| `DISCOVER_LIMIT`  | `0`                 | Max markets per quote asset (0=unlimited) |
| `REDIS_URL`       | `redis://...`       | Redis connection string                   |

See the [main README](../../README.md#-environment-configuration) for the complete configuration guide.

---

## Data Format

The Oracle writes ticker data to Valkey in the following format:

### **Redis Key Structure**
```
tickers:{SYMBOL}
```

### **Data Fields**
| Field       | Type   | Description        | Example          |
| ----------- | ------ | ------------------ | ---------------- |
| `price`     | float  | Last traded price  | `50000.00`       |
| `timestamp` | float  | Unix timestamp     | `1703123456.789` |
| `bid`       | float  | Best bid price     | `49999.50`       |
| `ask`       | float  | Best ask price     | `50000.50`       |
| `bidVolume` | float  | Volume at best bid | `1.234`          |
| `askVolume` | float  | Volume at best ask | `0.567`          |
| `symbol`    | string | Trading pair       | `BTC/USDT`       |

### **Example Redis Command**
```bash
HSET tickers:BTC/USDT price 50000.00 timestamp 1703123456.789 bid 49999.50 ask 50000.50
```

---

## Discovery Mode

The Oracle can automatically discover trading pairs when `DISCOVER_QUOTES=true`:

- **Manual Mode** (`DISCOVER_QUOTES=false`): Uses only the `SYMBOLS` list
- **Discovery Mode** (`DISCOVER_QUOTES=true`): Automatically finds markets ending with specified quote assets
- **Limit Control** (`DISCOVER_LIMIT`): Maximum markets per quote asset (0 = unlimited)

### **How to Discover All USDT Trading Pairs**

To discover all trading pairs that end with USDT:

```bash
# In your .env file:
QUOTES=USDT                    # Quote asset to discover
DISCOVER_QUOTES=true           # Enable discovery mode
DISCOVER_LIMIT=0               # No limit (get all USDT pairs)
SYMBOLS=                       # Leave empty to use discovery
```

This will automatically find all markets like `BTC/USDT`, `ETH/USDT`, `ADA/USDT`, etc.

**Note**: If `QUOTES` is empty, the Oracle will fall back to using the `QUOTE` variable (default: `USDT`).

### **Multiple Quote Assets**

You can also discover multiple quote assets at once:

```bash
# Discover both USDT and EUR pairs
QUOTES=USDT,EUR
DISCOVER_QUOTES=true
DISCOVER_LIMIT=10              # Max 10 pairs per quote asset
```

### **Practical Examples**

#### **Example 1: Manual Mode (Default)**
```bash
# .env configuration
EXCHANGE=binance
SYMBOLS=BTC/USDT,ETH/USDT,ADA/USDT
DISCOVER_QUOTES=false
```
**Result**: Only fetches BTC/USDT, ETH/USDT, and ADA/USDT

#### **Example 2: Discover All USDT Pairs**
```bash
# .env configuration
EXCHANGE=binance
SYMBOLS=                           # Leave empty
QUOTES=USDT
DISCOVER_QUOTES=true
DISCOVER_LIMIT=0                   # No limit
```
**Result**: Discovers all available USDT trading pairs (BTC/USDT, ETH/USDT, ADA/USDT, etc.)

#### **Example 3: Discover Top 10 USDT Pairs**
```bash
# .env configuration
EXCHANGE=binance
SYMBOLS=
QUOTES=USDT
DISCOVER_QUOTES=true
DISCOVER_LIMIT=10
```
**Result**: Discovers first 10 USDT trading pairs found

#### **Example 4: Using QUOTE Fallback**
```bash
# .env configuration
EXCHANGE=binance
SYMBOLS=
QUOTES=                    # Empty - will use QUOTE fallback
QUOTE=USDT                 # Fallback quote asset
DISCOVER_QUOTES=true
DISCOVER_LIMIT=5
```
**Result**: Discovers first 5 EUR trading pairs (BTC/EUR, ETH/EUR, etc.)

## Supported Exchanges

The Oracle supports all exchanges available in [CCXT](https://docs.ccxt.com/), including:

- **Binance** - Most popular crypto exchange
- **Coinbase** - US-based exchange
- **Kraken** - European exchange
- **Bitfinex** - Professional trading
- **And many more** - See [CCXT documentation](https://docs.ccxt.com/)

## Integration

The Oracle integrates with the MockExchange stack:

1. **Fetches prices** from configured exchange
2. **Writes to Valkey** using `tickers:{SYMBOL}` keys
3. **Engine reads** prices for order matching
4. **Dashboard displays** real-time data

## Development

### **Adding New Exchanges**
Simply change the `EXCHANGE` environment variable to any CCXT-supported exchange.

### **Custom Price Feeds**
You can replace the Oracle with any service that writes to Valkey using the same `tickers:{SYMBOL}` format.

