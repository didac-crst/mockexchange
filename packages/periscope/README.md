# MockX Periscope

**MockX Periscope** is the web dashboard for the MockExchange suite, providing a real-time interface to monitor portfolios, orders, and trading activity.

## Overview

MockX Periscope provides:

- **Portfolio Dashboard** - Real-time balance overview and asset allocation
- **Order Management** - View and track order status and execution
- **Order Details** - Detailed view of individual orders with complete history
- **Performance Analytics** - Comprehensive trading activity and performance metrics
- **Real-time Updates** - Auto-refresh with configurable intervals
- **Responsive Design** - Works on desktop and mobile devices
- **Streamlit UI** - Modern, clean interface built with Streamlit

## Quick Start

The Periscope dashboard is part of the full MockExchange stack. See the [main README](../../README.md) for complete setup instructions.

### **Individual Service Management**
```bash
# Start just the dashboard (requires Engine)
make start-periscope

# View dashboard logs
make logs-periscope

# Check dashboard status
make status
```

### **Access the Dashboard**
Once running, the dashboard is available at:
- **Local**: http://localhost:8501
- **Docker**: http://localhost:8501

## Configuration

The dashboard uses environment variables from the root `.env` file. Key variables include:

| Variable          | Default                 | Description                  |
| ----------------- | ----------------------- | ---------------------------- |
| `API_URL`         | `http://localhost:8000` | Engine API URL               |
| `API_KEY`         | `dev-key`               | Authentication key           |
| `REFRESH_SECONDS` | `60`                    | Auto-refresh interval        |
| `QUOTE_ASSET`     | `USDT`                  | Portfolio valuation currency |
| `APP_TITLE`       | `MockExchange`          | Dashboard title              |
| `FRESH_WINDOW_S`  | `60`                    | Fresh window for highlighting (seconds) |
| `N_VISUAL_DEGRADATIONS` | `60`            | Number of fade-out levels for visual feedback |
| `SLIDER_MIN`      | `10`                    | Minimum value for order count slider |
| `SLIDER_MAX`      | `1000`                  | Maximum value for order count slider |
| `SLIDER_STEP`     | `10`                    | Step size for order count slider |
| `SLIDER_DEFAULT`  | `50`                    | Default value for order count slider |
| `LOCAL_TZ`        | `Europe/Berlin`         | Timezone for timestamps |
| `LOGO_FILE`       | ``                      | Logo file for dashboard (optional) |
| `UI_URL`          | `http://localhost:8501` | UI base URL for links |

**Note**: For Docker deployment, `API_URL` should be `http://engine:8000`. For local development, use `http://localhost:8000`.

See the [main README](../../README.md#-environment-configuration) for the complete configuration guide.

## Features

### **Performance Page**
<img src="./docs/img/page_performance.png" alt="Performance Dashboard" width="800">

- **Investment Multiples** - RVPI, DPI, and TVPI ratios for performance measurement
- **Capital Breakdown** - Waterfall chart showing distribution between net investment, P&L, assets, and cash
- **Performance Metrics** - Gross/net earnings, fees, and current asset valuations
- **Advanced Toggle** - Switch between simple and detailed performance views
- **Real-time Updates** - Auto-refresh with current portfolio performance data

### **Portfolio Page**
<img src="./docs/img/page_portfolio.png" alt="Portfolio Dashboard" width="800">

- **Asset Overview** - Current holdings with free, used, and total balances per asset
- **Portfolio Value** - Total equity and market value in quote currency (USDT)
- **Asset Allocation** - Interactive donut chart with "Other" grouping for small positions
- **Advanced Breakdown** - Toggle between simple equity view and detailed cash/asset breakdown
- **Sortable Table** - Human-readable table with formatted numbers and portfolio shares

### **Order Book Page**
<img src="./docs/img/page_order_book.png" alt="Order Book" width="800">

- **Order Management** - Complete order history with status, price, and execution details
- **Smart Filtering** - Filter by status, symbol, side, type, and configurable time range
- **Data Range Control** - Slider to fetch recent orders (10-1000) or entire order book
- **Visual Feedback** - Color-coded rows highlighting new activity with fade-out effect
- **Order Details Access** - Click any order to view complete information and execution history

### **Order Details Page**
<img src="./docs/img/page_order_details.png" alt="Order Details" width="800">

- **Order Summary** - Complete order information including status, type, and timestamps
- **Execution History** - Step-by-step order history with timestamps and price changes
- **Trade Breakdown** - Detailed view of all individual trades that fulfilled the order
- **Order Actions** - Cancel open orders directly from the interface
- **Navigation** - Contextual navigation buttons to return to main views

## Architecture

### **Frontend**
- **Streamlit** - Web framework for data apps
- **Plotly** - Interactive charts and visualizations
- **Responsive Design** - Mobile-friendly interface

### **Backend Integration**
- **REST API** - Communicates with MockX Engine
- **Real-time Updates** - Polling-based data refresh
- **Authentication** - API key-based security

## Development

### **Local Development**
```bash
# Install dependencies
poetry install

# Run locally
streamlit run app/main.py
```

### **Adding New Pages**
1. Create new module in `app/_pages/`
2. Add navigation in `app/main.py`
3. Implement API calls in `app/services/api.py`

### **Customization**
- **Styling** - Modify `app/_pages/_colors.py`
- **Configuration** - Update `app/config.py`
- **API Integration** - Extend `app/services/api.py`

## Dependencies

- **Streamlit** - Web application framework
- **Plotly** - Interactive visualizations
- **Requests** - HTTP client for API calls
- **Python-dotenv** - Environment variable management

