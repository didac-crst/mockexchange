"""
Smoke-test for *deposit* / *withdrawal* helpers.

Goals
~~~~~
1. **Reset the world** – verify that ``DELETE /admin/data`` really wipes *everything* (orders *and* balances) so each run starts from a known blank state.
2. **Credit & debit assets** – randomised deposit/withdraw cycles on up to ``NUMBER_OF_ASSETS`` tradable assets plus the main cash asset (``USDT``).
3. **Balance integrity** – after *every* funding operation we assert:

   * ``free``  equals the net position we just built for that asset,
   * ``used``  stays ``0`` (no reservations until later order tests),
   * ``total`` is simply ``free + used``.

Rationale
~~~~~~~~~
Later test-suites rely on a pristine portfolio. If this file fails, *all* subsequent
scenarios will produce garbage results – so we surface any funding bug as early as
possible.
"""

# --------------------------------------------------------------------------- #
# Imports & helpers
# --------------------------------------------------------------------------- #
import pytest
import random
from .helpers import reset, deposit, withdrawal, get_tickers, get_ticker_price

MAIN_ASSET = "USDT"  # base cash asset (1:1 pricing)
NUMBER_OF_ASSETS = 30  # upper limit of distinct assets touched per run
MIN_INVESTMENT = 1_000.0  # min USDT injected per funding op
MAX_INVESTMENT = 5_000.0  # max USDT injected per funding op


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


def test_funding(client):
    """End-to-end deposit/withdraw loop.

    **Procedure**::

        1. ``reset``  → hard-wipe orders + balances via the admin API.
        2. Build an ``assets_to_trade`` list consisting of *USDT* plus a random
           sample of other tradeable assets.
        3. For each asset, run a *deposit* followed by a *withdrawal* (order is
           irrelevant – the point is to exercise both code paths).
        4. After each HTTP call, fetch ``/balance/{asset}`` and assert the math.
    """

    # 1️⃣ Clean slate – makes later assertions deterministic
    reset(client=client)

    # 2️⃣ Choose assets and prepare per-asset investment ledger
    tradeable_pairs = get_tickers(client)
    tradeable_assets = [p.split("/")[0] for p in tradeable_pairs]
    number_of_assets = min(len(tradeable_assets), NUMBER_OF_ASSETS)
    assets_to_trade = [MAIN_ASSET] + random.sample(tradeable_assets, number_of_assets)

    # 3️⃣ Fund & drain each asset once – track net position locally
    for asset in assets_to_trade:
        net_investment = 0.0  # ➟ *quote* currency (USDT)

        for funding_op in (deposit, withdrawal):
            # Decide random quote amount and keep running net
            if funding_op is deposit:
                quote_amount = random.uniform(MIN_INVESTMENT, MAX_INVESTMENT)
                net_investment += quote_amount
            else:  # withdrawal
                quote_amount = random.uniform(0.0, net_investment)
                net_investment -= quote_amount

            # Convert quote to base units (unless asset == MAIN_ASSET)
            price = (
                1.0
                if asset == MAIN_ASSET
                else get_ticker_price(client, f"{asset}/{MAIN_ASSET}")
            )
            base_units = quote_amount / price
            expected_free_base = net_investment / price

            # Perform funding operation
            funding_op(client, asset, base_units)

            # 4️⃣ Validate on-chain state against expected math
            bal = client.get(f"/balance/{asset}").json()

            assert bal["free"] == pytest.approx(expected_free_base)
            assert bal["used"] == pytest.approx(0.0)
            assert bal["total"] == pytest.approx(expected_free_base)
