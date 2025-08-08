"""model.py

Pydantic **domain models** shared across UI layers.

These classes mirror the JSON payloads coming from the MockExchange API
so that Streamlit pages (or any other consumer) can benefit from
*automatic type validation* and *autocompletion* while staying agnostic
of the wire format.

Only comments and docstrings were added – the data model remains
unchanged.
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Standard library
# -----------------------------------------------------------------------------
from datetime import datetime
from typing import Literal, Optional

# Third-party
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Balance models
# -----------------------------------------------------------------------------

class BalanceAsset(BaseModel):
    """Single asset row inside a `/balance` snapshot."""

    asset: str                     # e.g. "BTC"
    free: float                    # immediately available amount
    used: float                    # frozen on open orders
    total: float                   # convenience: free + used (server side)
    quote_price: Optional[float] = None  # last price in quote asset (e.g. USDT)

    @property
    def value(self) -> float:  # noqa: D401 – short property description fine
        """Market value in **quote asset** – falls back to 0 if price missing."""
        return (self.total or 0) * (self.quote_price or 0)


class BalanceSnapshot(BaseModel):
    """Top-level structure returned by `/balance`."""

    equity_quote: float = Field(..., alias="equityQuote")  # total equity in quote asset
    assets: list[BalanceAsset]                              # per-asset breakdown


# -----------------------------------------------------------------------------
# Order model (used by Orders page & details pop-up)
# -----------------------------------------------------------------------------

class Order(BaseModel):
    """Flat representation of an order row from `/orders`."""

    id: str
    symbol: str                           # e.g. "BTC/USDT"
    side: Literal["BUY", "SELL"]         # forced upper-case by API
    type: str                             # "market", "limit", … – no enum yet
    price: float                          # average execution price so far
    qty: float                            # requested quantity
    filled: float                         # executed quantity
    status: str                           # enum as string ("filled", …)
    ts: datetime                          # creation timestamp