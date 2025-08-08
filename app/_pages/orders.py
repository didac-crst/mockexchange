"""orders.py

Streamlit page that displays the **order book** of MockExchange.

Key features
------------
* Pulls the most‑recent *N* orders from the REST back‑end (`get_orders`).
* Lets the user interactively **filter** by order *status*, *side*, *type* and *asset*.
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

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from app.services.api import get_orders, get_trades_overview, get_overview_capital
from ._helpers import (
    _add_details_column,
    _display_trades_details,
    _format_significant_float,
    advanced_filter_toggle,
    convert_to_local_time,
    fmt_side_marker,
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
# Number of colour‑fade steps between "brand‑new" and "old" rows.
N_VISUAL_DEGRADATIONS = int(os.getenv("N_VISUAL_DEGRADATIONS", 12))

# Slider defaults for the "tail" (how many recent orders to pull).
SLIDER_MIN = int(os.getenv("SLIDER_MIN", 10))
SLIDER_MAX = int(os.getenv("SLIDER_MAX", 1000))
SLIDER_STEP = int(os.getenv("SLIDER_STEP", 10))
SLIDER_DEFAULT = int(os.getenv("SLIDER_DEFAULT", 100))


# -----------------------------------------------------------------------------
# Main page renderer – Streamlit entry‑point
# -----------------------------------------------------------------------------

def render() -> None:  # noqa: D401 – imperative mood is clearer here
    """Render the **Order Book** page.

    Workflow
    --------
    1. Read user‑defined *tail* (number of rows) and **filters** from the
       sidebar/expander.
    2. Fetch the corresponding slice from REST – falling back to the
       full order book if the user chooses so.
    3. Sync filter selections with ``st.session_state`` so they persist
       across reruns. Implement **freeze** checkboxes allowing the user
       to keep a filter even after auto‑refresh.
    4. Build a human‑friendly dataframe (amount formatting, price/fee
       prettifiers, latency computation…).
    5. Style the rows according to their *age* so new activity pops out.
    6. Finally, display the table with a dynamic height capped at 800 px.
    """

    # Basic Streamlit page config
    st.set_page_config(page_title="Order Book")
    st.title("Order Book")

    # ------------------------------------------------------------------
    # Keep track of the auto‑refresh ticker so we can detect new reruns
    # ------------------------------------------------------------------
    curr_tick = st.session_state.get("refresh", 0)
    last_tick = st.session_state.get("_last_refresh_tick", None)

    # ------------------------------------------------------------------
    # 1) Expander – global filters (how much data to fetch)
    # ------------------------------------------------------------------
    filters_expander = st.expander("Filters", expanded=False)
    with filters_expander:
        limit_toggle = st.checkbox(
            "Fetch the whole order book", value=False, key="limit_toggle"
        )
        # ``tail=None`` signals the API client to drop the limit.
        tail = None if limit_toggle else st.slider(
            "Max number of last orders to load",
            min_value=SLIDER_MIN,
            max_value=SLIDER_MAX,
            value=SLIDER_DEFAULT,
            step=SLIDER_STEP,
            key="tail_slider",
        )

    # ------------------------------------------------------------------
    # 2) Fetch raw data from the API and pre‑process
    # ------------------------------------------------------------------
    base = os.getenv("UI_URL", "http://localhost:8000")
    # ``_add_details_column`` injects the 🡒 Details link.
    df_raw = get_orders(tail=tail).pipe(_add_details_column, base_url=base)
    if df_raw.empty:
        st.info("No orders found.")
        return  # early exit – nothing else to do

    trades_summary, cash_asset = get_trades_overview()
    summary_capital = get_overview_capital()

    # ------------------------------------------------------------------
    # Sidebar – advanced equity breakdown & toggle
    # ------------------------------------------------------------------

    advanced_display = advanced_filter_toggle()

    # -------------------------------------------------------------------
    # 3) Display trade metrics (simple vs advanced)
    # ------------------------------------------------------------------

    _display_trades_details(summary_capital, trades_summary, cash_asset, df_raw, advanced_display)

    # `df_copy` will be mutated for visual purposes; keep df_raw pristine.
    df_copy = df_raw.copy()
    df_copy["Posted"] = df_copy["ts_create"].map(convert_to_local_time)
    df_copy["Updated"] = df_copy["ts_update"].map(convert_to_local_time)
    # Split "BTC/USDT" → Asset="BTC", quote_asset="USDT"
    df_copy[["Asset", "quote_asset"]] = df_copy["symbol"].str.split("/", expand=True)

    # ------------------------------------------------------------------
    # 3) Build filter option lists & ensure session_state consistency
    # ------------------------------------------------------------------
    def _sync_filter_state(key: str, options: list[str]) -> None:
        """Guarantee that ``st.session_state[key]`` exists & is valid."""
        if key not in st.session_state:
            # First visit → pre‑select all choices.
            st.session_state[key] = options[:]
            return
        # Drop selections that disappeared in the new dataset.
        st.session_state[key] = [v for v in st.session_state[key] if v in options]

    status_opts = sorted(
        df_copy["status"].str.replace("_", " ").str.capitalize().unique()
    )
    side_opts = sorted(df_copy["side"].str.upper().unique())
    type_opts = sorted(df_copy["type"].str.capitalize().unique())
    asset_opts = sorted(df_copy["Asset"].unique())

    FILTER_KEYS = ["status_filter", "side_filter", "type_filter", "asset_filter"]

    # If the user changed the *tail* slider, reset all filters (new context).
    if st.session_state.get("_last_tail") != tail:
        for k in FILTER_KEYS:
            st.session_state.pop(k, None)
        st.session_state["_last_tail"] = tail

    # Keep the stored selections in sync with the current data universe.
    _sync_filter_state("status_filter", status_opts)
    _sync_filter_state("side_filter", side_opts)
    _sync_filter_state("type_filter", type_opts)
    _sync_filter_state("asset_filter", asset_opts)

    # ------------------------------------------------------------------
    # 4) Render filter widgets (multiselects + freeze checkboxes)
    # ------------------------------------------------------------------
    with filters_expander:
        left, right = st.columns([0.8, 0.2])

        # Right column → reset button
        with right:
            st.write("")  # spacer for alignment
            if st.button("🔄 Reset filters"):
                for k in FILTER_KEYS:
                    st.session_state.pop(k, None)
                # Re‑seed defaults (select all)
                _sync_filter_state("status_filter", status_opts)
                _sync_filter_state("side_filter", side_opts)
                _sync_filter_state("type_filter", type_opts)
                _sync_filter_state("asset_filter", asset_opts)
                # Also reset the "freeze" flags so UI stays intuitive.
                st.session_state.update(
                    reset_status_filter=False,
                    reset_side_filter=False,
                    reset_type_filter=False,
                    reset_asset_filter=False,
                )
                st.rerun()

        # Left column → actual controls
        with left:
            status_sel = st.multiselect("Status", status_opts, key="status_filter")
            status_freeze = st.checkbox(
                "Freeze status filter on reload", value=False, key="reset_status_filter"
            )
            side_sel = st.multiselect("Side", side_opts, key="side_filter")
            side_freeze = st.checkbox(
                "Freeze side filter on reload", value=False, key="reset_side_filter"
            )
            type_sel = st.multiselect("Type", type_opts, key="type_filter")
            type_freeze = st.checkbox(
                "Freeze type filter on reload", value=False, key="reset_type_filter"
            )
            asset_sel = st.multiselect("Asset (base)", asset_opts, key="asset_filter")
            asset_freeze = st.checkbox(
                "Freeze asset filter on reload", value=False, key="reset_asset_filter"
            )

    # ------------------------------------------------------------------
    # Freeze logic – drop selections only when NOT frozen on a new refresh
    # ------------------------------------------------------------------
    is_new_refresh = (last_tick is None) or (curr_tick != last_tick)
    if is_new_refresh and not status_freeze:
        st.session_state.pop("status_filter", None)
    if is_new_refresh and not side_freeze:
        st.session_state.pop("side_filter", None)
    if is_new_refresh and not type_freeze:
        st.session_state.pop("type_filter", None)
    if is_new_refresh and not asset_freeze:
        st.session_state.pop("asset_filter", None)
    # Store tick for next run so we can detect changes.
    st.session_state["_last_refresh_tick"] = curr_tick

    # ------------------------------------------------------------------
    # 5) Apply the composite mask to the dataframe
    # ------------------------------------------------------------------
    mask = (
        df_copy["status"].str.replace("_", " ").str.capitalize().isin(status_sel)
        & df_copy["side"].str.upper().isin(side_sel)
        & df_copy["type"].str.capitalize().isin(type_sel)
        & df_copy["Asset"].isin(asset_sel)
    )
    df = df_copy[mask].copy()

    # Friendly caption – how much data did we load vs display?
    if tail is not None:
        st.caption(
            f"🧾 Loaded {len(df_raw)} rows (showing {len(df)}) from last {tail} orders"
        )
    else:
        st.caption(
            f"🧾 Loaded {len(df_raw)} rows (showing {len(df)}) from the whole order book"
        )

    # ------------------------------------------------------------------
    # 6) Derive helper columns (latency, formatted quantities/prices…)
    # ------------------------------------------------------------------
    ts_create_num = pd.to_numeric(df["ts_create"], errors="coerce")
    ts_finish_num = pd.to_numeric(df["ts_finish"], errors="coerce")

    df["Exec. latency"] = (
        (ts_finish_num - ts_create_num).div(1000).round(2).where(ts_finish_num.notna(), "")
    )

    # Human‑friendly quantity formatting (strip tiny rounding remainders)
    df["Req. Qty"] = df["amount"].map(lambda v: _format_significant_float(value=v))
    df["Filled Qty"] = df["actual_filled"].apply(lambda v: _format_significant_float(value=v))

    # Append currency codes where applicable
    df["Limit price"] = df.apply(
        lambda r: _format_significant_float(value=r.limit_price, unity=r.quote_asset),
        axis=1,
    )
    df["Exec. price"] = df.apply(
        lambda r: _format_significant_float(value=r.price, unity=r.quote_asset),
        axis=1,
    )

    # Notional & fee prettifiers ------------------------------------------------
    df["Reserved notional"] = df.apply(
        lambda r: _format_significant_float(value=r.reserved_notion_left, unity=r.notion_currency),
        axis=1,
    )
    df["Actual notional"] = df.apply(
        lambda r: _format_significant_float(value=r.actual_notion, unity=r.notion_currency),
        axis=1,
    )
    df["Reserved fee"] = df.apply(
        lambda r: _format_significant_float(value=r.reserved_fee_left, unity=r.fee_currency),
        axis=1,
    )
    df["Actual fee"] = df.apply(
        lambda r: _format_significant_float(value=r.actual_fee, unity=r.fee_currency),
        axis=1,
    )

    # Normalise naming for the final view --------------------------------------
    df["Order ID"] = df["id"].astype(str)
    df["Exec. latency"] = df["Exec. latency"].apply(
        lambda v: f"{v:,.2f} s" if isinstance(v, (int, float)) else ""
    )
    df["Side"] = df["side"].map(fmt_side_marker)
    df["Type"] = df["type"].str.capitalize()
    df["Status"] = df["status"].str.replace("_", " ").str.capitalize()

    # Select & order columns for the UI
    df_view = (
        df[
            [
                "Details",
                "Order ID",
                "Posted",
                "Updated",
                "Asset",
                "Side",
                "Status",
                "Type",
                "Limit price",
                "Exec. price",
                "Req. Qty",
                "Filled Qty",
                "Reserved notional",
                "Actual notional",
                "Reserved fee",
                "Actual fee",
                "Exec. latency",
            ]
        ]
        .sort_values("Updated", ascending=False)
        .reset_index(drop=True)
    )

    # ------------------------------------------------------------------
    # 6½) Style – row fading for recently updated orders
    # ------------------------------------------------------------------
    styler = (
        df_view.style
        .format({"Details": lambda html: html}, escape="html")
        .apply(
            _row_style,
            axis=1,
            levels=N_VISUAL_DEGRADATIONS,
            fresh_window_s=FRESH_WINDOW_S,
        )
    )

    # ------------------------------------------------------------------
    # 7) Display the dataframe
    # ------------------------------------------------------------------
    # Dynamic height: ~35 px per row, but cap at 800 px for usability.
    height_calc = min(35 * (1 + len(df_view)) + 5, 800)

    st.dataframe(
        styler,
        hide_index=True,
        use_container_width=True,
        height=height_calc,
        column_config={
            # render the URL as a clickable link
            "Details": st.column_config.LinkColumn(
                label=" ",
                display_text="🔍",    # fixed magnifier emoji
                max_chars=1,          # don’t truncate your emoji!
                help="View order details",
            ),
        },
    )