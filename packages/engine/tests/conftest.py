"""Shared fixtures for engine tests."""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_redis():
    """Mock Redis client for unit tests."""
    return Mock()


@pytest.fixture
def sample_order():
    """Sample order data for testing."""
    return {
        "id": "test_order_123",
        "symbol": "BTC/USDT",
        "side": "BUY",
        "type": "LIMIT",
        "amount": 1.0,
        "price": 50000.0,
        "status": "new",
        "timestamp": 1234567890.0,
    }


@pytest.fixture
def sample_ticker():
    """Sample ticker data for testing."""
    return {
        "price": 50000.0,
        "bid": 49900.0,
        "ask": 50100.0,
        "bidVolume": 10.0,
        "askVolume": 5.0,
        "timestamp": 1234567890.0,
        "symbol": "BTC/USDT",
    }
