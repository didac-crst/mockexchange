"""Unit tests for orderbook module."""

import pytest
from unittest.mock import Mock, patch
from core.orderbook import OrderBook


class TestOrderBook:
    """Test OrderBook class functionality."""

    def test_orderbook_initialization(self):
        """Test OrderBook initialization."""
        mock_redis = Mock()
        orderbook = OrderBook(mock_redis, "BTC/USDT")
        assert orderbook.redis is mock_redis
        assert orderbook.symbol == "BTC/USDT"

    def test_add_buy_order(self):
        """Test adding a buy order to the orderbook."""
        mock_redis = Mock()
        orderbook = OrderBook(mock_redis, "BTC/USDT")

        order = {
            "id": "order_123",
            "side": "BUY",
            "amount": 1.0,
            "price": 50000.0,
            "type": "LIMIT",
        }

        orderbook.add_order(order)

        # Verify order was added to buy side
        mock_redis.zadd.assert_called()

    def test_add_sell_order(self):
        """Test adding a sell order to the orderbook."""
        mock_redis = Mock()
        orderbook = OrderBook(mock_redis, "BTC/USDT")

        order = {
            "id": "order_456",
            "side": "SELL",
            "amount": 0.5,
            "price": 51000.0,
            "type": "LIMIT",
        }

        orderbook.add_order(order)

        # Verify order was added to sell side
        mock_redis.zadd.assert_called()

    def test_remove_order(self):
        """Test removing an order from the orderbook."""
        mock_redis = Mock()
        orderbook = OrderBook(mock_redis, "BTC/USDT")

        orderbook.remove_order("order_123", "BUY")

        # Verify order was removed from buy side
        mock_redis.zrem.assert_called()

    def test_get_best_bid_ask(self):
        """Test getting best bid and ask prices."""
        mock_redis = Mock()
        mock_redis.zrange.return_value = [{"price": 50000.0}, {"price": 51000.0}]

        orderbook = OrderBook(mock_redis, "BTC/USDT")
        best_bid, best_ask = orderbook.get_best_bid_ask()

        assert best_bid == 50000.0
        assert best_ask == 51000.0

    def test_get_orderbook_depth(self):
        """Test getting orderbook depth."""
        mock_redis = Mock()
        mock_redis.zrange.return_value = [
            {"price": 50000.0, "amount": 1.0},
            {"price": 49900.0, "amount": 2.0},
        ]

        orderbook = OrderBook(mock_redis, "BTC/USDT")
        depth = orderbook.get_depth(5)

        assert len(depth["bids"]) == 2
        assert len(depth["asks"]) == 2
