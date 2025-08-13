"""
Unit tests for the OrderBook class.
"""

import unittest
from unittest.mock import Mock, patch

from core._types import Order, OrderState
from core.orderbook import OrderBook


class TestOrderBook(unittest.TestCase):
    """Test cases for the OrderBook class."""

    def test_orderbook_initialization(self):
        """Test OrderBook initialization."""
        mock_redis = Mock()
        orderbook = OrderBook(mock_redis)
        assert orderbook.r is mock_redis
        assert orderbook.HASH_KEY == "orders"
        assert orderbook.OPEN_ALL_KEY == "open:set"
        assert orderbook.OPEN_SYM_KEY == "open:{sym}"

    def test_add_order(self):
        """Test adding an order to the orderbook."""
        mock_redis = Mock()
        orderbook = OrderBook(mock_redis)

        # Create a mock order
        mock_order = Mock(spec=Order)
        mock_order.id = "order123"
        mock_order.symbol = "BTC/USDT"
        mock_order.status = OrderState.NEW
        mock_order.to_json.return_value = '{"id": "order123", "symbol": "BTC/USDT"}'

        orderbook.add(mock_order)

        mock_redis.hset.assert_called_once_with(
            "orders", "order123", '{"id": "order123", "symbol": "BTC/USDT"}'
        )
        mock_redis.sadd.assert_any_call("open:set", "order123")
        mock_redis.sadd.assert_any_call("open:BTC/USDT", "order123")

    def test_add_closed_order(self):
        """Test adding a closed order (should not be indexed)."""
        mock_redis = Mock()
        orderbook = OrderBook(mock_redis)

        # Create a mock closed order
        mock_order = Mock(spec=Order)
        mock_order.id = "order123"
        mock_order.symbol = "BTC/USDT"
        mock_order.status = OrderState.FILLED
        mock_order.to_json.return_value = '{"id": "order123", "status": "filled"}'

        orderbook.add(mock_order)

        mock_redis.hset.assert_called_once_with(
            "orders", "order123", '{"id": "order123", "status": "filled"}'
        )
        # Should not add to open indexes
        mock_redis.sadd.assert_not_called()

    def test_get_order(self):
        """Test getting an order from the orderbook."""
        mock_redis = Mock()
        mock_redis.hget.return_value = (
            '{"id": "order123", "symbol": "BTC/USDT", "status": "open"}'
        )

        orderbook = OrderBook(mock_redis)

        with patch("core.orderbook.Order.from_json") as mock_from_json:
            mock_order = Mock(spec=Order)
            mock_from_json.return_value = mock_order

            result = orderbook.get("order123")

            assert result is mock_order
            mock_redis.hget.assert_called_once_with("orders", "order123")
            mock_from_json.assert_called_once_with(
                '{"id": "order123", "symbol": "BTC/USDT", "status": "open"}',
                include_history=False,
            )

    def test_get_order_not_found(self):
        """Test getting an order that doesn't exist."""
        mock_redis = Mock()
        mock_redis.hget.return_value = None

        orderbook = OrderBook(mock_redis)

        with self.assertRaises(ValueError) as context:
            orderbook.get("nonexistent")

        self.assertIn("Order nonexistent not found", str(context.exception))
        mock_redis.hget.assert_called_once_with("orders", "nonexistent")

    def test_update_order(self):
        """Test updating an existing order."""
        mock_redis = Mock()
        orderbook = OrderBook(mock_redis)

        # Create a mock order
        mock_order = Mock(spec=Order)
        mock_order.id = "order123"
        mock_order.to_json.return_value = '{"id": "order123", "updated": true}'

        orderbook.update(mock_order)

        mock_redis.hset.assert_called_once_with(
            "orders", "order123", '{"id": "order123", "updated": true}'
        )
        mock_order.to_json.assert_called_once_with(include_history=True)

    def test_remove_order(self):
        """Test removing an order from the orderbook."""
        mock_redis = Mock()
        mock_redis.hget.return_value = (
            '{"id": "order123", "symbol": "BTC/USDT", "status": "open"}'
        )
        mock_pipeline = Mock()
        mock_redis.pipeline.return_value = mock_pipeline

        orderbook = OrderBook(mock_redis)

        with patch("core.orderbook.Order.from_json") as mock_from_json:
            mock_order = Mock(spec=Order)
            mock_order.id = "order123"
            mock_order.symbol = "BTC/USDT"
            mock_order.status = OrderState.NEW
            mock_from_json.return_value = mock_order

            orderbook.remove("order123")

            mock_redis.hget.assert_called_once_with("orders", "order123")
            mock_redis.srem.assert_any_call("open:set", "order123")
            mock_redis.srem.assert_any_call("open:BTC/USDT", "order123")
            mock_pipeline.hdel.assert_called_once_with("orders", "order123")
            mock_pipeline.execute.assert_called_once()

    def test_remove_nonexistent_order(self):
        """Test removing an order that doesn't exist."""
        mock_redis = Mock()
        mock_redis.hget.return_value = None

        orderbook = OrderBook(mock_redis)

        orderbook.remove("nonexistent")

        mock_redis.hget.assert_called_once_with("orders", "nonexistent")
        # Should not call any other operations
        mock_redis.srem.assert_not_called()
        mock_redis.hdel.assert_not_called()

    def test_list_orders_open_status(self):
        """Test listing orders with open status (uses indexes)."""
        mock_redis = Mock()
        mock_redis.smembers.return_value = {"order123", "order456"}
        mock_redis.hmget.return_value = [
            '{"id": "order123", "symbol": "BTC/USDT", "status": "open"}',
            '{"id": "order456", "symbol": "ETH/USDT", "status": "open"}',
        ]

        orderbook = OrderBook(mock_redis)

        with patch("core.orderbook.Order.from_json") as mock_from_json:
            mock_order1 = Mock(spec=Order)
            mock_order1.id = "order123"
            mock_order1.symbol = "BTC/USDT"
            mock_order1.status = OrderState.NEW
            mock_order1.ts_update = 1000

            mock_order2 = Mock(spec=Order)
            mock_order2.id = "order456"
            mock_order2.symbol = "ETH/USDT"
            mock_order2.status = OrderState.NEW
            mock_order2.ts_update = 2000

            mock_from_json.side_effect = [mock_order1, mock_order2]

            result = orderbook.list(status=OrderState.NEW)

            assert result == [mock_order2, mock_order1]  # Sorted by ts_update desc
            mock_redis.smembers.assert_called_once_with("open:set")
            # Check that hmget was called with the correct arguments, but order may vary
            mock_redis.hmget.assert_called_once()
            args = mock_redis.hmget.call_args[0]
            assert args[0] == "orders"
            assert set(args[1:]) == {"order123", "order456"}

    def test_list_orders_with_symbol_filter(self):
        """Test listing orders filtered by symbol."""
        mock_redis = Mock()
        mock_redis.smembers.return_value = {"order123"}
        mock_redis.hmget.return_value = [
            '{"id": "order123", "symbol": "BTC/USDT", "status": "open"}'
        ]

        orderbook = OrderBook(mock_redis)

        with patch("core.orderbook.Order.from_json") as mock_from_json:
            mock_order = Mock(spec=Order)
            mock_order.id = "order123"
            mock_order.symbol = "BTC/USDT"
            mock_order.status = OrderState.NEW
            mock_order.ts_update = 1000
            mock_from_json.return_value = mock_order

            result = orderbook.list(status=OrderState.NEW, symbol="BTC/USDT")

            assert result == [mock_order]
            mock_redis.smembers.assert_called_once_with("open:BTC/USDT")
            mock_redis.hmget.assert_called_once_with("orders", "order123")

    def test_clear_orderbook(self):
        """Test clearing the entire orderbook."""
        mock_redis = Mock()
        mock_redis.keys.return_value = ["open:BTC/USDT", "open:ETH/USDT"]
        mock_pipeline = Mock()
        mock_redis.pipeline.return_value = mock_pipeline

        orderbook = OrderBook(mock_redis)

        orderbook.clear()

        # Should use pipeline for all operations
        mock_redis.pipeline.assert_called_once()
        mock_pipeline.delete.assert_any_call("orders")
        mock_pipeline.delete.assert_any_call("open:set")
        # Should delete all symbol-specific sets
        mock_pipeline.delete.assert_any_call("open:BTC/USDT")
        mock_pipeline.delete.assert_any_call("open:ETH/USDT")
        mock_pipeline.execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
