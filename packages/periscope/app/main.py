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
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone   #  ← add datetime import

import streamlit as st
from streamlit_autorefresh import st_autorefresh

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
load_dotenv(Path(__file__).parent.parent / ".env")
APP_TITLE = os.getenv("APP_TITLE", "")
LOGO_FILE= os.getenv("LOGO_FILE", "")
LOCAL_TZ_str = os.getenv("LOCAL_TZ", "UTC")  # e.g. "Europe/Berlin"

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
# Local imports (after Streamlit initialisation)
# -----------------------------------------------------------------------------
from app.config import settings
from app._pages import portfolio, orders, performance, order_details
from app._pages._helpers import update_page, TS_FMT, convert_to_local_time

# -----------------------------------------------------------------------------
# 1) Sidebar – navigation radio
# -----------------------------------------------------------------------------
if LOGO_FILE != "":
    LOGO_PATH = Path(__file__).parent / "misc" / LOGO_FILE
    st.sidebar.image(LOGO_PATH, width=500)
if APP_TITLE != "":
    st.sidebar.title(APP_TITLE)

# Pull current URL parameters as early as possible
params = st.query_params                     # returns a QueryParamsProxy
oid    = params.get("order_id")              # already a single value (or None)

# Default to portfolio if param missing
initial_page = params.get("page", "Performance")    # default to "Performance"

# Two-page app: Portfolio ↔ Order Book
page = st.sidebar.radio(
    "Navigate",
    ("Performance", "Portfolio", "Order Book"),
    index=["Performance", "Portfolio", "Order Book"].index(initial_page),
    key="sidebar_page",
    on_change=update_page # Update URL query-params when page changes
)

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
utc_now = datetime.now(timezone.utc).strftime(TS_FMT)
# Put it wherever you like: sidebar, main body, or page footer
local_time = convert_to_local_time(datetime.now(timezone.utc), TS_FMT)
st.sidebar.metric(
    label="🕒 Last refresh:",
    value=local_time,
    delta=LOCAL_TZ_str,
    delta_color="off",
)