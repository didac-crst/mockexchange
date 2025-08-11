# cli.py  ── thin HTTP wrapper around the FastAPI service
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx  # pip install httpx

"""Command-line helper for *MockExchange*.

Adds coverage for all current API endpoints (August 2025).

Usage examples
--------------

```bash
# List all symbols
mockx tickers

# Show one ticker
mockx ticker BTC/USDT

# Deposit 10 000 USDT
mockx deposit USDT 10000

# Withdrawal some BTC
mockx withdrawal BTC 0.25

# Place a limit order
mockx order BTC/USDT buy 0.01 --type limit --price 28000

# Portfolio summaries
mockx overview-capital          # aggregated P&L
mockx overview-assets           # cash + frozen breakdown
mockx overview-trades --side buy --assets BTC,ETH
```
"""

# ────────────────────────────── Config ──────────────────────────────── #
API_URL = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "invalid-key")
TIMEOUT = float(os.getenv("API_TIMEOUT_SEC", "10"))
HEADERS = {"x-api-key": API_KEY}

client = httpx.Client(base_url=API_URL, headers=HEADERS, timeout=TIMEOUT)

# ───────────────────────────── Helpers ──────────────────────────────── #


def _get(path: str, **params):
    r = client.get(path, params={k: v for k, v in params.items() if v is not None})
    _raise_for_status(r)
    return r.json()


def _post(path: str, payload: dict[str, Any] | None = None):
    r = client.post(path, json=payload or {})
    _raise_for_status(r)
    return r.json()


def _patch(path: str, payload: dict[str, Any]):
    r = client.patch(path, json=payload)
    _raise_for_status(r)
    return r.json()


def _delete(path: str):
    r = client.delete(path)
    _raise_for_status(r)
    return r.json()


def _raise_for_status(r: httpx.Response) -> None:
    if r.is_success:
        return
    try:
        detail = r.json().get("detail", r.text)
    except ValueError:
        detail = r.text or r.reason_phrase
    sys.exit(f"HTTP {r.status_code}: {detail}")


def pp(obj: Any):
    print(json.dumps(obj, indent=2, sort_keys=True))


# ───────────────────────────── argparse ─────────────────────────────── #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("mockx")
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- market ------------------------------------------------------ #
    sub.add_parser("tickers")  # list all
    tk = sub.add_parser("ticker")
    tk.add_argument("symbol", help="BTC/USDT or A,B,C list")

    # --- portfolio --------------------------------------------------- #
    sub.add_parser("balance")  # full snapshot
    bl = sub.add_parser("balance-asset")  # one row
    bl.add_argument("asset")
    sub.add_parser("balance-list")  # just names

    dep = sub.add_parser("deposit")  # POST /balance/{asset}/deposit
    dep.add_argument("asset")
    dep.add_argument("amount", type=float)

    wd = sub.add_parser("withdrawal")  # POST /balance/{asset}/withdrawal
    wd.add_argument("asset")
    wd.add_argument("amount", type=float)

    # --- orders ------------------------------------------------------ #
    ordp = sub.add_parser("order")
    ordp.add_argument("symbol")
    ordp.add_argument("side", choices=["buy", "sell"])
    ordp.add_argument("amount", type=float)
    ordp.add_argument("--type", choices=["market", "limit"], default="market")
    ordp.add_argument("--price", type=float, dest="limit_price")

    can = sub.add_parser("can-exec")
    for a in ("symbol", "side", "amount"):
        can.add_argument(a)
    can.add_argument("--price", type=float)

    sub.add_parser("orders")  # verbose list (filters via flags)
    ol = sub.add_parser("orders-simple")  # just ids
    for a in ("status", "symbol", "side"):
        ol.add_argument(f"--{a}")
    ol.add_argument("--tail", type=int)

    og = sub.add_parser("order-get")
    og.add_argument("order_id")

    oc = sub.add_parser("cancel")
    oc.add_argument("order_id")

    # --- overview ---------------------------------------------------- #
    sub.add_parser("overview-capital").add_argument(
        "--raw", action="store_true", help="return unaggregated data"
    )
    sub.add_parser("overview-assets")

    ot = sub.add_parser("overview-trades")
    ot.add_argument("--side", choices=["buy", "sell"])
    ot.add_argument("--assets", help="Comma-separated base symbols, e.g. BTC,ETH")

    # --- admin helpers ---------------------------------------------- #
    sb = sub.add_parser("set-balance")
    sb.add_argument("asset")
    sb.add_argument("--free", type=float, required=True)
    sb.add_argument("--used", type=float, default=0.0)

    sp = sub.add_parser("set-price")
    sp.add_argument("symbol")
    sp.add_argument("price", type=float)
    sp.add_argument("--bid-volume", type=float)
    sp.add_argument("--ask-volume", type=float)

    sub.add_parser("reset-data")
    sub.add_parser("health")

    return p


# ───────────────────────────── dispatch ────────────────────────────── #


def main():  # noqa: C901 – big matcher is fine here
    args = build_parser().parse_args()

    match args.cmd:
        # Market -------------------------------------------------------
        case "tickers":
            pp(_get("/tickers"))
        case "ticker":
            pp(_get(f"/tickers/{args.symbol}"))

        # Portfolio ----------------------------------------------------
        case "balance":
            pp(_get("/balance"))
        case "balance-asset":
            pp(_get(f"/balance/{args.asset}"))
        case "balance-list":
            pp(_get("/balance/list"))
        case "deposit":
            pp(_post(f"/balance/{args.asset}/deposit", {"amount": args.amount}))
        case "withdrawal":
            pp(_post(f"/balance/{args.asset}/withdrawal", {"amount": args.amount}))

        # Orders -------------------------------------------------------
        case "order":
            body = {
                "symbol": args.symbol,
                "side": args.side,
                "type": args.type,
                "amount": args.amount,
                "limit_price": args.limit_price,
            }
            pp(_post("/orders", body))
        case "cancel":
            pp(_post(f"/orders/{args.order_id}/cancel"))
        case "orders":
            pp(_get("/orders"))
        case "orders-simple":
            pp(
                _get(
                    "/orders/list",
                    status=args.status,
                    symbol=args.symbol,
                    side=args.side,
                    tail=args.tail,
                )
            )
        case "order-get":
            pp(_get(f"/orders/{args.order_id}"))
        case "can-exec":
            body = {
                "symbol": args.symbol,
                "side": args.side,
                "amount": float(args.amount),
                "price": args.price,
            }
            pp(_post("/orders/can_execute", body))

        # Overview -----------------------------------------------------
        case "overview-capital":
            pp(_get("/overview/capital", aggregation=not args.raw))
        case "overview-assets":
            pp(_get("/overview/assets"))
        case "overview-trades":
            pp(_get("/overview/trades", side=args.side, assets=args.assets))

        # Admin --------------------------------------------------------
        case "set-balance":
            pp(
                _patch(
                    f"/admin/balance/{args.asset}",
                    {"free": args.free, "used": args.used},
                )
            )
        case "set-price":
            payload = {
                "price": args.price,
                "bid_volume": args.bid_volume,
                "ask_volume": args.ask_volume,
            }
            pp(_patch(f"/admin/tickers/{args.symbol}/price", payload))
        case "reset-data":
            pp(_delete("/admin/data"))
        case "health":
            pp(_get("/admin/health"))
        case _:
            sys.exit("Unknown command – check --help")


if __name__ == "__main__":
    main()
