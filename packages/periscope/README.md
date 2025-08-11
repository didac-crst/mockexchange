# MockX Periscope

**MockX Periscope** is the web dashboard for the MockExchange suite, providing a real-time interface to monitor portfolios, orders, and trading activity.

## Overview

MockX Periscope provides:

- **Portfolio Dashboard** - Real-time balance overview and asset allocation
- **Order Management** - View and track order status and execution
- **Trade History** - Complete trading activity and performance metrics
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

**Note**: For Docker deployment, `API_URL` should be `http://engine:8000`. For local development, use `http://localhost:8000`.

See the [main README](../../README.md#-environment-configuration) for the complete configuration guide.

## Features

### **Portfolio Page**
- **Asset Balances** - Free, used, and total balances for each asset
- **Portfolio Value** - Total value in quote currency (USDT)
- **Asset Allocation** - Pie chart showing portfolio distribution
- **Performance Metrics** - PnL and percentage changes

### **Orders Page**
- **Order List** - All orders with status, price, and execution details
- **Filtering** - Filter by status, symbol, side, and time range
- **Real-time Updates** - Live order status changes
- **Order Details** - Click to view complete order information

### **Performance Page**
- **Trade Statistics** - Aggregated trading metrics
- **Performance Charts** - Visual representation of trading activity
- **Asset Performance** - Individual asset performance tracking

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

## Screenshots

![Portfolio Dashboard](./docs/img/portfolio_page.png)
![Orders Page](./docs/img/orders_page.png)

## Dependencies

- **Streamlit** - Web application framework
- **Plotly** - Interactive visualizations
- **Requests** - HTTP client for API calls
- **Python-dotenv** - Environment variable management

## License

MIT License - see [LICENSE](LICENSE) for details.