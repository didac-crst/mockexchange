# Mockexchange API - Dry Run Example 🚀

This directory contains a Dockerized dry run example for the **mockexchange-api** library, designed to run continuously for hours or days. It simulates trading activity by **generating random orders (no strategy)**, so the simulated portfolio value should erode over time 📉. It logs operations and validates behavior without using live endpoints.

## Contents

- `start_dryrun.sh`  
Builds and starts the Dockerized dry run environment.
- `log_dryrun.sh`    
Follows the Docker container logs for the order generator.
- `on_docker/`       
- **Dockerfile**: Slim Python 3.12 image, installs dependencies, sets working directory.
- **docker-compose.yml**: Defines `dryrun-order-gen` service with host networking and resource limits.
- **requirements.txt**: Python runtime dependencies (`httpx`, `python-dotenv`).
- **.env.example**: Template for environment variables.
- **scripts**/
    - `dryrun_continuous_order_generator.py`: Places randomized orders based on env vars.
    - `helpers.py`: HTTPX client utilities (reset, fund, patch ticker, fetch prices).
    - `conftest.py`: Pytest fixtures to reset and fund backend before tests.

## Prerequisites

- **Docker** & **Docker Compose v2+**
- **Git** for cloning the repository

## Installation

1. **Clone the repository**:
```sh
git clone https://github.com/yourorg/mockexchange-api.git
```
2. **Navigate to the dry run example**:
```sh
cd mockexchange-api/examples/dry_run
```
3. **Prepare environment file**:
```sh
cp on_docker/.env.example on_docker/.env
```
Then edit `on_docker/.env` to set your **API endpoint** and **credentials**.

## Dockerized Usage

1. Ensure the mockexchange-api backend is already running before starting the dry run... 😅
2. Ensure your Docker daemon is running.
3. **Start the dry run**:
```sh
./start_dryrun.sh
```
4. **Follow container logs**:
```sh
./log_dryrun.sh
```
5. To stop and clean up:
```sh
cd on_docker
docker compose down
```

## Tunable Parameters (in `.env`)

| Parameter                      | Default                                                   | Description                                                                                 |
|--------------------------------|-----------------------------------------------------------|---------------------------------------------------------------------------------------------|
| **API_URL**                    | `https://mockexchange-api.your-domain.com/`               | Base URL of the MockExchange API endpoint.                                                 |
| **TEST_ENV**                   | `true`                                                    | If `true`, enables test mode (no use of API_KEY authentication).                                             |
| **API_KEY**                    | `"your-super-secret-key"`                               | API authentication key.                                                                     |
| **FUNDING_AMOUNT**             | `5000`                                                    | Initial balance in the quote asset for generating orders.                                   |
| **QUOTE_ASSET**                | `USDT`                                                    | The quote currency used for all orders.                                                    |
| **BASE_ASSETS_TO_BUY**         | `BTC,ETH,SOL,XRP,BNB,ADA,DOGE,DOT`                        | Comma-separated list of core assets to trade.                                              |
| **NUM_EXTRA_ASSETS**           | `4`                                                       | Number of additional (random) assets to include beyond the base list.             |
| **TRADING_TYPES**              | `market,limit`                                           | Order types to randomly choose from.                                                       |
| **MIN_ORDERS_PER_BATCH**       | `1`                                                       | Minimum number of orders generated in each batch.                                          |
| **MAX_ORDERS_PER_BATCH**       | `3`                                                       | Maximum number of orders generated in each batch.                                          |
| **MIN_SLEEP**                  | `30`                                                      | Minimum seconds to wait between batches.                                                   |
| **MAX_SLEEP**                  | `300`                                                     | Maximum seconds to wait between batches.                                                   |
| **NOMINAL_TICKET_QUOTE**       | `50.0`                                                    | Target quote-currency amount per order.                                                    |
| **FAST_SELL_TICKET_AMOUNT_RATIO** | `0.05`                                                | Fraction of holdings to sell in “fast” sell orders.                                        |
| **MIN_ORDER_QUOTE**            | `1.0`                                                     | Don’t place orders below this quote-currency amount.                                       |
| **MIN_BALANCE_CASH_QUOTE**     | `250.0`                                                   | Keep at least this much quote balance free to cover fees.                                  |
| **MIN_BALANCE_ASSETS_QUOTE**   | `2.0`                                                     | Maintain this quote value worth of assets as a buffer to avoid insufficient-balance issues.|

## Directory Structure

```text
examples/dry_run/
├── README.md
├── reset_start_dryrun.sh  ← It starts the dry-run from scratch - It resets the back-end before starting
├── continue_dryrun.sh     ← It continues the dry-run with the existing state of the back-end. (No Reset)
├── log_dryrun.sh
└── on_docker/
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    ├── .env.example
    └── scripts/
        ├── dryrun_continuous_order_generator.py
        ├── helpers.py
        └── conftest.py
```