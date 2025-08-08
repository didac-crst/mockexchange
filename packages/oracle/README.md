# MockX Oracle 🔮 <!-- omit in toc -->

Price feed service for **MockExchange**.

Fetches live market data from a configured exchange via [`ccxt`](https://github.com/ccxt/ccxt) and writes it into Valkey/Redis in the schema expected by the **MockX Engine**.

---

## 📑 Table of Contents <!-- omit in toc -->
- [Usage](#usage)
  - [1. Configure Environment](#1-configure-environment)
  - [2. Run with Docker Compose](#2-run-with-docker-compose)
- [Environment Variables](#environment-variables)
- [Interface with MockExchange](#interface-with-mockexchange)
- [🔗 See Also](#-see-also)

---

## Usage

### 1. Configure Environment
Copy `.env.example` to `.env` and edit values to match your setup.

### 2. Run with Docker Compose
```bash
docker compose up --build
```

Or run Valkey separately with authentication:
```bash
docker run -d --name mockx-valkey \
    -p 6379:6379 \
    valkey/valkey \
    --requirepass "SuperSecretPass"
```

---

## Environment Variables

| Variable          | Description                                                                   |
| ----------------- | ----------------------------------------------------------------------------- |
| `EXCHANGE`        | Exchange id for ccxt (e.g. `binance`)                                         |
| `SYMBOLS`         | Comma-separated list of symbols (e.g. `BTC/USDT,ETH/USDT`)                    |
| `DISCOVER_QUOTES` | Comma-separated list of quote assets for auto-discovery (e.g. `USDT,EUR,BTC`) |
| `DISCOVER_LIMIT`  | Limit for discovered markets per quote asset (0 = unlimited)                  |
| `DISCOVER_ENABLE` | Enable discovery mode (`true` / `false`)                                      |
| `INTERVAL_SEC`    | Fetch interval in seconds                                                     |
| `REDIS_HOST`      | Redis host (default: `127.0.0.1`)                                             |
| `REDIS_PORT`      | Redis port (default: `6379`)                                                  |
| `REDIS_DB`        | Redis database index (default: `0`)                                           |
| `REDIS_PASSWORD`  | Redis password (leave empty if no password is set)                            |
| `LOG_LEVEL`       | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)                           |

**Security tip:**  
If Valkey is exposed outside localhost, set a strong password via `--requirepass` and provide it through `REDIS_PASSWORD`.

---

## Interface with MockExchange

The **MockX Oracle** is a standalone service that:

1. Uses `ccxt` to fetch real-time price data from a configured exchange.
2. Stores this data in Valkey under the key pattern:
   ```
   tickers:<symbol>
   ```
   with fields:
   - `price` — last trade price  
   - `timestamp` — exchange timestamp or local time if unavailable  
   - `bid` — highest bid  
   - `ask` — lowest ask  
   - `bidVolume` — volume at best bid  
   - `askVolume` — volume at best ask  
   - `symbol` — symbol name (e.g. `BTC/USDT`)
3. The **MockX Engine** reads from these keys when matching orders.

Without the Oracle (or another price feed writing in the same schema), the Engine cannot execute trades.

---

## 🔗 See Also
- [Main MockExchange README](../README.md) — full architecture, story, and usage.
- [CCXT Documentation](https://docs.ccxt.com/) — list of supported exchanges and methods.