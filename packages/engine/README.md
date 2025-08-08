# MockExchange API 📈

**_Trade without fear, greed, or actual money — because sometimes the best way to lose less is to not play at all._**

---

## Table of Contents

- [TL;DR](#tldr)
- [The Story](#the-story)
- [Core Features](#core-features)
- [Quick Start (Docker)](#quick-start-docker)
- [Environment Variables](#environment-variables-complete)
- [Authentication](#authentication)
- [REST Endpoints](#rest-endpoints)
- [Example Workflow](#example-workflow)
- [Tick-loop Internals](#tick-loop-internals)
- [Installation (from source)](#installation-from-source)
- [Using the CLI (`mockx`)](#using-the-cli-mockx)
- [Running the Test-suite](#running-the-test-suite-)
- [Dry Run Example](#dry-run-example-)
- [Repo Layout](#repo-layout-updated-2025-07)
- [Development Notes](#development-notes)
- [Front-end Dashboard](#front-end-dashboard)
- [Gateway](#gateway)
- [Contributing](#contributing)
- [License](#license-)

---

## TL;DR

- Want to test your trading bot **without risk**?
- MockExchange simulates a full ccxt-compatible exchange — but runs entirely in memory.
- Plug in market data, issue orders, get fills.
- No real assets involved.
- Backtests, dry runs, live testing (safely).

---

## The Story

> It was **2013**, and Bitcoin had just hit a jaw-dropping **$300**.  
> Someone in our old engineering WhatsApp group brought it up.  
> I asked innocently, *“What’s that?”*  
>  
> The response came instantly, dripping with confidence:  
> *“You’re too late — this bubble is about to burst…”*  
>  
> Which, in hindsight, was probably the most confidently
> wrong (and overly cautious) financial advice I’ve ever received.

But something about it intrigued me. I didn’t fully understand it.  
I didn’t even think it would work — and yet, I bought in.  
Just **2/3 of a BTC**, about **180 €**, which, at the time, I mentally wrote off as *“money I’ll never see again.”*  
Spoiler: it was the **best terrible financial decision** I’ve ever made.

I held.  
And held.  
And held some more.

Then came **2017** — the year of Lambos, moon memes, and FOMO-induced insomnia.  
I began checking prices at night before bed, and again first thing in the morning —
not for fun, but to confirm whether I was now rich… or still stuck working 9 to 5.

This, of course, led me to the **classic rookie move**: diversification.  
I dove into altcoins with names like **LTC**, **TROY**, and others I’ve repressed like a bad haircut from high school.  
Let’s just say: they didn’t go to the moon — they dug a tunnel.

Decision after decision, I watched my gains **evaporate in slow motion**.  
Eventually, I realized I needed support — not from a financial advisor (they’d only
remind me of my poor decisions), but from something more aligned with my goals — not theirs.

**Something logical**.  
Emotionless.  
Free from fear and greed.  
Unimpressed by sudden price spikes or Twitter hype.  
A system that won’t panic sell or chase pumps.

I wanted an intelligent system that could make decisions based on **data**, not **dopamine**.  
Something that would just execute the plan, no matter how boring or unsexy that plan was.  
Something more disciplined than I’d ever been — able to stay locked on a single task for hours, without fatigue, distraction, or the urge to check the news.

In short, I wanted to build a **trader with no feelings** —
like a **psychopath**, but helpful.

So in **2020**, full of optimism and free time, I enrolled in an **AI-for-trading** program.  
I was ready to automate the pain away.

Then… I became a dad.

Suddenly, my trading ambitions were replaced with diapers, sleep deprivation,
and learning the fine art of **negotiating with toddlers**.  
Needless to say, the bot went on standby — alongside my hobbies, ambitions, and most adult-level reasoning.

Fast forward to **2024**. The kids sleep (sometimes), and my curiosity roared back to life.  
I decided it was time to build — **for real**.  
Not to get rich — but because this is what I do for fun:
connect dots, explore computer science, study markets, and challenge my past self
with fewer emotional trades and more intelligent systems.

But ideas need hardware.  
So I bought my first Raspberry Pi.  
Because if I was going to burn time, I wasn’t about to burn kilowatts.  
I needed something that could run 24/7 without turning my electricity bill into a second mortgage.  
Resilient, quiet, efficient — like a monk with a TPU, ready to meditate on market patterns in silence for as long as it takes.  
It wasn’t much, but it was enough to get started.

From there, the system began to grow — and spiral.  
Scraping prices in real time, keeping databases efficient, aggregating data, archiving old data,
writing little scripts that somehow become immortal zombie processes needing to be killed by hand...  
I genuinely didn’t expect it to be so much.

And yet — I like it.  
This is how I relax: designing systems no one asked for, solving problems I created myself,  
and picking up strange new skills in the process — the kind you never set out to learn, but somehow end up mastering.

Which brings us to **2025**, and **MockExchange**:  
a stateless, deterministic, no-risk spot-exchange emulator that speaks fluent **ccxt**,
pretends it’s real, and stores the last price-tick, balance and order in **Valkey** (aka Redis) —
instead of touching live markets — so you can test, dry-run, and debug your bot
without risking a single satoshi.

No more fear.  
No more “should I have bought?” or “why did I sell?”  
Just logic, fake orders, and enough tooling to safely build the thing
that trades smarter than I did.

---

## Core Features

* **One binary, three faces**  
    * 🐍 Import as a normal Python package in your back-tests.  
    * 🐳 Run as a Docker container exposing a FastAPI server.  
    * 💻 Fire quick commands via the bundled CLI.  
* **Deterministic & Stateless** — wipe everything with one `POST /admin/reset`.  
* **Pluggable data-feed** — point the engine to any key-value store that writes `sym_<SYMBOL>` → *last price* and the tick-loop does the rest.  
* **Consistent commission model** — flat `COMMISSION` rate applied on every fill.  

---  

## Quick start (Docker)  

> **Prerequisite** : an accessible **Valkey** instance is mandatory.  
> The commands below launch one locally; set `REDIS_URL` if you already run Valkey elsewhere.  

```bash
# 1  Start Valkey (persist to ./data)
docker run -d --name valkey -p 6379:6379 \
    -v "$(pwd)"/data:/data valkey/valkey:latest

# 2  Boot the API in front of it (auth enabled)
docker run -d --name mockexchange-api --network host \
    -e API_KEY=my-secret \
    ghcr.io/your-org/mockexchange-api:latest

# 3  Open docs (only if TEST_ENV=true)
xdg-open http://localhost:8000/docs     # or "open" on macOS
```  

### Using docker-compose for Valkey Docker

```yaml
# docker-compose.yml
services:
  valkey-tradingbot-cache:
    image: valkey/valkey:latest
    container_name: valkey-cryptobot-cache
    network_mode: "host"
    restart: always
    volumes:
      - valkey_data:/data
    # Save a snapshot every 60 s if ≥ 1 write; keep an AOF as well
    command: ["valkey-server", "--save", "60", "1", "--appendonly", "yes"]

volumes:
  valkey_data:
```  

Bring Valkey up with: `docker compose up -d valkey-tradingbot-cache`  
then start **MockExchange** as shown above.  

---  

## Environment variables (complete)  

| Var | Default (dev) | Purpose / Notes |
|-----|---------------|-----------------|
| `API_URL`	| `http://localhost:8000` |	Base‑URL the CLI (and integration tests) call. |
| `API_TIMEOUT_SEC` |	`10` | Per‑request timeout used by the CLI’s httpx client. |
| `API_KEY` | `invalid-key` | Required header value for **every** request (`x-api-key`). |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Where Valkey lives. |
| `CASH_ASSET` | `USDT` | The “cash” currency used by the engine when computing PnL / fees. |
| `COMMISSION` | `0.00075` | Fee rate (0.075 %). |
| `TEST_ENV` | `false` | `true` disables auth **and** re-enables `/docs`; tests set this to `True`. |
| `TICK_LOOP_SEC` | `30` | Scan interval for the background price-tick loop (seconds). |
| `PRUNE_EVERY_MIN` | `60` | How often the prune job runs (minutes). `0` disables automatic pruning. |
| `STALE_AFTER_H` | `24` | Age threshold for permanent deletion of *filled* / *canceled* / *partially_canceled* / *expired* / *rejected* orders (hours). |
| `EXPIRE_AFTER_H` | `24` | Age threshold for non-traded "OPEN" orders  *new* / *partially_filled* orders (hours). |
| `MIN_TIME_ANSWER_ORDER_MARKET` | `3` | Lower bound for artificial latency (seconds) before a market order is filled. |
| `MAX_TIME_ANSWER_ORDER_MARKET` | `5` | Upper bound for the artificial latency. |
| `SIGMA_FILL_MARKET_ORDER` | `0.1` | Standard‑deviation parameter that controls the random partial‑fill ratio for simulated market orders – higher values mean more variability and a greater chance of partial fills. |

### `.env` template  

A ready-to-use template lives at **`.env.example`**. Copy it and tweak as needed:  

```bash
cp .env.example .env
```  

```dotenv
# .env
API_URL=http://localhost:8000
API_TIMEOUT_SEC=10
API_KEY="your-super-secret-key"
REDIS_URL=redis://127.0.0.1:6379/0
CASH_ASSET=USDT
COMMISSION=0.00075
TEST_ENV=True
TICK_LOOP_SEC=30
PRUNE_EVERY_MIN=60
STALE_AFTER_H=24
EXPIRE_AFTER_H=24
MIN_TIME_ANSWER_ORDER_MARKET=3
MAX_TIME_ANSWER_ORDER_MARKET=5
SIGMA_FILL_MARKET_ORDER=0.1
URL_API=https://mockexchange.your-domain.com/
```  

> **Tip :** set `TEST_ENV=true` in CI so Postman or integration tests don’t need the header.  

---  

## Authentication  

Production containers reject any request that doesn’t include the correct key:  

```http
x-api-key: my-secret
```  

Set the header once at *collection* level in Postman or use `curl -H "x-api-key:$API_KEY" …`.  

---  

Below is an updated **REST Endpoints** section that mirrors exactly what’s in `server.py` today.
Feel free to drop-in replace the old table in the README.

## REST Endpoints

| Method | Path                                           | Description                                                                            |
| ------ | ---------------------------------------------- | -------------------------------------------------------------------------------------- |
| **GET** | `/tickers`                                    | List all symbols currently cached.                                                     |
| **GET** | `/tickers/{symbol}`                           | Latest ticker for one symbol (`BTC/USDT`).                                             |
| **GET** | `/balance`                                    | Full portfolio snapshot.                                                               |
| **GET** | `/balance/list`                               | Number of assets and list of them.                                                     |
| **GET** | `/balance/{asset}`                            | Balance row for `BTC`, `USDT`, …                                                       |
| **GET** | `/orders`                                     | List orders — filters: `status`, `symbol`, `side`, `tail`.                             |
| **GET** | `/orders/list`                                | Number of orders and oid- filters: `status`, `symbol`, `side`, `tail`.                 |
| **GET** | `/orders/{oid}`                               | Inspect a single order.                                                                |
| **POST** | `/orders`                                    | Create *market* or *limit* order.                                                      |
| **POST** | `/orders/can_execute`                        | Dry-run: check if there’s enough balance for the order.                                |
| **POST** | `/orders/{oid}/cancel`                       | Cancel an *OPEN* order (`new` / `partially_filled`)                                    |
| **GET** | `/overview/assets`                            | Overview on total balances, frozen assets on open orders and mismatches between them.  |
| **PATCH** | `/admin/tickers/{symbol}/price`             | Manually patch a ticker’s last-price (plus optional volumes).                          |
| **PATCH** | `/admin/balance/{asset}`                    | Overwrite or create a balance row (`free`, `used`).                                    |
| **POST** | `/admin/fund`                                | Credit an asset’s `free` column (quick top-up).                                        |
| **DELETE** | `/admin/data`                              | Wipe **all** balances *and* orders (clean slate).                                      |
| **GET** | `/admin/healthz` *(not in schema)*            | Simple health probe (`{"status":"ok"}`).                                               |


---  

## Example workflow  

```bash
# Fund the account with 100 000 USDT
auth='-H "x-api-key:my-secret"'
curl -X POST $auth -H "Content-Type: application/json" \
    -d '{"asset":"USDT","amount":100000}' \
    http://localhost:8000/admin/fund

# Get initial balance
curl $auth http://localhost:8000/balance

# Dry-run a 0.05 BTC market buy
data='{"symbol":"BTC/USDT","side":"buy","amount":0.05}'
curl -X POST $auth -H "Content-Type: application/json" \
    -d "$data" http://localhost:8000/orders/can_execute

# Execute the order for real
curl -X POST $auth -H "Content-Type: application/json" \
    -d "$data" http://localhost:8000/orders
```  

---  

## Tick-loop internals  

A background coroutine scans Valkey for keys matching `sym_*`, feeds the latest price into `ExchangeEngine.process_price_tick(symbol)` and settles any limit orders that crossed. Interval is `TICK_LOOP_SEC` seconds (default **10 s**).  

### Feeding live prices  

MockExchange is agnostic about **where** prices come from; it simply expects a hash per symbol with these fields:

  | field       | example value |
  |-------------|---------------|
  | `price`     | `117800.01`   |
  | `timestamp` | `1752853159.996` |
  | `bid`       | `117800.00`   |
  | `ask`       | `117800.01`   |
  | `bidVolume` | `0.05537`     |
  | `askVolume` | `8.91369`     |
  | `symbol`    | `BTC/USDT`    |

`HSET sym_BTC/USDT price 117800.01 timestamp 752853159.996 bid ...`

The reference feeder we use in production is a 40-line script that:  

1. Pulls fresh tickers from **Binance** via **CCXT** every 10 s.  
2. For each symbol it writes a Valkey hash at the key `sym_<SYMBOL>`.

Any mechanism that follows the same convention works (Kafka consumer, WebSocket stream, another exchange, etc.).

---  

## Installation (from source)  

1. **Install Poetry** (one-liner below, or follow the [official docs](https://python-poetry.org/docs/#installation)):  

    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    # or with pipx:
    pipx install poetry
    ```  

2. Clone & install dev-deps:  

    ```bash
    git clone https://github.com/your-org/mockexchange-api.git
    cd mockexchange-api
    poetry install --with dev      # core + tests + linters
    ```

---  

## Using the CLI (`mockx`)

The image (and any `pip/poetry` install) ships a thin command‑line helper called **`mockx`**.
It talks to the API over HTTP, so you can run it from **your host** or **inside the container** as long as:

* `API_URL` points at the FastAPI service (default `http://localhost:8000`)
* `API_KEY` is set when `TEST_ENV=false`
* `API_TIMEOUT_SEC` sets the per‑request timeout (default `10` s)

```bash
# host shell – example
export API_URL=http://localhost:8000
export API_KEY=my-secret

mockx balance                 # full portfolio
mockx ticker BTC/USDT         # latest price snapshot
```

### Command reference

| CLI | Maps to REST | What it does |
|-----|--------------|--------------|
| `mockx balance` | `GET /balance` | Dump every asset row. |
| `mockx ticker <SYM>` | `GET /tickers/<SYM>` | Latest ticker (comma list allowed). |
| `mockx order <SYM> <buy\|sell> <qty> [--type limit] [--price P]` | `POST /orders` | Create market/limit order. |
| `mockx cancel <OID>` | `POST /orders/{oid}/cancel` | Cancel an **OPEN** order. |
| `mockx orders [...]` | `GET /orders` | List orders (`--status`, `--symbol`, …). |
| `mockx order-get <OID>` | `GET /orders/{oid}` | Inspect one order. |
| `mockx orders-simple` | `GET /orders/list` | Count + OID list. |
| `mockx can-exec <SYM> <buy\|sell> <qty> [--price P]` | `POST /orders/can_execute` | Dry‑run balance check. |
| `mockx fund <ASSET> <AMOUNT>` | `POST /admin/fund` | Quick top‑up (admin). |
| `mockx set-balance <ASSET> --free F --used U` | `PATCH /admin/balance/{asset}` | Overwrite a balance row. |
| `mockx set-price <SYM> <P> [--bid-volume V] [--ask-volume V]` | `PATCH /admin/tickers/{sym}/price` | Force last‑price & volumes. |
| `mockx reset-data` | `DELETE /admin/data` | Wipe **all** balances + orders. |
| `mockx health` | `GET /admin/health` | Simple health probe. |

> `mockx -h` and `mockx <sub‑command> -h` print the same information on the CLI.

### Quick demo inside the running container

```bash
docker exec -it mockexchange-api bash

# Inside the docker
mockx reset-data
mockx fund USDT 100000
mockx order BTC/USDT buy 0.05
mockx orders --status filled
```

---

## Running the test-suite 🧪  

We ship a full integration suite that spins up a **temporary Valkey** (no persistence, no AOF) and hammers the API in-process and over HTTP.  

*Run everything:*  

```bash
poetry run pytest -q
```  

*Run one high-traffic test (100 buy + 100 sell concurrent market orders):*  

```bash
poetry run pytest src/tests/test_03_market_orders_concurrent.py -vv
```  

Useful flags:  

* `--lf` to re-run only the last failures.  

> **Note :** tests assume `URL_API=http://localhost:8000` — override if you point to a remote instance.  

---

## Dry Run Example 🚀  

After validating with tests, run a continuous Dockerized dry run to simulate random orders (no strategy), which will cause portfolio value erosion over time 📉.  
See the detailed [dry run README](examples/dry_run/README.md) for setup, tunable parameters, and usage.

---

## Repo layout (updated 2025-07)  

```text
mockexchange-api/
├── Dockerfile                   ← Uvicorn + Poetry export
├── docker-compose.yml           ← Convenience wrapper (host-network)
├── README.md                    ← You’re here
├── pyproject.toml               ← Poetry deps & build meta
├── start_mockexchange.sh        ← Quick dev helpers
├── stop_mockexchange.sh
├── logs_mockexchange.sh
├── src/
│   ├── mockexchange/            ← Core engine (stateless library)
│   │   ├── __init__.py          ← Re-exports Engine, version, …
│   │   ├── engine.py            ← Order flow & matching
│   │   ├── market.py            ← Ticker facade
│   │   ├── portfolio.py         ← Balances
│   │   ├── orderbook.py         ← Orders & fills
│   │   ├── _types.py            ← Enums & dataclasses
│   │   └── logging_config.py    ← Centralised logging setup
│   ├── mockexchange_api/        ← API layer & CLI
│   │   ├── __init__.py
│   │   ├── server.py            ← FastAPI app (`mockexchange_api.server:app`)
│   │   └── cli.py               ← Thin command-line helper
│   └── tests/                   ← Pytest suite (unit + integration)
│       ├── conftest.py
│       ├── helpers.py
│       └── test_*               ← 01-05 & cover reset → cancel flow; also cli
└── LICENSE
```  

---  

## Development notes  

* Unit-tests boot a throw-away Valkey with  
  `valkey-server --save '' --appendonly no --port 0` (**random port**).  
* Market data is whatever you drop into hashes:  
  `HSET sym_BTC/USDT price 56000 timestamp $(date +%s)`.  
* Commission is read from `COMMISSION` env (default `0.00075` = 0.075 %).  
* Code style: **Black** & **Ruff** (`poetry run ruff check .`) — run `ruff format .` to auto-fix.  
* Static typing: **MyPy** (`poetry run mypy src/mockexchange`).  

---

## Front‑end dashboard

If you prefer a GUI, check the companion repo [**mockexchange‑deck**](https://github.com/didac-crst/mockexchange-deck).

It’s a single‑user Streamlit dashboard that shows your balances and existing orders.

---

## Gateway

If your scripts need a CCXT-like interface to talk to mockexchange-api, [**mockexchange‑gateway**](https://github.com/didac-crst/mockexchange-gateway) has you covered:
* Market data, balances, order lifecycle, dry-run
* Minimal surface — logic stays server-side, so your code remains swappable with real exchanges

---  

## Contributing  

Pull-requests, feature ideas and bug reports are welcome!  
Please run `ruff check .`, `ruff format .` and `pytest` before opening a PR.  

---  

## License 🪪  

This project is released under the MIT License — see [`LICENSE`](LICENSE) for details.  

> **Don’t risk real money.**  Spin up MockExchange, hammer it with tests, then hit the real markets only when your algos are solid.