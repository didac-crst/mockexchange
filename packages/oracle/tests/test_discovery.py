"""Unit tests for Oracle discovery functionality."""

from unittest.mock import Mock, patch

from oracle.main import discover_symbols_for_quotes, parse_csv


class TestDiscovery:
    """Test discovery functionality."""

    def test_parse_csv_empty(self):
        """Test parsing empty CSV string."""
        result = parse_csv("")
        assert result == []

    def test_parse_csv_single(self):
        """Test parsing single value."""
        result = parse_csv("USDT")
        assert result == ["USDT"]

    def test_parse_csv_multiple(self):
        """Test parsing multiple values."""
        result = parse_csv("USDT,EUR,BTC")
        assert result == ["USDT", "EUR", "BTC"]

    def test_parse_csv_with_spaces(self):
        """Test parsing CSV with spaces."""
        result = parse_csv(" USDT , EUR , BTC ")
        assert result == ["USDT", "EUR", "BTC"]

    def test_parse_csv_duplicates(self):
        """Test parsing CSV with duplicates."""
        result = parse_csv("USDT,EUR,USDT,BTC")
        assert result == ["USDT", "EUR", "BTC"]

    @patch("oracle.main.log")
    def test_discover_symbols_for_quotes_no_limit(self, mock_log):
        """Test discovering symbols without limit."""
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = {
            "BTC/USDT": {},
            "ETH/USDT": {},
            "ADA/USDT": {},
            "BTC/EUR": {},
            "ETH/EUR": {},
        }

        quotes = ["USDT", "EUR"]
        result = discover_symbols_for_quotes(mock_exchange, quotes, 0)

        expected = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "BTC/EUR", "ETH/EUR"]
        assert result == expected
        mock_log.info.assert_called()

    @patch("oracle.main.log")
    def test_discover_symbols_for_quotes_with_limit(self, mock_log):
        """Test discovering symbols with limit."""
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = {
            "BTC/USDT": {},
            "ETH/USDT": {},
            "ADA/USDT": {},
            "SOL/USDT": {},
            "BTC/EUR": {},
            "ETH/EUR": {},
        }

        quotes = ["USDT", "EUR"]
        result = discover_symbols_for_quotes(mock_exchange, quotes, 2)

        # Should get 2 USDT pairs and 2 EUR pairs
        assert len(result) == 4
        assert all("/USDT" in sym or "/EUR" in sym for sym in result)
        mock_log.info.assert_called()

    def test_discover_symbols_no_matches(self):
        """Test discovering symbols when no matches found."""
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = {"BTC/BTC": {}, "ETH/ETH": {}}

        quotes = ["USDT"]
        result = discover_symbols_for_quotes(mock_exchange, quotes, 0)

        assert result == []

    def test_discover_symbols_deduplication(self):
        """Test that symbols are deduplicated across quotes."""
        mock_exchange = Mock()
        mock_exchange.load_markets.return_value = {
            "BTC/USDT": {},
            "BTC/EUR": {},
            "ETH/USDT": {},
            "ETH/EUR": {},
        }

        quotes = ["USDT", "EUR"]
        result = discover_symbols_for_quotes(mock_exchange, quotes, 0)

        # Should not have duplicates
        assert len(result) == len(set(result))
        assert len(result) == 4
