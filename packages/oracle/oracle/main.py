"""
MockX Oracle — fetch normalized tickers via ccxt and write them to Valkey/Redis.

New in this version
-------------------
- Multi-quote discovery via QUOTES env (e.g., "USDT,EUR,USDC").
- Backward compatible: if QUOTES is empty, falls back to QUOTE (single).

Behavior
--------
- If DISCOVER_QUOTES=true and SYMBOLS is empty:
    Discover symbols ending with any of the provided quotes (*/USDT, */EUR, ...),
    up to DISCOVER_LIMIT *per quote* (de-duplicated across quotes).
- Else, use the SYMBOLS comma list.
- Writes one hash per symbol under: f"{VALKEY_TICKERS_ROOT}{symbol}"
  Example key: "tickers:BTC/USDT"

Hash fields:
- price:      last price (or close, or mid(bid,ask) as fallback)
- timestamp:  float epoch seconds (ms converted to s automatically)
- bid / ask:  best bid/ask if provided by the exchange
- bidVolume / askVolume: volumes if available (0.0 otherwise)
- symbol:     the <BASE/QUOTE> symbol, e.g., BTC/USDT

Environment variables (with defaults)
-------------------------------------
- EXCHANGE=binance
- SYMBOLS=""                         # e.g., "BTC/USDT,ETH/USDT"
- QUOTES=""                          # e.g., "USDT,EUR,USDC"  (preferred)
- QUOTE=USDT                         # legacy single-quote fallback if QUOTES is empty
- DISCOVER_QUOTES=false              # auto-discover */<QUOTE> markets if SYMBOLS empty
- DISCOVER_LIMIT=0                   # max discovered per quote - set to 0 for no limit
- REDIS_URL=redis://127.0.0.1:6379/0
- INTERVAL_SEC=10
- LOG_LEVEL=INFO
"""

import os
import time
import signal
import logging
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import ccxt
import redis
from dotenv import load_dotenv

# Load .env if present (noop if missing)
load_dotenv()

# --- Config (env-driven) ------------------------------------------------------

EXCHANGE = os.getenv("EXCHANGE", "binance")
SYMBOLS_RAW = os.getenv("SYMBOLS", "")

# Preferred multi-quote var; fallback to legacy single QUOTE
QUOTES_RAW = os.getenv("QUOTES", "")
LEGACY_QUOTE = os.getenv("QUOTE", "USDT")
DISCOVER_QUOTES = os.getenv("DISCOVER_QUOTES", "false").lower() == "true"
DISCOVER_LIMIT = int(os.getenv("DISCOVER_LIMIT", "0"))

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

INTERVAL_SEC = int(os.getenv("INTERVAL_SEC", "10"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Constants
VALKEY_TICKERS_ROOT = "tickers:"

# --- Logging ------------------------------------------------------------------

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("mockx-oracle")

# --- Helpers ------------------------------------------------------------------


def parse_csv(raw: str) -> List[str]:
    """Parse a comma-separated list into a clean list of unique, order-preserving items."""
    if not raw:
        return []
    seen = set()
    out: List[str] = []
    for s in (x.strip() for x in raw.split(",")):
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def normalize_timestamp(ts: Optional[float]) -> float:
    """Return a float epoch seconds; fall back to now() if input is None/invalid. Convert ms→s."""
    try:
        if ts is None:
            return float(time.time())
        ts_f = float(ts)
        return ts_f / 1000.0 if ts_f > 1e12 else ts_f
    except Exception:
        return float(time.time())


def normalize_ticker(sym: str, t: Dict) -> Dict:
    """
    Normalize a ccxt ticker dict to the schema we persist in Valkey.

    Fallback precedence for price:
      last -> close -> mid(bid, ask) -> None
    """
    bid = t.get("bid")
    ask = t.get("ask")

    price = t.get("last") or t.get("close")
    if price is None and (bid is not None and ask is not None):
        price = (bid + ask) / 2.0

    ts = normalize_timestamp(t.get("timestamp"))

    return {
        "price": price,
        "timestamp": ts,
        "bid": bid,
        "ask": ask,
        "bidVolume": t.get("bidVolume") or 0.0,
        "askVolume": t.get("askVolume") or 0.0,
        "symbol": sym,
    }


def discover_symbols_for_quotes(
    exchange: "ccxt.Exchange", quotes: Sequence[str], limit_per_quote: int
) -> List[str]:
    """
    Discover symbols ending with any of the provided quotes (e.g., */USDT, */EUR), up to
    `limit_per_quote` per quote. Duplicates across quotes are de-duplicated, order preserved.
    """
    _has_limit = limit_per_quote > 0
    msg = (
        "Discovering markets for quotes=%s (limit per quote=%d)..."
        if _has_limit
        else "Discovering markets for quotes=%s (no limit)..."
    )
    log.info(
        msg,
        quotes,
        limit_per_quote,
    )
    markets = exchange.load_markets()

    # Order-preserving de-dupe
    seen = set()
    results: List[str] = []
    for q in quotes:
        cnt = 0
        suffix = f"/{q}"
        for s in markets.keys():
            if s.endswith(suffix) and s not in seen:
                results.append(s)
                seen.add(s)
                cnt += 1
                if _has_limit and cnt >= limit_per_quote:
                    log.debug(
                        "Reached limit of %d symbols for quote=%s", limit_per_quote, q
                    )
                    break
        log.info("Discovered %d symbols for quote=%s", cnt, q)
    log.info("Total discovered symbols: %d", len(results))
    return results


def write_tickers(
    r: "redis.Redis", root: str, items: Iterable[Tuple[str, Dict]]
) -> None:
    """Write a batch of (symbol, ticker_dict) pairs into Valkey under f'{root}{symbol}'."""
    for sym, t in items:
        payload = normalize_ticker(sym, t)
        r.hset(f"{root}{sym}", mapping=payload)


# --- Main loop ----------------------------------------------------------------


def main() -> int:
    """
    Run the Oracle loop:
    - Build symbol list from SYMBOLS or multi-quote discovery.
    - Fetch tickers via ccxt (batch when available, otherwise per-symbol).
    - Upsert into Valkey hashes under {VALKEY_TICKERS_ROOT}{symbol}.
    """
    # Build QUOTES list (prefer QUOTES, fallback to QUOTE)
    quotes = parse_csv(QUOTES_RAW) or [LEGACY_QUOTE]

    log.info(
        "Starting MockX Oracle — exchange=%s quotes=%s interval=%ss root='%s'",
        EXCHANGE,
        quotes,
        INTERVAL_SEC,
        VALKEY_TICKERS_ROOT,
    )

    # Initialize exchange + Redis
    ex = getattr(ccxt, EXCHANGE)({"enableRateLimit": True})

    if REDIS_PASSWORD:
        REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    else:
        REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    # Determine symbols
    symbols = parse_csv(SYMBOLS_RAW)
    if not symbols and DISCOVER_QUOTES:
        symbols = discover_symbols_for_quotes(ex, quotes, DISCOVER_LIMIT)

    if not symbols:
        # Default to BTC/<first_quote> to avoid running empty
        default_sym = f"BTC/{quotes[0]}"
        log.warning(
            "No symbols configured (SYMBOLS empty and DISCOVER_QUOTES=false). Defaulting to %s",
            default_sym,
        )
        symbols = [default_sym]

    log.info("Symbols: %s", symbols)

    # Graceful shutdown
    running = True

    def _stop(_sig, _frame):
        nonlocal running
        log.info("Shutdown signal received.")
        running = False

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    # Loop
    while running:
        start = time.time()
        try:
            if hasattr(ex, "fetch_tickers"):
                # Batch fetch preferred when available
                tickers = ex.fetch_tickers(symbols) if symbols else ex.fetch_tickers()
                write_tickers(r, VALKEY_TICKERS_ROOT, tickers.items())
                log.debug("Updated %d symbols (batch).", len(tickers))
            else:
                # Fallback: per-symbol
                count = 0
                for sym in symbols:
                    t = ex.fetch_ticker(sym)
                    write_tickers(r, VALKEY_TICKERS_ROOT, [(sym, t)])
                    count += 1
                log.debug("Updated %d symbols (loop).", count)
        except Exception as e:  # noqa: BLE001
            log.exception("Oracle loop error: %s", e)

        # Sleep the remainder of the interval accounting for fetch time
        elapsed = time.time() - start
        sleep_for = max(0.0, INTERVAL_SEC - elapsed)
        time.sleep(sleep_for)

    log.info("MockX Oracle stopped.")
    return 0


if __name__ == "__main__":
    # Run the main function and exit with its return code
    raise SystemExit(main())
