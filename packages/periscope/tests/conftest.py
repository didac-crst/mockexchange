"""Shared fixtures for periscope tests."""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_api_response():
    """Mock API response data."""
    return {
        "balances": {
            "BTC": {"free": 1.0, "used": 0.1, "total": 1.1},
            "USDT": {"free": 50000.0, "used": 0.0, "total": 50000.0},
        },
        "orders": {
            "order_123": {
                "id": "order_123",
                "symbol": "BTC/USDT",
                "side": "BUY",
                "amount": 1.0,
                "price": 50000.0,
                "status": "filled",
            }
        },
        "tickers": {
            "BTC/USDT": {
                "price": 50000.0,
                "bid": 49900.0,
                "ask": 50100.0,
                "timestamp": 1234567890.0,
            }
        },
    }


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit for testing."""
    return Mock()
