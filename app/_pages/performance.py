"""performance.py

Streamlit page that displays the **performance** of MockExchange.

Key features
------------
* Pulls the most‑recent *N* trades from the REST back‑end (`get_trades_overview`).
* Lets the user interactively **filter** by trade *status*, *side*, *type* and *asset*.
* Persists those filters across automatic page refreshes – unless the
  user explicitly unfreezes them.
* Shows a colour‑coded dataframe where **freshly updated** rows are
  highlighted and slowly fade out (visual degradations).
* Optionally displays an "advanced" equity breakdown in the sidebar.

The code is intentionally verbose on comments to serve as a living
reference for new contributors.
"""

import os
import time  # noqa: F401  # imported for completeness – not used directly yet
from pathlib import Path
from dotenv import load_dotenv

import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go
import altair as alt

from app.services.api import get_trades_overview,  get_overview_capital
from ._helpers import (
    _display_performance_details,
    advanced_filter_toggle,
    tvpi_gauge,
    CHART_COLORS,
)
from ._colors import _row_style

# -----------------------------------------------------------------------------
# Configuration & constants
# -----------------------------------------------------------------------------
# Load environment variables from the project root .env so this file
# can be executed standalone (e.g. `streamlit run src/.../orders.py`).
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# How long a row stays "fresh" (seconds) → affects row colouring.
FRESH_WINDOW_S = int(os.getenv("FRESH_WINDOW_S", 300))  # default 5 min


# -----------------------------------------------------------------------------
# Main page renderer – Streamlit entry‑point
# -----------------------------------------------------------------------------

def render() -> None:  # noqa: D401 – imperative mood is clearer here
    """Render the **Order Book** page.

    Workflow
    --------
    """

    # Basic Streamlit page config
    st.set_page_config(page_title="Performance")  # browser tab + sidebar label
    st.title("Performance")

    # ------------------------------------------------------------------
    # Keep track of the auto‑refresh ticker so we can detect new reruns
    # ------------------------------------------------------------------
    curr_tick = st.session_state.get("refresh", 0)
    last_tick = st.session_state.get("_last_refresh_tick", None)

    # ------------------------------------------------------------------
    # 2) Fetch raw data from the API and pre‑process
    # ------------------------------------------------------------------
    base = os.getenv("UI_URL", "http://localhost:8000")


    trades_summary, cash_asset = get_trades_overview()
    summary_capital = get_overview_capital()

    # ------------------------------------------------------------------
    # Sidebar – advanced equity breakdown & toggle
    # ------------------------------------------------------------------

    advanced_display = advanced_filter_toggle()

    # --- capital -------------------------------------------------
    equity = summary_capital.get("equity", 0.0)
    paid_in_capital = summary_capital.get("deposits", 0.0)
    distributions = summary_capital.get("withdrawals", 0.0)
    net_investment = paid_in_capital - distributions  # net invested capital

    # --- core amounts --------------------------------------------------
    incomplete_data        = trades_summary["TOTAL"]["amount_value_incomplete"]
    total_buys             = trades_summary["BUY"]["notional"]
    total_sells            = trades_summary["SELL"]["notional"]
    total_paid_fees        = trades_summary["TOTAL"]["fee"]

    buy_current_value      = trades_summary["BUY"]["amount_value"] # Current value of all buy trades - even if part of them have already been sold
    sell_current_value     = trades_summary["SELL"]["amount_value"] # Current value of all sell trades - somehow is the missing opportunity value
    volatile_assets        = buy_current_value - sell_current_value # still held
    liquid_assets          = equity - volatile_assets  # cash + liquid assets

    # --- cash & P&L figures -------------------------------------------
    net_earnings           = equity - net_investment  # after fees
    gross_earnings         = net_earnings + total_paid_fees  # before fees

    # --- multiples (gross) --------------------------------------------
    rvpi = equity / paid_in_capital if paid_in_capital > 0 else None # RVPI = Residual Value to Paid-In
    dpi  = distributions / paid_in_capital if paid_in_capital > 0 else None # DPI = Distributions to Paid-In
    tvpi = dpi + rvpi if None not in (dpi, rvpi) else None # TVPI = Total Value to Paid-In

    _display_performance_details(
        equity=equity,
        paid_in_capital=paid_in_capital,
        distributions=distributions,
        net_investment=net_investment,
        incomplete_data=incomplete_data,
        total_buys=total_buys,
        total_sells=total_sells,
        liquid_assets=liquid_assets,
        volatile_assets=volatile_assets,
        total_paid_fees=total_paid_fees,
        buy_current_value=buy_current_value,
        sell_current_value=sell_current_value,
        gross_earnings=gross_earnings,
        net_earnings=net_earnings,
        rvpi=rvpi,
        dpi=dpi,
        tvpi=tvpi,
        cash_asset=cash_asset,
        advanced_display=advanced_display
    )

    # Graph 1 --------------------------------------------------

    st.markdown("---")
    st.subheader("Multiples")
    fig1 = tvpi_gauge(tvpi)
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("---")
    st.subheader("Capital Breakdown")
    fig2 = go.Figure()

    gross_PL_color = CHART_COLORS['green'] if gross_earnings >= 0 else CHART_COLORS['red']
    steps_fig2 = [
        # label                 y-value                     measure      colour
        ("Net Investment",      net_investment,            "absolute",  CHART_COLORS['blue']),
        ("Gross P&L",           gross_earnings,            "relative",  gross_PL_color),
        ("Fees",               -total_paid_fees,           "relative",  CHART_COLORS['red']),
        ("Volatile Assets",    -volatile_assets,           "relative",  CHART_COLORS['blue']),
        ("Cash Equivalents",   -liquid_assets,             "relative",  CHART_COLORS['blue']),
    ]

    cum_base = 0
    for label, y_val, meas, colour in steps_fig2:
        fig2.add_trace(
            go.Waterfall(
                x=[label],
                y=[y_val],
                measure=[meas],
                base=cum_base if meas != "absolute" else None,
                increasing=dict(marker=dict(color=colour)),
                decreasing=dict(marker=dict(color=colour)),
                totals=dict(marker=dict(color=colour)),
                showlegend=False
            )
        )
        # Update running base for the next bar (only if not 'total')
        if meas != "total":
            cum_base += y_val

    fig1.update_layout(showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

    # # Graph 2 --------------------------------------------------
    # st.markdown("---")
    # st.subheader("Multiples")
    # color_dpi = CHART_COLORS['BLUE']
    # color_rvpi = CHART_COLORS['GREEN'] if (equity >= net_investment) else CHART_COLORS['RED']
    # color_tvpi = CHART_COLORS['GREEN'] if tvpi >= 1 else CHART_COLORS['RED']
    # if distributions > 0:
    #     fig2 = go.Figure()
    #     steps_fig2 = [
    #         # label                  y-value                     measure      colour
    #         ("DPI (Realized)",       dpi,                 "absolute",  color_dpi),
    #         ("RVPI (Unrealized)",    rvpi,                "relative",  color_rvpi),
    #         ("TVPI (Total)",         -tvpi,                "relative",  color_tvpi),
    #     ]

    #     cum_base = 0
    #     for label, y_val, meas, colour in steps_fig2:
    #         fig2.add_trace(
    #             go.Waterfall(
    #                 x=[label],
    #                 y=[y_val],
    #                 measure=[meas],
    #                 base=cum_base if meas != "absolute" else None,
    #                 increasing=dict(marker=dict(color=colour)),
    #                 decreasing=dict(marker=dict(color=colour)),
    #                 totals=dict(marker=dict(color=colour)),
    #                 showlegend=False
    #             )
    #         )
    #         # Update running base for the next bar (only if not 'total')
    #         if meas != "total":
    #             cum_base += y_val

    #     fig2.update_layout(showlegend=False)
    #     st.plotly_chart(fig2, use_container_width=True)