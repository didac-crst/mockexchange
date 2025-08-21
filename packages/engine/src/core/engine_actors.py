"""
Exchange engine implemented with Pykka actors.
Non-blocking, single-threaded semantics inside each actor.
"""

# engine_actors.py
from __future__ import annotations

import base64
import hashlib
import itertools
import logging
import math
import os
import random
import threading
import time
from collections import defaultdict
from datetime import timedelta
from typing import Any

import pandas as pd
import pykka
import redis

from ._types import AssetBalance, Order, TradingPair
from .constants import (
    CLOSED_STATUS,  # {OrderState.FILLED, …}
    OPEN_STATUS,  # {OrderState.NEW, …}
    OrderSide,
    OrderState,
    OrderType,
)
from .logging_config import logger
from .market import Market
from .orderbook import OrderBook
from .portfolio import Portfolio

logging.getLogger("pykka").setLevel(logging.WARNING)


# ────────────────────────────────────────────
MIN_TIME = float(os.getenv("MIN_TIME_ANSWER_ORDER_MARKET", 0))
MAX_TIME = float(os.getenv("MAX_TIME_ANSWER_ORDER_MARKET", 1))
SIGMA_FILL = float(os.getenv("SIGMA_FILL_MARKET_ORDER", 0.1))
# ────────────────────────────────────────────

# ---------- Constants ------------------------------------------------ #

TRADES_INDEX_COUNT = "trades:index:count"
TRADES_INDEX_AMOUNT = "trades:index:amount"
TRADES_INDEX_NOTIONAL = "trades:index:notional"
TRADES_INDEX_FEE = "trades:index:fee"

DEPOSITS_INDEX = "deposits:index"
WITHDRAWALS_INDEX = "withdrawals:index"


# ---------- Domain actors ------------------------------------------------ #
class _BaseActor(pykka.ThreadingActor):
    """Keeps a thread-local Redis client."""

    def __init__(self, redis_url: str):
        super().__init__()
        self.redis = redis.from_url(redis_url, decode_responses=True)


class MarketActor(_BaseActor):
    def __init__(self, redis_url: str):
        super().__init__(redis_url)
        self.market = Market(self.redis)

    def last_price(self, symbol: str) -> float:
        return self.market.last_price(symbol)

    def fetch_ticker(self, symbol: str) -> TradingPair | None:
        return self.market.fetch_ticker(symbol)

    def set_last_price(self, *args: Any, **kwargs: Any) -> None:
        return self.market.set_last_price(*args, **kwargs)

    @property
    def tickers(self) -> list[str]:
        return self.market.tickers


class PortfolioActor(_BaseActor):
    def __init__(self, redis_url: str):
        super().__init__(redis_url)
        self.portfolio = Portfolio(self.redis)

    def get(self, asset: str) -> AssetBalance:
        return self.portfolio.get(asset)

    def set(self, bal: AssetBalance) -> None:
        self.portfolio.set(bal)

    def all(self) -> dict[str, AssetBalance]:
        return self.portfolio.all()

    def clear(self) -> None:
        self.portfolio.clear()


class OrderBookActor(_BaseActor):
    def __init__(self, redis_url: str):
        super().__init__(redis_url)
        self.ob = OrderBook(self.redis)

    # CRUD
    def add(self, o: Order) -> None:
        self.ob.add(o)

    def update(self, o: Order) -> None:
        self.ob.update(o)

    def get(self, oid: str, include_history: bool = False) -> Order:
        return self.ob.get(oid, include_history=include_history)

    def list(self, **kw: Any) -> list[Order]:
        return self.ob.list(**kw)

    def remove(self, oid: str) -> None:
        self.ob.remove(oid)

    def clear(self) -> None:
        self.ob.clear()


# ---------- Engine actor -------------------------------------------------- #
class ExchangeEngineActor(_BaseActor):
    """
    One instance per process.
    Every public method runs in this actor’s thread ⇒ no data races.
    """

    def __init__(self, *, redis_url: str, commission: float, cash_asset: str = "USDT"):
        _BaseActor.__init__(self, redis_url)  # <- brings self.redis
        self.cash_asset = cash_asset
        self.commission = commission
        self._oid = itertools.count(1)

        # Child actors (proxies)
        self.market = MarketActor.start(redis_url).proxy()
        self.portfolio = PortfolioActor.start(redis_url).proxy()
        self.order_book = OrderBookActor.start(redis_url).proxy()

        # Keep timer handles so we can cancel on shutdown
        self._timers: list[threading.Timer] = []

    # ---------- helpers ------------------------------------------------ #
    def _uid(self) -> str:
        ts = int(time.time())  # seconds
        raw = f"{int(ts*1000)}_{next(self._oid)}".encode()
        hash = base64.urlsafe_b64encode(hashlib.md5(raw).digest()).decode()  # Remove padding
        hash = hash.replace("_", "").replace("-", "")[:6]
        oid = f"{ts:010d}_{hash}"
        return oid

    def _reserve(self, asset: str, qty: float) -> None:
        bal = self.portfolio.get(asset).get()
        if bal.free < qty:
            raise ValueError(f"insufficient {asset} to reserve")
        bal.free -= qty
        bal.used += qty
        self.portfolio.set(bal)

    def _release(self, asset: str, qty: float) -> float:
        bal = self.portfolio.get(asset).get()
        if bal.used < qty:
            # In case of cancellation, we need to release everything even if used < qty due to rounding
            # and ensure to have used == 0.0
            qty = bal.used
        bal.used -= qty
        bal.free += qty
        if bal.free and bal.used / bal.free < 1e-10:
            bal.used = 0.0
        self.portfolio.set(bal)
        return qty

    @staticmethod
    def _slippage_simulate(amount: float, sigma: float = 0.5) -> float:
        """
        Simulate a random slippage based on a mean and a delta.
        Half of the time it will be exactly the amount requested,
        the other half it will be less, but never more than requested.
        """
        mean = 1.0
        random_number = random.gauss(mean, sigma)
        if random_number < 0:
            random_number = 0.0
        if random_number > mean:
            random_number = mean
        return amount * random_number

    # ---- reservation guard ------------------------------------------- #
    def _rejected_for_insufficient_reserve(self, o: Order, reason: str) -> None:
        """
        Reject *o* because the amounts still reserved
        in the portfolio are not enough to execute the next fill.

        The function
        • releases whatever is still reserved,
        • sets the status to rejected / partially_rejected,
        • appends a history entry,
        • squashes the residual booking,
        • updates the order book and emits a log entry.
        """
        base, quote = o.symbol.split("/")

        # release leftovers
        if o.side is OrderSide.BUY:
            self._release(quote, o.residual_quote)
        else:
            self._release(base, o.residual_base)
            self._release(quote, o.residual_quote)

        # final order status
        o.status = OrderState.REJECTED if o.actual_filled == 0 else OrderState.PARTIALLY_REJECTED
        ts = int(time.time() * 1000)
        o.ts_update = o.ts_finish = ts
        o.comment = reason
        o.add_history(ts=ts, status=o.status, comment=o.comment)
        o.squash_booking()

        # persist and log
        self.order_book.update(o)
        self._log_order(o)

    # ---------- logging ------------------------------------------------ #
    def _log_order(self, order: Order) -> None:
        px = order.price if order.price is not None else order.limit_price
        fee_str = (
            f"{order.actual_fee:.2f} {order.fee_currency}"
            if order.actual_fee is not None
            else "N/A"
        )
        asset = order.symbol.split("/")[0]
        if order.status in {OrderState.PARTIALLY_FILLED, OrderState.FILLED}:
            order_hist = order.last_history
            if order_hist is None:
                logger.warning("No history for order %s", order.id)
                return
            amount = order_hist.actual_filled
            px_str = f"{order_hist.price:.2f} {order.symbol}"
            fee_str = f"{order_hist.actual_fee:.2f} {order.fee_currency}"
        else:
            amount = order.amount - order.actual_filled
            px_str = f"{px:.2f} {order.symbol}" if px else "MKT"
            fee_str = "N/A"
        base_msg = (
            f"Order {order.id} [{order.type}] "
            f"{order.side.upper()} {amount:.8f} {asset} at {px_str}, fee {fee_str}"
        )
        status_prefix = order.status.label
        logger.info("%s %s", status_prefix, base_msg)

    def _update_trade_stats(
        self,
        symbol: str,
        side: OrderSide,
        amount: float,  # base units
        notional: float,  # quote units
        fee: float,  # quote units
        asset_fee: str,  # fee asset, usually the quote currency
        is_new: bool = True,  # whether this is the first trade for the corresponding order
    ) -> None:
        """
        Compact trade counters.

        ─ trades:<SIDE>:<BASE>:count        {"BTC": …, "ETH": …}
        ─ trades:<SIDE>:<BASE>:amount       {"BTC": …, "ETH": …}
        ─ trades:<SIDE>:<BASE>:notional     {"BTC": …, "ETH": …}
        ─ trades:<SIDE>:<BASE>:fee          {"BTC": …, "ETH": …}
        """
        base, quote = symbol.split("/")

        pipe = self.redis.pipeline()
        # Need to keep track of the key structure:
        count_valkey = f"trades:{side.value}:{base}:count"
        amount_valkey = f"trades:{side.value}:{base}:amount"
        notional_valkey = f"trades:{side.value}:{base}:notional"
        fee_valkey = f"trades:{side.value}:{base}:fee"
        # Increment the counters atomically
        if (
            is_new
        ):  # In case the order is already partially filled, we do not increment the counters
            pipe.hincrby(count_valkey, quote, 1)  # Number of trades for `base` in `quote`
        pipe.hincrbyfloat(amount_valkey, quote, amount)  # Bought `base` with `quote`
        pipe.hincrbyfloat(
            notional_valkey, quote, notional
        )  # Paid the notional with `quote` to trade `base`
        pipe.hincrbyfloat(
            fee_valkey, asset_fee, fee
        )  # Paid the fee with `asset_fee` to trade `base`
        # Remember the hash-keys so we can enumerate/reset later -------------
        # a small helper list to avoid repetition
        index_ops = [
            (TRADES_INDEX_COUNT, count_valkey),
            (TRADES_INDEX_AMOUNT, amount_valkey),
            (TRADES_INDEX_NOTIONAL, notional_valkey),
            (TRADES_INDEX_FEE, fee_valkey),
        ]

        for set_name, hash_key in index_ops:
            pipe.sadd(set_name, hash_key)

        pipe.execute()  # ← atomic MULTI/EXEC

    def _update_deposit_account(
        self,
        asset: str,
        amount: float,
    ) -> None:
        """
        Update the deposit account for a specific asset.

        If `is_new` is True, a new deposit account will be created if it doesn't exist.
        """
        pipe = self.redis.pipeline()
        deposit_key = f"deposits:{asset}"
        pipe.sadd(DEPOSITS_INDEX, deposit_key)
        # set ref_symbol (self.cash_asset) is; only if not already present
        pipe.hsetnx(deposit_key, "ref_symbol", self.cash_asset)
        pipe.hincrbyfloat(deposit_key, "asset_quantity", amount)
        if asset == self.cash_asset:
            value = amount  # Cash asset is always 1:1
        else:
            symbol = f"{asset}/{self.cash_asset}"
            value = amount * self.market.last_price(symbol).get()
        pipe.hincrbyfloat(deposit_key, "ref_value", value)
        pipe.execute()
        logger.info("Deposited %.8f %s to deposit account", amount, asset)

    def _update_withdrawal_account(
        self,
        asset: str,
        amount: float,
    ) -> None:
        """
        Update the withdrawal account for a specific asset.

        If `is_new` is True, a new withdrawal account will be created if it doesn't exist.
        """
        pipe = self.redis.pipeline()
        withdrawal_key = f"withdrawals:{asset}"
        pipe.sadd(WITHDRAWALS_INDEX, withdrawal_key)
        # set ref_symbol (self.cash_asset) is; only if not already present
        pipe.hsetnx(withdrawal_key, "ref_symbol", self.cash_asset)
        pipe.hincrbyfloat(withdrawal_key, "asset_quantity", amount)
        if asset == self.cash_asset:
            value = amount  # Cash asset is always 1:1
        else:
            symbol = f"{asset}/{self.cash_asset}"
            value = amount * self.market.last_price(symbol).get()
        pipe.hincrbyfloat(withdrawal_key, "ref_value", value)
        pipe.execute()

        logger.info("Withdrew %.8f %s from withdrawal account", amount, asset)

    # ---------- core balance moves ------------------------------------ #
    def _execute_buy(
        self,
        *,
        base: str,
        quote: str,
        fillable_amount: float,
        price: float,
        order_is_new: bool,
        order_will_close: bool,
        residual_quote: float,
    ) -> dict[str, float]:
        filled_notion = fillable_amount * price
        filled_fee = filled_notion * self.commission
        # Reduce the cash balance
        if order_will_close:
            # If the order will close, we release the still reserved notion + fee
            # This is to avoid mismatches on the used balances
            self._release(quote, residual_quote)
        else:
            # If the order will not close, we release only the fillable part
            self._release(quote, filled_notion + filled_fee)
        cash = self.portfolio.get(quote).get()
        cash.free -= filled_notion + filled_fee
        self.portfolio.set(cash)
        # Increase the asset balance
        asset = self.portfolio.get(base).get()
        asset.free += fillable_amount
        self.portfolio.set(asset)
        self._update_trade_stats(
            symbol=f"{base}/{quote}",
            side=OrderSide.BUY,
            amount=fillable_amount,
            notional=filled_notion,
            fee=filled_fee,
            asset_fee=quote,  # fee is usually in the quote currency
            is_new=order_is_new,
        )
        return {"filled_notion": filled_notion, "filled_fee": filled_fee}

    def _execute_sell(
        self,
        *,
        base: str,
        quote: str,
        fillable_amount: float,
        price: float,
        order_is_new: bool,
        order_will_close: bool,
        residual_quote: float,
    ) -> dict[str, float]:
        filled_notion = fillable_amount * price
        filled_fee = filled_notion * self.commission
        # Reduce the asset balance
        self._release(base, fillable_amount)
        asset = self.portfolio.get(base).get()
        asset.free -= fillable_amount
        self.portfolio.set(asset)
        # Increase the cash balance
        if order_will_close:
            # If the order will close, we release the still reserved fee
            # This is to avoid mismatches on the used balances
            self._release(quote, residual_quote)
        else:
            # If the order will not close, we release only the fillable part
            self._release(quote, filled_fee)
        cash = self.portfolio.get(quote).get()
        cash.free += filled_notion - filled_fee
        self.portfolio.set(cash)
        self._update_trade_stats(
            symbol=f"{base}/{quote}",
            side=OrderSide.SELL,
            amount=fillable_amount,
            notional=filled_notion,
            fee=filled_fee,
            asset_fee=quote,  # fee is usually in the quote currency
            is_new=order_is_new,
        )
        return {"filled_notion": filled_notion, "filled_fee": filled_fee}

    # ---------- consistency checks ------------------------------------ #
    def check_consistency(self, eps: float = 1e-9) -> dict[str, dict[str, float]]:
        """
        Compare what *should* be reserved (from open orders) with what's in portfolio.used.
        Returns a dict of mismatches.
        """
        open_orders = self.order_book.list(status=OPEN_STATUS).get()

        expected: dict[str, float] = defaultdict(float)
        for o in open_orders:
            base, quote = o.symbol.split("/")
            if o.side is OrderSide.BUY:
                expected[quote] += max(o.residual_quote, 0.0)
            else:
                expected[base] += max(o.residual_base, 0.0)
                expected[quote] += max(o.residual_quote, 0.0)

        mismatches = {}

        # current balances
        balances = self.portfolio.all().get()

        # check all assets that appear anywhere
        assets = set(balances.keys()) | set(expected.keys())
        for asset in assets:
            used_now = balances.get(asset, AssetBalance(asset)).used
            used_should = expected.get(asset, 0.0)
            if not math.isclose(used_now, used_should, rel_tol=0.0, abs_tol=eps):
                mismatches[asset] = {"used_now": used_now, "used_should": used_should}

        if mismatches:
            logger.error("Reservation mismatches: %s", mismatches)
        else:
            logger.info("No reservation mismatches found")
        return mismatches

    # ---------- public API  ------------------------------------------- #
    @property
    def tickers(self) -> list[str]:
        return self.market.tickers.get()  # type: ignore

    def fetch_ticker(self, symbol: str) -> TradingPair:
        tick = self.market.fetch_ticker(symbol).get()
        if tick is None:
            raise ValueError(f"Ticker {symbol} not available")
        return tick  # type: ignore

    def fetch_balance(self, asset: str | None = None) -> dict[str, Any]:
        info = {k: info.to_dict() for k, info in self.portfolio.all().get().items()}
        bal = info if asset is None else info.get(asset, {})
        sorted_bal = {k: bal[k] for k in sorted(bal.keys())}  # sort by asset name
        return sorted_bal

    def fetch_balance_list(self) -> list[str]:
        assets_owned_list = list(self.portfolio.all().get().keys())
        assets_owned_list.sort()  # sort by asset name
        return assets_owned_list

    def create_order(
        self,
        *,
        symbol: str,
        side: OrderSide | str,  # <-- may come in as str
        type: OrderType | str,  # <-- may come in as str
        amount: float,
        limit_price: float | None = None,
    ) -> dict[str, Any]:
        # NORMALISE side / type  ────────────────────────────────
        if isinstance(side, str):
            try:
                side = OrderSide(side)
            except ValueError as e:
                raise ValueError(f"invalid side {side!r}") from e

        if isinstance(type, str):
            try:
                type = OrderType(type)
            except ValueError as e:
                raise ValueError(f"invalid order type {type!r}") from e

        # validation
        if symbol not in self.market.tickers.get():
            raise ValueError(f"Ticker {symbol} does not exist")
        if amount <= 0:
            raise ValueError("amount must be > 0")
        if type is OrderType.LIMIT and (limit_price is None or limit_price < 0):
            raise ValueError("limit_price must be ≥ 0 for limit orders")

        last = self.market.last_price(symbol).get()
        px = last
        if type is OrderType.LIMIT:
            if limit_price is None:
                raise ValueError("limit orders need limit_price")
            if side is OrderSide.BUY:
                px = limit_price
            else:  # sell – must reserve against worst-case (higher) price
                px = max(limit_price, last)

        base, quote = symbol.split("/")
        notion, fee = amount * px, amount * px * self.commission

        # funds check
        comment = None
        enough_funds = False
        if side is OrderSide.BUY:
            have = self.portfolio.get(quote).get().free
            if have >= notion + fee:
                enough_funds = True
            else:
                comment = f"Need {notion + fee:.2f} {quote}, have {have:.2f}"
        else:
            # Test if we have enough base to sell
            have = self.portfolio.get(base).get().free
            if have >= amount:
                enough_funds = True
            else:
                comment = f"Need {amount:.8f} {base}, have {have:.8f}"
            # Test if we have enough quote to pay the fee
            have = self.portfolio.get(quote).get().free
            if have >= fee:
                enough_funds = enough_funds and True
            else:
                comment = (
                    (f"Need {fee:.2f} {quote}, have {have:.2f}")
                    if comment is None
                    else comment + f", need {fee:.2f} {quote}, have {have:.2f}"
                )
        if enough_funds:
            if side is OrderSide.BUY:
                self._reserve(quote, notion + fee)
            else:
                self._reserve(base, amount)
                self._reserve(quote, fee)
        # set booked values per side
        booked_notion = notion if side is OrderSide.BUY else 0.0
        status = OrderState.NEW if enough_funds else OrderState.REJECTED
        initial_booked_notion = booked_notion if enough_funds else 0.0
        reserved_notion_left = booked_notion if enough_funds else 0.0
        initial_booked_fee = fee if enough_funds else 0.0
        reserved_fee_left = fee if enough_funds else 0.0
        # open order
        ts = int(time.time() * 1000)
        order = Order(
            id=self._uid(),
            symbol=symbol,
            side=side,  # now an OrderSide
            type=type,  # now an OrderType
            amount=amount,
            limit_price=None if type is OrderType.MARKET else limit_price,
            notion_currency=quote,
            fee_currency=quote,
            fee_rate=self.commission,
            status=status,
            initial_booked_notion=initial_booked_notion,
            reserved_notion_left=reserved_notion_left,
            initial_booked_fee=initial_booked_fee,
            reserved_fee_left=reserved_fee_left,
            ts_create=ts,
            ts_update=ts,
            ts_finish=ts if status in CLOSED_STATUS else None,
            comment=comment,
        )
        self.order_book.add(order)
        self._log_order(order)

        # market order ⇒ schedule async settle
        if type is OrderType.MARKET:
            delay = random.uniform(MIN_TIME, MAX_TIME)
            t = threading.Timer(
                delay,
                lambda: self.actor_ref.tell({"cmd": "_settle_market", "oid": order.id}),
            )
            t.start()
            self._timers.append(t)

        return order.public_payload()

    # expose await-able helper
    def create_order_async(self, **kw: Any) -> dict[str, Any]:
        # This method is called on an ActorProxy, so Pykka automatically wraps the return in a Future
        return self.create_order(**kw)

    def cancel_order(self, oid: str) -> dict[str, Any]:
        o = self.order_book.get(oid).get()
        if o.status not in OPEN_STATUS:
            raise ValueError("Only *open* orders can be canceled")
        base, quote = o.symbol.split("/")
        if o.side is OrderSide.BUY:
            rq = o.residual_quote
            released_quote = self._release(quote, rq)
            released_base = 0.0
        else:
            rb = o.residual_base
            rq = o.residual_quote
            released_base = self._release(base, rb)
            released_quote = self._release(quote, rq)
        o.status = OrderState.CANCELED if o.actual_filled == 0 else OrderState.PARTIALLY_CANCELED
        ts = int(time.time() * 1000)
        o.ts_finish = o.ts_update = ts
        o.comment = "Order canceled by user"
        o.add_history(
            ts=ts,
            status=o.status,
            comment=o.comment,
        )
        o.squash_booking()
        self.order_book.update(o)
        self._log_order(o)
        # Sanity checks (idempotency + no leaks)
        if o.side is OrderSide.BUY:
            assert o.reserved_notion_left >= -1e-9
            assert o.reserved_fee_left >= -1e-9
        else:
            assert o.residual_base >= -1e-9
            assert o.reserved_fee_left >= -1e-9

        return {
            "canceled_order": o.public_payload(),
            "freed": {base: released_base, quote: released_quote},
        }

    # ---------- price-tick & housekeeping ----------------------------- #
    def process_single_order(self, o: Order, trading_pair: TradingPair) -> None:
        """
        Process a single order based on the current market state.
        This simulates order fills based on the current market state.
        """

        o_fresh = self.order_book.get(o.id, include_history=False).get()
        if o_fresh.status not in OPEN_STATUS or o_fresh.actual_filled >= o_fresh.amount - 1e-12:
            return
        o = o_fresh
        fillable = False
        need_amount = o.amount - o.actual_filled
        order_is_new = o.status is OrderState.NEW
        # Simulate slippage
        total_amount_available = (
            trading_pair.ask_volume if o.side is OrderSide.BUY else trading_pair.bid_volume
        )
        amount_available = self._slippage_simulate(total_amount_available, SIGMA_FILL)
        if amount_available < need_amount:
            fillable_amount = amount_available
            order_will_close = False
        else:
            fillable_amount = need_amount
            order_will_close = True
        if fillable_amount <= 0:
            return
        if o.type is OrderType.MARKET:
            fillable = True
        elif o.type is OrderType.LIMIT:
            if o.limit_price is None:
                raise ValueError("Limit orders must have a limit_price")
            fillable = (o.side is OrderSide.BUY and trading_pair.ask <= o.limit_price) or (
                o.side is OrderSide.SELL and trading_pair.bid >= o.limit_price
            )
        if not fillable:
            return
        base, quote = o.symbol.split("/")
        px = trading_pair.ask if o.side is OrderSide.BUY else trading_pair.bid

        # ---------------- reservation check ---------------------------
        # If the order is not fillable due to insufficient reserves,
        # we reject it and release the reserved amounts.
        if o.side is OrderSide.BUY:
            need_quote = fillable_amount * px * (1 + self.commission)
            total_balance_q = self.portfolio.get(quote).get().total
            if total_balance_q + 1e-12 < need_quote:
                self._rejected_for_insufficient_reserve(
                    o,
                    reason=f"Insufficient {quote} reserved to buy (need {need_quote:.8f} {quote}, have {total_balance_q:.8f} {quote})",
                )
                return
        else:  # sell
            need_asset = fillable_amount
            need_fee_q = fillable_amount * px * self.commission
            total_balance_a = self.portfolio.get(base).get().total
            total_balance_q = self.portfolio.get(quote).get().total
            if total_balance_a + 1e-12 < need_asset:
                self._rejected_for_insufficient_reserve(
                    o,
                    reason=(
                        f"Insufficient {base} reserved for sell (need {need_asset:.8f} {base}, have {total_balance_a:.8f} {base})"
                    ),
                )
                return
            elif total_balance_q + 1e-12 < need_fee_q:
                self._rejected_for_insufficient_reserve(
                    o,
                    reason=(
                        f"Insufficient {quote} reserved for sell to pay fee "
                        f"(need {need_fee_q:.8f} {quote}, have {total_balance_q:.8f} {quote})"
                    ),
                )
                return
        tx = (self._execute_buy if o.side is OrderSide.BUY else self._execute_sell)(
            base=base,
            quote=quote,
            fillable_amount=fillable_amount,
            price=px,
            order_is_new=order_is_new,
            order_will_close=order_will_close,
            residual_quote=o.residual_quote,
        )
        # Calculate the new order state
        ts = int(time.time() * 1000)
        total_filled = o.actual_filled + fillable_amount
        total_notion = o.actual_notion + tx["filled_notion"]
        total_fee = o.actual_fee + tx["filled_fee"]
        # Update the order
        o.ts_update = ts
        o.actual_filled = total_filled
        o.actual_notion = total_notion
        o.actual_fee = total_fee
        o.price = o.actual_notion / o.actual_filled if o.actual_filled > 0 else px

        # shrink reservations
        if o.side is OrderSide.BUY:
            o.reserved_notion_left = max(o.reserved_notion_left - tx["filled_notion"], 0.0)
            o.reserved_fee_left = max(o.reserved_fee_left - tx["filled_fee"], 0.0)
        else:
            # sell: only fee was reserved in quote, base reservation shrinks via residual_base
            o.reserved_fee_left = max(o.reserved_fee_left - tx["filled_fee"], 0.0)

        if order_will_close:
            new_status = OrderState.FILLED
            o.ts_finish = ts
            o.squash_booking()
        else:
            new_status = OrderState.PARTIALLY_FILLED
        o.status = new_status
        o.add_history(
            ts=ts,
            status=new_status,
            price=px,
            amount_remain=o.amount_remain,
            actual_filled=fillable_amount,
            actual_notion=tx["filled_notion"],
            actual_fee=tx["filled_fee"],
            reserved_notion_left=o.reserved_notion_left,
            reserved_fee_left=o.reserved_fee_left,
        )
        # Update the order book
        self.order_book.update(o)
        self._log_order(o)

    def process_price_tick(self, symbol: str) -> None:
        """
        Process a price tick for the given symbol.
        This simulates order fills based on the current market state.
        """
        trading_pair = self.fetch_ticker(symbol)  # ask, bid, ask_volume, bid_volume
        open_orders = self.order_book.list(status=OPEN_STATUS, symbol=symbol).get()
        for o in open_orders:
            self.process_single_order(o, trading_pair)

    def prune_orders_older_than(
        self,
        *,
        age: timedelta,
    ) -> int:
        """
        Prune orders that are older than the specified age.
        This removes orders that are in CLOSED_STATUS and older than the specified age.
        Returns the number of orders removed.
        """
        now_ms = int(time.time() * 1000)
        cutoff = now_ms - int(age.total_seconds() * 1000)
        removed = 0
        for s in CLOSED_STATUS:
            for o in self.order_book.list(status=s).get():
                if o.status in CLOSED_STATUS:
                    ts = o.ts_finish
                    if ts < cutoff:
                        self.order_book.remove(o.id)
                        removed += 1
        if removed:
            logger.info("Pruned %d stale orders older than %s", removed, age)
        else:
            logger.info("No stale orders older than %s found", age)
        return removed

    def expire_orders_older_than(
        self,
        *,
        age: timedelta,
    ) -> int:
        """
        Expire open orders that are older than the specified age.
        """
        now_ms = int(time.time() * 1000)
        cutoff = now_ms - int(age.total_seconds() * 1000)
        expired = 0
        comment = "Order expired due to inactivity"
        for s in OPEN_STATUS:
            for o in self.order_book.list(status=s).get():
                if o.status in OPEN_STATUS:
                    if o.status is OrderState.NEW:
                        expired_status = OrderState.EXPIRED
                    else:
                        expired_status = OrderState.PARTIALLY_EXPIRED
                    base, quote = o.symbol.split("/")
                    ts = o.ts_update
                    if ts < cutoff:
                        # release leftovers
                        if o.side is OrderSide.BUY:
                            self._release(quote, o.residual_quote)
                        else:
                            self._release(base, o.residual_base)
                            self._release(quote, o.residual_quote)
                        o.status = expired_status
                        o.ts_update = o.ts_finish = now_ms
                        o.reserved_notion_left = 0.0
                        o.reserved_fee_left = 0.0
                        o.comment = comment
                        o.add_history(
                            ts=now_ms,
                            status=expired_status,
                            comment=comment,
                        )
                        self.order_book.update(o)
                        self._log_order(o)
                        expired += 1
        if expired:
            logger.info("Expired %d inactive orders older than %s", expired, age)
        else:
            logger.info("No expired orders older than %s found", age)
        return expired

    # ----- dry-run helper --------------------------------------------------- #
    def can_execute(
        self, *, symbol: str, side: OrderSide, amount: float, price: float | None = None
    ) -> dict[str, bool | str]:
        """
        Check if an order can be executed without actually executing it.
        This checks if there are enough funds in the portfolio to execute the order.
        Returns a dict with keys 'ok' (bool) and 'reason' (str or None).
        """
        px = price or self.market.last_price(symbol).get()
        base, quote = symbol.split("/")
        fee = amount * px * self.commission
        if side is OrderSide.BUY:
            have = self.portfolio.get(quote).get().free
            need = amount * px + fee
            ok = have >= need
            reason = None if ok else f"need {need:.2f} {quote}, have {have:.2f}"
        else:  # sell
            have = self.portfolio.get(base).get().free
            ok = have >= amount
            reason = None if ok else f"need {amount:.8f} {base}, have {have:.8f}"
        return {"ok": ok, "reason": reason}  # type: ignore[dict-item,unused-ignore]

    # ----- overview helpers --------------------------------------------- #

    def _get_tradeable_assetslist_tickerslist_from_current_market(
        self,
    ) -> tuple[list[str], list[str]]:
        """Get a list of assets from the tickers list.
        This function extracts the assets from the tickers list, EXCLUDING the cash asset.
        It returns a list of asset names.
        If there are no tradeable assets, it returns an empty list.
        """
        trading_pairs = self.market.tickers.get()
        if not trading_pairs:
            logger.warning("No tradeable assets found in trading_pairs, returning empty lists")
            return [], []
        assetslist = [t.split("/")[0] for t in trading_pairs]
        return assetslist, trading_pairs

    def _get_assetslist_and_tickerslist_from_portfolio(
        self, portfolio: dict[str, AssetBalance]
    ) -> tuple[list[str], list[str]]:
        """Get a list of assets and their tickers from the portfolio.
        This function extracts the assets from the portfolio, EXCLUDING the cash asset.
        It returns a tuple of two lists: the first list contains the asset names,
        the second list contains the asset tickers.
        """
        assets_list = [a for a in portfolio.keys() if a != self.cash_asset]
        tickers_list = [f"{a}/{self.cash_asset}" for a in assets_list]
        if not assets_list:
            logger.warning("No assets found in portfolio, returning empty lists")
            return ([], [])
        return (assets_list, tickers_list)

    def _get_summary_assets_balance(
        self, portfolio: dict[str, AssetBalance], prices: dict[str, float]
    ) -> dict[str, float]:
        """Get a summary of the assets in the portfolio.
        This function calculates the total value of all assets in the portfolio.
        It returns a dict with the total value of each asset, including cash.
        The values are calculated based on the prices of the assets in the portfolio.
        If there are no assets in the portfolio, it returns a dict with all values set to 0.0.
        """
        _assets = {}
        assets_list, tickers_list = self._get_assetslist_and_tickerslist_from_portfolio(portfolio)
        cash_balance = portfolio.get(self.cash_asset)
        if cash_balance is None:
            cash = {"free": 0.0, "used": 0.0}
        else:
            # cash_balance is a dict from AssetBalance.to_dict()
            cash = {
                "free": cash_balance.get("free", 0.0),  # type: ignore[attr-defined]
                "used": cash_balance.get("used", 0.0),  # type: ignore[attr-defined]
            }
        for a, t in zip(assets_list, tickers_list, strict=False):
            asset_balance = {}
            if a == self.cash_asset:
                continue
            if prices.get(t) is None:
                logger.warning("No price for asset %s, skipping", t)
                continue
            # portfolio[a] is a dict from AssetBalance.to_dict()
            asset_balance["free"] = portfolio[a].get("free", 0.0)  # type: ignore[attr-defined]
            asset_balance["used"] = portfolio[a].get("used", 0.0)  # type: ignore[attr-defined]
            asset_balance["price"] = prices[t]
            _assets[a] = asset_balance
        # Convert to pandas to vector operations
        assets_pd = pd.DataFrame(_assets).T
        # If there are no assets, return a dict with all values set to 0.0
        if assets_pd.empty:
            _tmp_assets_dict = {
                "assets_free_value": 0.0,
                "assets_frozen_value": 0.0,
                "assets_total_value": 0.0,
            }
            assets_pd_summary = pd.Series(_tmp_assets_dict)
        else:
            assets_pd["assets_free_value"] = assets_pd["free"] * assets_pd["price"]
            assets_pd["assets_frozen_value"] = assets_pd["used"] * assets_pd["price"]
            assets_pd["assets_total_value"] = (
                assets_pd["assets_free_value"] + assets_pd["assets_frozen_value"]
            )
            assets_pd.drop(columns=["free", "used", "price"], inplace=True)
            assets_pd_summary = assets_pd.sum(numeric_only=True)
        balance_value = assets_pd_summary.to_dict()
        balance_value["cash_free_value"] = cash.get("free", 0.0)
        balance_value["cash_frozen_value"] = cash.get("used", 0.0)
        balance_value["cash_total_value"] = (
            balance_value["cash_free_value"] + balance_value["cash_frozen_value"]
        )
        balance_value["total_free_value"] = (
            balance_value["cash_free_value"] + balance_value["assets_free_value"]
        )
        balance_value["total_frozen_value"] = (
            balance_value["cash_frozen_value"] + balance_value["assets_frozen_value"]
        )
        balance_value["total_equity"] = (
            balance_value["cash_total_value"] + balance_value["assets_total_value"]
        )
        return balance_value  # type: ignore[dict-item,unused-ignore]

    def _get_summary_assets_orders(
        self, open_orders: list[Order], prices: dict[str, float]
    ) -> dict[str, float]:
        """Get a summary of the frozen assets in open orders.
        This function calculates the total value of reserved assets and fees in open orders.
        It returns a dict with the total reserved value of assets and quotes, and the total frozen value.
        The values are calculated based on the prices of the assets in the open orders.
        If there are no open orders, it returns a dict with all values set to 0.0.
        """
        RELEVANT_COLS = [
            "symbol",
            "side",
            "amount",
            "actual_filled",
            "reserved_notion_left",
            "reserved_fee_left",
        ]
        if not open_orders:
            return {
                "assets_frozen_value": 0.0,
                "cash_frozen_value": 0.0,
                "total_frozen_value": 0.0,
            }
        open_orders_pd = pd.DataFrame([o.to_dict() for o in open_orders])
        open_orders_pd = open_orders_pd[RELEVANT_COLS]
        open_orders_pd["price"] = open_orders_pd["symbol"].map(prices)  # type: ignore[attr-defined]
        # We need to calculate the reserved assets, but this only makes sense for SELL orders.
        open_orders_pd["assets_frozen_value"] = 0.0
        open_orders_pd.loc[open_orders_pd["side"] == OrderSide.SELL, "assets_frozen_value"] = (
            open_orders_pd["amount"] - open_orders_pd["actual_filled"]
        ) * open_orders_pd["price"]
        open_orders_pd["cash_frozen_value"] = (
            open_orders_pd["reserved_notion_left"] + open_orders_pd["reserved_fee_left"]
        )
        open_orders_pd = open_orders_pd[["assets_frozen_value", "cash_frozen_value"]]
        open_orders_pd_summary = open_orders_pd.sum(numeric_only=True)  # type: ignore[attr-defined]
        orders_frozen_value = open_orders_pd_summary.to_dict()
        orders_frozen_value["total_frozen_value"] = (
            orders_frozen_value["assets_frozen_value"] + orders_frozen_value["cash_frozen_value"]
        )
        return orders_frozen_value  # type: ignore[dict-item,unused-ignore]

    def get_summary_assets(self) -> dict[str, Any]:
        """
        Get a summary of all value assets in the portfolio and frozen assets in open orders.
        """
        # To be sure that we have the same price on both balance and orders, we want to fetch the latest prices
        # only once. Therefore, we need to prepare the portfolio and orders first.
        # Portfolio data:
        portfolio = self.fetch_balance()
        tickers_list_portfolio = self._get_assetslist_and_tickerslist_from_portfolio(portfolio)[1]
        # Get open orders and their tickers
        open_orders = self.order_book.list(status=OPEN_STATUS, include_history=False).get()
        tickers_list_orders = [o.symbol for o in open_orders]
        # My expectation is that all open orders tickers are also in the portfolio,
        # but I am not sure if this is always the case.
        tickers_list = list(set(tickers_list_portfolio + tickers_list_orders))
        # Now we can fetch the prices for all tickers
        prices = {t: self.market.last_price(t).get() for t in tickers_list}
        output = {}
        output["balance_source"] = self._get_summary_assets_balance(portfolio, prices)
        output["orders_source"] = self._get_summary_assets_orders(open_orders, prices)
        b_source = output["balance_source"]
        o_source = output["orders_source"]
        # Check for mismatches between balance and orders
        _mismatch = {}
        TOLERANCE = 1e-3  # in cash value units (e.g. 0.001 USDT)
        for k in o_source.keys():
            o_val = o_source[k]
            b_val = b_source.get(k, 0.0)
            if math.isclose(o_val, b_val, rel_tol=0.0, abs_tol=TOLERANCE):  # type: ignore[arg-type,unused-ignore]
                _mismatch[k] = False
            else:
                _mismatch[k] = True

        output["misc"] = {  # type: ignore[dict-item]
            "cash_asset": self.cash_asset,
            "mismatch": _mismatch,
        }
        return output  # type: ignore[return-value]

    def get_trade_stats(
        self,
        *,
        side: OrderSide | str | None = None,
        assets: list[str] | str | None = None,  # "BTC", "USDT", …
    ) -> dict[str, Any]:
        """
        Return the counters in the familiar structure ::

            {
                "BUY":  {"count": {...}, "amount": {...}, "notional": {...}, "fee": {...}},
                "SELL": { ... }
            }

        Optional filters
        ----------------
        side   – restrict output to BUY or SELL
        asset  – return only fields whose *name* equals that asset
        """
        # 1️⃣ normalise input ----------------------------------------------------
        if isinstance(side, str):
            side = OrderSide(side)

        if isinstance(assets, str):
            assets = [assets]

        # helper ────────────────────────────────────────────────────────────────
        def _collect(metric: str, _side: OrderSide, _assets: list[str] | None) -> dict[str, float]:
            """
            Gather all hashes whose key matches:
                trades:<_side>:*:<metric>
            """
            index_key = f"trades:index:{metric}"
            keys = [k for k in self.redis.smembers(index_key) if k.split(":")[1] == _side.value]

            pipe = self.redis.pipeline()
            base_list = []
            for k in keys:
                base = k.split(":")[2]
                if _assets and base not in _assets:
                    continue
                base_list.append(base)
                pipe.hgetall(k)
            raw = pipe.execute() if keys else []
            raw_dict = {base: r for base, r in zip(base_list, raw, strict=False) if r}
            return raw_dict  # type: ignore[dict-item,unused-ignore]

        # 2️⃣ build the response -------------------------------------------------
        wanted_sides = [side] if side else (OrderSide.BUY, OrderSide.SELL)
        out: dict[str, Any] = {}
        for s in wanted_sides:
            out[s.value.upper()] = {
                "count": _collect("count", s, assets),
                "amount": _collect("amount", s, assets),
                "notional": _collect("notional", s, assets),
                "fee": _collect("fee", s, assets),
            }

        return out

    def _get_investment_assets_list(self) -> list[str]:
        """
        Get a list of all investment assets in the portfolio.
        This function retrieves all assets that have a deposit or a withdrawal account.
        It returns a list of asset names that have either a deposit or withdrawal account.

        Returns
        -------
        list[str]
            A list of asset names that have either a deposit or withdrawal account.
            If no assets have a deposit or withdrawal account, it returns an empty list.
        """
        assets = set()
        hash_deposits = self.redis.smembers(DEPOSITS_INDEX)
        hash_withdrawals = self.redis.smembers(WITHDRAWALS_INDEX)
        if hash_deposits:
            for key in hash_deposits:
                asset = key.split(":")[1]
                assets.add(asset)
        if hash_withdrawals:
            for key in hash_withdrawals:
                asset = key.split(":")[1]
                assets.add(asset)
        # If no assets found, return empty list
        if not assets:
            return []
        return list(assets)

    def _get_investment_asset(self, asset: str) -> dict[str, Any]:
        """
        Get the investment and withdrawal accounts for a given asset.
        This function retrieves the deposit and withdrawal accounts for the specified asset.
        If the asset does not have a deposit or withdrawal account, it returns an empty dict for that account.

        Parameters
        ----------
        asset : str
            The asset for which to retrieve the deposit and withdrawal accounts.

        Returns
        -------
        dict[str, float]
            A dictionary containing the deposit and withdrawal accounts for the specified asset.
            The keys are "deposit_account" and "withdrawal_account", and the values are dictionaries
            with asset balances (free and used) as floats.
        If the asset does not have a deposit or withdrawal account, the corresponding value will be an empty dict.
        If the asset does not exist, it will return empty dicts for both accounts.
        """
        FLOAT_KEYS = ("asset_quantity", "ref_value")
        fmt_investment = lambda d: {k: float(v) if k in FLOAT_KEYS else v for k, v in d.items()}
        deposit_key = f"deposits:{asset}"
        withdrawal_key = f"withdrawals:{asset}"
        output = {}
        # Check if the deposit account exists
        if deposit_key in self.redis.smembers(DEPOSITS_INDEX):
            output["deposits"] = fmt_investment(self.redis.hgetall(deposit_key))
        else:
            output["deposits"] = {}
        if withdrawal_key in self.redis.smembers(WITHDRAWALS_INDEX):
            output["withdrawals"] = fmt_investment(self.redis.hgetall(withdrawal_key))
        else:
            output["withdrawals"] = {}
        return output

    def get_summary_capital(self, aggregation: bool = True) -> dict[str, Any]:
        """
        Get a summary of all capital related amounts in the portfolio.
        - Total equity in the portfolio (free + used)
        - Total deposits.
        - Total withdrawals.
        - Performance.
        """
        # BALANCE ----------------------------------------------------
        balance = self.fetch_balance()
        # Get the prices for all assets in the portfolio
        assets_list, tickers_list = self._get_assetslist_and_tickerslist_from_portfolio(balance)
        prices = {t: self.market.last_price(t).get() for t in tickers_list}
        for a, t in zip(assets_list, tickers_list, strict=False):
            _price = prices.get(t)
            balance[a]["price"] = _price
            balance[a]["value"] = _price * balance[a]["total"]
        if balance.get(self.cash_asset) is not None:
            balance[self.cash_asset]["price"] = 1.0  # cash asset is always 1.0
            balance[self.cash_asset]["value"] = balance[self.cash_asset]["total"]
        # INVESTMENT ASSETS ----------------------------------------
        investment_accounts = {}
        # We will also use this to get the deposit and withdrawal accounts for each asset.
        for asset in self._get_investment_assets_list():
            investment_accounts[asset] = self._get_investment_asset(asset)
        # AGGREGATION ----------------------------------------
        # If aggregation is requested, we will aggregate the investment accounts
        # by summing up the free and used amounts for each asset.
        # This will give us a total capital in the portfolio.
        if aggregation:
            # Aggregate the investment accounts
            equity = 0.0
            deposits = 0.0
            withdrawals = 0.0
            for b in balance.values():
                equity += b["value"]
            for invest in investment_accounts.values():
                deposits += invest.get("deposits", {}).get("ref_value", 0.0)  # type: ignore[union-attr,call-overload]
                withdrawals += invest.get("withdrawals", {}).get("ref_value", 0.0)  # type: ignore[union-attr,call-overload]
            # Prepare the output
            output = {
                "equity": equity,
                "deposits": deposits,
                "withdrawals": withdrawals,
                "profit_loss": equity - (deposits - withdrawals),
            }
            return output
        else:
            # If aggregation is not requested, we will return the balance and investment accounts as is
            return {
                "balance": balance,
                "investment_assets": investment_accounts,
            }

    # ----- admin helpers ---------------------------------------------------- #
    def set_balance(self, asset: str, *, free: float = 0.0, used: float = 0.0) -> dict[str, float]:
        """
        Set the balance for a given asset.
        This function sets the free and used balance for the specified asset.
        If the asset is not tradeable, it raises a ValueError.
        If free or used is negative, it raises a ValueError.
        It returns the updated balance as a dict.

        Parameters
        ----------
        asset : str
            The asset for which to set the balance.
        free : float, optional
            The free balance of the asset (default is 0.0).
        used : float, optional
            The used balance of the asset (default is 0.0).

        Returns
        -------
        dict
            The updated balance of the asset as a dict.
        """
        # Check if the asset is tradeable
        # Exclude the cash asset from this check
        if asset != self.cash_asset:
            tradeable_assets = self._get_tradeable_assetslist_tickerslist_from_current_market()[0]
            if asset not in tradeable_assets:
                raise ValueError(f"Asset {asset} unknown or not tradeable")
        # Check if the free and used balances are valid
        if free < 0 or used < 0:
            raise ValueError("free/used must be ≥ 0")
        self.portfolio.set(AssetBalance(asset, free, used))
        balance = self.portfolio.get(asset).get()  # type: ignore[union-attr,no-any-return]
        return balance.to_dict()  # type: ignore[no-any-return]

    def deposit_asset(self, asset: str, amount: float) -> dict[str, float]:
        """
        Deposit an asset into the portfolio.
        This function adds the specified amount of the asset to the portfolio.
        If the asset is not tradeable, it raises a ValueError.
        If the amount is less than or equal to 0, it raises a ValueError.
        It returns the updated balance as a dict.

        Parameters
        ----------
        asset : str
            The asset to deposit.
        amount : float
            The amount of the asset to deposit.

        Returns
        -------
        dict
            The updated balance of the asset as a dict.
        """
        # Check if the asset is tradeable
        # Exclude the cash asset from this check
        if asset != self.cash_asset:
            tradeable_assets = self._get_tradeable_assetslist_tickerslist_from_current_market()[0]
            if asset not in tradeable_assets:
                raise ValueError(f"Asset {asset} unknown or not tradeable")
        # Check if the amount is valid
        if amount <= 0:
            raise ValueError("Amount must be > 0")
        bal = self.portfolio.get(asset).get()  # type: ignore[union-attr,no-any-return]
        bal.free += amount
        self.portfolio.set(bal)
        self._update_deposit_account(asset, amount)
        # Return the updated balance
        return bal.to_dict()  # type: ignore[no-any-return,unused-ignore]

    def withdrawal_asset(self, asset: str, amount: float) -> dict[str, float]:
        """
        Withdraw an asset from the portfolio.
        This function removes the specified amount of the asset from the portfolio.
        If the asset is not tradeable, it raises a ValueError.
        If the amount is less than or equal to 0, it raises a ValueError.
        If there is insufficient balance, it raises a ValueError.
        It returns the updated balance as a dict.

        Parameters
        ----------
        asset : str
            The asset to withdraw.
        amount : float
            The amount of the asset to withdraw.

        Returns
        -------
        dict
            The updated balance of the asset as a dict.
        """
        # Check if the asset is tradeable
        # Exclude the cash asset from this check
        if asset != self.cash_asset:
            tradeable_assets = self._get_tradeable_assetslist_tickerslist_from_current_market()[0]
            if asset not in tradeable_assets:
                raise ValueError(f"Asset {asset} unknown or not tradeable")
        # Try to get the balance of the asset
        # If the asset does not exist, create a temporal new balance with 0.0
        try:
            bal = self.portfolio.get(asset).get()  # type: ignore[union-attr,no-any-return]
        except KeyError:
            bal = AssetBalance(asset, 0.0, 0.0)
        # Check if the amount is valid and if there is enough balance
        if amount <= 0:
            raise ValueError("Amount must be > 0")
        if bal.free < amount:
            raise ValueError(
                f"Insufficient balance: {bal.free} {asset}, requested {amount} {asset}"
            )
        bal.free -= amount
        self.portfolio.set(bal)
        self._update_withdrawal_account(asset, amount)
        # Return the updated balance
        return bal.to_dict()  # type: ignore[no-any-return,unused-ignore]

    def set_ticker(
        self,
        symbol: str,
        price: float,
        bid_volume: float | None = None,
        ask_volume: float | None = None,
    ) -> dict[str, Any]:
        ts = int(time.time() * 1000)
        dummy_notion = 10**12  # just a large number to ensure liquid volumes
        bid_volume = bid_volume or dummy_notion / price
        ask_volume = ask_volume or dummy_notion / price

        if symbol not in self.market.tickers.get():
            raise ValueError(f"Ticker {symbol} does not exist")

        # 1️⃣ fire‑and‑forget the price update
        self.market.set_last_price(
            TradingPair(
                symbol=symbol,
                price=price,
                timestamp=ts,
                bid=price,
                ask=price,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
            )
        ).get()  # we still wait here to ensure the write has finished

        # 2️⃣ read the now‑current ticker snapshot and hand it back
        return self.market.fetch_ticker(symbol).get().to_dict()  # type: ignore[no-any-return,unused-ignore]

    # ------------- reset helpers -------------------------------------------- #
    ############################################################################
    # These methods are used to reset the state of the engine, e.g. for tests or
    # when starting fresh. They remove all hashes and index sets related to trades.
    ############################################################################

    def _reset_hash_keys(self, index_set: list[str]) -> int:
        """
        Remove every all hashes existing in the given index set **plus** the index sets themselves.

        Parameters
        ----------
        index_set : list[str]
            List of index set names (e.g. `["trades:index:count", "trades:index:amount"]`).

        Returns
        -------
        int
            Total number of Redis keys removed (hashes + index sets).
        """
        # Fetch members of every index set in one round-trip
        pipe = self.redis.pipeline()
        for s in index_set:
            pipe.smembers(s)
        index_members: list[set[str]] = pipe.execute()

        # Flatten to a list of hash-keys; keep only non-empty strings
        hash_keys: list[str] = [k for member_set in index_members for k in member_set if k]

        # 2️⃣ also purge the index sets themselves ------------------------------
        keys_to_delete = hash_keys + list(index_set)

        if not keys_to_delete:
            logger.info("Hash counters already reset – nothing to delete")
            return 0

        deleted = self.redis.unlink(*keys_to_delete)  # non-blocking in Redis ≥4
        logger.info("Hash counters reset – %d keys removed", deleted)

        return deleted

    def reset(self) -> None:
        self.portfolio.clear()
        self.order_book.clear()
        # cancel and drain timers
        for t in self._timers:
            t.cancel()
        self._timers.clear()
        self._oid = itertools.count(1)
        INDEX_SETS = (
            TRADES_INDEX_COUNT,
            TRADES_INDEX_AMOUNT,
            TRADES_INDEX_NOTIONAL,
            TRADES_INDEX_FEE,
            DEPOSITS_INDEX,
            WITHDRAWALS_INDEX,
        )
        # Reset all hash keys in the index sets
        self._reset_hash_keys(index_set=list(INDEX_SETS))  # type: ignore[arg-type,unused-ignore]

    # ---------- message handler & lifecycle --------------------------- #
    def on_receive(self, msg: Any) -> None:
        """
        Handle incoming messages.
        This method processes commands sent to the actor.
        """
        if msg.get("cmd") == "_settle_market":
            oid = msg["oid"]
            try:
                o = self.order_book.get(oid).get()
            except KeyError:
                logger.warning("Order %s vanished before settle; ignoring", oid)
                return
            if o.status not in OPEN_STATUS or o.actual_filled >= o.amount - 1e-12:
                return
            trading_pair = self.fetch_ticker(o.symbol)
            self.process_single_order(o, trading_pair)

    def on_stop(self) -> None:
        """
        Stop the actor and clean up resources.
        This method is called when the actor is stopped.
        It cancels all pending timers and stops the market, portfolio, and order book actors.
        """
        logger.info("Stopping ExchangeEngineActor %s", self.actor_ref)
        # stop all timers
        self._timers.clear()
        # stop the market, portfolio, and order book actors
        logger.info("Stopping market, portfolio, and order book actors")
        # Note: we do not need to call `stop()` on the market, portfolio, and order_book actors,
        # as they are already managed by the actor system.
        # cancel pending timers
        for t in self._timers:
            t.cancel()
        for a in (self.market, self.portfolio, self.order_book):
            a.stop()


# ---------- façade helper ---------------------------------------------- #
def start_engine(redis_url: str, commission: float) -> pykka.ActorProxy:
    """
    Convenience for tests / server:
        engine = start_engine("redis://127.0.0.1:6379/0", commission=0.001)
    """
    return ExchangeEngineActor.start(redis_url=redis_url, commission=commission).proxy()
