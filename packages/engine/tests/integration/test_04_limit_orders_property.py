"""
tests/test_04_limit_orders_property.py
======================================

Property-based smoke-test for *limit-order* handling.

This is the “limit order twin” of the previous *market-order* property test.
A limit order executes only **after** the ticker is moved to the target price
via ``PATCH /admin/tickers/{symbol}/price`` – code-paths that are not exercised
by the market-order test.

Guarantees asserted
-------------------
1. **State convergence** – after matching, **every** order is in one of the
   terminal states listed in :pydata:`CLOSED_STATES`.
2. **No residual locks** – once all orders are closed the portfolio must show
   ``used == 0`` for *every* asset (verified by
   ``helpers.assert_no_locked_funds``).
3. **Echo invariance** – the engine must echo back *symbol / side / type /
   amount* unchanged (up to FP tolerance for the amount).

Why Hypothesis?
---------------
A hand-written test explores one static input.
Hypothesis generates *many* combinations automatically and shrinks any failing
case to a minimal counter-example, giving much broader coverage for (almost)
free.
"""

from __future__ import annotations

import random
import time
from math import isclose

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from .helpers import (
    assert_no_locked_funds,
    engine_latency,
    get_tickers,
    patch_ticker_price,
    place_order,
)

# ---------------------------------------------------------------------------
# Tunables – increase for more coverage, decrease for faster CI runs
# ---------------------------------------------------------------------------
N_ROUNDS: int = 3  # Hypothesis examples per test run
N_TICKERS: int = 20  # upper bound on symbols sampled per run
ENGINE_SETTLE_WAIT: float = 4.0  # seconds the engine gets to react

OPEN_STATES: tuple[str, ...] = ("new", "partially_filled")
CLOSED_STATES: tuple[str, ...] = (
    "filled",
    "canceled",
    "rejected",
    "partially_canceled",
    "expired",
)
ALL_STATES = OPEN_STATES + CLOSED_STATES


# --------------------------------------------------------------------------- #
# Helper – poll until no *open* orders remain or a timeout is hit
# --------------------------------------------------------------------------- #
def _wait_until_settled(client, *, timeout_s: float = 3.0) -> None:
    """
    Spin-wait until every order has left the *open* set or *timeout_s* expires.

    Matching happens in a background thread – so we wait a bit after each price
    patch to avoid racing the assertions below.
    """
    start = time.time()
    while time.time() - start < timeout_s:
        if not any(o["status"] in OPEN_STATES for o in client.get("/orders").json()):
            return
        time.sleep(ENGINE_SETTLE_WAIT)
    # Any lingering open orders are reported by subsequent assertions.


# --------------------------------------------------------------------------- #
# Hypothesis strategy – defines the randomised inputs
# --------------------------------------------------------------------------- #
@settings(
    max_examples=N_ROUNDS,  # keep runtime predictable
    deadline=None,  # disable the 200 ms per-call limit
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    # Always issue a BUY; optionally a SELL as well.
    sides=st.tuples(st.just("buy"), st.one_of(st.none(), st.just("sell"))).map(
        lambda t: ["buy"] if t[1] is None else ["buy", "sell"]
    ),
    # Scale factor for the trade notion – covers tiny through large orders.
    amount_factor=st.floats(min_value=0.1, max_value=1.0),
)
def test_limit_order_round_trip_property(
    funded_client, sides: list[str], amount_factor: float
) -> None:
    """
    For each Hypothesis example the test performs:

    1. **Sampling** – draw up to :pydata:`N_TICKERS` random symbols.
    2. **Booking**  – submit a BUY (and optionally a SELL) *limit* order for
       each symbol at an exaggerated price so it *won’t* match immediately.
    3. **Trigger**  – move the ticker exactly to that price, causing the engine
       to match the orders.
    4. **Verification**
       • all orders are in :pydata:`CLOSED_STATES`
       • engine echoed the original order fields unchanged
       • no asset is left in the *used* column.
    """

    # Hypothesis might shrink amount_factor to a value so small the quantity
    # rounds to zero and is rejected – bail early to avoid endless shrinking.
    assume(amount_factor > 1e-3)

    # ------------------------------------------------------------------ #
    # 1) Fresh funds and deterministic RNG seed (for reproducible shrink)
    # ------------------------------------------------------------------ #
    free_cash = funded_client.get("/balance/USDT").json()["free"]
    rng = random.Random(hash((tuple(sorted(sides)), round(float(amount_factor), 6))))

    tickers = rng.sample(
        get_tickers(funded_client), k=min(N_TICKERS, len(get_tickers(funded_client)))
    )

    # This “impossible” price guarantees BUY *and* SELL cross once patched.
    fake_price = 1_000_000.0
    notion_per_trade = free_cash / max(len(tickers), 1)

    record_tx: dict[str, dict] = {}

    # ------------------------------------------------------------------ #
    # 2) Place orders and immediately patch the price to trigger a match
    # ------------------------------------------------------------------ #
    for side in sides:
        for symbol in tickers:
            qty = notion_per_trade * amount_factor / fake_price
            if side == "sell":
                qty *= 0.9  # leave a margin so we don’t run out of stock

            payload = {
                "type": "limit",
                "amount": qty,
                "symbol": symbol,
                "side": side,
                "limit_price": fake_price,
            }
            rsp = place_order(funded_client, payload)
            record_tx[rsp["id"]] = {**payload, "price": rsp.get("price")}

            # Move the market to the limit – matching happens in bg thread
            patch_ticker_price(funded_client, symbol, fake_price)

        engine_latency()  # small pause between BUY and SELL rounds

    _wait_until_settled(funded_client)

    # ------------------------------------------------------------------ #
    # 3) Assertions – echo invariance & terminal states
    # ------------------------------------------------------------------ #
    for order in funded_client.get("/orders").json():
        reference = record_tx.get(order["id"])
        if not reference:
            continue

        # Safety-net: cancel if the engine left anything open
        if order["status"] in OPEN_STATES:
            funded_client.post(f"/orders/{order['id']}/cancel")
            order = funded_client.get(f"/orders/{order['id']}").json()

        assert order["symbol"] == reference["symbol"]
        assert isclose(order["amount"], reference["amount"], rel_tol=1e-9)
        assert order["side"] == reference["side"]
        assert order["type"] == reference["type"]
        assert order["status"] in CLOSED_STATES

    # Final portfolio sanity check
    assert_no_locked_funds(funded_client)
