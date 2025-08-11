"""
tests/test_06B_fund_and_rejected_insufficient_trade_when_sell.py
==============================================================

Twin-scenario of *test 06A* – this time for the **SELL** side.

Rationale
~~~~~~~~~
* When a **SELL** order is accepted the engine books

    • *base*  : the BTC amount in `used`
    • *quote* : the fee (= amount × price × commission) in `used`

* If – before the order is matched – somebody tinkers with the balances and
  lowers either reservation, the trade **must not** go through.
  The engine has to **reject** (or partially reject) the order and roll back
  whatever it had reserved.

Test outline
------------
1. **Reset & fund** both BTC (to sell) *and* USDT (to pay the fee).
2. **Create** a SELL-limit order – the engine reserves BTC + fee.
3. **Tamper** with the BTC balance so that *used &lt; reserved*.
4. **Tick** the market price to the limit price (simulating a match).
5. **Assert** the order is *rejected / partially_rejected* and every
   reservation is released.

A failure means the “pre–execution funds check” is broken for sell orders.
"""

# --------------------------------------------------------------------------- #
# Imports & helpers
# --------------------------------------------------------------------------- #
from xmlrpc import client
from .helpers import (
    reset_and_deposit,
    deposit,
    get_ticker_price,
)
from math import isclose

# --------------------------------------------------------------------------- #
# Constants for the scenario
# --------------------------------------------------------------------------- #
QUOTE = "USDT"
ASSET = "BTC"
SYMBOL = f"{ASSET}/{QUOTE}"

AMOUNT_BTC = 5.0  # BTC we want to off-load
COMMISSION = 0.001  # matches default in env (0.1 %)


# --------------------------------------------------------------------------- #
# Test case
# --------------------------------------------------------------------------- #
def test_sell_order_rejects_when_base_is_missing(client):
    """
    Full *happy‑path* description of what happens in this test:

    1. **Price discovery**
       The test first fetches the current ticker so it can calculate a *worst‑
       case* limit‑price that is guaranteed to be above market.
       That limit price is then used to work out the maximum possible fee.

    2. **Funding**
       • BTC is credited so it can be sold.
       • Plenty of USDT is credited so the engine can reserve the trading fee.

    3. **Order creation**
       A *SELL‑limit* order is placed.
       The engine should now have moved the BTC amount **and** the USDT fee to
       their respective `used` buckets.

    4. **Tampering**
       We secretly reduce the “used” BTC so that there are not enough coins
       left for the order to execute.

    5. **Trigger**
       The ticker is moved up to the limit price which would normally cause the
       order to match.  The engine is expected to spot the shortfall and reject
       (or partially reject) the order.

    6. **Assertions**
       The order status must be *rejected / partially_rejected* **and** every
       reservation has to be rolled back – i.e. both `used` columns are `0`.
    """

    # --- Step 0: Ask the exchange for the current market price so we can define a "high" limit price.
    market_price = get_ticker_price(client, SYMBOL)
    assert market_price > 0, "Market price must be greater than zero"
    # Choose a limit price = 2×market.  With such a generous price the order
    # would definitely match *if* funds were available.
    limit_price = round(market_price * 2, 0)  # round to 2 decimal places

    # Calculate the maximum fee the engine will try to reserve (worst‑case).
    fee_usdt = AMOUNT_BTC * limit_price * COMMISSION

    fund_usdt = fee_usdt * 10  # plenty of quote for fee

    # --- Step 1: Reset the exchange state and fund the assets ---
    # --- Reset state and credit the selling BTC ---
    reset_and_deposit(client, ASSET, AMOUNT_BTC)  # wipes → add BTC
    # --- Credit USDT so the engine can also reserve the taker fee ---
    deposit(client, QUOTE, fund_usdt)

    # Expectation after the funding phase.
    # Portfolio must now contain both assets
    bals = client.get("/balance").json()
    assert bals[ASSET]["free"] == AMOUNT_BTC
    assert bals[ASSET]["used"] == 0.0
    assert bals[QUOTE]["free"] == fund_usdt
    assert bals[QUOTE]["used"] == 0.0

    # --- Step 2: submit the SELL‑limit order ---
    order_req = {
        "symbol": SYMBOL,
        "side": "sell",
        "type": "limit",
        "amount": AMOUNT_BTC,
        "limit_price": limit_price,
    }
    o = client.post("/orders", json=order_req).json()

    # Engine accepted the order and should have booked BTC + fee.
    assert o["status"] == "new"
    fee_rate = o["fee_rate"]
    reserved_fee = AMOUNT_BTC * limit_price * fee_rate
    assert isclose(o["initial_booked_fee"], reserved_fee, rel_tol=1e-6)

    # Locked amounts should show up
    bals_after = client.get("/balance").json()
    print(f"Bals after order: {bals_after}")
    assert bals_after[ASSET]["used"] == AMOUNT_BTC
    assert bals_after[QUOTE]["used"] == reserved_fee

    # --- Step 3: simulate an external process stealing a slice of the reserved BTC ---
    # Tamper: make *used BTC* smaller than what the order needs
    tampered_used_btc = AMOUNT_BTC * 0.99  # 99% of the amount we wanted to sell
    client.patch(
        f"/admin/balance/{ASSET}",
        json={"free": 0.0, "used": tampered_used_btc},
    )

    # --- Step 4: move the market so the order *would* execute ---
    client.patch(f"/admin/tickers/{SYMBOL}/price", json={"price": limit_price})

    # --- Step 5: verify the engine reacted correctly ---
    o_final = client.get(f"/orders/{o['id']}").json()
    assert o_final["status"] in {"rejected", "partially_rejected"}

    # No asset or fee should remain locked – everything must be released.
    bals_final = client.get("/balance").json()

    assert bals_final[ASSET]["used"] == 0.0
    assert bals_final[QUOTE]["used"] == 0.0  # fee reservation released
    # The BTC that *had* been in used flows back to free
    assert isclose(
        bals_final[ASSET]["free"],
        tampered_used_btc,
        rel_tol=1e-9,
    )
