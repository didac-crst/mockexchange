"""Integration tests for price validation functionality."""

from unittest.mock import Mock

from oracle.main import write_tickers


class TestPriceValidationIntegration:
    """Test price validation integration in write_tickers function."""

    def test_write_tickers_with_valid_prices(self):
        """Test that tickers with valid prices are written to Redis."""
        mock_redis = Mock()

        # Mock tickers with valid prices
        tickers = [
            ("BTC/USDT", {"last": 50000.0, "timestamp": 1234567890.0}),
            ("ETH/USDT", {"last": 3000.0, "timestamp": 1234567890.0}),
        ]

        write_tickers(mock_redis, "tickers:", tickers)

        # Should call hset twice (once for each valid ticker)
        assert mock_redis.hset.call_count == 2

        # Verify the calls were made with correct keys
        calls = mock_redis.hset.call_args_list
        assert calls[0].args[0] == "tickers:BTC/USDT"
        assert calls[1].args[0] == "tickers:ETH/USDT"

    def test_write_tickers_with_invalid_prices(self):
        """Test that tickers with invalid prices are skipped."""
        mock_redis = Mock()

        # Mock tickers with invalid prices
        tickers = [
            ("INVALID/USDT", {"last": 0.0, "timestamp": 1234567890.0}),
            ("NEGATIVE/USDT", {"last": -1.0, "timestamp": 1234567890.0}),
        ]

        write_tickers(mock_redis, "tickers:", tickers)

        # Should not call hset at all (no valid prices)
        mock_redis.hset.assert_not_called()

    def test_write_tickers_mixed_valid_invalid(self):
        """Test that only valid tickers are written when mixed with invalid ones."""
        mock_redis = Mock()

        # Mock tickers with mixed valid/invalid prices
        tickers = [
            ("BTC/USDT", {"last": 50000.0, "timestamp": 1234567890.0}),  # Valid
            ("INVALID/USDT", {"last": 0.0, "timestamp": 1234567890.0}),  # Invalid
            ("ETH/USDT", {"last": 3000.0, "timestamp": 1234567890.0}),  # Valid
            ("NEGATIVE/USDT", {"last": -1.0, "timestamp": 1234567890.0}),  # Invalid
        ]

        write_tickers(mock_redis, "tickers:", tickers)

        # Should call hset twice (only for valid tickers)
        assert mock_redis.hset.call_count == 2

        # Verify the calls were made with correct keys
        calls = mock_redis.hset.call_args_list
        assert calls[0].args[0] == "tickers:BTC/USDT"
        assert calls[1].args[0] == "tickers:ETH/USDT"

    def test_write_tickers_no_price_fallback(self):
        """Test that tickers with no price fallback to 0.0 and are skipped."""
        mock_redis = Mock()

        # Mock ticker with no price information
        tickers = [
            ("NO_PRICE/USDT", {"timestamp": 1234567890.0}),  # No price field
        ]

        write_tickers(mock_redis, "tickers:", tickers)

        # Should not call hset (price will be 0.0 and invalid)
        mock_redis.hset.assert_not_called()

    def test_write_tickers_mid_price_validation(self):
        """Test that mid price calculation is validated correctly."""
        mock_redis = Mock()

        # Mock ticker with bid/ask but no last/close (will use mid price)
        tickers = [
            (
                "MID_PRICE/USDT",
                {"bid": 100.0, "ask": 102.0, "timestamp": 1234567890.0},
            ),  # Mid price = 101.0 (valid)
        ]

        write_tickers(mock_redis, "tickers:", tickers)

        # Should call hset once (mid price is valid)
        assert mock_redis.hset.call_count == 1

        # Verify the call was made with correct key
        call = mock_redis.hset.call_args
        assert call.args[0] == "tickers:MID_PRICE/USDT"

        # Verify the price in the mapping is the mid price
        mapping = call.kwargs["mapping"]
        assert mapping["price"] == 101.0

    def test_write_tickers_mid_price_invalid(self):
        """Test that invalid mid prices are skipped."""
        mock_redis = Mock()

        # Mock ticker with invalid bid/ask (negative or zero)
        tickers = [
            (
                "INVALID_MID/USDT",
                {"bid": -1.0, "ask": 1.0, "timestamp": 1234567890.0},
            ),  # Will fallback to 0.0 (invalid)
        ]

        write_tickers(mock_redis, "tickers:", tickers)

        # Should not call hset (price will be 0.0 and invalid)
        mock_redis.hset.assert_not_called()

    def test_write_tickers_none_prices(self):
        """Test that tickers with None prices are skipped."""
        mock_redis = Mock()

        # Mock tickers with None prices
        tickers = [
            ("NONE_LAST/USDT", {"last": None, "timestamp": 1234567890.0}),
            ("NONE_CLOSE/USDT", {"close": None, "timestamp": 1234567890.0}),
            (
                "NONE_BID_ASK/USDT",
                {"bid": None, "ask": None, "timestamp": 1234567890.0},
            ),
        ]

        write_tickers(mock_redis, "tickers:", tickers)

        # Should not call hset at all (all prices will be 0.0 and invalid)
        mock_redis.hset.assert_not_called()

    def test_write_tickers_mixed_none_valid_prices(self):
        """Test that only valid tickers are written when mixed with None prices."""
        mock_redis = Mock()

        # Mock tickers with mixed None/valid prices
        tickers = [
            ("BTC/USDT", {"last": 50000.0, "timestamp": 1234567890.0}),  # Valid
            (
                "NONE_LAST/USDT",
                {"last": None, "timestamp": 1234567890.0},
            ),  # Invalid (None)
            ("ETH/USDT", {"last": 3000.0, "timestamp": 1234567890.0}),  # Valid
            (
                "NONE_BID_ASK/USDT",
                {"bid": None, "ask": None, "timestamp": 1234567890.0},
            ),  # Invalid (None)
        ]

        write_tickers(mock_redis, "tickers:", tickers)

        # Should call hset twice (only for valid tickers)
        assert mock_redis.hset.call_count == 2

        # Verify the calls were made with correct keys
        calls = mock_redis.hset.call_args_list
        assert calls[0].args[0] == "tickers:BTC/USDT"
        assert calls[1].args[0] == "tickers:ETH/USDT"
