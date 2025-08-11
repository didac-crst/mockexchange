"""
Unit tests for the Market class.
"""

import unittest
from unittest.mock import Mock, patch

from core.market import Market


class TestMarket(unittest.TestCase):
    """Test cases for the Market class."""

    def test_market_initialization(self):
        """Test Market initialization."""
        mock_redis = Mock()
        market = Market(mock_redis)
        assert market.conn is mock_redis
        assert market.root_key == "tickers:"

    def test_market_initialization_with_custom_root_key(self):
        """Test Market initialization with custom root key."""
        mock_redis = Mock()
        market = Market(mock_redis, root_key="custom:")
        assert market.conn is mock_redis
        assert market.root_key == "custom:"

    def test_fetch_ticker_success(self):
        """Test fetching a ticker successfully."""
        mock_redis = Mock()
        mock_redis.hgetall.return_value = {
            "price": "50000.0",
            "timestamp": "1640995200.0",
            "bid": "49900.0",
            "ask": "50100.0",
            "bidVolume": "1.5",
            "askVolume": "2.0",
        }

        market = Market(mock_redis)
        ticker = market.fetch_ticker("BTC/USDT")

        assert ticker is not None
        assert ticker.symbol == "BTC/USDT"
        assert ticker.price == 50000.0
        assert ticker.timestamp == 1640995200.0
        assert ticker.bid == 49900.0
        assert ticker.ask == 50100.0
        assert ticker.bid_volume == 1.5
        assert ticker.ask_volume == 2.0
        mock_redis.hgetall.assert_called_once_with("tickers:BTC/USDT")

    def test_fetch_ticker_not_found(self):
        """Test fetching a ticker that doesn't exist."""
        mock_redis = Mock()
        mock_redis.hgetall.return_value = {}

        market = Market(mock_redis)
        ticker = market.fetch_ticker("BTC/USDT")

        assert ticker is None
        mock_redis.hgetall.assert_called_once_with("tickers:BTC/USDT")

    def test_fetch_ticker_malformed_data(self):
        """Test fetching a ticker with malformed data."""
        mock_redis = Mock()
        mock_redis.hgetall.return_value = {
            "price": "invalid",
            "timestamp": "1640995200.0",
        }

        market = Market(mock_redis)
        ticker = market.fetch_ticker("BTC/USDT")

        assert ticker is None
        mock_redis.hgetall.assert_called_once_with("tickers:BTC/USDT")

    def test_last_price_success(self):
        """Test getting last price successfully."""
        mock_redis = Mock()
        mock_redis.hgetall.return_value = {
            "price": "50000.0",
            "timestamp": "1640995200.0",
        }

        market = Market(mock_redis)
        price = market.last_price("BTC/USDT")

        assert price == 50000.0
        mock_redis.hgetall.assert_called_once_with("tickers:BTC/USDT")

    def test_last_price_not_available(self):
        """Test getting last price when ticker is not available."""
        mock_redis = Mock()
        mock_redis.hgetall.return_value = {}

        market = Market(mock_redis)

        with self.assertRaises(RuntimeError) as context:
            market.last_price("BTC/USDT")

        self.assertIn("Ticker for BTC/USDT not available", str(context.exception))
        mock_redis.hgetall.assert_called_once_with("tickers:BTC/USDT")

    def test_tickers_property(self):
        """Test the tickers property returns all available tickers."""
        mock_redis = Mock()
        mock_redis.scan_iter.return_value = [
            "tickers:BTC/USDT",
            "tickers:ETH/USDT",
            "tickers:ADA/USDT",
            "other:key",  # Should be filtered out
        ]

        market = Market(mock_redis)
        tickers = market.tickers

        assert tickers == ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        mock_redis.scan_iter.assert_called_once_with("tickers:*")

    def test_set_last_price(self):
        """Test setting the last price of a ticker."""
        mock_redis = Mock()
        market = Market(mock_redis)

        # Create a mock TradingPair
        mock_ticker = Mock()
        mock_ticker.symbol = "BTC/USDT"
        mock_ticker.price = 50000.0
        mock_ticker.timestamp = 1640995200.0
        mock_ticker.bid = 49900.0
        mock_ticker.ask = 50100.0
        mock_ticker.bid_volume = 1.5
        mock_ticker.ask_volume = 2.0

        market.set_last_price(mock_ticker)

        expected_mapping = {
            "symbol": "BTC/USDT",
            "price": 50000.0,
            "timestamp": 1640995200.0,
            "bid": 49900.0,
            "ask": 50100.0,
            "bidVolume": 1.5,
            "askVolume": 2.0,
        }
        mock_redis.hset.assert_called_once_with(
            "tickers:BTC/USDT", mapping=expected_mapping
        )

    def test_set_last_price_no_symbol(self):
        """Test setting last price with no symbol raises error."""
        mock_redis = Mock()
        market = Market(mock_redis)

        # Create a mock TradingPair with no symbol
        mock_ticker = Mock()
        mock_ticker.symbol = ""

        with self.assertRaises(RuntimeError) as context:
            market.set_last_price(mock_ticker)

        self.assertIn("TradingPair must have a symbol", str(context.exception))
        mock_redis.hset.assert_not_called()


if __name__ == "__main__":
    unittest.main()
