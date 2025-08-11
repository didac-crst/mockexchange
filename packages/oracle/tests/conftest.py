"""Shared fixtures for oracle tests."""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_exchange():
    """Mock CCXT exchange for testing."""
    exchange = Mock()
    exchange.load_markets.return_value = {
        "BTC/USDT": {"symbol": "BTC/USDT", "active": True},
        "ETH/USDT": {"symbol": "ETH/USDT", "active": True},
        "ADA/USDT": {"symbol": "ADA/USDT", "active": True},
        "BTC/EUR": {"symbol": "BTC/EUR", "active": True},
        "ETH/EUR": {"symbol": "ETH/EUR", "active": True},
    }
    return exchange


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    return Mock()


@pytest.fixture
def sample_ticker_data():
    """Sample ticker data from exchange."""
    return {
        "last": 50000.0,
        "bid": 49900.0,
        "ask": 50100.0,
        "bidVolume": 10.0,
        "askVolume": 5.0,
        "timestamp": 1234567890000.0,  # milliseconds
    }
