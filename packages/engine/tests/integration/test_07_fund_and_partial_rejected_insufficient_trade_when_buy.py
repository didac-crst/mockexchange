"""
tests/test_06B_fund_and_partial_rejected_insufficient_trade_when_buy.py
======================================

End-to-end check for **reservation roll-back** when the account balance is
manually corrupted *after* an order has been accepted but *before* it can be
filled.

Use case:
* partial_reject     – some BTC filled → status == partially_rejected

Why this test exists
--------------------
* Every **BUY** order first *locks* the necessary quote currency
  ( notional + fee ) in the portfolio’s `used` column.
* If, in the meantime, something external reduces that balance
  (e.g. a bug, a manual intervention, or concurrent withdrawal),
  the engine **must** detect the shortfall *right before execution* and
  reject the order, releasing whatever was still reserved.

The test follows these steps:

1. **Reset & fund** the account with plenty of USDT.
2. **Create** a BUY-limit order on *BTC/USDT* – this books funds.
3. **Tamper** with the USDT balance so that *used &lt; originally reserved*.
4. **Move** the market price to the limit price – the engine tries to settle.
5. **Assert** that the order ends up *rejected / partially_rejected* and all
   previously-locked USDT is back in `free` while `used` is zero.
"""

# --------------------------------------------------------------------- #
# Imports & helpers
# --------------------------------------------------------------------- #
import time

from .helpers import (
    reset_and_deposit,
)

QUOTE = "USDT"
ASSET = "BTC"
SYMBOL = f"{ASSET}/{QUOTE}"
LIMIT_PX = 2.0  # 1 BTC ≙ 2 USDT
NOTIONAL_TO_BUY = 10_000.0  # 10 k USDT
FUNDING = NOTIONAL_TO_BUY * 2  # leave plenty of head-room


# --------------------------------------------------------------------- #
# Test matrix: two variants with tiny differences in tampering strategy
# --------------------------------------------------------------------- #
def test_insufficient_funds_rejection(client):
    """
    1. fund the wallet
    2. place BUY-limit
    3. (optionally) let engine fill a *tiny* slice (partial_reject only)
    4. tamper with balance so that reservation < needed
    5. move price → engine settles → order must end as  REJECT / PARTIAL_REJECT
    """
    # --------------------------------------------------------------------- #
    # 1️⃣  Preparation – fund the quote currency
    # --------------------------------------------------------------------- #
    reset_and_deposit(client, QUOTE, FUNDING)

    # sanity-check funding
    assert client.get(f"/balance/{QUOTE}").json()["free"] == FUNDING

    # --------------------------------------------------------------------- #
    # 2️⃣  Place the BUY-limit order – this *books* funds
    # --------------------------------------------------------------------- #
    qty_btc = NOTIONAL_TO_BUY / LIMIT_PX
    order_req = {
        "symbol": SYMBOL,
        "side": "buy",
        "type": "limit",
        "amount": qty_btc,
        "limit_price": LIMIT_PX,
    }
    order = client.post("/orders", json=order_req).json()
    assert order["status"] == "new"
    fee = order["initial_booked_fee"]
    booked = NOTIONAL_TO_BUY + fee  # USDT locked

    # --------------------------------------------------------------------- #
    # 3️⃣A  Tamper with the balance – simulate disappearing funds
    # --------------------------------------------------------------------- #
    # Drop 10 % of the fee ⇒ insufficient on next fill attempt
    new_used = booked - fee * 0.1
    tamper_resp = client.patch(
        f"/admin/balance/{QUOTE}",
        json={"free": 0.0, "used": new_used},
    )
    assert tamper_resp.status_code == 200
    tampered = tamper_resp.json()  # keep for final assertions

    # --------------------------------------------------------------------- #
    # 3️⃣B  Create a *tiny* partial fill first
    # --------------------------------------------------------------------- #
    # Pump in a fake volume so only ~5 % of order can fill.
    # That leaves the rest still “open”.
    client.patch(
        f"/admin/tickers/{SYMBOL}/price",
        json={
            "price": LIMIT_PX,  # crosses immediately
            "ask_volume": qty_btc * 0.05,
            "bid_volume": qty_btc * 0.05,
        },
    )
    # Give the engine a moment (tick loop) to settle
    time.sleep(0.1)

    # --------------------------------------------------------------------- #
    # 4️⃣  Move the market to the limit price → engine tries to fill
    # --------------------------------------------------------------------- #
    client.patch(
        f"/admin/tickers/{SYMBOL}/price",
        json={"price": LIMIT_PX},  # same price, triggers settle
    )
    time.sleep(0.1)  # allow async settle

    # --------------------------------------------------------------------- #
    # 5️⃣  Order must be rejected
    # --------------------------------------------------------------------- #
    order_after = client.get(f"/orders/{order['id']}").json()
    assert order_after["status"] in {"rejected", "partially_rejected"}

    balances = client.get("/balance").json()
    # Only USDT should exist in the portfolio
    assert sorted(balances.keys()) == sorted([QUOTE, ASSET])

    # Locked USDT is back in `free`; nothing remains in `used`
    assert balances[QUOTE]["free"] < tampered["used"]
    assert balances[QUOTE]["used"] == 0.0
    assert balances[QUOTE]["total"] < tampered["free"] + tampered["used"]
