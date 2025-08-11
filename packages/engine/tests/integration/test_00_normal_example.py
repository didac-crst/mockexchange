"""
tests/test_00_normal_example.py
===============================

Smoke-test that *primes* the exchange with a **realistic starting portfolio**.

What does it do?
----------------
1. **Reset** the backend and credit a clean wallet with a fixed USDT stash.
2. **Round-robin BUY** several major coins (BTC, ETH, …) at market   \
   size chosen so that every purchase is a “nice” round number \
   (first significant digit only) – e.g. `1234.567 → 1000`, `0.000254 → 0.0002`.
3. Leave the exchange in that *post-trade* state so subsequent examples can
   assume a non-trivial portfolio without repeating this setup.

It deliberately **does not** assert anything about P/L or price movement –
only the happy-path of order placement and the basic echo invariants
(symbol/side/amount/status).
"""

from __future__ import annotations

import math
import random
from typing import Final

from .helpers import (
    get_ticker_price,
    get_tickers,
    place_order,
    reset_and_deposit,
)

# --------------------------------------------------------------------------- #
# Scenario constants – tweak here, not in the test logic
# --------------------------------------------------------------------------- #
QUOTE: Final[str] = "USDT"
FUNDING_AMOUNT: Final[float] = 50_000.0  # initial USDT bankroll
ASSETS_TO_BUY: Final[list[str]] = [  # majors we accumulate
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "BNB",
    "ADA",
    "DOGE",
    "DOT",
]
NUM_EXTRA_ASSETS = 12  # additional assets to buy, if available
TRADING_TYPES = ["market", "limit"]  # order types we can place


# --------------------------------------------------------------------------- #
# Utility – “floor to 1st significant digit” (no fractional fluff)
# --------------------------------------------------------------------------- #
def floor_to_first_sig(x: float) -> float:
    """
    Round **down** to the most-significant digit, zeroing everything else.

    Examples
    --------
    >>> floor_to_first_sig(1234.5678)   # → 1000.0
    1000.0
    >>> floor_to_first_sig(0.0002543)   # → 0.0002
    0.0002
    >>> floor_to_first_sig(-87.9)       # → -80.0
    -80.0
    """
    if x == 0:
        return 0.0

    sign = -1.0 if x < 0 else 1.0
    ax = abs(x)

    # 10-exponent of the first significant digit: 1234 → 3, 0.000254 → -4
    d = math.floor(math.log10(ax))

    # Bring first digit into the units place, floor it, scale back.
    first_digit = math.floor(ax / 10**d)
    return sign * first_digit * 10**d


# --------------------------------------------------------------------------- #
# Test body
# --------------------------------------------------------------------------- #
def test_normal_example(client):
    """
    End-to-end “happy-path” that seeds a **typical diversified portfolio**.

    Steps
    -----
    1. Use the *helpers.reset_and_fund* fixture to wipe all state and credit
       ``FUNDING_AMOUNT`` USDT.
    2. Loop over :pydata:`ASSETS_TO_BUY`, fetch each ticker’s last price and
       place a *market BUY* for a nicely-rounded quantity.
    3. Assert that the engine echoes *symbol, side, amount* unchanged and
       that every newly-created order starts in the ``new`` state.

    The resulting portfolio is intentionally **left intact** – later tests
    can build on it instead of re-funding the wallet from scratch.
    """

    # ── 1) Clean slate + funding ─────────────────────────────────────── #
    reset_and_deposit(client, QUOTE, FUNDING_AMOUNT)

    expected_balance = {
        "asset": QUOTE,
        "free": FUNDING_AMOUNT,
        "used": 0.0,
        "total": FUNDING_AMOUNT,
    }
    assert client.get(f"/balance/{QUOTE}").json() == expected_balance

    # ── 2) Buy a basket of majors ─────────────────────────────────────── #
    # Get the list of defined tickers + the extra ones we want to buy.
    tickers_list = get_tickers(client)
    tickers_to_trade = [f"{a}/{QUOTE}" for a in ASSETS_TO_BUY]
    extra_tickers = [t for t in tickers_list if t not in tickers_to_trade]
    extra_tickers = random.sample(extra_tickers, NUM_EXTRA_ASSETS)
    tickers_to_trade.extend(extra_tickers)
    # Verify that all tickers are available
    tickers_to_trade = [t for t in tickers_to_trade if t in tickers_list]
    # Even split of our bankroll between the assets (×0.5 so we keep half USDT)
    notion_per_asset = FUNDING_AMOUNT / (2 * len(tickers_to_trade))

    for symbol in tickers_to_trade:
        # price = client.get(f"/tickers/{symbol}").json()[symbol]["last"]
        price = get_ticker_price(client, symbol)

        # Randomise a bit so identical seeds don’t always trade the same size
        notion = notion_per_asset * random.uniform(0.5, 4.0)
        quantity = floor_to_first_sig(notion / price)

        assert quantity > 0, "Rounded quantity must stay positive"

        # Choose a random trading type (market or limit) and set limit price
        # to slightly below market for limit orders (to avoid immediate fill).
        t_type = random.choice(TRADING_TYPES)
        if t_type == "limit":
            limit_price = (
                get_ticker_price(client, symbol) * 0.9995
            )  # slightly below market
        else:
            limit_price = None

        order = place_order(
            client,
            {
                "type": t_type,
                "amount": quantity,
                "symbol": symbol,
                "side": "buy",
                "limit_price": limit_price,
            },
        )

        # ── 3) Echo-invariance sanity checks ────────────────────────── #
        assert order["status"] in ("new", "rejected")  # market orders start as *new*
        assert order["symbol"] == symbol
        assert math.isclose(order["amount"], quantity, rel_tol=1e-9)
        assert order["side"] == "buy"
