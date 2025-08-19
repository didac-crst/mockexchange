"""
server.py
~~~~~~~~~

FastAPI façade over :class:`core.engine_actors.ExchangeEngineActor`.

* **No business logic** lives here – we only translate *HTTP ⇄ Python*.
* Designed to run **inside a Docker container** (host-network is fine).
* All state (balances, orders, tick data) persists in Valkey/Redis.
* **Authentication**
  Every request must include
  ``x-api-key: $API_KEY`` unless the container is started with
  ``TEST_ENV=true`` (integration tests).

Environment variables
---------------------
API_KEY required key for every request (default: "invalid-key")
REDIS_URL redis://host:port/db (default: localhost:6379/0)
COMMISSION trading fee, e.g. 0.001 (default: 0.001 = 0.1 %)
TICK_LOOP_SEC price-tick scan interval (default: 10 s)
TEST_ENV set to 1 / true to disable auth & expose /docs

HTTP Endpoints
--------------
Market data
~~~~~~~~~~~
GET  **/tickers**                      → list of all symbols
GET  **/tickers/{ticker}**             → one ticker (e.g. ``BTC/USDT``)

Portfolio
~~~~~~~~~
GET  **/balance**                      → full account snapshot
GET  **/balance/list**                 → list of all assets with balances
GET  **/balance/{asset}**              → asset row only (``free``, ``used``)
POST **/balance/{asset}/deposit**      → deposit asset (e.g. ``USDT``)
POST **/balance/{asset}/withdrawal**   → withdraw asset (e.g. ``USDT``)

Orders
~~~~~~
GET  **/orders**                       → display all orders, optional filters
GET  **/orders/list**                  → list orders, optional filters
GET  **/orders/{oid}**                 → single order by id
POST **/orders**                       → create *market* | *limit* order
POST **/orders/can_execute**           → dry-run balance check
POST **/orders/{oid}/cancel**          → cancel *open* order

Overview
~~~~~~~~~~~
GET  **/overview/capital**             → portfolio capital summary
GET  **/overview/assets**              → portfolio assets summary
GET  **/overview/trades**              → trade statistics (by asset, side)

Admin
~~~~~
PATCH **/admin/tickers/{ticker}/price** → set ticker price and volumes
PATCH **/admin/balance/{asset}**        → set asset balance (free, used)
DELETE **/admin/data**                  → wipe balances **and** orders
GET **/admin/health**                   → check service health

Implementation notes
--------------------
* The background *tick-loop* scans keys ``tickers:*`` in Redis every
  ``TICK_LOOP_SEC`` seconds and settles limit orders whose prices have
  crossed.
* API docs (`/docs`) and the raw OpenAPI JSON are **disabled in
  production** for safety; they are exposed automatically when
  ``TEST_ENV=true``.

"""

# server.py
from __future__ import annotations

# Standard library imports
import asyncio
import contextlib
import os
import socket
import time
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Literal

import redis
from core.constants import ALL_SIDES_STR, ALL_STATUS_STR, ALL_TYPES_STR
from core.engine_actors import start_engine  # NEW import
from core.logging_config import logger
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from pykka import Future

# load environment from your project’s .env
load_dotenv(Path(__file__).parent.parent / ".env")


_ALL_STATUS = Literal[*ALL_STATUS_STR]  # type alias for all order statuses
_TRADING_SIDES = Literal[*ALL_SIDES_STR]  # type alias for all trading sides
_ORDER_TYPES = Literal[*ALL_TYPES_STR]  # type alias for all order types

CASH_ASSET = os.getenv("CASH_ASSET", "USDT")  # default cash asset


# ─────────────────────────── Pydantic models ────────────────────────── #
class OrderReq(BaseModel):
    symbol: str = "BTC/USDT"
    side: _TRADING_SIDES
    type: _ORDER_TYPES = "market"
    amount: float
    limit_price: float | None = None


class BalanceReq(BaseModel):
    free: float = Field(1.0, ge=0)
    used: float = Field(0.0, ge=0)


class FundReq(BaseModel):
    amount: float = Field(100000.0, gt=0)


class ModifyTickerReq(BaseModel):
    price: float = Field(..., gt=0)
    bid_volume: float | None = None
    ask_volume: float | None = None


# ───────────────────── initialise actor engine ──────────────────────── #
REFRESH_S = int(os.getenv("TICK_LOOP_SEC", "10"))
VALKEY_HOST = os.getenv("VALKEY_HOST", "localhost")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
VALKEY_PASSWORD = os.getenv("VALKEY_PASSWORD", "")
_r = redis.Redis(
    host=VALKEY_HOST, port=VALKEY_PORT, password=VALKEY_PASSWORD, decode_responses=True
)
MY_ID = f"{socket.gethostname()}:{os.getpid()}"
TEST_ENV = os.getenv("TEST_ENV", "FALSE").lower() in ("1", "true", "yes")
API_KEY = os.getenv("API_KEY", "invalid-key")
COMMISSION = float(os.getenv("COMMISSION", "0.0"))
PRUNE_EVERY_SEC = int(float(os.getenv("PRUNE_EVERY_MIN", "60")) * 60)
STALE_AFTER_SEC = int(float(os.getenv("STALE_AFTER_H", "24")) * 3600)
EXPIRE_AFTER_SEC = int(float(os.getenv("EXPIRE_AFTER_H", "24")) * 3600)
SANITY_CHECK_EVERY_SEC = int(float(os.getenv("SANITY_CHECK_EVERY_MIN", 5)) * 60)

REDIS_URL = (
    f"redis://:{VALKEY_PASSWORD}@{VALKEY_HOST}:{VALKEY_PORT}/0"
    if VALKEY_PASSWORD
    else f"redis://{VALKEY_HOST}:{VALKEY_PORT}/0"
)
ENGINE = start_engine(redis_url=REDIS_URL, commission=COMMISSION)

LOCK_KEY = "engine:leader"
LOCK_TTL = 30  # seconds


# auth dependency
async def verify_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(403, "Invalid API Key")


prod_depends = [] if TEST_ENV else [Depends(verify_key)]


# ───────────────────────────── FastAPI app ──────────────────────────── #
@asynccontextmanager
async def lifespan(app):
    # Run expiration check on startup
    expire_age = timedelta(seconds=EXPIRE_AFTER_SEC)
    ENGINE.expire_orders_older_than(age=expire_age).get()

    # Start background tasks
    logger.info(f"Starting background tasks - TICK_LOOP_SEC: {REFRESH_S}s, PRUNE_EVERY_SEC: {PRUNE_EVERY_SEC}s")
    tick_task = asyncio.create_task(tick_loop())
    prune_task = asyncio.create_task(prune_and_expire_loop())
    sanity_task = asyncio.create_task(sanity_loop())
    yield
    for t in (tick_task, prune_task, sanity_task):
        t.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await t


app = FastAPI(
    title="MockExchange API",
    version="0.3",
    description="A mock exchange API for testing purposes",
    docs_url=None if not TEST_ENV else "/docs",
    lifespan=lifespan,
    swagger_ui_parameters={
        "tryItOutEnabled": True,  # enable "Try it out" button
    },
)


# helper to unwrap futures ------------------------------------------------ #
def _g(x):
    # return x.get() if hasattr(x, "get") else x
    # Only unwrap actual Pykka futures, leave plain dict/list untouched
    return x.get() if isinstance(x, Future) else x


# ─────────────────────────────── endpoints ───────────────────────────── #
@app.get("/", include_in_schema=False)
def root():
    return {"service": "mockexchange-api", "version": app.version}


# market ----------------------------------------------------------------- #
@app.get("/tickers", tags=["Market"])
def all_tickers():
    return ENGINE.tickers.get()


@app.get("/tickers/{symbols:path}", tags=["Market"])
def ticker(symbols: str = "BTC/USDT"):
    """Return one ticker (str) or many tickers (comma-separated list).

    Examples
    --------
    GET /tickers/BTC/USDT
    GET /tickers/BTC/USDT,ETH/USDT,XRP/USDT
    """
    # split on ',' and strip whitespace
    requested = [s.strip() for s in symbols.split(",") if s.strip()]
    out: dict[str, dict] = {}
    # many symbols → aggregate, but don’t blow up if one is unknown
    for sym in requested:
        try:
            out[sym] = _g(ENGINE.fetch_ticker(sym))
        except ValueError as e:  # unknown or inactive symbol
            out[sym] = {"error": str(e)}
    return out


# portfolio -------------------------------------------------------------- #
@app.get("/balance", tags=["Portfolio"])
def balance():
    return _g(ENGINE.fetch_balance())


@app.get("/balance/list", tags=["Portfolio"])
def balance_list():
    asset_owned_list = _g(ENGINE.fetch_balance_list())
    return {"length": len(asset_owned_list), "assets": asset_owned_list}


@app.get("/balance/{asset}", tags=["Portfolio"])
def asset_balance(asset: str):
    return _g(ENGINE.fetch_balance(asset))


@app.post("/balance/{asset}/deposit", tags=["Portfolio"], dependencies=prod_depends)
def deposit_asset(req: FundReq, asset: str = CASH_ASSET):
    try:
        return _g(ENGINE.deposit_asset(asset, req.amount))
    except ValueError as e:
        # Turn any ValueError into a 400 Bad Request
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/balance/{asset}/withdrawal", tags=["Portfolio"], dependencies=prod_depends)
def withdraw_asset(req: FundReq, asset: str = CASH_ASSET):
    try:
        return _g(ENGINE.withdrawal_asset(asset, req.amount))
    except ValueError as e:
        # Turn any ValueError into a 400 Bad Request
        raise HTTPException(status_code=400, detail=str(e)) from e


# orders ----------------------------------------------------------------- #
@app.get("/orders", tags=["Orders"])
def list_orders(
    status: _ALL_STATUS | None = Query(None),
    symbol: str | None = None,
    side: _TRADING_SIDES | None = Query(None),
    tail: int | None = None,
    include_history: bool = Query(
        False, description="Include order history in response"
    ),
):
    orders = _g(
        ENGINE.order_book.get().list(
            status=status,
            symbol=symbol,
            side=side,
            tail=tail,
            include_history=include_history,
        )
    )
    return [o.to_dict(include_history=include_history) for o in orders]


@app.get("/orders/list", tags=["Orders"])
def list_orders_simple(
    status: _ALL_STATUS | None = Query(None),
    symbol: str | None = None,
    side: _TRADING_SIDES | None = Query(None),
    tail: int | None = None,
):
    orders = _g(
        ENGINE.order_book.get().list(status=status, symbol=symbol, side=side, tail=tail)
    )
    ids = [o.id for o in orders]
    return {"length": len(ids), "orders": ids}


@app.get("/orders/{oid}", tags=["Orders"])
def get_order(
    oid: str,
    include_history: bool = Query(
        False, description="Include order history in response"
    ),
):
    try:
        o = _g(ENGINE.order_book.get().get(oid, include_history=include_history))
        return o.to_dict(include_history=include_history)
    except ValueError as e:
        return {"error": str(e)}


@app.post("/orders", tags=["Orders"], dependencies=prod_depends)
def new_order(req: OrderReq):
    """
    Non-blocking for FastAPI: the call runs in the default thread-pool,
    `.get()` blocks only that worker, not the event loop.
    """
    try:
        return _g(ENGINE.create_order_async(**req.model_dump()))
    except ValueError as e:
        return {"error": str(e)}


@app.post("/orders/can_execute", tags=["Orders"])
def dry_run(req: OrderReq):
    return _g(
        ENGINE.can_execute(
            symbol=req.symbol,
            side=req.side,
            amount=req.amount,
            price=req.limit_price,
        )
    )


@app.post("/orders/{oid}/cancel", tags=["Orders"], dependencies=prod_depends)
def cancel(oid: str):
    try:
        return _g(ENGINE.cancel_order(oid))
    except ValueError as e:
        # 400 = client made a bad request (nothing wrong with the server)
        return {"error": str(e)}


# overview --------------------------------------------------------------- #
@app.get("/overview/capital", tags=["Overview"])
def get_summary_capital(
    aggregation: bool = Query(True, description="Portfolio aggregated capital")
):
    """
    Get a summary of all capital related amounts in the portfolio.
    - Current equity in the portfolio (free + used)
    - Total invested capital.
    - Total withdrawn funds.
    - Profit and Loss.
    """
    sum_capital = _g(ENGINE.get_summary_capital(aggregation=aggregation))
    # If aggregation is True, we return a single dict with all assets aggregated
    # If aggregation is False, we return a dict with each asset's capital separately
    return sum_capital


@app.get("/overview/assets", tags=["Overview"])
def get_summary_assets():
    sum_assets_bal = _g(ENGINE.get_summary_assets())
    return sum_assets_bal


@app.get("/overview/trades", tags=["Overview"])
def get_summary_trades(
    assets: str | None = Query(None),
    # assets: str | None = None,
    side: _TRADING_SIDES | None = Query(None),
):
    # turn "BTC,ETH" → ["BTC", "ETH"]; keep None if nothing supplied
    assets_list = (
        [s.strip() for s in assets.split(",") if s.strip()] if assets else None
    )
    sum_trades = _g(ENGINE.get_trade_stats(assets=assets_list, side=side))
    return sum_trades


# admin ------------------------------------------------------------------ #
@app.patch(
    "/admin/tickers/{ticker:path}/price", tags=["Admin"], dependencies=prod_depends
)
def patch_ticker_price(ticker: str, body: ModifyTickerReq):
    data = _g(
        ENGINE.set_ticker(
            symbol=ticker,
            price=body.price,
            bid_volume=body.bid_volume,
            ask_volume=body.ask_volume,
        )
    )
    _g(ENGINE.process_price_tick(ticker))
    return data


@app.patch("/admin/balance/{asset}", tags=["Admin"], dependencies=prod_depends)
def set_balance(asset: str, req: BalanceReq):
    return _g(ENGINE.set_balance(asset, free=req.free, used=req.used))


# @app.post("/admin/fund", tags=["Admin"], dependencies=prod_depends)
# def fund(req: FundReq):
#     return _g(ENGINE.fund_asset(req.asset, req.amount))

# @app.post("/admin/withdraw", tags=["Admin"], dependencies=prod_depends)
# def withdraw(req: WithdrawReq):
#     return _g(ENGINE.withdraw_asset(req.asset, req.amount))


@app.delete("/admin/data", tags=["Admin"], dependencies=prod_depends)
def purge_all():
    ENGINE.reset().get()
    return {"status": "ok"}


@app.get("/admin/health", tags=["Admin"])
def health():
    return {"status": "ok"}


# ─────────────────────── background tasks ────────────────────────────── #


def i_am_leader() -> bool:
    # atomic: SET key val NX EX ttl
    # returns True if lock acquired
    got = _r.set(LOCK_KEY, MY_ID, nx=True, ex=LOCK_TTL)
    if got:
        logger.debug(f"Acquired leader lock: {MY_ID}")
        return True
    # already held? renew if it's me
    current_leader = _r.get(LOCK_KEY)
    if current_leader == MY_ID:
        _r.expire(LOCK_KEY, LOCK_TTL)
        logger.debug(f"Renewed leader lock: {MY_ID}")
        return True
    logger.debug(f"Not leader. Current leader: {current_leader}, My ID: {MY_ID}")
    return False


async def tick_loop():
    while True:
        logger.debug(f"Tick loop started - REFRESH_S: {REFRESH_S} seconds")
        start_time = time.time()
        try:
            if i_am_leader():
                tickers = ENGINE.tickers.get()
                logger.debug(f"Found {len(tickers)} tickers to process")
                for t in tickers:
                    ENGINE.process_price_tick(t).get()
                # run every REFRESH_S seconds, so we don't hammer Redis
                logger.debug(f"Refreshed tickers data - processed {len(tickers)} tickers")
            else:
                logger.debug("Not the leader, skipping tick processing")
        except Exception as e:
            logger.exception("Error in tick_loop: %s", e)
            # If an error occurs, we log it and continue the loop
        finally:
            # As it is a matter of seconds, we can afford to skip 1 tick
            elapsed = time.time() - start_time
            await asyncio.sleep(max(1, REFRESH_S - elapsed))


async def prune_and_expire_loop():
    prune_age = timedelta(seconds=STALE_AFTER_SEC)
    expire_age = timedelta(seconds=EXPIRE_AFTER_SEC)
    while True:
        logger.debug(
            f"Prune and expire loop started - PRUNE_EVERY_SEC: {PRUNE_EVERY_SEC} seconds"
        )
        try:
            if i_am_leader():
                ENGINE.prune_orders_older_than(age=prune_age).get()
                ENGINE.expire_orders_older_than(age=expire_age).get()
        except Exception as e:
            logger.exception(f"Error in prune_and_expire_loop: {e}")
            # If an error occurs, we log it and continue the loop
        finally:
            # If an error occurs, we will miss one prune cycle.
            await asyncio.sleep(PRUNE_EVERY_SEC)


async def sanity_loop():
    while True:
        logger.debug(
            f"Sanity loop started - SANITY_CHECK_EVERY_SEC: {SANITY_CHECK_EVERY_SEC} seconds"
        )
        try:
            if i_am_leader():
                ENGINE.check_consistency().get()
        except Exception as e:
            logger.exception(f"Error in sanity_loop: {e}")
            # If an error occurs, we log it and continue the loop
        finally:
            # If an error occurs, we will miss one prune cycle.
            await asyncio.sleep(SANITY_CHECK_EVERY_SEC)
