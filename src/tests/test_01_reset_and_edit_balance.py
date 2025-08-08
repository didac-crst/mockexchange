"""
tests/test_01_reset_and_edit_balance.py
---------------------------------------

Smoke-tests for basic admin endpoints:

1. **test_reset**
   • Ensures the exchange starts from a clean state after calling `/admin/data`
     – no stray balances, no open or closed orders.

2. **test_edit_balance**
   • Verifies that after a clean reset we can overwrite an asset balance via the
     `/admin/balance/{asset}` endpoint, and that the new numbers are stored
     exactly as requested.

The helper utilities (`reset`, `reset_and_fund`, `edit_balance`) live in
`tests/helpers.py` and wrap REST calls so the test code stays concise.
"""

# ---------------------------------------------------------------------- #
# Imports & helpers
# ---------------------------------------------------------------------- #
from .helpers import reset, edit_balance


# ---------------------------------------------------------------------- #
# Tests
# ---------------------------------------------------------------------- #
def test_reset(client):
    """
    Ensure the backend starts with **no persistent state**.

    Steps
    -----
    1. Call ``/admin/data`` through the ``reset`` helper – this wipes both
       balances and orders.
    2. Assert that:
       * ``/orders`` returns an **empty list**.
       * ``/balance`` returns an **empty dict**.

    Any leftovers here would suggest that the prune / reset logic isn’t working
    as expected.
    """
    print(client.base_url)
    reset(client)

    # After a full reset the system must report *nothing* stored anywhere.
    assert client.get("/orders").json() == []
    assert client.get("/balance").json() == {}


def test_edit_balance(client):
    """
    Overwrite (or create) a balance row and confirm the exact numbers persist.

    Scenario
    --------
    * Asset under test  : **USDT**
    * Desired snapshot  : ``free = 8 000`` | ``used = 2 000``

    We PATCH the balance endpoint and then read it back to make sure the values
    match precisely.
    """
    asset = "USDT"
    expected_free = 8_000.0
    expected_used = 2_000.0

    # Update balance via helper (wrapper around PATCH /admin/balance/USDT)
    edit_balance(client, asset, expected_free, expected_used)

    # Fetch the single-asset view and validate every field
    assert client.get(f"/balance/{asset}").json() == {
        "asset": asset,
        "free": expected_free,
        "used": expected_used,
        "total": expected_free + expected_used,
    }
