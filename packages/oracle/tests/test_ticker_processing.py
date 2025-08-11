"""Unit tests for ticker processing functionality."""

from oracle.main import normalize_ticker, normalize_timestamp


class TestTickerProcessing:
    """Test ticker processing functionality."""

    def test_normalize_timestamp_none(self):
        """Test normalizing None timestamp."""
        result = normalize_timestamp(None)
        assert isinstance(result, float)
        assert result > 0

    def test_normalize_timestamp_seconds(self):
        """Test normalizing timestamp in seconds."""
        timestamp = 1234567890.0
        result = normalize_timestamp(timestamp)
        assert result == timestamp

    def test_normalize_timestamp_milliseconds(self):
        """Test normalizing timestamp in milliseconds."""
        timestamp_ms = 1234567890000.0
        result = normalize_timestamp(timestamp_ms)
        assert result == timestamp_ms / 1000.0

    def test_normalize_ticker_with_last_price(self):
        """Test normalizing ticker with last price."""
        ticker = {
            "last": 50000.0,
            "bid": 49900.0,
            "ask": 50100.0,
            "bidVolume": 10.0,
            "askVolume": 5.0,
            "timestamp": 1234567890.0,
        }

        result = normalize_ticker("BTC/USDT", ticker)

        assert result["price"] == 50000.0
        assert result["bid"] == 49900.0
        assert result["ask"] == 50100.0
        assert result["bidVolume"] == 10.0
        assert result["askVolume"] == 5.0
        assert result["symbol"] == "BTC/USDT"

    def test_normalize_ticker_with_close_price(self):
        """Test normalizing ticker with close price (no last)."""
        ticker = {
            "close": 50000.0,
            "bid": 49900.0,
            "ask": 50100.0,
            "bidVolume": 10.0,
            "askVolume": 5.0,
            "timestamp": 1234567890.0,
        }

        result = normalize_ticker("BTC/USDT", ticker)

        assert result["price"] == 50000.0

    def test_normalize_ticker_mid_price(self):
        """Test normalizing ticker using mid price (no last/close)."""
        ticker = {
            "bid": 49900.0,
            "ask": 50100.0,
            "bidVolume": 10.0,
            "askVolume": 5.0,
            "timestamp": 1234567890.0,
        }

        result = normalize_ticker("BTC/USDT", ticker)

        expected_mid = (49900.0 + 50100.0) / 2.0
        assert result["price"] == expected_mid

    def test_normalize_ticker_no_price(self):
        """Test normalizing ticker with no price information."""
        ticker = {"bidVolume": 10.0, "askVolume": 5.0, "timestamp": 1234567890.0}

        result = normalize_ticker("BTC/USDT", ticker)

        assert result["price"] is None
        assert result["bid"] is None
        assert result["ask"] is None

    def test_normalize_ticker_missing_volumes(self):
        """Test normalizing ticker with missing volume data."""
        ticker = {
            "last": 50000.0,
            "bid": 49900.0,
            "ask": 50100.0,
            "timestamp": 1234567890.0,
        }

        result = normalize_ticker("BTC/USDT", ticker)

        assert result["bidVolume"] == 0.0
        assert result["askVolume"] == 0.0

    def test_normalize_ticker_invalid_timestamp(self):
        """Test normalizing ticker with invalid timestamp."""
        ticker = {
            "last": 50000.0,
            "bid": 49900.0,
            "ask": 50100.0,
            "timestamp": "invalid",
        }

        result = normalize_ticker("BTC/USDT", ticker)

        assert isinstance(result["timestamp"], float)
        assert result["timestamp"] > 0
