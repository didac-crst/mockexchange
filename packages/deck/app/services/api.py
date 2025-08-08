"""api.py

Thin synchronous REST wrapper around the MockExchange back-end.

* Centralises **base-URL** + **API-key** handling so pages can simply call
  `get_balance()`, `get_orders()` … without repeating boilerplate.
* Normalises the varying shapes returned by `/balance`, `/tickers`, …
  into predictable pandas DataFrames or dicts.
* Adds a tiny layer of *resilience* (type checks, helpful exceptions)
  while keeping network I/O trivial (`requests.get`, timeout=3 s).

Only docstrings and comments have been added – runtime logic is intact.
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Standard library & 3rd-party imports
# -----------------------------------------------------------------------------
import requests
import pandas as pd

# Project settings helper – returns a dict of env-based config values
from app.config import settings

# -----------------------------------------------------------------------------
# Global constants (resolved once at import time)
# -----------------------------------------------------------------------------
HEAD, BASE = {"x-api-key": settings()["API_KEY"]}, settings()["API_URL"]
QUOTE = settings()["QUOTE_ASSET"]  # e.g. "USDT"

# -----------------------------------------------------------------------------
# Internal convenience helpers (prefixed with underscore)
# -----------------------------------------------------------------------------

def _get(path: str):  # noqa: D401 – short desc fine
    """Perform a **GET** request to *BASE + path* with auth header.

    Raises ``requests.exceptions.HTTPError`` on non-200 responses so the
    caller can handle it explicitly.
    """
    r = requests.get(f"{BASE}{path}", headers=HEAD, timeout=3)
    r.raise_for_status()
    return r.json()


def _prices_for_assets(assets: list[str]) -> dict[str, float]:  # noqa: D401
    """Return mapping ``{asset: last_price_in_quote}``.

    Supports two payload styles:
    * **Dict** – as delivered by `/tickers/BTC/USDT,ETH/USDT`
    * **List** – future-proof for a potential `/ticker/price` alias

    Any unknown shape will raise ``TypeError`` so pages fail early.
    """

    # Build comma-separated pair list (skip the quote asset itself)
    pairs = [f"{a}/{QUOTE}" for a in assets if a != QUOTE]
    price_map = get_prices(pairs)
    # Quote asset always maps to 1.0 so downstream math is simpler
    price_map.setdefault(QUOTE, 1.0)

    price_asset_map = {symbol.split("/")[0]: value for symbol, value in price_map.items()}

    return price_asset_map


def _extract_assets(raw):  # noqa: D401 – helper, not user-facing
    """Normalise the many `/balance` response shapes into *list[dict]*.

    Handles five shapes defined in the docstring; raises ``ValueError`` if
    the payload is completely unfamiliar so bugs surface fast.
    """
    # Simple list – already what we want (#4)
    if isinstance(raw, list):
        return raw

    if isinstance(raw, dict):
        # Variants #1-3 – assets stored under a key
        for key in ("assets", "data", "balances"):
            if key in raw and isinstance(raw[key], list):
                return raw[key]

        # Variant #5 – mapping style {"BTC": {...}, ...}
        if all(isinstance(v, dict) for v in raw.values()):
            return [{"asset": k, **v} for k, v in raw.items()]

    raise ValueError("Unrecognised `/balance` payload shape")

# -----------------------------------------------------------------------------
# Public API helpers (called by Streamlit pages)
# -----------------------------------------------------------------------------

def get_overview_capital() -> dict:
    """Return a dict with the current capital summary.

    The dict contains:
    - `equity` – current equity in quote asset (e.g. USDT)
    - `deposits` – total deposits in quote asset
    - `withdrawals` – total withdrawals in quote asset
    - `profit_loss` – current profit/loss in quote asset

    """
    res = _get("/overview/capital")
    if not isinstance(res, dict):
        raise TypeError(f"Expected dict from /overview/capital, got {type(res)}")
    
    # Ensure all expected keys are present
    expected_keys = {"equity", "deposits", "withdrawals", "profit_loss"}
    if not expected_keys.issubset(res.keys()):
        raise KeyError(f"Missing keys in /overview/capital response: {expected_keys - res.keys()}")

    return res    

def get_prices(tickers: list[str]) -> dict[str, float]:
    """Return a mapping of ``{ticker: last_price_in_quote}``.

    The *tickers* list must contain pairs like "BTC/USDT", "ETH/USDT" etc.
    The quote asset is determined by the global setting (e.g. "USDT").
    """
    res = _get(f"/tickers/{','.join(tickers)}")

    def _extract_price(d: dict) -> float | None:
        """Find the price field regardless of CCXT vs simplified schema."""
        if "last" in d:  # standard CCXT ticker
            return float(d["last"])
        if "info" in d and "price" in d["info"]:
            return float(d["info"]["price"])
        return None  # unknown format → caller will skip

    price_map: dict[str, float] = {}

    # ---------------- Dict payload ----------------
    if isinstance(res, dict):
        for data in res.values():
            p = _extract_price(data)
            if p is not None:
                price_map[data["symbol"]] = p

    # ---------------- List payload ----------------
    elif isinstance(res, list):
        for data in res:
            p = _extract_price(data)
            if p is not None and "symbol" in data:
                price_map[data["symbol"]] = p
    else:
        raise TypeError(f"Unexpected ticker payload type: {type(res)}")

    return price_map

def get_balance() -> dict:
    """Fetch `/balance` and return a structured dict
    (equity, quote_asset, assets_df)."""

    snap = _get("/balance")
    if len(snap) == 0:
        return {
            "equity": 0.0,
            "quote_asset": settings()["QUOTE_ASSET"],
            "assets_df": pd.DataFrame(),
        }

    assets_df = pd.DataFrame(_extract_assets(snap))

    # ---- Ensure mandatory columns exist --------------------------------
    if "asset" not in assets_df.columns:
        raise KeyError("`/balance` response lacks an 'asset' column")

    if "total" not in assets_df.columns:
        # Derive from free + locked as fallback
        free = assets_df.get("free")
        locked = assets_df.get("locked", 0)
        if free is not None:
            assets_df["total"] = free + locked
        else:
            raise KeyError("Neither 'total' nor 'free' present in balance data")

    # ---- Attach last prices -------------------------------------------
    if "quote_price" not in assets_df.columns:
        price_map = _prices_for_assets(assets_df["asset"].tolist())
        assets_df["quote_price"] = assets_df["asset"].map(price_map)

    equity = (assets_df["total"] * assets_df["quote_price"]).sum()

    return {
        "equity": equity,
        "quote_asset": settings()["QUOTE_ASSET"],
        "assets_df": assets_df,
    }


def get_active_asset_count() -> int:
    """Return just the `count` field from `/balance/list`."""
    return _get("/balance/list")["count"]


def get_assets_overview() -> dict:
    """Return the dict payload from `/overview/assets` with basic validation."""
    summary = _get("/overview/assets")
    if not isinstance(summary, dict):
        raise TypeError(f"Expected dict from /overview/assets, got {type(summary)}")
    return summary


def get_orders(status: str | None = None, tail: int = 50) -> pd.DataFrame:
    """Return recent orders as a DataFrame.

    Parameters
    ----------
    status : str | None
        Optional filter – e.g. "open", "filled", "canceled". ``None`` → all.
    tail : int, default 50
        How many most-recent rows to pull; maps to the server's ``tail`` query param.
    """

    params: list[str] = []
    if status:
        params.append(f"status={status}")
    if tail:
        params.append(f"tail={tail}")
    path = "/orders" + ("?" + "&".join(params) if params else "")

    rows = _get(path)  # returns list[dict]
    return pd.DataFrame(rows)

def get_trades_overview() -> tuple[dict, str]:
    """Return the dict payload from `/overview/trades` with basic validation.
    raw  – JSON you pasted above (already loaded to a dict)
    quote – e.g. "USDT".  If None, we aggregate every quote we find.

    Returns
    -------
    {
        "BUY":  {"count": 3, "amount": 2675.819..., "notional": 2_170.011..., "fee": 1.627...},
        "SELL": {"count": 1, "amount":  241.525..., "notional":   182.183..., "fee": 0.137...},
        "TOTAL":{... BUY+SELL ...}
    }
    """
    raw = _get("/overview/trades")
    if not isinstance(raw, dict):
        raise TypeError(f"Expected dict from /overview/trades, got {type(raw)}")
    
    # helper that finds out all the assets in the trades
    def _find_assets_in_trades(raw: dict) -> set[str]:
        assets = set()
        for side in ("BUY", "SELL"):
            side_block = raw.get(side, {})
            for base, _ in side_block.get("amount", {}).items():
                assets.add(base)
        return assets

    assets_in_trades = [base for base in _find_assets_in_trades(raw) if base != QUOTE]
    # Here we are passing only the asset name and not the full pair like "BTC/USDT"
    # In sum_metric we will only need the base asset name, not the quote.
    last_prices = _prices_for_assets(assets_in_trades) # noqa: D401

    # helper that digs into one metric (count/amount/notional/fee)
    def _sum_metric(side_block: dict, metric: str, last_prices: dict) -> float:
        is_missing_price = False
        total = 0.0
        # side_block[metric] looks like  {"ADA":{"USDT":"…"}, "XRP":{"USDT":"…"}}
        for base, q_dict in side_block[metric].items():
            for q, val in q_dict.items():
                if q != QUOTE:
                    continue
                if metric == "amount":
                    # Convert amount to value in quote currency (e.g. USDT)
                    try:
                        last_price = last_prices[base]
                    except KeyError:
                        is_missing_price = True
                        continue
                    total += float(val) * last_price
                else:
                   total += float(val)
        return total, is_missing_price

    sides = ("BUY", "SELL")
    out: dict[str, dict[str, float]] = {s: {} for s in sides}

    for s in sides:
        block = raw.get(s, {})
        if not block:
            continue
        out[s]["count"], _ = _sum_metric(block, "count", last_prices)
        out[s]["amount_value"], out[s]["amount_value_incomplete"] = _sum_metric(block, "amount", last_prices)
        out[s]["notional"], _ = _sum_metric(block, "notional", last_prices)
        out[s]["fee"], _ = _sum_metric(block, "fee", last_prices)

    # grand-total across sides
    out["TOTAL"] = {
        k: out.get("BUY", {}).get(k, 0) + out.get("SELL", {}).get(k, 0)
        for k in ("count", "amount_value", "notional", "fee")
    }
    out["TOTAL"]["amount_value_incomplete"] = bool(
        out["BUY"]["amount_value_incomplete"] or
        out["SELL"]["amount_value_incomplete"]
    )
    return out, QUOTE