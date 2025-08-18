"""Integration tests for Periscope portfolio page functionality."""

from unittest.mock import Mock, patch

import pandas as pd
import pytest
import streamlit as st

from app._pages.portfolio import render


class TestPortfolioPageIntegration:
    """Test the portfolio page integration with new features."""

    @patch("app._pages.portfolio.get_balance")
    @patch("app._pages.portfolio.get_assets_overview")
    @patch("app._pages.portfolio._display_portfolio_details")
    @patch("app._pages.portfolio._display_assets_pie_chart_compact")
    @patch("streamlit.columns")
    @patch("streamlit.plotly_chart")
    @patch("streamlit.dataframe")
    @patch("streamlit.subheader")
    @patch("streamlit.info")
    def test_portfolio_page_with_valid_data(
        self,
        mock_info,
        mock_subheader,
        mock_dataframe,
        mock_plotly_chart,
        mock_columns,
        mock_display_assets_chart,
        mock_display_portfolio_details,
        mock_get_assets_overview,
        mock_get_balance,
    ):
        """Test portfolio page with valid data and new features."""
        # Mock balance data
        mock_get_balance.return_value = {
            "equity": 15000.0,
            "quote_asset": "USDT",
            "assets_df": pd.DataFrame({
                "asset": ["BTC", "ETH", "USDT"],
                "free": [1.0, 10.0, 5000.0],
                "used": [0.1, 1.0, 0.0],
                "total": [1.1, 11.0, 5000.0],
                "quote_price": [50000.0, 3000.0, 1.0],
            }),
        }

        # Mock assets overview data
        mock_get_assets_overview.return_value = {
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

        # Mock columns for side-by-side layout
        mock_col1, mock_col2 = Mock(), Mock()
        mock_columns.return_value = (mock_col1, mock_col2)

        # Mock advanced filter toggle
        with patch("app._pages.portfolio.advanced_filter_toggle", return_value=False):
            render()

        # Verify API calls were made
        mock_get_balance.assert_called_once()
        mock_get_assets_overview.assert_called_once()

        # Verify portfolio details were called with assets overview data
        mock_display_portfolio_details.assert_called_once()
        call_args = mock_display_portfolio_details.call_args
        assert call_args[1]["assets_overview"] == mock_get_assets_overview.return_value

        # Verify columns were created for side-by-side layout
        mock_columns.assert_called_once_with(2)

        # Verify subheaders were created
        mock_subheader.assert_any_call("Portfolio Distribution by Asset")
        mock_subheader.assert_any_call("Asset Distribution: Frozen vs Free")

        # Verify assets pie chart was called
        mock_display_assets_chart.assert_called_once_with(mock_get_assets_overview.return_value)

    @patch("app._pages.portfolio.get_balance")
    @patch("app._pages.portfolio.get_assets_overview")
    @patch("streamlit.info")
    def test_portfolio_page_with_empty_data(self, mock_info, mock_get_assets_overview, mock_get_balance):
        """Test portfolio page with empty assets data."""
        # Mock empty balance data
        mock_get_balance.return_value = {
            "equity": 0.0,
            "quote_asset": "USDT",
            "assets_df": pd.DataFrame(),  # Empty DataFrame
        }

        # Mock assets overview data
        mock_get_assets_overview.return_value = {
            "balance_source": {},
            "orders_source": {},
            "misc": {"cash_asset": "USDT", "mismatch": {}},
        }

        with patch("app._pages.portfolio.advanced_filter_toggle", return_value=False):
            render()

        # Should show info message for empty portfolio
        mock_info.assert_called_once_with("No equity or assets found.")

    @patch("app._pages.portfolio.get_balance")
    @patch("app._pages.portfolio.get_assets_overview")
    @patch("streamlit.columns")
    @patch("streamlit.plotly_chart")
    @patch("streamlit.dataframe")
    @patch("streamlit.subheader")
    def test_portfolio_page_advanced_mode(
        self,
        mock_subheader,
        mock_dataframe,
        mock_plotly_chart,
        mock_columns,
        mock_get_assets_overview,
        mock_get_balance,
    ):
        """Test portfolio page in advanced mode."""
        # Mock balance data
        mock_get_balance.return_value = {
            "equity": 15000.0,
            "quote_asset": "USDT",
            "assets_df": pd.DataFrame({
                "asset": ["BTC", "ETH"],
                "free": [1.0, 10.0],
                "used": [0.1, 1.0],
                "total": [1.1, 11.0],
                "quote_price": [50000.0, 3000.0],
            }),
        }

        # Mock assets overview data
        mock_get_assets_overview.return_value = {
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

        # Mock columns for side-by-side layout
        mock_col1, mock_col2 = Mock(), Mock()
        mock_columns.return_value = (mock_col1, mock_col2)

        # Mock advanced filter toggle returning True
        with patch("app._pages.portfolio.advanced_filter_toggle", return_value=True):
            render()

        # Verify API calls were made
        mock_get_balance.assert_called_once()
        mock_get_assets_overview.assert_called_once()

        # Verify columns were created for side-by-side layout
        mock_columns.assert_called_once_with(2)

    @patch("app._pages.portfolio.get_balance")
    @patch("app._pages.portfolio.get_assets_overview")
    def test_portfolio_page_api_error_handling(self, mock_get_assets_overview, mock_get_balance):
        """Test portfolio page error handling when API calls fail."""
        import requests

        # Mock API error
        mock_get_balance.side_effect = requests.exceptions.HTTPError("API Error")

        with pytest.raises(requests.exceptions.HTTPError):
            render()

    @patch("app._pages.portfolio.get_balance")
    @patch("app._pages.portfolio.get_assets_overview")
    @patch("streamlit.columns")
    @patch("streamlit.plotly_chart")
    @patch("streamlit.dataframe")
    @patch("streamlit.subheader")
    def test_portfolio_page_chart_data_processing(
        self,
        mock_subheader,
        mock_dataframe,
        mock_plotly_chart,
        mock_columns,
        mock_get_assets_overview,
        mock_get_balance,
    ):
        """Test that chart data is processed correctly."""
        # Mock balance data with assets that will be grouped into "Other"
        mock_get_balance.return_value = {
            "equity": 15000.0,
            "quote_asset": "USDT",
            "assets_df": pd.DataFrame({
                "asset": ["BTC", "ETH", "ADA", "XRP", "DOT"],
                "free": [1.0, 10.0, 1000.0, 5000.0, 100.0],
                "used": [0.1, 1.0, 100.0, 500.0, 10.0],
                "total": [1.1, 11.0, 1100.0, 5500.0, 110.0],
                "quote_price": [50000.0, 3000.0, 1.0, 0.5, 10.0],
            }),
        }

        # Mock assets overview data
        mock_get_assets_overview.return_value = {
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

        # Mock columns for side-by-side layout
        mock_col1, mock_col2 = Mock(), Mock()
        mock_columns.return_value = (mock_col1, mock_col2)

        with patch("app._pages.portfolio.advanced_filter_toggle", return_value=False):
            render()

        # Verify plotly chart was called (for the first chart)
        mock_plotly_chart.assert_called()

        # Verify dataframe was called (for the table)
        mock_dataframe.assert_called_once()


class TestPortfolioPageDataValidation:
    """Test data validation in portfolio page."""

    @patch("app._pages.portfolio.get_balance")
    @patch("app._pages.portfolio.get_assets_overview")
    @patch("streamlit.columns")
    @patch("streamlit.plotly_chart")
    @patch("streamlit.dataframe")
    @patch("streamlit.subheader")
    def test_portfolio_page_with_malformed_data(
        self,
        mock_subheader,
        mock_dataframe,
        mock_plotly_chart,
        mock_columns,
        mock_get_assets_overview,
        mock_get_balance,
    ):
        """Test portfolio page with malformed data."""
        # Mock balance data with missing columns
        mock_get_balance.return_value = {
            "equity": 15000.0,
            "quote_asset": "USDT",
            "assets_df": pd.DataFrame({
                "asset": ["BTC", "ETH"],
                # Missing required columns: free, used, total, quote_price
            }),
        }

        # Mock assets overview data
        mock_get_assets_overview.return_value = {
            "balance_source": {},
            "orders_source": {},
            "misc": {"cash_asset": "USDT", "mismatch": {}},
        }

        # Mock columns for side-by-side layout
        mock_col1, mock_col2 = Mock(), Mock()
        mock_columns.return_value = (mock_col1, mock_col2)

        with patch("app._pages.portfolio.advanced_filter_toggle", return_value=False):
            # Should handle missing columns gracefully
            render()

        # Verify API calls were made
        mock_get_balance.assert_called_once()
        mock_get_assets_overview.assert_called_once()
