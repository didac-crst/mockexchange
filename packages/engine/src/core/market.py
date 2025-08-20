"""
Read-only ticker feed (Valkey hashes `tickers:<SYMBOL>`).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import redis

from ._types import TradingPair
from .logging_config import logger


@dataclass
class Market:
    """
    Minimal reader for price hashes named ``tickers:<PAIR>``.

    The hash *must* contain at least:

        {"price": "...", "timestamp": "..."}

    Optional fields `bid`, `ask`, `bid_volume`, `ask_volume`
    default to sensible fall-backs.
    """

    conn: redis.Redis
    root_key: str = "tickers:"

    # Public API ---------------------------------------------------------
    @property
    def tickers(self) -> list[str]:
        """
        Return a list of all known tickers.

        This is a list of strings, e.g. ``["BTC/USDT", "ETH/USDT"]``.
        """
        fmt_ticker = lambda k: k[len(self.root_key) :]  # strip the root key
        return [
            fmt_ticker(k)
            for k in self.conn.scan_iter(f"{self.root_key}*")
            if k.startswith(self.root_key)
        ]

    def fetch_ticker(self, ticker: str) -> TradingPair | None:
        """
        Fetch a ticker by its symbol, e.g. "BTC/USDT".

        Returns a `TradingPair` object with the following fields:
        - `symbol`: The ticker symbol.
        - `price`: The last price.
        - `timestamp`: The timestamp of the last price.
        - `bid`: The current bid price (default to last price if not provided).
        - `ask`: The current ask price (default to last price if not provided).
        - `bid_volume`: The volume at the bid price (default to 0.0).
        - `ask_volume`: The volume at the ask price (default to 0.0).

        If the ticker does not exist, returns `None`.

        :raises ValueError: if the ticker is malformed or missing mandatory fields.
        :raises RuntimeError: if the ticker cannot be parsed correctly.
        """
        h = self.conn.hgetall(f"{self.root_key}{ticker}")
        if not h:
            return None  # ticker vanished – treat as absent
        try:
            price = float(h["price"])
            ts = float(h["timestamp"])
        except (KeyError, ValueError):
            # Just log once and skip this ticker
            logger.warning("Malformed ticker blob for %s: %s", ticker, h)
            return None

        return TradingPair(
            symbol=ticker,
            price=price,
            # Use the current time if timestamp is missing or malformed
            timestamp=ts if ts else time.time() / 1000,
            # Default bid/ask to the last price if not provided
            bid=float(h.get("bid", price)),
            ask=float(h.get("ask", price)),
            bid_volume=float(h.get("bidVolume", 0.0)),
            ask_volume=float(h.get("askVolume", 0.0)),
            info=str(h),
        )

    def last_price(self, symbol: str) -> float:
        """
        Return the last price of the ticker.

        :raises RuntimeError: if the ticker is not available
        """
        requested_TradingPair = self.fetch_ticker(symbol)
        if requested_TradingPair is None:
            raise RuntimeError(f"Ticker for {symbol} not available")
        return requested_TradingPair.price

    def set_last_price(self, TradingPair: TradingPair) -> None:
        """
        Set the last price of the ticker.

        :param TradingPair: The TradingPair object containing the ticker data.
        :raises RuntimeError: if the ticker cannot be set.
        """
        if not TradingPair.symbol:
            raise RuntimeError("TradingPair must have a symbol")

        fields = {
            "symbol": TradingPair.symbol,
            "price": TradingPair.price,
            "timestamp": TradingPair.timestamp,
            "bid": TradingPair.bid,
            "ask": TradingPair.ask,
            "bidVolume": TradingPair.bid_volume,
            "askVolume": TradingPair.ask_volume,
        }

        # Redis won’t store None, so drop them first.
        clean = {k: str(v) for k, v in fields.items() if v is not None}

        self.conn.hset(f"{self.root_key}{TradingPair.symbol}", mapping=clean)
