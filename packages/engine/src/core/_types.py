"""
Shared tiny enums / dataclasses used across the package.
Keeps circular-import headaches away from the business logic.
"""

# _types.py
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from dataclasses import fields as dataclass_fields
from typing import Any

from .constants import CLOSED_STATUS, OrderSide, OrderState, OrderType


# ─── Data classes ────────────────────────────────────────────────────────
@dataclass
class AssetBalance:
    """
    One row inside the portfolio hash.

    *Why not store ``total``?*
    It’s always `free + used`, so we compute it on the fly.
    """

    asset: str
    free: float = 0.0
    used: float = 0.0

    # Derived ------------------------------------------------------------
    @property
    def total(self) -> float:
        return self.free + self.used

    # (De)serialise ------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset,
            "free": self.free,
            "used": self.used,
            "total": self.total,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AssetBalance:
        return cls(
            asset=d["asset"],
            free=float(d.get("free", 0.0)),
            used=float(d.get("used", 0.0)),
        )


@dataclass
class TradingPair:
    """
    Trading pair data structure.

    Fields
    ------
    symbol: trading pair symbol (e.g., "BTC/USDT")
    price: current price of the trading pair
    timestamp: timestamp of the last update (in seconds since epoch)
    bid: current highest bid price
    ask: current lowest ask price
    bid_volume: volume at the current highest bid price
    ask_volume: volume at the current lowest ask price
    """

    symbol: str
    price: float
    timestamp: float
    bid: float
    ask: float
    bid_volume: float
    ask_volume: float
    info: str = None

    # (De)serialise ------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "timestamp": self.timestamp,
            "bid": self.bid,
            "ask": self.ask,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TradingPair:
        return cls(
            symbol=d["symbol"],
            price=float(d["price"]),
            timestamp=float(d["timestamp"]),
            bid=float(d["bid"]),
            ask=float(d["ask"]),
            bid_volume=float(d["bid_volume"]),
            ask_volume=float(d["ask_volume"]),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))


@dataclass
class OrderHistory:
    """
    Order history entry.

    Fields
    ------
    ts        millis when the history entry was created
    status    order status (e.g., filled, canceled, etc.)
    price     execution price (None for market orders)
    amount_remain    amount remaining to be filled
    actual_filled   filled amount at this point
    actual_notion    filled notion value at this point
    actual_fee       fee paid for this fill (None for market orders)
    reserved_notion_left  notion value booked for the order (not yet filled)
    reserved_fee_left     fee booked for the order (not yet paid)
    comment   optional comment for the history entry
    """

    ts: int
    status: str
    price: float | None = None
    amount_remain: float | None = None
    actual_filled: float | None = None
    actual_notion: float | None = None
    actual_fee: float | None = None
    reserved_notion_left: float | None = None
    reserved_fee_left: float | None = None
    comment: str | None = None


@dataclass
class Order:
    """
    Internal order representation (kept small on purpose).

    Fields
    ------
    id            unique, URL-safe token
    symbol        trading pair (e.g., "BTC/USDT")
    side          ``buy`` / ``sell``
    type          ``market`` / ``limit``
    amount        order size in base currency
    status        ``new`` / ``filled`` / ``canceled`` / ``expired`` / ``rejected`` / ``partially_filled`` / ``partially_canceled`` / ``partially_expired`` / ``partially_rejected``
    price         actual execution price (set at fill time)
    limit_price   user-defined limit price (None for market orders)
    actual_filled        total amount filled so far
    initial_booked_notion  initial notion value booked for the order (not yet filled)
    reserved_notion_left  initial notion value booked for the order (not yet filled)
    actual_notion        total traded value (filled × price)
    initial_booked_fee     initial fee booked for the order (not yet filled)
    reserved_fee_left   fee booked for the order (not yet paid)
    actual_fee      fee paid for the order
    fee_rate      fee rate (e.g. 0.001 for 0.1%)
    notion_currency  quote currency used for value (e.g. USDT)
    fee_currency     currency in which the fee is charged
    ts_create       millis when the order was *created*
    ts_update       millis when the order was last *updated*
    ts_finish       millis when it can't be further updated (e.g. filled, canceled...)
    history         transaction history of every order update
    history_count  number of history entries (used to index the history)
    _seed history   only if this is a fresh object (no history loaded yet)

    Notes
    -----
    Fees are quoted in the *quote* currency (usually `USDT`).
    """

    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    amount: float
    notion_currency: str  # usually the quote currency, e.g. USDT
    fee_currency: str
    fee_rate: float
    # Runtime-mutable fields
    actual_filled: float = 0.0  # until filled
    price: float | None = None
    limit_price: float | None = None  # None for market orders
    status: OrderState = OrderState.NEW
    initial_booked_notion: float = 0.0
    reserved_notion_left: float = 0.0  # until filled
    actual_notion: float = 0.0  # until filled
    initial_booked_fee: float = 0.0
    reserved_fee_left: float = 0.0  # until filled
    actual_fee: float = 0.0  #  until filled
    ts_create: int = field(default_factory=lambda: int(time.time() * 1000))
    ts_update: int = field(default_factory=lambda: int(time.time() * 1000))
    ts_finish: int | None = None  # updated when status→closed
    comment: str | None = None  # optional comment for the order
    # History management
    history: dict[int, OrderHistory] = field(default_factory=dict)
    history_count: int = 0  # next free index (not last!)
    _seed_history: bool = True

    def __post_init__(self):
        # Only seed history if requested and it's a fresh object (no history yet)
        if not self._seed_history or self.history:
            return
        self.add_history(
            ts=self.ts_create,
            status=self.status,
            price=self.price,
            amount_remain=self.amount,
            reserved_notion_left=self.reserved_notion_left,
            reserved_fee_left=self.reserved_fee_left,
            comment=self.comment,
        )

    # (De)serialise ------------------------------------------------------
    def to_dict(self, *, include_history: bool = True) -> dict:
        """Return a plain dict representation. Optionally strip history to keep payloads small."""
        d = asdict(self)
        # enums -> their raw value so json.dumps works
        d["side"] = self.side.value
        d["type"] = self.type.value
        d["status"] = self.status.value
        if not include_history:
            d.pop("history", None)
        d.pop("_seed_history", None)
        return d

    def to_json(self, *, include_history: bool = True) -> str:
        d = self.to_dict(include_history=include_history)
        return json.dumps(d, separators=(",", ":"))

    @classmethod
    def from_json(cls, blob: str, *, include_history: bool = False) -> Order:
        data = json.loads(blob)
        # normalise string literals back to Enum instances
        if isinstance(data.get("side"), str):
            data["side"] = OrderSide(data["side"])
        if isinstance(data.get("type"), str):
            data["type"] = OrderType(data["type"])
        if isinstance(data.get("status"), str):
            data["status"] = OrderState(data["status"])
        allowed = {f.name for f in dataclass_fields(cls)}
        if include_history:
            raw_hist = data.get("history", {}) or {}
            hist: dict[int, OrderHistory] = {}
            # rebuild contiguous indices 0..N-1 to avoid gaps
            for i, (_, v) in enumerate(
                sorted(((int(k), v) for k, v in raw_hist.items()), key=lambda x: x[0])
            ):
                hist[i] = OrderHistory(**v)
            data["history"] = hist
            data["history_count"] = len(hist)
            data["_seed_history"] = False  # already have history, do not seed again
        else:
            # keep counter correct even if we drop the heavy history payload
            raw_hist = data.get("history", {}) or {}
            if isinstance(raw_hist, dict) and raw_hist:
                # next_idx = max(int(k) for k in raw_hist.keys()) + 1
                next_idx = len(raw_hist)
            else:
                next_idx = data.get("history_count", 0)
            data["history_count"] = next_idx
            # drop heavy fields and mark to skip seeding
            data["_seed_history"] = False
        # keep only known fields
        data = {k: v for k, v in data.items() if k in allowed}
        return cls(**data)

    # History management ---------------------------------------------
    def add_history(
        self,
        ts: int,
        status: str,
        price: float | None = None,
        amount_remain: float | None = None,
        actual_filled: float | None = None,
        reserved_notion_left: float | None = None,
        actual_notion: float | None = None,
        reserved_fee_left: float | None = None,
        actual_fee: float | None = None,
        comment: str | None = None,
    ) -> None:
        """Add a new history entry."""
        history = OrderHistory(
            ts=ts,
            status=status,
            price=price,
            amount_remain=amount_remain,
            actual_filled=actual_filled,
            actual_notion=actual_notion,
            actual_fee=actual_fee,
            reserved_notion_left=reserved_notion_left,
            reserved_fee_left=reserved_fee_left,
            comment=comment,
        )
        idx = self.history_count
        self.history[idx] = history
        self.history_count = idx + 1

    # Residuals handling -----------------------------------
    @property
    def residual_base(self) -> float:
        if self.status in CLOSED_STATUS or self.side is OrderSide.BUY:
            # If the order is closed or a buy order, there are no residuals
            # This is because buy orders do not have a residual base
            return 0.0
        else:
            # For sell orders, the residual base is the amount not yet filled
            # (i.e., the amount that can still be sold)
            # This is the difference between the total amount and what has been filled
            return max(self.amount - self.actual_filled, 0.0)

    @property
    def residual_quote(self) -> float:
        """What’s still reserved in quote currency (USDT) that must be released."""
        if self.status in CLOSED_STATUS:
            # If the order is closed, there are no residuals
            return 0.0
        if self.side is OrderSide.BUY:
            # For buy orders, the residual quote is the sum of reserved notion and fee
            # This is the total value that was reserved for the order but not yet filled
            # It includes both the notion value and the fee that was reserved
            return max(self.reserved_notion_left, 0.0) + max(
                self.reserved_fee_left, 0.0
            )
        else:
            # For sell orders, the residual quote is the fee that was reserved
            # This is the fee that was reserved for the order but not yet paid
            # It does not include the notion value, as it is not reserved for sell orders
            return max(self.reserved_fee_left, 0.0)

    def squash_booking(self):
        # keep accountability: align booked_* to actual
        self.reserved_notion_left = 0.0
        self.reserved_fee_left = 0.0

    @property
    def amount_remain(self) -> float:
        return max(self.amount - self.actual_filled, 0.0)

    @property
    def last_history(self) -> OrderHistory | None:
        """Get the last history entry."""
        if self.history and self.history_count >= 0:
            return self.history.get(self.history_count - 1)
        return None

    def public_payload(self) -> dict:
        d = self.to_dict(include_history=False)
        return d
