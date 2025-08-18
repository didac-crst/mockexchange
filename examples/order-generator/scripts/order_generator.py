"""
Continuously places random dry-run orders against a MockExchange API.

All tunables are taken from environment variables (see .env.example).
"""

from __future__ import annotations

import os
import random
import time
from math import floor, log10

import httpx

# ---------- helpers from your own codebase ----------
from helpers import (
    get_overview_balances,
    get_ticker_price,
    get_tickers,
    place_order,
    reset_and_fund,
)

# ────────────────────────────────────────────────────
# Configuration via ENV (with sensible defaults)
# ────────────────────────────────────────────────────
BASE_URL = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY") or None  # optional
TEST_ENV = os.getenv("TEST_ENV", "true").lower() in ("true", "1", "yes")

QUOTE = os.getenv("QUOTE_ASSET", "USDT")
FUNDING_AMOUNT = float(os.getenv("FUNDING_AMOUNT", 100_000))

BASE_ASSETS_TO_BUY = os.getenv(
    "BASE_ASSETS_TO_BUY",
    "BTC,ETH,SOL,XRP,BNB,ADA,DOGE,DOT",
).split(",")

NUM_EXTRA_ASSETS = int(os.getenv("NUM_EXTRA_ASSETS", 8))
TRADING_TYPES = os.getenv("TRADING_TYPES", "market,limit").split(",")

MIN_ORDERS_PER_BATCH = int(os.getenv("MIN_ORDERS_PER_BATCH", 1))
MAX_ORDERS_PER_BATCH = int(os.getenv("MAX_ORDERS_PER_BATCH", 3))

MIN_SLEEP = float(os.getenv("MIN_SLEEP", 30))
MAX_SLEEP = float(os.getenv("MAX_SLEEP", 60))

NOMINAL_TICKET_QUOTE = float(os.getenv("NOMINAL_TICKET_QUOTE", 50.0))
FAST_SELL_TICKET_AMOUNT_RATIO = float(os.getenv("FAST_SELL_TICKET_AMOUNT_RATIO", 0.005))
MIN_ORDER_QUOTE = float(os.getenv("MIN_ORDER_QUOTE", 1.0))
MIN_BALANCE_CASH_QUOTE = float(os.getenv("MIN_BALANCE_CASH_QUOTE", 100.0))
MIN_BALANCE_ASSETS_QUOTE = float(os.getenv("MIN_BALANCE_ASSETS_QUOTE", 2.0))

# HTTP headers (add API key only if provided)
HEADERS = {"x-api-key": API_KEY} if TEST_ENV else None


# ────────────────────────────────────────────────────
# Reset function
# ────────────────────────────────────────────────────

# Use environment variable instead of file flag to avoid persistence issues
RESET_ENV_VAR = "RESET_PORTFOLIO"


def maybe_reset_api(client) -> list[str]:
    reset_requested = os.getenv(RESET_ENV_VAR, "false").lower() in ("true", "1", "yes")

    if reset_requested:
        print("🔄 Reset requested via environment variable. Resetting API...")
        try:
            # Seed the wallet once per container start
            tickers = _get_tickers_to_trade(client)
            reset_and_fund(client, QUOTE, FUNDING_AMOUNT)
            print("✅ Reenitialized wallet with funding amount:", FUNDING_AMOUNT)
        except Exception as e:
            print(f"❌ Reset failed: {e}")
    else:
        print("🚀 No reset requested. Continuing as normal.")
        tickers = _get_existing_tickers(client)
    print("Trading the following tickers:", ", ".join(tickers))
    return tickers


# ────────────────────────────────────────────────────
# Utility functions
# ────────────────────────────────────────────────────
_BUY = "buy"
_SELL = "sell"


def define_sides_probability(cash_ratio: float) -> list[str]:
    """Establish the sides based on the cash ratio.
    The higher the cash ratio, the more likely we are to buy.
    The lower the cash ratio, the more likely we are to sell.
    """
    buy_weight = max(1, floor(8 * cash_ratio) - 2)
    sell_weight = max(1, floor(40 * (1 - cash_ratio)) - 32)
    sides = [_BUY] * buy_weight + [_SELL] * sell_weight
    random.shuffle(sides)  # Shuffle to mix buy/sell orders
    return sides


def _get_tickers_to_trade(client: httpx.Client) -> list[str]:
    """Return the fixed majors plus *NUM_EXTRA_ASSETS* random tickers."""
    tickers_list = get_tickers(client)
    majors = [f"{a}/{QUOTE}" for a in BASE_ASSETS_TO_BUY]
    extra_pool = [t for t in tickers_list if t not in majors]
    extras = random.sample(extra_pool, min(NUM_EXTRA_ASSETS, len(extra_pool)))
    return majors + extras


def _get_existing_tickers(client: httpx.Client) -> list[str]:
    """Return the list of tickers already being traded in the backend."""
    assets_list = client.get("/balance").json().keys()
    tickers_list = [f"{asset}/{QUOTE}" for asset in assets_list if asset != QUOTE]
    return tickers_list


def _floor_to_first_sig(x: float) -> float:
    """Round **down** to the most-significant digit only."""
    if x == 0:
        return 0.0
    sign = -1.0 if x < 0 else 1.0
    ax = abs(x)
    d = floor(log10(ax))  # exponent of first sig-digit
    first_digit = floor(ax / 10**d)
    return sign * first_digit * 10**d


# ────────────────────────────────────────────────────
# Main loop
# ────────────────────────────────────────────────────
def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=20.0, headers=HEADERS) as client:
        # Seed the wallet once per container start
        tickers = maybe_reset_api(client=client)
        n_tickers = len(tickers)
        max_orders_per_batch = min(
            MAX_ORDERS_PER_BATCH, n_tickers
        )  # Ensure we don't exceed available tickers
        while True:
            last_balances = client.get("/balance").json()
            overview_balances = get_overview_balances(client)
            total_equity = overview_balances["total_equity"]
            cash_equity = overview_balances["cash_total_value"]
            ratio_cash_equity = cash_equity / total_equity if total_equity > 0 else 0.0
            sides = define_sides_probability(ratio_cash_equity)
            print(f"Cash ratio: {ratio_cash_equity:.2%} | Sides: {sides}")
            n_orders = random.randint(MIN_ORDERS_PER_BATCH, max_orders_per_batch)
            batch = random.sample(tickers, n_orders)
            last_prices = get_ticker_price(client, batch)

            for symbol in batch:
                asset = symbol.split("/")[0]
                side = random.choice(sides)

                # Sell only if we actually hold the asset
                if side == _SELL and asset not in last_balances:
                    side = _BUY

                # Randomly choose an order type to test both limit and market orders
                order_type = random.choice(TRADING_TYPES)
                px = last_prices[symbol]
                if order_type == "limit":
                    px = px * random.gauss(1.0, 0.0005)

                if side == _BUY:
                    cash_free = last_balances[QUOTE]["free"]
                    if cash_free < MIN_BALANCE_CASH_QUOTE:
                        # Skip if no free cash available
                        print(f"Skipping {symbol} buy order: no free cash available.")
                        continue
                    elif cash_free > NOMINAL_TICKET_QUOTE:
                        # If we have enough free cash, use a nominal ticket quote
                        ticket_amount_q = NOMINAL_TICKET_QUOTE
                    else:
                        # If we don't have enough free cash, use everything we have
                        # minus a small buffer to avoid rejecting orders due to insufficient balance
                        # or not being able to pay fees.
                        ticket_amount_q = cash_free - MIN_BALANCE_CASH_QUOTE
                else:
                    balance_free_asset = last_balances[asset]["free"]
                    balance_free_asset_q = balance_free_asset * px
                    if balance_free_asset_q < MIN_BALANCE_ASSETS_QUOTE:
                        # Skip if no free asset available
                        print(f"Skipping {symbol} sell order: no free asset available.")
                        continue
                    fast_ticket_amount_q = total_equity * FAST_SELL_TICKET_AMOUNT_RATIO
                    if balance_free_asset_q >= (2 * fast_ticket_amount_q):
                        # If we have "a lot of asset", use a fast ticket amount,
                        # to sell it quickly.
                        # This is to avoid small shares being sold at a loss.
                        # The threshold is set to 2x the fast ticket amount.
                        # If it was only 1x, we would be selling the whole asset,
                        # only if we have exactly the fast ticket amount.
                        ticket_amount_q = fast_ticket_amount_q
                    elif balance_free_asset_q > NOMINAL_TICKET_QUOTE:
                        # If we have "a little bit" of free asset, use a nominal ticket quote.
                        ticket_amount_q = NOMINAL_TICKET_QUOTE
                    else:
                        # If we have "a very little bit" of free asset.
                        # We keep some buffer to avoid rejecting orders due to insufficient balance.
                        ticket_amount_q = (
                            balance_free_asset_q - MIN_BALANCE_ASSETS_QUOTE
                        )
                # Calculate the amount to sell
                if ticket_amount_q < MIN_ORDER_QUOTE:
                    # Skip if the ticket amount is below the minimum order quote
                    print(
                        f"Skipping {symbol} {side} order: "
                        f"ticket amount {ticket_amount_q:.2f} is below minimum {MIN_ORDER_QUOTE:.2f}."
                    )
                    continue
                # Calculate the amount to buy/sell
                ticket_amount = ticket_amount_q / px

                order = place_order(
                    client,
                    {
                        "symbol": symbol,
                        "side": side,
                        "type": order_type,
                        "amount": ticket_amount,
                        "limit_price": px if order_type == "limit" else None,
                    },
                )

                limit_price = order["limit_price"]
                limit_price_str = (
                    f"{px:>16,.4f}" if limit_price is not None else " " * 16
                )
                timestamp = order["ts_create"] / 1000  # Convert from ms to seconds
                datetime_str = time.strftime(
                    "%d/%m %H:%M:%S", time.localtime(timestamp)
                )
                print(
                    f"{datetime_str} | "
                    f"Status: {order['status']:<10} | "
                    f"{order['symbol']:<15} | "
                    f"{order['side']:<4} - {order['type']:<6} >> {order['amount']:>16,.4f} "
                    f"@ {limit_price_str} [{ticket_amount_q:>10,.2f} {QUOTE}]"
                )

            time.sleep(random.uniform(MIN_SLEEP, MAX_SLEEP))


if __name__ == "__main__":
    main()
