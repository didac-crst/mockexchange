"""main.py

Streamlit **entry-point** for the MockExchange dashboard.

Responsibilities
----------------
* Define global page layout (wide view, expanded sidebar, title).
* Implement a simple **navigation radio** – "Portfolio" vs *Order Book*.
* Poll URL query-params so a direct link such as
  ``...?order_id=123`` opens the *Order Details* sub-page immediately.
* Trigger an **auto-refresh** every *REFRESH_SECONDS* (defined in app
  configuration) so the UI stays live without manual reloads.

Only comments and docstrings were added – runtime behaviour is exactly
unchanged.
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Third-party imports
# -----------------------------------------------------------------------------
import os
from datetime import UTC, datetime  #  ← add datetime import
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

# -----------------------------------------------------------------------------
# Local imports (after Streamlit initialisation)
# -----------------------------------------------------------------------------
from app._pages import order_details, orders, performance, portfolio
from app._pages._helpers import TS_FMT, convert_to_local_time, update_page
from app.config import settings

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
APP_TITLE = settings().get("APP_TITLE", "")
LOGO_FILE = settings().get("LOGO_FILE", "")
LOCAL_TZ_str = settings().get("LOCAL_TZ", "UTC")  # e.g. "Europe/Berlin"

# -----------------------------------------------------------------------------
# 0) Global page configuration – must run before any Streamlit call
# -----------------------------------------------------------------------------
# * wide layout gives more room to tables
# * keep the sidebar expanded by default so navigation is obvious
st.set_page_config(
    page_icon=":chart_with_upwards_trend:",  # Custom icon can be set
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# 1) Sidebar – navigation radio
# -----------------------------------------------------------------------------
if LOGO_FILE != "":
    LOGO_PATH = Path(__file__).parent / "misc" / LOGO_FILE
    st.sidebar.image(LOGO_PATH, width=500)
if APP_TITLE != "":
    st.sidebar.title(APP_TITLE)

# Pull current URL parameters as early as possible
params = st.query_params  # returns a QueryParamsProxy
oid = params.get("order_id")  # already a single value (or None)

# Default to portfolio if param missing
initial_page = params.get("page", "Performance")  # default to "Performance"

# Only show navigation when not viewing order details
if not oid:
    # Three-page app: Performance ↔ Portfolio ↔ Order Book
    st.sidebar.markdown("**Navigate:**")
    
    # Create indentation using columns: 10% spacer + 80% buttons
    _1, col2, _3 = st.sidebar.columns([0.1, 0.8, 0.1])
    
    with col2:
        # Determine which page is currently active
        current_page = initial_page
        
        # Performance button with highlighting
        if current_page == "Performance":
            st.button("Performance", key="nav_performance_active", use_container_width=True, disabled=True, type="secondary")
        else:
            if st.button("Performance", key="nav_performance", use_container_width=True):
                st.query_params["page"] = "Performance"
                st.rerun()
        
        # Portfolio button with highlighting
        if current_page == "Portfolio":
            st.button("Portfolio", key="nav_portfolio_active", use_container_width=True, disabled=True, type="secondary")
        else:
            if st.button("Portfolio", key="nav_portfolio", use_container_width=True):
                st.query_params["page"] = "Portfolio"
                st.rerun()
        
        # Order Book button with highlighting
        if current_page == "Order Book":
            st.button("Order Book", key="nav_orders_active", use_container_width=True, disabled=True, type="secondary")
        else:
            if st.button("Order Book", key="nav_orders", use_container_width=True):
                st.query_params["page"] = "Order Book"
                st.rerun()
    
    page = current_page
else:
    # Add navigation buttons to return to different pages
    st.sidebar.markdown("**Navigate back to:**")
    
    # Create indentation using columns: 10% spacer + 80% buttons
    _1, col2, _3 = st.sidebar.columns([0.1, 0.8, 0.1])
    
    with col2:
        if st.button("Performance", key="back_to_performance", use_container_width=True):
            # Navigate back to performance page
            st.query_params.clear()
            st.query_params["page"] = "Performance"
            st.rerun()
        
        if st.button("Portfolio", key="back_to_portfolio", use_container_width=True):
            # Navigate back to portfolio page
            st.query_params.clear()
            st.query_params["page"] = "Portfolio"
            st.rerun()
        
        if st.button("Order Book", key="back_to_orders", use_container_width=True):
            # Navigate back to order book page
            st.query_params.clear()
            st.query_params["page"] = "Order Book"
            st.rerun()

# -----------------------------------------------------------------------------
# 2) Auto-refresh – keeps data up-to-date without F5
# -----------------------------------------------------------------------------
# The key "refresh" is also used by child pages to detect reruns.
st_autorefresh(interval=settings()["REFRESH_SECONDS"] * 1000, key="refresh")

# -----------------------------------------------------------------------------
# 3) Routing logic – order details page has priority
# -----------------------------------------------------------------------------
if oid:
    # Specific order requested via URL – render its dedicated page
    order_details.render(order_id=oid)
else:
    # Otherwise fall back to the radio-selected main page
    if page == "Performance":
        performance.render()
    elif page == "Portfolio":
        portfolio.render()
    else:  # page == "Order Book"
        orders.render()

st.sidebar.markdown("---")
# ────────────────────────────────────────────────────────────────
# UTC clock (updates on every autorefresh)
# ────────────────────────────────────────────────────────────────
utc_now = datetime.now(UTC).strftime(TS_FMT)
# Put it wherever you like: sidebar, main body, or page footer
local_time = convert_to_local_time(datetime.now(UTC), TS_FMT)
st.sidebar.metric(
    label="🕒 Last refresh:",
    value=local_time,
    delta=LOCAL_TZ_str,
    delta_color="off",
)
