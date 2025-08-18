# MockExchange Suite <!-- omit in toc -->

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-available-blue.svg)](https://www.docker.com/)
[![Poetry](https://img.shields.io/badge/poetry-managed-orange.svg)](https://python-poetry.org/)
[![Tests](https://img.shields.io/badge/tests-available-green.svg)](https://github.com/didac-crst/mockexchange)
[![Status](https://img.shields.io/badge/status-active-success.svg)](https://github.com/didac-crst/mockexchange)
[![Code Quality](https://img.shields.io/badge/code%20quality-maintained-blue.svg)](https://github.com/didac-crst/mockexchange)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: ruff](https://img.shields.io/badge/linting-ruff-red.svg)](https://github.com/astral-sh/ruff)
[![Type checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](https://mypy-lang.org/)

**_Trade without fear, greed, or actual money — because every fake loss is a real step up._**

This repository contains the full **MockExchange** paper-trading platform:
- **MockX Engine** – Matching engine, portfolio tracking, and API layer.
- **MockX Periscope** – Streamlit-based dashboard for visualizing portfolio and orders.
- **MockX Oracle** – Price feed service (e.g., Binance via CCXT → Valkey).
- [*MockX Gateway** (external repo)](https://github.com/didac-crst/mockexchange-gateway) – Lightweight Python wrapper for the MockX Engine API, providing a ccxt-style interface for bots and scripts.

---

## Table of Contents <!-- omit in toc -->

- [TL;DR](#tldr)
- [📜 Story](#-story)
- [✨ Core Features](#-core-features)
- [🗺 Architecture & Ecosystem](#-architecture--ecosystem)
- [📦 Packages in this Monorepo](#-packages-in-this-monorepo)
- [🚀 Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [1. Clone and Setup](#1-clone-and-setup)
  - [2. Start All Services](#2-start-all-services)
  - [3. Access Your Services](#3-access-your-services)
  - [Alternative: Manual Service Management](#alternative-manual-service-management)
  - [Development Setup](#development-setup)
- [🚀 Release Management](#-release-management)
  - [**Quick Release Commands**](#quick-release-commands)
  - [**Makefile Release Commands**](#makefile-release-commands)
  - [**Deploying Versioned Releases**](#deploying-versioned-releases)
  - [**Release Process**](#release-process)
  - [**Docker Image Tags**](#docker-image-tags)
  - [**Release Workflow**](#release-workflow)
  - [**Version Management**](#version-management)
- [📚 Examples](#-examples)
  - [Common Use Cases](#common-use-cases)
  - [Order Generator](#order-generator)
- [🔧 Environment Configuration](#-environment-configuration)
  - [Quick Setup](#quick-setup)
  - [Key Configuration Sections](#key-configuration-sections)
    - [**Valkey (Database)**](#valkey-database)
    - [**Oracle (Price Feeds)**](#oracle-price-feeds)
    - [**Engine (API)**](#engine-api)
    - [**Periscope (Dashboard)**](#periscope-dashboard)
  - [Benefits of Centralized Configuration](#benefits-of-centralized-configuration)
- [🗂 Monorepo Structure](#-monorepo-structure)
- [📚 Documentation](#-documentation)
  - [**Core Documentation**](#core-documentation)
  - [**Project Documentation**](#project-documentation)
  - [**External Resources**](#external-resources)
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
- 🚀 **Ready for production** — Dockerized services with pinned versions, path-filtered CI, and clear interface boundaries.
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

| Package             | Path                  | Description                                       | README                                           |
| ------------------- | --------------------- | ------------------------------------------------- | ------------------------------------------------ |
| **MockX Valkey**    | `packages/valkey/`    | Redis-compatible database for data persistence.   | [Valkey README](packages/valkey/README.md)       |
| **MockX Oracle**    | `packages/oracle/`    | Market data feeder (ccxt → Valkey/Redis).         | [Oracle README](packages/oracle/README.md)       |
| **MockX Engine**    | `packages/engine/`    | Core engine (core/), API layer (api/), CLI tools. | [Engine README](packages/engine/README.md)       |
| **MockX Periscope** | `packages/periscope/` | Streamlit dashboard for portfolio and orders.     | [Periscope README](packages/periscope/README.md) |

Related (external):
- **MockX Gateway** – https://github.com/didac-crst/mockexchange-gateway  
    Minimal ccxt-style Python client to interact with the Engine API (install via `pip` or `poetry`).

---

## 🚀 Quick Start

### Prerequisites
- **Docker** and **Docker Compose** installed
- **Git** for cloning the repository

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/your-username/mockexchange.git
cd mockexchange

# Setup environment (first time only)
cp .env.example .env
# Edit .env if needed (defaults work for most cases)
```

### 2. Start All Services
```bash
# One command to start everything
make start
```

**What this launches:**
- **MockX Valkey** (Redis-compatible database) on port 6379
- **MockX Oracle** (price feed service) 
- **MockX Engine** (trading API) on port 8000
- **MockX Periscope** (dashboard) on port 8501

### 3. Access Your Services
- **📊 Dashboard**: http://localhost:8501
- **🔌 API**: http://localhost:8000
- **📖 API Docs**: http://localhost:8000/docs
- **📋 Logs**: `make logs`

### Alternative: Manual Service Management
If you prefer to start services individually:

```bash
# Start services in order (recommended)
make start-valkey      # Database first
make start-oracle      # Price feed
make start-engine      # Trading API
make start-periscope   # Dashboard

# Or stop/restart individual services
make stop-engine       # Stop only the API
make restart-oracle    # Restart price feed
make logs-periscope    # View dashboard logs
```

### Development Setup
For contributors and developers:

```bash
# Install development dependencies
make dev

# Run all tests
make test

# Format and lint code
make format
make lint

# Check service status
make status

# Release management
make release-branch    # Create release branch (interactive)
make version          # Show current version and tags
```
make logs-valkey       # Database logs only
make logs-engine       # Engine logs only
make logs-oracle       # Oracle logs only
make logs-periscope    # Dashboard logs only

# Check service status
make status            # Show all service statuses

## 🚀 How we ship

### Standard Workflow (Recommended)
1. Create a feature branch, implement changes.
2. Open a Pull Request (PR). CI runs tests and lint.
3. When green, merge into `main`.
4. **Create a release**:
   - **GitHub UI** (Recommended): **Releases** → *Draft a new release* → Tag `vX.Y.Z` → Publish
   - **CLI**: 
     ```bash
     git checkout main && git pull --ff-only
     git tag -a vX.Y.Z -m "MockExchange vX.Y.Z"
     git push origin vX.Y.Z
     ```

CI will run on the tag to validate the release commit.

### Release Branch Workflow (For Complex Releases)
For more control or when you need to freeze changes for QA/testing:

1. Create feature branch → implement changes
2. Open PR → CI runs tests
3. **Create release branch** (automated):
   ```bash
   # Interactive mode (recommended)
   make release-branch
   
   # Direct mode
   ./scripts/create-release-branch.sh patch    # 0.1.0 → 0.1.1
   ./scripts/create-release-branch.sh minor    # 0.1.0 → 0.2.0
   ./scripts/create-release-branch.sh major    # 0.1.0 → 1.0.0
   
   # Preview what would happen
   ./scripts/create-release-branch.sh patch --dry-run
   ```
4. **Tag the release branch**: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
5. **Push tag**: `git push origin vX.Y.Z`
6. **Merge to main** after release is validated

### Release Branch Script Features

The `scripts/create-release-branch.sh` script provides:

- **🔄 Automatic version calculation** - Fetches latest tags and calculates next version
- **✅ Git validation** - Checks branch, working directory, and remote sync
- **🛡️ Safety features** - Dry-run mode, confirmations, error handling
- **🎨 User-friendly** - Colored output, clear instructions, help text
- **📋 Next steps** - Shows what to do after branch creation

**Requirements:**
- Must be on `main` branch (or confirm override)
- Working directory must be clean
- Remote tags must be up to date

**Examples:**
```bash
# See what would happen
./scripts/create-release-branch.sh patch --dry-run

# Create a patch release branch
./scripts/create-release-branch.sh patch

# Interactive mode with menu
make release-branch
```

### Quick Reference: Common Release Commands

```bash
# Check current version and tags
make version

# Create release branch (interactive)
make release-branch

# Create release branch (direct)
./scripts/create-release-branch.sh patch

# Create and push a tag
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin v0.1.1

# Deploy specific version
VERSION=v0.1.1 docker-compose up -d
```

### When to use Release Branches

Use a release branch when you need to:
- **Freeze changes** for QA/testing while `main` continues development
- **Cherry-pick hotfixes** onto a stable release candidate
- **Maintain multiple release lines** (e.g., v1.x and v2.x simultaneously)

**Default workflow**: Tag directly on `main` for simplicity.

## 📦 Install from GitHub tags

You can install any service directly from a Git tag:

**Oracle**
```bash
pip install "git+https://github.com/didac-crst/mockexchange.git@vX.Y.Z#subdirectory=packages/oracle"
```

**Engine**
```bash
pip install "git+https://github.com/didac-crst/mockexchange.git@vX.Y.Z#subdirectory=packages/engine"
```

**Periscope**
```bash
pip install "git+https://github.com/didac-crst/mockexchange.git@vX.Y.Z#subdirectory=packages/periscope"
```

Alternatively, clone at a tag and install with Poetry inside each package:

```bash
git clone --depth 1 --branch vX.Y.Z git@github.com:didac-crst/mockexchange.git
cd mockexchange/packages/engine && poetry install
```

### Common Use Cases

```bash
# Development workflow
make start-valkey      # Start database first
make start-oracle      # Start price feed
make start-engine      # Then start the API
make logs-engine       # Monitor engine logs
make restart-engine    # Restart after code changes

# Debugging specific services
make logs-valkey       # Check database connectivity
make logs-oracle       # Check if price feed is working
make restart-periscope # Restart dashboard if UI is stuck
make status            # See which services are running

# Selective deployment
make start-valkey make start-engine make start-periscope  # Skip oracle if using external data
```

---

## 📚 Examples

The `examples/` directory contains tools and examples that demonstrate how to use the MockExchange platform.

### Order Generator

A Dockerized tool that generates random orders to test your MockExchange instance:

```bash
# Show available examples
make examples

# Start the order generator (fresh start with reset)
make order-generator

# Continue without reset
make order-generator-restart

# Continue with reset
make order-generator-restart-reset

# View logs
make order-generator-logs

# Stop the generator
make order-generator-stop

# Check status
make order-generator-status
```

**Manual usage:**
```bash
# Ensure MockExchange stack is running
make start

# Start the order generator
cd examples/order-generator
cp .env.example .env
# Edit .env with your API settings
./manage.sh start --reset
```

For more details, see [examples/README.md](examples/README.md).

---

## 🔧 Environment Configuration

All environment variables are centralized in the root `.env` file. This eliminates duplication and makes configuration management much easier.

### Quick Setup
```bash
# Copy the template and customize if needed
cp .env.example .env
```

**Note**: The `.env.example` is configured for local development. For Docker deployment, change `API_URL` from `http://localhost:8000` to `http://engine:8000`.

### Key Configuration Sections

#### **Valkey (Database)**
- `VALKEY_PASSWORD` - Database authentication
- `VALKEY_PORT` - Database port (default: 6379)

#### **Oracle (Price Feeds)**
- `EXCHANGE` - Source exchange (binance, coinbase, etc.)
- `SYMBOLS` - Trading pairs to monitor
- `INTERVAL_SEC` - Price update frequency

#### **Engine (API)**
- `ENGINE_PORT` - API server port (default: 8000)
- `COMMISSION` - Trading commission rate
- `API_KEY` - Authentication key

#### **Periscope (Dashboard)**
- `PERISCOPE_PORT` - Dashboard port (default: 8501)
- `APP_TITLE` - Dashboard title
- `REFRESH_SECONDS` - Auto-refresh interval

### Benefits of Centralized Configuration
- ✅ **Single source of truth** - All config in one place
- ✅ **No duplication** - Eliminates scattered `.env` files
- ✅ **Easy customization** - Change once, applies everywhere
- ✅ **Better security** - Centralized password management
- ✅ **Simplified deployment** - One config file to manage

---

## 🗂 Monorepo Structure
```text
mockexchange/
├── packages/
│   ├── valkey/        # MockX Valkey (Redis database)
│   ├── engine/        # MockX Engine (core/ + api/)
│   ├── periscope/     # MockX Periscope (dashboard)
│   └── oracle/        # MockX Oracle (price feeds)
├── examples/          # Examples and tools
│   ├── order-generator/ # Random order generator
│   └── README.md      # Examples overview
├── .github/workflows/ # CI/CD pipelines
├── docker-compose.yml # Full stack orchestration
├── .env.example       # Environment configuration template
├── Makefile          # Development commands
├── pyproject.toml    # Root workspace config
├── .pre-commit-config.yaml # Code quality hooks
├── scripts/          # Development and release scripts
│   └── create-release-branch.sh # Automated release branch creation
├── CHANGELOG.md      # Version history and release notes
├── DOCKER_VERSIONS.md # Docker version pinning documentation
└── README.md         # This file
```

---

## 📚 Documentation

### **Core Documentation**
- [Valkey README](packages/valkey/README.md) - Database layer and data structures
- [Oracle README](packages/oracle/README.md) - Price feed service and configuration
- [Engine README](packages/engine/README.md) - Trading engine and API reference
- [Periscope README](packages/periscope/README.md) - Dashboard features and usage

### **Project Documentation**
- [CHANGELOG.md](CHANGELOG.md) - Version history and release notes
- [Docker Version Pinning](DOCKER_VERSIONS.md) - Reproducible Docker builds
- [Examples README](examples/README.md) - Usage examples and tools

### **External Resources**
- [MockX Gateway](https://github.com/didac-crst/mockexchange-gateway) - ccxt-style Python client

---

## 🪪 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

> **Don’t risk real money.**  
> Spin up MockExchange, hammer it with tests, then hit live markets only when your algos are solid.