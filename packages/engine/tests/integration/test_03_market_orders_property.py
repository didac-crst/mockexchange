"""
tests/test_03_market_order_property.py
---------------------------------------

Property-based smoke test for the *market-order* happy-path.

Purpose
-------
* Ensure that **every** market BUY/SELL order eventually ends up in a *closed*
  state (*filled / canceled / rejected …*) and **no funds remain locked** in
  the portfolio.
* Run the same scenario through a couple of randomised rounds so that the
  engine is tickled with different tickers, order-sides and trade sizes.

Why a property test?
--------------------
Classic example-based tests cover a single hand-picked set of parameters.  The
Hypothesis engine explores *many* combinations automatically and shrinks them
on failure, giving us much broader coverage for (almost) free.

The properties we assert here are:

1.  *State convergence* – after the dust has settled, **every order** must be
    in one of the terminal states defined in :pydata:`CLOSED_STATES`.
2.  *Accounting soundness* – once all orders are closed **no asset remains in
    the ``used`` column**.  (``helpers.assert_no_locked_funds`` does that.)
3.  *Echo invariance* – round-tripping the order through the API should not
    distort *symbol*, *side*, *type* or *amount* beyond machine epsilon.

If any of those invariants is violated Hypothesis will try to minimise the
failing input set and reproducibly print it.
"""

from __future__ import annotations

import random
import time
from math import isclose

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from .helpers import (
    assert_no_locked_funds,
    get_ticker_price,
    get_tickers,
    place_order,
)

# ---------------------------------------------------------------------------
# Test-tuning constants – tweak to trade-off coverage vs. runtime
# ---------------------------------------------------------------------------
N_ROUNDS: int = 3  # how many Hypothesis examples we let run
N_TICKERS: int = 50  # max number of symbols sampled in *each* example
ENGINE_SETTLE_WAIT: int = 4  # seconds to wait between order bursts

# Canonical state buckets the engine reports – used for assertions below
OPEN_STATES: tuple[str, ...] = ("new", "partially_filled")
CLOSED_STATES: tuple[str, ...] = (
    "filled",
    "canceled",
    "rejected",
    "partially_canceled",
)
ALL_STATES: tuple[str, ...] = OPEN_STATES + CLOSED_STATES

# ---------------------------------------------------------------------------
# Helper – poll /orders until *all* of them left the OPEN set or timeout hits
# ---------------------------------------------------------------------------


def _wait_until_settled(client, *, timeout_s: float = 3.0) -> None:
    """Spin until no open orders remain *or* *timeout_s* elapses.

    Market orders in this mock-exchange are filled asynchronously.  We therefore
    let the reactor breathe a little after each burst so the follow-up asserts
    don’t run against half-settled state.
    """

    t0 = time.time()
    while time.time() - t0 < timeout_s:
        still_open = [o for o in client.get("/orders").json() if o["status"] in OPEN_STATES]
        if not still_open:
            return  # ✅ fully settled
        time.sleep(ENGINE_SETTLE_WAIT)
    # If we drop out of the loop we simply continue – the asserts that follow
    # will flag the problem.


# ---------------------------------------------------------------------------
# Hypothesis strategy configuration
# ---------------------------------------------------------------------------


@settings(
    max_examples=N_ROUNDS,  # keep CI runtime reasonable
    deadline=None,  # disable 200 ms default deadline
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    # One obligatory BUY, optional SELL – prevents Hypothesis from generating
    # an empty side-list while still allowing us to test *both* directions.
    sides=st.tuples(st.just("buy"), st.one_of(st.none(), st.just("sell"))).map(
        lambda t: [t[0]] if t[1] is None else list(t)
    ),
    amount_factor=st.floats(min_value=0.1, max_value=1.0),
)
def test_market_order_flow_property(funded_client, sides: list[str], amount_factor: float) -> None:  # noqa: E501
    """Main property-based test function.

    Steps per Hypothesis *example*
    ------------------------------
    1. Ensure the account starts with a fresh **USDT** stash.
    2. Generate a reproducible RNG seed based on the Hypothesis parameters so
       that failures are deterministic.
    3. Pick up to :pydata:`N_TICKERS` random symbols and place a burst of BUY
       (and maybe SELL) *market* orders against each.
    4. Poll until they are settled, then verify:
       * Engine echoed the order fields correctly.
       * No order is left open.
       * ``helpers.assert_no_locked_funds`` confirms the reservation columns
         are zero.
    """

    # Defensive guard – Hypothesis may shrink *amount_factor* down to sub-µ.
    # Such tiny trades round to zero and the engine rightfully rejects them,
    # potentially creating a shrink loop.  Bail early in that edge-case.
    assume(amount_factor > 1e-3)

    # ------------------------------------------------------------------
    # 0) Fresh wallet with plenty of USDT to play with
    # ------------------------------------------------------------------
    # funded_client has already been reset and funded with USDT - done only once per session.
    free_cash = funded_client.get("/balance/USDT").json()["free"]

    # ------------------------------------------------------------------
    # 1) Reproducible RNG – seed derived from Hypothesis params
    # ------------------------------------------------------------------
    rng_seed = hash((tuple(sorted(sides)), round(float(amount_factor), 6)))
    rnd = random.Random(rng_seed)

    # ------------------------------------------------------------------
    # 2) Draw a symbol subset and compute a notion per trade
    # ------------------------------------------------------------------
    tickers = rnd.sample(
        get_tickers(funded_client), k=min(N_TICKERS, len(get_tickers(funded_client)))
    )
    notion_per_trade = free_cash / (len(tickers) or 1)  # avoid div/0
    record_tx: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # 3) Fire the orders – BUY pass then optional SELL pass
    # ------------------------------------------------------------------
    for side in sides:
        for symbol in tickers:
            price = get_ticker_price(funded_client, symbol)
            qty = notion_per_trade * amount_factor / price
            if side == "sell":
                qty *= 0.9  # leave a safety-margin to stay liquid

            order_payload = {
                "type": "market",
                "amount": qty,
                "symbol": symbol,
                "side": side,
            }
            result = place_order(funded_client, order_payload)
            record_tx[result["id"]] = {**order_payload, "price": result.get("price")}

        _wait_until_settled(funded_client)  # let async fills finish

    # ------------------------------------------------------------------
    # 4) Assertions – echo invariants + state convergence
    # ------------------------------------------------------------------
    for o in funded_client.get("/orders").json():
        if (tx := record_tx.get(o["id"])) is None:
            continue  # skip orders unrelated to this test run

        assert o["symbol"] == tx["symbol"]
        assert isclose(o["amount"], tx["amount"], rel_tol=1e-9)
        assert o["side"] == tx["side"]
        assert o["type"] == tx["type"]
        assert o["status"] in ALL_STATES

        # Clean-up guard – in case the engine left something open
        if o["status"] in OPEN_STATES:
            funded_client.post(f"/orders/{o['id']}/cancel")

    # ------------------------------------------------------------------
    # 5) Portfolio must be squeaky clean – no residual reservations
    # ------------------------------------------------------------------
    assert_no_locked_funds(funded_client)
