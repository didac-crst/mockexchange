"""
Balances live in *one* Valkey hash:  HSET balances <ASSET> <json>.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
import redis
from typing import Dict, Any
from ._types import AssetBalance

class Portfolio:
    """
    Thin CRUD wrapper over *one* Redis hash called ``balances``.

    Keys   : asset symbol (BTC, USDT…)  
    Values : compact JSON produced by :class:`AssetBalance.to_dict`
    """

    def __init__(self, conn: redis.Redis) -> None:
        self.conn, self.key = conn, "balances"

    # Internal helpers ---------------------------------------------------
    def _dump(self, bal: AssetBalance) -> str:
        return json.dumps(bal.to_dict(), separators=(",", ":"))

    def _load(self, blob: str) -> AssetBalance:
        return AssetBalance.from_dict(json.loads(blob))

    # Public API ---------------------------------------------------------
    def get(self, asset: str) -> AssetBalance:
        """Return balance or a zeroed placeholder if none exists."""
        try:
            asset = asset.upper()
            blob = self.conn.hget(self.key, asset)
            return self._load(blob) if blob else AssetBalance(asset)
        except redis.RedisError as e:
            raise RuntimeError(f"Failed to get balance for {asset}: {e}")

    def set(self, bal: AssetBalance) -> None:
        """Insert / overwrite a balance atomically (`HSET`)."""
        self.conn.hset(self.key, bal.asset, self._dump(bal))

    def all(self) -> Dict[str, AssetBalance]:
        """Return *all* balances as a dict keyed by asset."""
        return {a: self._load(b) for a, b in self.conn.hgetall(self.key).items()}

    def clear(self) -> None:
        """Delete the entire hash – use with care."""
        self.conn.delete(self.key)