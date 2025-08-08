"""
tests/test_05_cancel_limit_orders.py
====================================

Regression-test for the *explicit cancellation* workflow.

Goal
----
When a user cancels open limit orders the engine must

* move the order to a terminal state (``canceled`` or
  ``partially_canceled``),
* release **all** reservations so no asset remains in the portfolio’s
  ``used`` column.

This test creates a large batch of *deliberately unfillable* limit orders
(BUY at an absurdly low price, SELL at an absurdly high price), then
cancels them and verifies the two guarantees above.
"""

from __future__ import annotations

import random

from .helpers import (
    assert_no_locked_funds,
    cancel_order,
    deposit,
    get_tickers,
    place_order,
    reset_and_deposit,
)

# Engine state buckets we expect to see
OPEN_STATES: tuple[str, ...] = ("new", "partially_filled")
CLOSED_STATES: tuple[str, ...] = (
    "filled",
    "canceled",
    "rejected",
    "partially_canceled",
    "expired",
)
ALL_STATES = OPEN_STATES + CLOSED_STATES

N_TICKERS: int = 100  # how many symbols we exercise in this test


# --------------------------------------------------------------------------- #
# Test case
# --------------------------------------------------------------------------- #
def test_cancel_orders(client):
    """
    *Create → Cancel → Verify* flow for a large batch of limit orders.

    Steps
    -----
    1. **Reset & Fund** the wallet with 100 000 USDT.
    2. **Seed inventory**: credit each *base* asset that will be sold so the
       SELL side never runs out of stock.
    3. **Submit** one BUY *and* one SELL limit order per symbol at prices that
       make them *impossible to fill*.
    4. **Cancel** every still-open order.
    5. **Assert**:
       * every order is now in :pydata:`CLOSED_STATES`;
       * portfolio is squeaky clean – no residual reservations.
    """

    # ------------------------------------------------------------------ #
    # 1) Fresh slate with plenty of USDT liquidity
    # ------------------------------------------------------------------ #
    initial_asset = "USDT"
    initial_amount = 100_000.0
    reset_and_deposit(client, initial_asset, initial_amount)

    assert client.get(f"/balance/{initial_asset}").json() == {
        "asset": initial_asset,
        "free": initial_amount,
        "used": 0.0,
        "total": initial_amount,
    }

    # ------------------------------------------------------------------ #
    # 2) Prepare: choose tickers and fund their *base* assets
    # ------------------------------------------------------------------ #
    tickers = random.sample(get_tickers(client), k=N_TICKERS)

    #   BUY orders use quote only, but SELL orders also reserve *base* +
    #   fee.  We therefore credit each base asset with plenty of units.
    for ticker in tickers:
        base_asset = ticker.split("/")[0]
        deposit(client, base_asset, initial_amount)

    # ------------------------------------------------------------------ #
    # 3) Submit the intentionally unfillable limit orders
    # ------------------------------------------------------------------ #
    # Notional per trade = total_cash / (1.2 * N) so we never blow the budget
    notion_per_order = initial_amount / (1.2 * N_TICKERS)

    # Price extremes that guarantee the orders will stay “far from market”
    LIMIT_PRICES = {
        "buy": 0.000001,  # absurdly low  → never hits ask
        "sell": 1_000_000.0,  # absurdly high → never hits bid
    }

    orders_by_id: dict[str, dict] = {}

    for side in ("buy", "sell"):
        for symbol in tickers:
            qty = notion_per_order / LIMIT_PRICES[side]
            if side == "sell":
                qty *= 0.9  # leave margin so the account stays liquid

            payload = {
                "type": "limit",
                "side": side,
                "symbol": symbol,
                "amount": qty,
                "limit_price": LIMIT_PRICES[side],
            }
            rsp = place_order(client, payload)
            orders_by_id[rsp["id"]] = {**payload, "id": rsp["id"]}

    # ------------------------------------------------------------------ #
    # 4) Cancel every order that is still open
    # ------------------------------------------------------------------ #
    for o in client.get("/orders").json():
        if o["status"] in OPEN_STATES:
            cancel_order(client, o["id"])

    # ------------------------------------------------------------------ #
    # 5) Assertions – terminal states & clean reservations
    # ------------------------------------------------------------------ #
    for o in client.get("/orders").json():
        ref = orders_by_id.get(o["id"])
        if not ref:
            continue  # ignore unrelated orders (other tests)

        assert o["status"] in CLOSED_STATES  # must be terminal
        assert o["symbol"] == ref["symbol"]  # echo invariant
        assert o["side"] == ref["side"]
        assert o["type"] == ref["type"]
        # Amount check: tiny FP noise possible due to rounding
        assert abs(o["amount"] - ref["amount"]) < 1e-9

    # Portfolio must have zero in every *used* column
    assert_no_locked_funds(client)
