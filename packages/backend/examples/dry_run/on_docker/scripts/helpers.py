from __future__ import annotations
import time
from typing import Any, Dict, List
from httpx import Client
from concurrent.futures import ThreadPoolExecutor, as_completed

# ───────────────────────── helpers ───────────────────────── #


def reset(client: Client) -> None:
    """Delete all data from the backend."""
    client.delete("/admin/data").raise_for_status()


def deposit(client: Client, asset: str, amount: float = 100_000) -> None:
    """Deposit a specified amount of an asset into the backend."""
    client.post(
        f"/balance/{asset}/deposit", json={"amount": amount}
    ).raise_for_status()


def edit_balance(client: Client, asset: str, free: float, used: float) -> None:
    """Edit the balance of a specific asset."""
    body = {"free": free, "used": used}
    client.patch(f"/admin/balance/{asset}", json=body).raise_for_status()


def reset_and_fund(client: Client, asset: str, amount: float = 100_000) -> None:
    """Reset the backend and fund the asset with a specified amount."""
    reset(client)
    deposit(client, asset, amount)


def get_tickers(client: Client) -> List[Dict[str, Any]]:
    """Get the list of tickers."""
    resp = client.get("/tickers")
    resp.raise_for_status()
    return resp.json()


def get_ticker_price(client: Client, tickers: list[str]) -> dict[str, float]:
    """Get the last price of a ticker."""
    symbols_to_retrieve = ",".join(tickers)
    resp = client.get(f"/tickers/{symbols_to_retrieve}")
    resp.raise_for_status()
    return {symbol: data["price"] for symbol, data in resp.json().items()}


def patch_ticker_price(client: Client, symbol: str, price: float) -> None:
    client.patch(
        f"/admin/tickers/{symbol}/price", json={"price": price}
    ).raise_for_status()


def place_order(client: Client, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Place a single order and return the response."""
    resp = client.post("/orders", json=payload)
    resp.raise_for_status()
    return resp.json()


def assert_no_locked_funds(client: Client, eps: float = 10**-8) -> None:
    for asset, row in client.get("/balance").json().items():
        assert row["used"] < row["total"] * eps, f"{asset} still locked: {row}"


def engine_latency(t: float = 0.5):
    """Sleep helper to let background tick-loop catch up."""
    time.sleep(t)


def cancel_order(client: Client, order_id: str) -> None:
    """Cancel an order by its ID."""
    # cancel the very low order
    client.post(f"/orders/{order_id}/cancel").raise_for_status()


def get_overview_balances(client: Client) -> dict[str, float]:
    """Get the total equity of the account."""
    resp = client.get("/overview/assets")
    resp.raise_for_status()
    return resp.json()["balance_source"]


# ────────────────── concurrent order submit ────────────────── #


def place_orders_parallel(
    client: Client, payloads: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Fire POST /orders for every payload concurrently (one thread each).
    Returns the list of order-JSONs in the *same order* as `payloads`.
    """

    def _send(body: Dict[str, Any]) -> Dict[str, Any]:
        r = client.post("/orders", json=body)
        r.raise_for_status()
        return r.json()

    results: Dict[int, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=len(payloads)) as pool:
        futures = {pool.submit(_send, body): idx for idx, body in enumerate(payloads)}
        for fut in as_completed(futures):
            idx = futures[fut]
            results[idx] = fut.result()

    return [results[i] for i in range(len(payloads))]
