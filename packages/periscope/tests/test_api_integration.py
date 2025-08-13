"""Unit tests for Periscope API integration."""

from unittest.mock import patch

import pytest
from app.services.api import get_balance, get_orders, get_prices


class TestAPIIntegration:
    """Test API integration functionality."""

    @patch("app.services.api._get")
    def test_get_balance_success(self, mock_get):
        """Test successful balance retrieval."""
        mock_get.return_value = [
            {"asset": "BTC", "free": 1.0, "used": 0.1, "total": 1.1},
            {"asset": "USDT", "free": 50000.0, "used": 0.0, "total": 50000.0},
        ]

        result = get_balance()

        assert "equity" in result
        assert "quote_asset" in result
        assert "assets_df" in result
        assert len(result["assets_df"]) == 2

    @patch("app.services.api._get")
    def test_get_balance_api_error(self, mock_get):
        """Test balance retrieval with API error."""
        import requests

        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

        with pytest.raises(requests.exceptions.HTTPError):
            get_balance()

    @patch("app.services.api._get")
    def test_get_orders_success(self, mock_get):
        """Test successful orders retrieval."""
        mock_get.return_value = [
            {
                "id": "order_123",
                "symbol": "BTC/USDT",
                "side": "buy",
                "amount": 1.0,
                "price": 50000.0,
                "status": "filled",
            }
        ]

        result = get_orders()

        assert len(result) == 1
        assert result.iloc[0]["symbol"] == "BTC/USDT"
        assert result.iloc[0]["side"] == "buy"

    @patch("app.services.api._get")
    def test_get_prices_success(self, mock_get):
        """Test successful prices retrieval."""
        mock_get.return_value = {
            "BTC/USDT": {
                "symbol": "BTC/USDT",
                "last": 50000.0,
                "bid": 49900.0,
                "ask": 50100.0,
                "timestamp": 1234567890.0,
            },
            "ETH/USDT": {
                "symbol": "ETH/USDT",
                "last": 3000.0,
                "bid": 2990.0,
                "ask": 3010.0,
                "timestamp": 1234567890.0,
            },
        }

        result = get_prices(["BTC/USDT", "ETH/USDT"])

        assert "BTC/USDT" in result
        assert "ETH/USDT" in result
        assert result["BTC/USDT"] == 50000.0
        assert result["ETH/USDT"] == 3000.0

    @patch("app.services.api._get")
    def test_api_timeout(self, mock_get):
        """Test API timeout handling."""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(requests.exceptions.Timeout):
            get_balance()

    @patch("app.services.api._get")
    def test_api_connection_error(self, mock_get):
        """Test API connection error handling."""
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(requests.exceptions.ConnectionError):
            get_balance()
