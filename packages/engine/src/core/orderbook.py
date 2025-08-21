"""
Redis-backed order book with secondary indexes:

* Hash  : orders          (id → json blob)             – canonical store
* Set   : open:set        (ids)                        – every open order
* Set   : open:{symbol}   (ids)                        – open orders per symbol
"""

# orderbook.py
from __future__ import annotations

from collections.abc import Iterable
from typing import TypeAlias

import redis

from ._types import Order
from .constants import OPEN_STATUS, OPEN_STATUS_STR, OrderSide, OrderState

StatusArg: TypeAlias = str | OrderState  # one element
SideArg: TypeAlias = str | OrderSide  # one element


class OrderBook:
    HASH_KEY = "orders"
    OPEN_ALL_KEY = "open:set"
    OPEN_SYM_KEY = "open:{sym}"  # .format(sym=symbol)

    def __init__(self, conn: redis.Redis) -> None:
        self.r = conn

    # ------------ internal helpers ------------------------------------ #
    def _index_add(self, order: Order) -> None:
        """Add id to the open indexes (only if order is OPEN)."""
        is_open = order.status in OPEN_STATUS or (
            isinstance(order.status, str) and order.status in OPEN_STATUS_STR
        )
        if not is_open:
            # If the order is not open, we don't need to index it.
            # This is important for performance, as we don't want to index
            # orders that are already closed (filled, canceled, etc.).
            # Only add to indexes if the order is open (new or partially filled)
            return
        self.r.sadd(self.OPEN_ALL_KEY, order.id)
        self.r.sadd(self.OPEN_SYM_KEY.format(sym=order.symbol), order.id)

    def _index_rem(self, order: Order) -> None:
        """Remove id from the open indexes."""
        self.r.srem(self.OPEN_ALL_KEY, order.id)
        self.r.srem(self.OPEN_SYM_KEY.format(sym=order.symbol), order.id)

    # ------------ CRUD ------------------------------------------------- #
    def add(self, order: Order) -> None:
        self.r.hset(self.HASH_KEY, order.id, order.to_json())
        self._index_add(order)

    def update(self, order: Order) -> None:
        """Update an existing order."""
        self.r.hset(self.HASH_KEY, order.id, order.to_json(include_history=True))

    def get(self, oid: str, *, include_history: bool = False) -> Order:
        blob = self.r.hget(self.HASH_KEY, oid)
        if blob is None:
            raise ValueError(f"Order {oid} not found")
        else:
            return Order.from_json(blob, include_history=include_history)

    def list(
        self,
        *,
        status: StatusArg | Iterable[StatusArg] | None = None,
        symbol: str | None = None,
        side: SideArg | None = None,
        tail: int | None = None,
        include_history: bool = False,
    ) -> list[Order]:
        """
        List orders by status, symbol, side, and limit the tail size.
        Open orders are indexed by symbol, so they can be fetched quickly.
        """
        orders: list[Order]
        # ── normalise `status` to a *set of raw-string values* ───────────────
        if status is None:
            status = {s.value for s in OrderState}
        elif isinstance(status, OrderState):
            status = {status.value}
        elif isinstance(status, str):
            status = {status}
        elif isinstance(status, Iterable):  # iterable of str | OrderState
            status = {s.value if isinstance(s, OrderState) else s for s in status}
        else:  # type: ignore[unreachable]
            status = set()  # fallback
        # ── normalise `side` to a *set of raw-string values* ────────────────
        if side is None:
            side_set = None  # means “no filtering”
        elif isinstance(side, OrderSide):
            side_set = {side.value}
        elif isinstance(side, str):
            side_set = {side}
        elif isinstance(side, Iterable):  # iterable of str | OrderSide
            side_set = {s.value if isinstance(s, OrderSide) else s for s in side}
        else:
            raise TypeError(
                f"side must be str | OrderSide | Iterable[str|OrderSide] | None, got {type(side)!r}"
            )
        # Use indexes only if caller asked exclusively for OPEN statuses and the set is non-empty
        use_indexes = bool(status) and all(s in OPEN_STATUS_STR for s in status)
        if use_indexes:
            # Use secondary indexes
            if symbol:
                ids = self.r.smembers(self.OPEN_SYM_KEY.format(sym=symbol))
            else:
                ids = self.r.smembers(self.OPEN_ALL_KEY)
            if not ids:
                return []
            blobs = self.r.hmget(
                self.HASH_KEY, *list(ids)
            )  # 1 round-trip, convert to list for stable order
            orders = [Order.from_json(b, include_history=include_history) for b in blobs if b]
            # Even when using indexes, re-filter by status to be robust to stale sets
            orders = [
                o
                for o in orders
                if (o.status.value if isinstance(o.status, OrderState) else o.status) in status
            ]
        else:
            # Legacy full scan
            orders = [
                Order.from_json(blob, include_history=include_history)
                for _, blob in self.r.hscan_iter(self.HASH_KEY)
            ]
            # Apply symbol filtering for legacy scan
            if symbol:
                orders = [o for o in orders if o.symbol == symbol]

        # Apply side filtering
        if side_set is not None:
            orders = [
                o
                for o in orders
                if (o.side.value if isinstance(o.side, OrderSide) else o.side) in side_set
            ]

        # Apply status filtering (only for legacy scan, index already filters for OPEN_STATUS)
        if not use_indexes:
            orders = [
                o
                for o in orders
                if (o.status.value if isinstance(o.status, OrderState) else o.status) in status
            ]

        # chronological order on update timestamp
        orders.sort(key=lambda o: o.ts_update, reverse=True)
        if tail is not None and tail > 0:
            orders = orders[:tail]
        return orders

    # ---------- hard delete ------------------------------------------ #
    def remove(self, oid: str) -> None:
        """Erase an order from storage and all indexes. Idempotent."""
        blob = self.r.hget(self.HASH_KEY, oid)
        if not blob:  # already gone
            return
        o = Order.from_json(blob)
        is_open = o.status in OPEN_STATUS or (
            isinstance(o.status, str) and o.status in OPEN_STATUS_STR
        )
        if is_open:
            self._index_rem(o)
        pipe = self.r.pipeline()
        pipe.hdel(self.HASH_KEY, oid)
        pipe.execute()

    # ---------- admin ------------------------------------------ #
    def clear(self) -> None:
        pipe = self.r.pipeline()
        pipe.delete(self.HASH_KEY)
        pipe.delete(self.OPEN_ALL_KEY)
        # nuke every per-symbol set in one pass
        for key in self.r.keys(self.OPEN_SYM_KEY.format(sym="*")):
            pipe.delete(key)
        pipe.execute()
