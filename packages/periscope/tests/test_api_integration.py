"""Unit tests for Periscope API integration."""

from unittest.mock import patch

import pytest

from app.services.api import get_assets_overview, get_balance, get_orders, get_prices


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

    @patch("app.services.api._get")
    def test_get_assets_overview_success(self, mock_get):
        """Test successful assets overview retrieval."""
        mock_get.return_value = {
            "balance_source": {
                "total_equity": 15000.0,
                "total_free_value": 12000.0,
                "total_frozen_value": 3000.0,
                "cash_total_value": 8000.0,
                "cash_free_value": 6000.0,
                "cash_frozen_value": 2000.0,
                "assets_total_value": 7000.0,
                "assets_free_value": 6000.0,
                "assets_frozen_value": 1000.0,
            },
            "orders_source": {
                "total_frozen_value": 3000.0,
                "cash_frozen_value": 2000.0,
                "assets_frozen_value": 1000.0,
            },
            "misc": {
                "cash_asset": "USDT",
                "mismatch": {
                    "total_frozen_value": False,
                    "cash_frozen_value": False,
                    "assets_frozen_value": False,
                },
            },
        }

        result = get_assets_overview()

        assert "balance_source" in result
        assert "orders_source" in result
        assert "misc" in result
        assert result["balance_source"]["total_equity"] == 15000.0
        assert result["misc"]["cash_asset"] == "USDT"

    @patch("app.services.api._get")
    def test_get_assets_overview_api_error(self, mock_get):
        """Test assets overview retrieval with API error."""
        import requests

        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

        with pytest.raises(requests.exceptions.HTTPError):
            get_assets_overview()

    @patch("app.services.api._get")
    def test_get_assets_overview_invalid_response(self, mock_get):
        """Test assets overview retrieval with invalid response type."""
        mock_get.return_value = "invalid_response_type"

        with pytest.raises(TypeError):
            get_assets_overview()

    @patch("app.services.api._get")
    def test_get_assets_overview_empty_data(self, mock_get):
        """Test assets overview retrieval with empty data."""
        mock_get.return_value = {
            "balance_source": {},
            "orders_source": {},
            "misc": {"cash_asset": "USDT", "mismatch": {}},
        }

        result = get_assets_overview()

        assert isinstance(result, dict)
        assert "balance_source" in result
        assert "orders_source" in result
        assert "misc" in result
