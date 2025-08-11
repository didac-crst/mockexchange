"""Unit tests for Periscope API integration."""

from unittest.mock import Mock, patch

import httpx
import pytest
from app.services.api import get_balances, get_orders, get_tickers


class TestAPIIntegration:
    """Test API integration functionality."""

    @patch("httpx.get")
    def test_get_balances_success(self, mock_get):
        """Test successful balance retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "BTC": {"free": 1.0, "used": 0.1, "total": 1.1},
            "USDT": {"free": 50000.0, "used": 0.0, "total": 50000.0},
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = get_balances("http://localhost:8000")

        assert "BTC" in result
        assert "USDT" in result
        assert result["BTC"]["free"] == 1.0
        assert result["USDT"]["total"] == 50000.0

    @patch("httpx.get")
    def test_get_balances_api_error(self, mock_get):
        """Test balance retrieval with API error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=Mock()
        )
        mock_get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            get_balances("http://localhost:8000")

    @patch("httpx.get")
    def test_get_orders_success(self, mock_get):
        """Test successful orders retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "order_123": {
                "id": "order_123",
                "symbol": "BTC/USDT",
                "side": "BUY",
                "amount": 1.0,
                "price": 50000.0,
                "status": "filled",
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = get_orders("http://localhost:8000")

        assert "order_123" in result
        assert result["order_123"]["symbol"] == "BTC/USDT"
        assert result["order_123"]["side"] == "BUY"

    @patch("httpx.get")
    def test_get_tickers_success(self, mock_get):
        """Test successful tickers retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "BTC/USDT": {
                "price": 50000.0,
                "bid": 49900.0,
                "ask": 50100.0,
                "timestamp": 1234567890.0,
            },
            "ETH/USDT": {
                "price": 3000.0,
                "bid": 2990.0,
                "ask": 3010.0,
                "timestamp": 1234567890.0,
            },
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = get_tickers("http://localhost:8000")

        assert "BTC/USDT" in result
        assert "ETH/USDT" in result
        assert result["BTC/USDT"]["price"] == 50000.0
        assert result["ETH/USDT"]["price"] == 3000.0

    @patch("httpx.get")
    def test_api_timeout(self, mock_get):
        """Test API timeout handling."""
        mock_get.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(httpx.TimeoutException):
            get_balances("http://localhost:8000")

    @patch("httpx.get")
    def test_api_connection_error(self, mock_get):
        """Test API connection error handling."""
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(httpx.ConnectError):
            get_balances("http://localhost:8000")
