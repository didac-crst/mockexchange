"""Unit tests for Periscope portfolio helper functions."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest
import streamlit as st

from app._pages._helpers import _display_assets_pie_chart_compact, _display_portfolio_details


class TestDisplayAssetsPieChartCompact:
    """Test the compact assets pie chart display function."""

    def test_display_assets_pie_chart_compact_with_valid_data(self):
        """Test pie chart creation with valid assets overview data."""
        # Mock assets overview data
        assets_overview = {
            "balance_source": {
                "cash_frozen_value": 1000.0,
                "cash_free_value": 5000.0,
                "assets_frozen_value": 2000.0,
                "assets_free_value": 8000.0,
            },
            "misc": {"cash_asset": "USDT"},
        }

        with patch("streamlit.plotly_chart") as mock_plotly_chart:
            _display_assets_pie_chart_compact(assets_overview)

            # Verify plotly chart was called
            mock_plotly_chart.assert_called_once()

    def test_display_assets_pie_chart_compact_with_zero_values(self):
        """Test pie chart creation with all zero values."""
        assets_overview = {
            "balance_source": {
                "cash_frozen_value": 0.0,
                "cash_free_value": 0.0,
                "assets_frozen_value": 0.0,
                "assets_free_value": 0.0,
            },
            "misc": {"cash_asset": "USDT"},
        }

        with patch("streamlit.info") as mock_info:
            _display_assets_pie_chart_compact(assets_overview)

            # Should show info message for empty data
            mock_info.assert_called_once_with("No assets data available for pie chart.")

    def test_display_assets_pie_chart_compact_with_partial_zero_values(self):
        """Test pie chart creation with some zero values."""
        assets_overview = {
            "balance_source": {
                "cash_frozen_value": 0.0,
                "cash_free_value": 5000.0,
                "assets_frozen_value": 2000.0,
                "assets_free_value": 0.0,
            },
            "misc": {"cash_asset": "USDT"},
        }

        with patch("streamlit.plotly_chart") as mock_plotly_chart:
            _display_assets_pie_chart_compact(assets_overview)

            # Should still create chart with non-zero values
            mock_plotly_chart.assert_called_once()

    def test_display_assets_pie_chart_compact_with_missing_data(self):
        """Test pie chart creation with missing balance source data."""
        assets_overview = {
            "balance_source": {},
            "misc": {"cash_asset": "USDT"},
        }

        with patch("streamlit.info") as mock_info:
            _display_assets_pie_chart_compact(assets_overview)

            # Should show info message for empty data
            mock_info.assert_called_once_with("No assets data available for pie chart.")

    def test_display_assets_pie_chart_compact_data_structure(self):
        """Test that the function creates correct data structure for the pie chart."""
        assets_overview = {
            "balance_source": {
                "cash_frozen_value": 1000.0,
                "cash_free_value": 5000.0,
                "assets_frozen_value": 2000.0,
                "assets_free_value": 8000.0,
            },
            "misc": {"cash_asset": "USDT"},
        }

        with patch("streamlit.plotly_chart") as mock_plotly_chart:
            _display_assets_pie_chart_compact(assets_overview)

            # Get the call arguments to verify data structure
            call_args = mock_plotly_chart.call_args
            fig = call_args[0][0]  # First positional argument is the figure

            # Verify the figure has the expected data
            assert fig.data[0].labels == ["Frozen Cash", "Free Cash", "Frozen Assets", "Free Assets"]
            assert fig.data[0].values == [1000.0, 5000.0, 2000.0, 8000.0]


class TestDisplayPortfolioDetails:
    """Test the portfolio details display function."""

    def test_display_portfolio_details_with_assets_overview(self):
        """Test portfolio details with provided assets overview data."""
        assets_overview = {
            "balance_source": {
                "total_equity": 10000.0,
                "total_free_value": 8000.0,
                "total_frozen_value": 2000.0,
                "cash_total_value": 5000.0,
                "cash_free_value": 4000.0,
                "cash_frozen_value": 1000.0,
                "assets_total_value": 5000.0,
                "assets_free_value": 4000.0,
                "assets_frozen_value": 1000.0,
            },
            "orders_source": {
                "total_frozen_value": 2000.0,
                "cash_frozen_value": 1000.0,
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

        with patch("streamlit.columns") as mock_columns, patch("streamlit.markdown") as mock_markdown:
            # Mock columns to return mock column objects
            mock_col1, mock_col2, mock_col3 = Mock(), Mock(), Mock()
            mock_columns.return_value = (mock_col1, mock_col2, mock_col3)

            _display_portfolio_details(assets_overview=assets_overview, advanced_display=True)

            # Verify columns were created
            mock_columns.assert_called_once_with(3)

    def test_display_portfolio_details_without_assets_overview(self):
        """Test portfolio details without provided assets overview (should fetch it)."""
        mock_assets_overview = {
            "balance_source": {"total_equity": 10000.0},
            "misc": {"cash_asset": "USDT"},
        }

        with patch("app._pages._helpers.get_assets_overview", return_value=mock_assets_overview) as mock_get, patch(
            "streamlit.columns"
        ) as mock_columns:
            mock_col1 = Mock()
            mock_columns.return_value = (mock_col1,)

            _display_portfolio_details(advanced_display=False)

            # Verify get_assets_overview was called
            mock_get.assert_called_once()

    def test_display_portfolio_details_simple_mode(self):
        """Test portfolio details in simple mode (not advanced)."""
        assets_overview = {
            "balance_source": {"total_equity": 10000.0},
            "misc": {"cash_asset": "USDT"},
        }

        with patch("streamlit.columns") as mock_columns:
            mock_col1 = Mock()
            mock_columns.return_value = (mock_col1,)

            _display_portfolio_details(assets_overview=assets_overview, advanced_display=False)

            # Should only create one column for simple mode
            mock_columns.assert_called_once_with(1)

    def test_display_portfolio_details_with_mismatch_data(self):
        """Test portfolio details with mismatch data (should show warnings)."""
        assets_overview = {
            "balance_source": {
                "total_equity": 10000.0,
                "total_free_value": 8000.0,
                "total_frozen_value": 2000.0,
                "cash_total_value": 5000.0,
                "cash_free_value": 4000.0,
                "cash_frozen_value": 1000.0,
                "assets_total_value": 5000.0,
                "assets_free_value": 4000.0,
                "assets_frozen_value": 1000.0,
            },
            "orders_source": {
                "total_frozen_value": 2500.0,  # Different from balance
                "cash_frozen_value": 1200.0,   # Different from balance
                "assets_frozen_value": 1300.0,  # Different from balance
            },
            "misc": {
                "cash_asset": "USDT",
                "mismatch": {
                    "total_frozen_value": True,   # Mismatch detected
                    "cash_frozen_value": True,    # Mismatch detected
                    "assets_frozen_value": True,  # Mismatch detected
                },
            },
        }

        with patch("streamlit.columns") as mock_columns, patch("streamlit.markdown") as mock_markdown:
            mock_col1, mock_col2, mock_col3 = Mock(), Mock(), Mock()
            mock_columns.return_value = (mock_col1, mock_col2, mock_col3)

            _display_portfolio_details(assets_overview=assets_overview, advanced_display=True)

            # Verify columns were created
            mock_columns.assert_called_once_with(3)


class TestPortfolioHelpersIntegration:
    """Integration tests for portfolio helper functions."""

    def test_portfolio_helpers_with_realistic_data(self):
        """Test both functions with realistic portfolio data."""
        realistic_assets_overview = {
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

        # Test both functions work together
        with patch("streamlit.plotly_chart") as mock_plotly_chart, patch("streamlit.columns") as mock_columns:
            mock_col1, mock_col2, mock_col3 = Mock(), Mock(), Mock()
            mock_columns.return_value = (mock_col1, mock_col2, mock_col3)

            # Test portfolio details
            _display_portfolio_details(assets_overview=realistic_assets_overview, advanced_display=True)
            
            # Test pie chart
            _display_assets_pie_chart_compact(realistic_assets_overview)

            # Verify both functions executed without errors
            mock_columns.assert_called_once()
            mock_plotly_chart.assert_called_once()
