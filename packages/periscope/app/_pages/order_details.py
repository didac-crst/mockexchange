"""order_details.py

Streamlit sub‑page that shows a **single order** in depth.

It is opened when the user clicks the 🔍 link in the Orders dataframe.
The page:

1. Pulls the order (plus its step‑by‑step *history*) from the REST API.
2. Shows headline metrics (status, type, timestamps…).
3. Lets the user **cancel** the order if it is still open.
4. Displays a compact summary grid (amounts, notional, fee).
5. Renders the full *order history* table.

Only comments & docstrings were added – runtime logic is unchanged.
"""

from __future__ import annotations

# Standard library -------------------------------------------------------------
from datetime import datetime, timezone
import os
from pathlib import Path
import requests

# Third‑party ------------------------------------------------------------------
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# First‑party ------------------------------------------------------------------
from ._helpers import _format_significant_float, fmt_side_marker, update_page, convert_to_local_time
from ._colors import _STATUS_LIGHT

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
load_dotenv(Path(__file__).parent.parent.parent / ".env")
API_BASE = os.getenv("API_BASE", "http://localhost:8000")  # REST back‑end

# -----------------------------------------------------------------------------
# Page renderer
# -----------------------------------------------------------------------------

def render(order_id: str) -> None:  # noqa: D401
    """Render the *Order Details* page for a given ``order_id``.

    Parameters
    ----------
    order_id : str
        Unique identifier of the order (UUID or int from database).
    """

    # ------------------------------------------------------------------
    # Formatting lambdas (local closures keep code below concise)
    # ------------------------------------------------------------------
    fmt = lambda v: _format_significant_float(v)  # noqa: E731
    fmt_notion = lambda v: _format_significant_float(v, data.get('notion_currency'))  # noqa: E731
    fmt_fee = lambda v: _format_significant_float(v, data.get('fee_currency'))  # noqa: E731

    # ------------------------------------------------------------------
    # Back navigation – remove "order_id" query param and rerun main page
    # ------------------------------------------------------------------
    if st.button("← Back to Order Book"):
        if "order_id" in st.query_params:
            del st.query_params["order_id"]
            update_page(page="Order Book")  # update query params
        st.rerun()

    # ------------------------------------------------------------------
    # Fetch order (with history) from REST API
    # ------------------------------------------------------------------
    url = f"{API_BASE}/orders/{order_id}?include_history=true"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # broad but adequate for a UI wrapper
        st.error(f"Could not load history:\n```\n{exc}\n```")
        return

    # In MockExchange errors come back as {"error": "..."} dict.
    if "error" in data:
        st.info(
            "No history found for order ID " f"{order_id} – Probably it has been pruned."
        )
        return

    # ------------------------------------------------------------------
    # 0) Derive helper variables for display
    # ------------------------------------------------------------------
    ticker = data.get("symbol")
    asset = ticker.split("/")[0]
    side = data.get("side")
    is_buy = (side == "buy")
    arrow_side = fmt_side_marker(side)  # format side with arrow

    _status = data.get("status")
    status_light = _STATUS_LIGHT.get(_status, "⚪")  # coloured emoji bullet
    status = _status.replace("_", " ").capitalize()

    # Type info → show limit price inline when applicable
    type_info = (
        f"{data.get('type').capitalize()} "
        f"[{fmt_notion(data.get('limit_price', 0))}]"
        if data.get("type") == "limit"
        else data.get("type").capitalize()
    )

    # Average execution price (None or 0 ⇢ blank)
    _price = data.get("price", 0)
    price = (
        fmt_notion(_price) if _price not in (None, 0) else None
    )

    # Time‑stamps -------------------------------------------------------
    placed_ts = convert_to_local_time(data.get("ts_create"))
    updated_ts = convert_to_local_time(data.get("ts_update"))
    executed_ts = convert_to_local_time(data.get("ts_finish")) if data.get("ts_finish") else None

    is_new = _status == "new"
    is_partial = "partially" in _status
    is_finished = executed_ts is not None
    latency = (
        f"{(data.get('ts_finish') - data.get('ts_create')) / 1000:,.2f} seconds"
        if is_finished
        else "N/A"
    )

    # ------------------------------------------------------------------
    # 1) Overview metrics (three columns)
    # ------------------------------------------------------------------
    st.set_page_config(page_title=f"Order {order_id}")
    st.header(f"{status_light} {arrow_side} Order #{order_id} [{ticker}]")

    c1, c2, c3 = st.columns(3)

    # Column 1 – basic id & status
    with c1:
        st.metric("Asset", asset)
        st.metric("Status", status)

    # Column 2 – type & avg price
    with c2:
        st.metric("Type", type_info)
        if price is not None:
            st.metric("Average price", price)

    # Column 3 – timestamps & latency (or cancel button if open)
    with c3:
        st.metric("Created", placed_ts)
        if not is_new:
            st.metric("Finished" if is_finished else "Updated", updated_ts)
        if is_finished:
            st.metric("Latency", latency)
        else:
            # Allow user to cancel still‑open orders
            if st.button("Cancel Order"):
                cancel_url = f"{API_BASE}/orders/{order_id}/cancel"
                try:
                    cancel_resp = requests.post(cancel_url, timeout=10)
                    cancel_resp.raise_for_status()
                    st.success("Order cancelled successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not cancel order:\n```\n{exc}\n```")

    st.markdown("---")

    # ------------------------------------------------------------------
    # 2) Compact summary grid (amount / notional / fee)
    # ------------------------------------------------------------------
    st.subheader("Quick summary")

    # Raw numeric values from the payload ------------------------------
    initial_amount = data.get("amount", 0)
    filled_amount = data.get("actual_filled", 0)
    remaining_amount = initial_amount - filled_amount

    initial_notion = data.get("initial_booked_notion", 0)
    actual_notion = data.get("actual_notion", 0)
    remaining_notion = data.get("reserved_notion_left", 0)

    initial_fee = data.get("initial_booked_fee", 0)
    actual_fee = data.get("actual_fee", 0)
    remaining_fee = data.get("reserved_fee_left", 0)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Asset ▶ Actual filled", fmt(filled_amount))
        st.metric("Asset ▶ Initial requested", fmt(initial_amount))
        if is_partial:
            st.metric("Asset ▶ Remaining", fmt(remaining_amount))

    with col2:
        actual_str = "Notional ▶ Actual paid" if is_buy else "Notional ▶ Actual received"
        st.metric(actual_str, fmt_notion(actual_notion))
        if is_buy:
            st.metric("Notional ▶ Initial booked", fmt_notion(initial_notion))
            if is_partial:
                st.metric("Notional ▶ Still booked", fmt_notion(remaining_notion))

    with col3:
        st.metric("Fee ▶ Actual paid", fmt_fee(actual_fee))
        st.metric("Fee ▶ Initial booked", fmt_fee(initial_fee))
        if is_partial:
            st.metric("Fee ▶ Still booked", fmt_fee(remaining_fee))

    st.markdown("---")

    # ------------------------------------------------------------------
    # 3) Fill history table
    # ------------------------------------------------------------------
    history = data.get("history", {})

    # Convert nested dict {step → {..}} into list[dict] for DataFrame
    records: list[dict] = []
    for step in sorted(history.keys(), key=int):
        rec = history[step]
        price = fmt_notion(rec.get("price", None))
        filled = fmt(rec.get("actual_filled", None))
        remaining = fmt(rec.get("amount_remain", None))
        actual_notion = fmt_notion(rec.get("actual_notion", None))
        reserved_notion_left = fmt_notion(rec.get("reserved_notion_left", None))
        actual_fee = fmt_fee(rec.get("actual_fee", None))
        reserved_fee_left = fmt_fee(rec.get("reserved_fee_left", None))
        records.append(
            {
                "Step": int(step),
                "Time": convert_to_local_time(rec.get("ts")),
                "Status": rec.get("status").replace("_", " ").capitalize(),
                "Price": price,
                "Actual filled": filled,
                "Remaining": remaining,
                "Actual Notional": actual_notion,
                "Notional left": reserved_notion_left,
                "Actual Fee": actual_fee,
                "Fee left": reserved_fee_left,
                "Comment": rec.get("comment", ""),
            }
        )

    df_hist = pd.DataFrame(records)

    st.subheader("Order history")
    st.dataframe(df_hist, hide_index=True, use_container_width=True)
    st.markdown(
        "This table shows the step‑by‑step history of the order."
    )