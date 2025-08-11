"""Unit tests for market module."""

from unittest.mock import Mock, patch

from core.market import Market


class TestMarket:
    """Test Market class functionality."""

    def test_market_initialization(self):
        """Test Market initialization."""
        mock_redis = Mock()
        market = Market(mock_redis)
        assert market.redis is mock_redis

    @patch("core.market.Market._get_ticker_data")
    def test_get_ticker_price_success(self, mock_get_ticker):
        """Test successful price retrieval."""
        mock_redis = Mock()
        mock_get_ticker.return_value = {"price": 50000.0, "timestamp": 1234567890}

        market = Market(mock_redis)
        price = market.get_ticker_price("BTC/USDT")

        assert price == 50000.0
        mock_get_ticker.assert_called_once_with("BTC/USDT")

    @patch("core.market.Market._get_ticker_data")
    def test_get_ticker_price_not_found(self, mock_get_ticker):
        """Test price retrieval when ticker doesn't exist."""
        mock_redis = Mock()
        mock_get_ticker.return_value = None

        market = Market(mock_redis)
        price = market.get_ticker_price("INVALID/PAIR")

        assert price is None

    def test_get_all_tickers(self):
        """Test retrieving all available tickers."""
        mock_redis = Mock()
        mock_redis.keys.return_value = [
            "tickers:BTC/USDT",
            "tickers:ETH/USDT",
            "tickers:ADA/USDT",
        ]

        market = Market(mock_redis)
        tickers = market.get_all_tickers()

        expected = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        assert tickers == expected
        mock_redis.keys.assert_called_once_with("tickers:*")
