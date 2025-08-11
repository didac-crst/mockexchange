# MockExchange Suite <!-- omit in toc -->

**_Trade without fear, greed, or actual money — because sometimes the best way to lose less is to not play at all._**

This repository contains the full **MockExchange** paper-trading platform:
- **MockX Engine** – Matching engine, portfolio tracking, and API layer.
- **MockX Periscope** – Streamlit-based dashboard for visualizing portfolio and orders.
- **MockX Oracle** – Price feed service (e.g., Binance via CCXT → Valkey).
- [*MockX Gateway** (external repo)](https://github.com/didac-crst/mockexchange-gateway) – Lightweight Python wrapper for the MockX Engine API, providing a ccxt-style interface for bots and scripts.

---

## 📑 Table of Contents <!-- omit in toc -->
- [TL;DR](#tldr)
- [📜 Story](#-story)
- [✨ Core Features](#-core-features)
- [🗺 Architecture \& Ecosystem](#-architecture--ecosystem)
- [📦 Packages in this Monorepo](#-packages-in-this-monorepo)
- [🚀 Quick Start](#-quick-start)
  - [Option 1: One-Command Setup (Recommended)](#option-1-one-command-setup-recommended)
  - [Option 2: Manual Setup](#option-2-manual-setup)
    - [0. Prepare Valkey (Redis)](#0-prepare-valkey-redis)
    - [1. Start MockX Oracle](#1-start-mockx-oracle)
    - [2. Start MockX Engine](#2-start-mockx-engine)
    - [3. Start MockX Periscope](#3-start-mockx-periscope)
  - [Development Setup](#development-setup)
  - [Individual Service Management](#individual-service-management)
  - [Common Use Cases](#common-use-cases)
- [🗂 Monorepo Structure](#-monorepo-structure)
- [📚 Documentation](#-documentation)
- [🪪 License](#-license)

---

## TL;DR

- Stateless, deterministic, no-risk spot-exchange emulator.
- ccxt-compatible API — test bots without touching live markets.
- Externalized price feed (MockX Oracle) so you can swap sources.
- Companion Streamlit dashboard (MockX Periscope) for monitoring.
- Full CLI + REST API + Docker support.

---

## 📜 Story

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

## ✨ Core Features

- 🧩 **Modular architecture** — Engine, Periscope, Oracle, and Gateway can run independently or together.
- 🔌 **Pluggable components** — swap price feeds, dashboards, or clients without touching the core.
- 🌐 **ccxt-inspired interface** — follows familiar trading API patterns to simplify bot integration.
- 📊 **Full visibility** — Periscope dashboard for live monitoring of balances, orders, and performance metrics.
- 🔮 **Realistic market simulation** — Oracle injects live exchange prices into a safe, risk-free trading environment.
- 🚀 **Ready for production** — Dockerized services, path-filtered CI, and clear interface boundaries.
- 🛠 **Developer-friendly** — One-command setup, pre-commit hooks, comprehensive testing, and linting.

---

## 🗺 Architecture & Ecosystem

```mermaid
flowchart TB
    subgraph Clients
        periscope["MockX Periscope<br/>(Streamlit UI)"]
        bot["Trading Bot / Script"]
    end

    subgraph Infra
        redis[("Valkey / Redis")]
        engine["MockX Engine 📈"]
    end

    subgraph External
        binance["Binance (Live Market Data)"]
    end

    bot -->|ccxt-like wrapper| gateway["MockX Gateway 🛡 (external)"]
    periscope -->|HTTP/REST| engine
    gateway -->|HTTP/REST| engine

    engine --> redis

    oracle["MockX Oracle 🔮<br/>(ccxt → Redis)"] --> redis
    binance -->|ccxt| oracle
```

---

## 📦 Packages in this Monorepo

| Package             | Path                  | Description                                                  | README                                           |
| ------------------- | --------------------- | ------------------------------------------------------------ | ------------------------------------------------ |
| **MockX Engine**    | `packages/engine/`    | Core engine, order-matching, balances, API layer, CLI tools. | [Engine README](packages/engine/README.md)       |
| **MockX Periscope** | `packages/periscope/` | Streamlit dashboard for portfolio and orders.                | [Periscope README](packages/periscope/README.md) |
| **MockX Oracle**    | `packages/oracle/`    | Market data feeder (ccxt → Valkey/Redis).                    | [Oracle README](packages/oracle/README.md)       |

Related (external):
- **MockX Gateway** – https://github.com/didac-crst/mockexchange-gateway  
    Minimal ccxt-style Python client to interact with the Engine API (install via `pip` or `poetry`).

---

## 🚀 Quick Start

### Option 1: One-Command Setup (Recommended)
Start everything with a single command:
```bash
make start
```

This launches:
- **Valkey** (Redis fork) on port 6379
- **MockX Oracle** (price feed) 
- **MockX Engine** (API) on port 8000
- **MockX Periscope** (dashboard) on port 8501

Access your services:
- **API**: http://localhost:8000
- **Dashboard**: http://localhost:8501
- **Logs**: `make logs`

### Option 2: Manual Setup
If you prefer to run services individually:

#### 0. Prepare Valkey (Redis)
```bash
docker run -d --name mockx-valkey \
            -p 6379:6379 \
            valkey/valkey \
            --requirepass "SuperSecretPass"
```

#### 1. Start MockX Oracle
```bash
cd packages/oracle
docker compose up --build
```

#### 2. Start MockX Engine
```bash
cd packages/engine
docker compose up --build
```

#### 3. Start MockX Periscope
```bash
cd packages/periscope
docker compose up --build
```

### Development Setup
For contributors and developers:

```bash
# Install dependencies and dev tools
make dev

# Run tests
make test

# Format code
make format

# Check code quality
make lint
```

### Individual Service Management
You can also manage services individually:

```bash
# Start specific services
make start-engine      # Start only the engine
make start-oracle      # Start only the oracle  
make start-periscope   # Start only the dashboard

# Stop specific services
make stop-engine       # Stop only the engine
make stop-oracle       # Stop only the oracle
make stop-periscope    # Stop only the dashboard

# Restart specific services
make restart-engine    # Restart only the engine
make restart-oracle    # Restart only the oracle
make restart-periscope # Restart only the dashboard

# View logs for specific services
make logs-engine       # Engine logs only
make logs-oracle       # Oracle logs only
make logs-periscope    # Dashboard logs only

# Check service status
make status            # Show all service statuses
```

### Common Use Cases

```bash
# Development workflow
make start-oracle      # Start price feed first
make start-engine      # Then start the API
make logs-engine       # Monitor engine logs
make restart-engine    # Restart after code changes

# Debugging specific services
make logs-oracle       # Check if price feed is working
make restart-periscope # Restart dashboard if UI is stuck
make status            # See which services are running

# Selective deployment
make start-engine make start-periscope  # Skip oracle if using external data
```

---

## 🗂 Monorepo Structure
```text
mockexchange/
├── packages/
│   ├── engine/        # MockX Engine (core API & matching)
│   ├── periscope/     # MockX Periscope (dashboard)
│   └── oracle/        # MockX Oracle (price feeds)
├── .github/workflows/ # CI/CD pipelines
├── docker-compose.yml # Full stack orchestration
├── Makefile          # Development commands
├── pyproject.toml    # Root workspace config
├── .pre-commit-config.yaml # Code quality hooks
└── README.md         # This file
```

---

## 📚 Documentation

- [Engine README](packages/engine/README.md)
- [Periscope README](packages/periscope/README.md)
- [Oracle README](packages/oracle/README.md)
- [MockX Gateway](https://github.com/didac-crst/mockexchange-gateway)

---

## 🪪 License

MIT License – see the licenses inside each package.

> **Don’t risk real money.**  
> Spin up MockExchange, hammer it with tests, then hit live markets only when your algos are solid.