# MockExchange Order Generator 🚀

This directory contains a Dockerized order generator for the **MockExchange** platform, designed to run continuously for hours or days. It simulates trading activity by **generating random orders (no strategy)**, so the simulated portfolio value should erode over time 📉. It logs operations and validates behavior without using live endpoints.

## Prerequisites

Before running the order generator, ensure the MockExchange stack is running:

```bash
# Start the full stack
make start

# Or start individual services
make start-valkey    # Database
make start-oracle    # Price feeds
make start-engine    # API server
```

## Contents

- `manage.sh`  
Unified script to manage the order generator (start, stop, logs, status).
- **Dockerfile**: Slim Python 3.12 image, installs dependencies, sets working directory.
- **docker-compose.yml**: Defines `order-generator` service with host networking and resource limits.
- **requirements.txt**: Python runtime dependencies (`httpx`, `python-dotenv`).
- **.env.example**: Template for environment variables.
- **scripts**/
    - `order_generator.py`: Places randomized orders based on env vars.
    - `helpers.py`: HTTPX client utilities (reset, fund, patch ticker, fetch prices).
    - `conftest.py`: Pytest fixtures to reset and fund backend before tests.

## Prerequisites

- **Docker** & **Docker Compose v2+**
- **Git** for cloning the repository

## Installation

1. **Clone the repository**:
```sh
git clone https://github.com/didac-crst/mockexchange.git
```
2. **Navigate to the order generator**:
```sh
cd mockexchange/examples/order-generator
```
3. **Prepare environment file**:
```sh
cp .env.example .env
```
Then edit `.env` to set your **API endpoint** and **credentials**.

**Note**: The order generator connects to the MockX Engine API on `http://localhost:8000` by default.

**Workflow:**
1. **First time**: `./manage.sh start --reset` (builds Docker, clears data)
2. **Continue**: `./manage.sh restart` (no rebuild, keeps data)
3. **Reset data**: `./manage.sh restart --reset` (no rebuild, clears data)

## Usage

1. Ensure the MockExchange stack is running (see Prerequisites above)
2. Ensure your Docker daemon is running.
3. **Manage the order generator**:
```sh
./manage.sh start --reset   # Fresh start with reset (builds Docker)
./manage.sh restart         # Continue without reset (no rebuild)
./manage.sh restart --reset # Continue with reset (no rebuild)
./manage.sh stop            # Stop the generator
./manage.sh logs            # View logs
./manage.sh status          # Check status
./manage.sh help            # Show all options
```

## Tunable Parameters (in `.env`)

| Parameter                         | Default                                     | Description                                                                                 |
| --------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------- |
| **API_URL**                       | `https://mockexchange-api.your-domain.com/` | Base URL of the MockExchange API endpoint.                                                  |
| **TEST_ENV**                      | `true`                                      | If `true`, enables test mode (no use of API_KEY authentication).                            |
| **API_KEY**                       | `"your-super-secret-key"`                   | API authentication key.                                                                     |
| **FUNDING_AMOUNT**                | `5000`                                      | Initial balance in the quote asset for generating orders.                                   |
| **QUOTE_ASSET**                   | `USDT`                                      | The quote currency used for all orders.                                                     |
| **BASE_ASSETS_TO_BUY**            | `BTC,ETH,SOL,XRP,BNB,ADA,DOGE,DOT`          | Comma-separated list of core assets to trade.                                               |
| **NUM_EXTRA_ASSETS**              | `4`                                         | Number of additional (random) assets to include beyond the base list.                       |
| **TRADING_TYPES**                 | `market,limit`                              | Order types to randomly choose from.                                                        |
| **MIN_ORDERS_PER_BATCH**          | `1`                                         | Minimum number of orders generated in each batch.                                           |
| **MAX_ORDERS_PER_BATCH**          | `3`                                         | Maximum number of orders generated in each batch.                                           |
| **MIN_SLEEP**                     | `30`                                        | Minimum seconds to wait between batches.                                                    |
| **MAX_SLEEP**                     | `300`                                       | Maximum seconds to wait between batches.                                                    |
| **NOMINAL_TICKET_QUOTE**          | `50.0`                                      | Target quote-currency amount per order.                                                     |
| **FAST_SELL_TICKET_AMOUNT_RATIO** | `0.05`                                      | Fraction of holdings to sell in “fast” sell orders.                                         |
| **MIN_ORDER_QUOTE**               | `1.0`                                       | Don’t place orders below this quote-currency amount.                                        |
| **MIN_BALANCE_CASH_QUOTE**        | `250.0`                                     | Keep at least this much quote balance free to cover fees.                                   |
| **MIN_BALANCE_ASSETS_QUOTE**      | `2.0`                                       | Maintain this quote value worth of assets as a buffer to avoid insufficient-balance issues. |

## Directory Structure

```text
examples/order-generator/
├── README.md
├── manage.sh             ← Unified script to manage the order generator
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── scripts/
    ├── order_generator.py
    ├── helpers.py
    └── conftest.py
```