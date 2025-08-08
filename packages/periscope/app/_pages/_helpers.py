"""_helpers.py

Utility helpers shared by multiple Streamlit pages.

The module groups three kinds of helpers:

1. **Formatting helpers** – e.g. `_remove_small_zeros` to strip trailing
   insignificant zeros from decimal strings.
2. **DataFrame enrichment** – `_add_details_column` injects a hyperlink
   column so each order row can point to its *Order Details* popup.
3. **Advanced equity display** – `_display_advanced_details` pulls a
   balance-vs-orderbook summary from the API and shows it as Streamlit
   metrics, highlighting mismatches with a warning icon.

Only **docstrings and comments** have been added; no functional changes.
"""

from __future__ import annotations
from pathlib import Path

# Third-party -----------------------------------------------------------------
import math, time, os
from typing import Literal
from datetime import datetime, timezone
from dotenv import load_dotenv
from zoneinfo import ZoneInfo  # Python 3.9+
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Project ---------------------------------------------------------------------
from app.services.api import get_assets_overview

load_dotenv(Path(__file__).parent.parent.parent / ".env")
# -----------------------------------------------------------------------------
# 0) Global page configuration – must run before any Streamlit call
# -----------------------------------------------------------------------------
def update_page(page: None | str = None) -> None:
    """Update the ?page=... query-parameter in the URL.
    Parameters
    ----------
    page : None | str
        The new page value to set or None to reset to the default.
    """
    # This overwrites/sets the ?page=... query-param
    if page is None:
        st.query_params.update(page=st.session_state.sidebar_page)
    else:
        st.query_params.update(page=page)

def advanced_filter_toggle() -> bool:
    """
    Render a checkbox in the sidebar to toggle advanced details display.
    Returns
    -------
    bool
        The current state of the advanced details toggle.
    Notes
    -----
    The function initializes the session state on first run and updates the
    query parameters if the user changes the toggle.
    """
    params = st.query_params                                        # returns a QueryParamsProxy
    st.sidebar.header("Filters")

    filter_advanced = params.get("filter_advanced", "False")        # default to False

    # Initialize session state on first run
    if "advanced_display" not in st.session_state:
        st.session_state.advanced_display = (filter_advanced == "True")  # convert to bool

    # Render checkbox with current session state
    # Do NOT pass `value=` — let Streamlit use session_state["advanced_display"]
    advanced_display = st.sidebar.checkbox(
        "Display advanced details",
        key="advanced_display"
    )

    # Only update query params if the user changes the toggle
    if advanced_display != (filter_advanced == "True"):
        st.query_params.update(filter_advanced="True" if advanced_display else "False")
    return advanced_display

# -----------------------------------------------------------------------------
# 1) Formatting helpers
# -----------------------------------------------------------------------------

LOCAL_TZ_str = os.getenv("LOCAL_TZ", "UTC")  # e.g. "Europe/Berlin"
LOCAL_TZ = ZoneInfo(LOCAL_TZ_str)   # ← now a tzinfo
TS_FMT = "%d/%m %H:%M:%S"  # Timestamp format for human-readable dates
ZERO_DISPLAY = "--"  # Default display for zero values
_W = "⚠️"  # warning icon – reused inline for brevity
CHART_COLORS = {
    "red_dark": "#8B0000",
    "red": "#C62828",
    "orange": "#EF6C00",
    "yellow": "#FFEB3B",
    "lime": "#B4FF05",
    "green": "#00DD0B",
    "blue": "#0EC1FD",
    "purple": "#9B00FB"
}

# Local lambdas for consistent formatting ---------------------------
fmt_num = lambda v, warning = False: f"{v:,.0f}" if not warning else f"^{_W} {v:,.0f}"
fmt_percent = lambda v, warning = False: f"{v:.2%}" if not warning else f"^{_W} {v:.2%}"
fmt_cash = lambda v, cash_asset, warning = False: f"{v:,.2f} {cash_asset}" if not warning else f"^{_W} {v:,.2f} {cash_asset}"

def _human_ts(ms: int | None) -> str:  # noqa: D401 – keep short description style
    """Convert **epoch‑milliseconds** to the user's local time‑zone.

    Parameters
    ----------
    ms : int | None
        Milliseconds since *Unix epoch* (UTC) or ``None``.

    Returns
    -------
    str
        Formatted timestamp ``YYYY-MM-DD HH:MM:SS`` or an empty string
        so the dataframe cell renders blank for ``null`` values.
    """

    if ms is None:
        return ""
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone()
    return dt.strftime(TS_FMT)

def convert_to_local_time(ts: int | datetime, fmt: str = TS_FMT) -> str:
    """
    Convert a UTC timestamp (seconds or ms) or datetime to the user's local time zone.
    This function handles both integer timestamps (epoch seconds) and
    datetime objects.

    Parameters
    ----------
    ts : int | datetime
        The UTC datetime to convert.
    fmt : str
        The format string to use for formatting the local time.

    Returns
    -------
    str
        The formatted local time.
    """
    # 1) If it's numeric, auto-scale ms → s
    if isinstance(ts, (int, float)):
        # If it's improbably large for seconds, assume ms
        if ts > 1e11:
            ts = ts / 1000.0
        ts = datetime.fromtimestamp(ts, tz=timezone.utc)
        # 2) If naive datetime, assume UTC
    elif isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    else:
        return ZERO_DISPLAY
    
    # 3) Convert to local tz and format
    return ts.astimezone(LOCAL_TZ).strftime(fmt)

def _remove_small_zeros(num_str: str) -> str:  # noqa: D401 – short desc fine
    """Strip redundant trailing zeros from a *decimal* string.

    Examples
    --------
    >>> _remove_small_zeros('1.230000')
    '1.23'
    >>> _remove_small_zeros('42.000')
    '42'

    Notes
    -----
    The function assumes the input is already formatted to the desired
    decimal precision (typically 6 d.p. in this app) and only performs a
    *pure string* operation – no rounding is applied.
    """
    try:
        # ``rstrip`` twice: first remove zeros, then a dangling decimal point.
        return num_str.rstrip("0").rstrip(".")
    except (ValueError, TypeError):
        # Fall back to the original string if parsing fails (e.g. None).
        return num_str

# -----------------------------------------------------------------------------
# 2) DataFrame manipulation helpers
# -----------------------------------------------------------------------------

def _add_details_column(
    df: pd.DataFrame,
    base_url: str,
    *,
    order_id_col: str = "id",
    new_col: str = "Details",
    path_template: str = "?order_id={oid}",
    text: str = "🔍",
) -> pd.DataFrame:  # noqa: D401 – keep same signature
    """Append a column with **HTML links** to the order-details page.

    Parameters
    ----------
    df : pd.DataFrame
        Input frame; *must* contain ``order_id_col``.
    base_url : str
        Base URL where the Streamlit app is served (currently unused but
        kept for future external links).
    order_id_col : str, default ``"id"``
        Column name holding order IDs.
    new_col : str, default ``"Details"``
        Name of the column to add.
    path_template : str
        Relative URL pattern where ``{oid}`` is interpolated – keeps the
        user in the same tab.
    text : str, default "🔍"
        Anchor text / icon for the hyperlink.

    Returns
    -------
    pd.DataFrame
        *Copy* of the original with an extra column of raw ``<a href>``
        strings – suitable for ``styler.format(escape="html")`` to render.
    """
    df = df.copy()

    def make_url(oid: str) -> str:
        # Example →  "?order_id=123&page=Orders"
        return path_template.format(oid=oid)

    if not df.empty:
        df[new_col] = df[order_id_col].astype(str).map(make_url)
    return df

def _format_significant_float(value: float | int | None, unity: str | None = None) -> str:
    """
    Format a float into a human-readable string with dynamic precision.

    Behavior:
    - For absolute values >= 1: formats with comma as thousands separator and 2 decimal places.
      Example:  1234.6565  → "1,234.66"
                -1234.6565 → "-1,234.66"

    - For absolute values < 1: keeps leading zeros and shows the first 2 significant decimal digits.
      Example:  
                0.6565     → "0.66"
               -0.06565    → "-0.066"
                0.006565   → "0.0066"
               -0.0006565  → "-0.00066"

    - For exact zero (positive or negative): returns a fixed display (e.g. "0.00")

    Args:
        value (float | int | None): The number to format.
        unity (str | None): Optional unit/currency suffix (e.g., "USD").

    Returns:
        str: The formatted number as a string.
    """
    if value is None or pd.isna(value) or value == 0.0:
        return ZERO_DISPLAY

    is_negative = value < 0
    abs_value = abs(value)

    if abs_value >= 1:
        formatted = f"{abs_value:,.2f}"
    else:
        # true “round to two significant digits”:
        # floor(log10(abs_value)) gives you the exponent of the leading sig‑digit.
        exp = math.floor(math.log10(abs_value))
        decimals = 2 - exp - 1
        rounded = round(abs_value, decimals)
        formatted = f"{rounded:.{decimals}f}"

    if is_negative:
        formatted = "-" + formatted
    if unity:
        formatted += f" {unity}"

    return formatted


fmt_side_marker = lambda side: {"BUY": "↗ BUY", "SELL": "↘ SELL"}[side.upper()]  # noqa: E731

def get_tempo_avg_trade_summary(df_raw: pd.DataFrame, equity: float) -> tuple[dict[str, dict[str, float]],str]:
    """Compute the hourly average trade summary"""
    # Get the order creation pace:
    # 1. Select & copy
    
    start_time = df_raw["ts_update"].min() / 1000  # Convert to seconds
    timespan = time.time() - start_time # in seconds
    # Executed orders
    df_filt = df_raw[['id','side','actual_notion', 'actual_fee']].copy()
    df_filt = df_filt[df_filt['actual_notion'] > 0]  # Filter out zero notional orders

    # Group by side and sum the theoretical notional and count
    # the number of orders for each side.
    sides = ["buy", "sell"]

    df_filt_agg = (
        df_filt
        .groupby("side")
        .agg(
            total_notional=("actual_notion", "sum"),
            order_count   =("actual_notion", "count"),
            total_fee     =("actual_fee",    "sum"),
        )
        # guarantee both rows – missing ones become 0
        .reindex(sides, fill_value=0)        # Force both BUY and SELL sides
        .reset_index()
    )
    # Convert dataframe to dict for display
    df_filt_agg = df_filt_agg.set_index('side') * 3600 / timespan  # convert to per-hour rate

    if df_filt_agg["total_notional"].sum() < (equity/10):
        # If the total notional is more than equity, convert to daily rate
        df_filt_agg = df_filt_agg * 24
        period_agg = "day"
    else:
        period_agg = "h"

    avg_trade_summary = df_filt_agg.to_dict(orient='index')  # convert to dict for display
    # Add a global summary entry
    avg_trade_summary["global"] = {}
    for metric in df_filt_agg.columns:
        avg_trade_summary["global"][metric] = df_filt_agg[metric].sum()
    return avg_trade_summary, period_agg

# -------------------------------------------------------------------------
# 3) Streamlit metric helpers  (paste into _helpers.py or a new utils_metrics.py)
# -------------------------------------------------------------------------

def _mk_key(label: str) -> str:
    """Stable session-state key from the metric label."""
    return f"_prev_{label.replace(' ', '_').lower()}"

def show_metric(
    label: str,
    value: float | None,
    *,
    value_type: Literal["integer", "percent", "normal"] = "normal",
    unit: str = "",
    incomplete: bool = False,
    # delta options ---------------------------------------------------
    baseline: float | None = None,          # None  → compare to last run
    delta_fmt: Literal["raw", None] = "raw",
    delta_color_rule: Literal["value", "delta"] = "value",
    # value-colour options -------------------------------------------
    neutral_100: bool = False,              # treat <1 as red
    bad_if_neg: bool = True,
    incomplete_display: bool = False,         # Metric to display when incomplete occurs
) -> None:
    """
    Print one st.metric with colour & delta handled.

    Parameters
    ----------
    label : str
        Label shown above the number.
    value : float | None
        Latest value. None → prints ZERO_DISPLAY and skips delta.
    value_type: Literal["integer", "percent", "normal"]
        How to format the main value.
    unit : str
        Suffix (e.g. "€", "×", "%", "USDT").
    incomplete : bool
        If True, show ⚠️ icon before the figure.
    baseline : float | None
        Reference value. If None, use the value stored in session_state.
    delta_fmt : Literal["raw", "percent", None]
        How to format the delta column.
    delta_color_rule : Literal["value", "delta"]
        • "value"  → red/green based on *value* (e.g. multiples <1 red)
        • "delta"  → red/green based on *delta* sign.
    neutral_100 : bool
        Treat 100% as break-even when colouring the value.
    bad_if_neg : bool
        For non-multiple values: colour red if value < 0.
    incomplete_display : bool
        Records with True, will only be displayed if incomplete is True.
    """
    # ---- format main value -----------------------------------------
    if value is None:
        txt_value = ZERO_DISPLAY
    else:
        if value_type == "integer":
            txt_value = f"{value:,.0f} {unit}"
        elif value_type == "percent":
            if abs(value) < 2:
                # When value is less than 2% it is shown as a percentage
                txt_value = f"{value:,.2%}"
            else:
                # When value is greater than 2% it is shown as a multiple
                txt_value = f"{value:,.2f}×"

        elif value_type == "normal":
            txt_value = f"{value:,.2f} {unit}"
        else:
            raise ValueError(f"Unknown value_type: {value_type}")
        if incomplete:
            txt_value = f"{_W} {txt_value}"
    # ---- compute & format delta ------------------------------------
    delta_raw = None
    key = _mk_key(label)
    ref = baseline if baseline is not None else st.session_state.get(key)

    if value is not None and ref is not None and delta_fmt:
        delta_raw = value - ref
        if delta_fmt == "raw":
            if value_type == "integer":
                delta_display = f"{delta_raw:+,.0f} {unit}"
            elif value_type == "percent":
                delta_display = f"{delta_raw:+,.2%}"
            elif value_type == "normal":
                delta_display = f"{delta_raw:+,.2f} {unit}"
        else:
            delta_display = None
    else:
        delta_display = None

    # ---- decide arrow colour ---------------------------------------
    if delta_display is None:
        delta_color = "off"
    elif delta_color_rule in ("normal", "inverse"):
        delta_color = delta_color_rule
    else:
        delta_color = "off"  # default to off if unknown

    # ---- store for next call ---------------------------------------
    st.session_state[key] = value

    # ---- render -----------------------------------------------------
    if incomplete_display:
        if not incomplete:
            return  # skip rendering if incomplete is False
        # If incomplete is True, show the incomplete_display value.
    st.metric(label, txt_value, delta_display, delta_color=delta_color)

def show_metrics_bulk(column, specs: list[dict]) -> None:
    """
    Print a list of metrics into the given Streamlit *column*.

    specs = [
        {"label": "Multiple ▶ RVPI", "value": rvpi, "is_multiple": True},
        {"label": "P&L ▶ Net", "value": net_earnings, "unit": " €"},
        ...
    ]
    """
    with column:
        for spec in specs:
            show_metric(**spec)


# -----------------------------------------------------------------------------
# 4) Advanced equity breakdown helper
# -----------------------------------------------------------------------------

def _display_portfolio_details(advanced_display: bool = False) -> None:  # noqa: D401
    """Show an advanced *equity vs frozen* breakdown in three metric columns.

    Fetches the combined summary from ``/overview/assets`` (via
    ``get_assets_overview``), then prints a grid of **st.metric** widgets
    comparing *portfolio* vs *order-book* numbers.  Any mismatch is
    flagged with a warning icon (⚠️) in front of the figure.
    """

    summary = get_assets_overview()
    misc = summary.get("misc", {})
    cash_asset = misc.get("cash_asset", "")
    mismatch = misc.get("mismatch", {})  # dict[field -> bool]

    balance_summary = summary.get("balance_source", {})
    orders_summary = summary.get("orders_source", {})

    # ------------------------------------------------------------------
    # Render three metric columns (equity / cash / assets)
    # ------------------------------------------------------------------
    c1, c2, c3 = st.columns(3)

    if advanced_display:
        # Equity ------------------------------------------------------------
        specs1 = [
            {"label": "Equity ▶ Total", "value": balance_summary["total_equity"], "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "normal"},
            {"label": "Equity ▶ Free", "value": balance_summary["total_free_value"], "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "normal"},
            {"label": "Equity ▶ Frozen", "value": balance_summary["total_frozen_value"], "unit": cash_asset, "incomplete": mismatch["total_frozen_value"], "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "Equity ▶ Frozen [Order book]", "value": orders_summary["total_frozen_value"], "unit": cash_asset, "incomplete": mismatch["total_frozen_value"], "delta_fmt": "raw", "delta_color_rule": "off", "incomplete_display": True}
        ]
        # Cash --------------------------------------------------------------
        specs2 = [
            {"label": "Cash Equivalents ▶ Total", "value": balance_summary["cash_total_value"], "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "Cash Equivalents ▶ Free", "value": balance_summary["cash_free_value"], "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "Cash Equivalents ▶ Frozen", "value": balance_summary["cash_frozen_value"], "unit": cash_asset, "incomplete": mismatch["cash_frozen_value"], "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "Cash Equivalents ▶ Frozen [Order book]", "value": orders_summary["cash_frozen_value"], "unit": cash_asset, "incomplete": mismatch["cash_frozen_value"], "delta_fmt": "raw", "delta_color_rule": "off", "incomplete_display": True}
        ]
        # Assets ------------------------------------------------------------
        specs3 = [
            {"label": "Volatile Assets ▶ Total", "value": balance_summary["assets_total_value"], "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "Volatile Assets ▶ Free", "value": balance_summary["assets_free_value"], "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "Volatile Assets ▶ Frozen", "value": balance_summary["assets_frozen_value"], "unit": cash_asset, "incomplete": mismatch["assets_frozen_value"], "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "Volatile Assets ▶ Frozen [Order book]", "value": orders_summary["assets_frozen_value"], "unit": cash_asset, "incomplete": mismatch["assets_frozen_value"], "delta_fmt": "raw", "delta_color_rule": "off", "incomplete_display": True}
        ]


        show_metrics_bulk(c1, specs1)
        show_metrics_bulk(c2, specs2)
        show_metrics_bulk(c3, specs3)
        st.markdown("---")
    else:
        # Equity ------------------------------------------------------------
        specs1 = [
            {"label": "Equity ▶ Total", "value": balance_summary["total_equity"], "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "normal"},
        ]
        show_metrics_bulk(c1, specs1)

# -----------------------------------------------------------------------------
# 5) Advanced performance details helper
# -----------------------------------------------------------------------------

def _display_performance_details(
        equity: float,
        paid_in_capital: float,
        distributions: float,
        net_investment: float,
        incomplete_data: bool,
        total_buys: float,
        total_sells: float,
        liquid_assets: float,
        volatile_assets: float,
        total_paid_fees: float,
        buy_current_value: float,
        sell_current_value: float,
        gross_earnings: float,
        net_earnings: float,
        rvpi: float,
        dpi: float,
        tvpi: float,
        cash_asset: str,
        advanced_display: bool
) -> None:
    """
    Show a basic *trades summary* in three metric columns.

    Fetches the combined summary from ``/overview/trades`` (via
    ``get_trades_overview``), then prints a grid of **st.metric** widgets
    comparing *total*, *buy*, and *sell* trades.  Any mismatch in the
    total amount is flagged with a warning icon (⚠️) in front of the figure.
    """
    # --- ROI on current risk ------------------------------------------
    gross_roi_on_cost      = gross_earnings / net_investment if net_investment > 0 else None  # before fees
    net_roi_on_cost        = net_earnings / net_investment if net_investment > 0 else None # after fees
    gross_roi_on_value     = gross_earnings / equity if equity > 0 else None # before fees
    net_roi_on_value       = net_earnings / equity if equity > 0 else None # after fees

    # ------------------------------------------------------------------
    # Render three metric columns
    # ------------------------------------------------------------------
    c1, c2, c3 = st.columns(3)

    if advanced_display:
        # Column 1 - Cash & P&L figures -----------------------------------------
        specs1 = [
            {"label": "Capital ▶ Equity", "value": equity, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "P&L ▶ Gross (Before Fees)", "value": gross_earnings, "unit": cash_asset, "incomplete": incomplete_data, "delta_fmt": "raw", "delta_color_rule": "normal"},
            {"label": "P&L ▶ Net (After Fees)", "value": net_earnings, "unit": cash_asset, "incomplete": incomplete_data, "delta_fmt": "raw", "delta_color_rule": "normal"},
        ]
        # Column 2 - ROI on current risk -----------------------------------------

        if net_investment > 0:
            specs2 = [
                {"label": "Capital ▶ Net Investment", "value": net_investment, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
                {"label": "ROI ▶ Gross on Cost", "value": gross_roi_on_cost, "value_type": "percent", "delta_fmt": "raw", "incomplete": incomplete_data, "delta_color_rule": "normal"},
                {"label": "ROI ▶ Net on Cost", "value": net_roi_on_cost, "value_type": "percent", "delta_fmt": "raw", "incomplete": incomplete_data, "delta_color_rule": "normal"},
            ]
        elif equity > 0:
            free_carry_surplus = abs(net_investment)
            specs2 = [
                {"label": "Capital ▶ Free Carry Surplus", "value": free_carry_surplus, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "normal"},
                {"label": "ROI ▶ Gross on Value", "value": gross_roi_on_value, "value_type": "percent", "delta_fmt": "raw", "incomplete": incomplete_data, "delta_color_rule": "normal"},
                {"label": "ROI ▶ Net on Value", "value": net_roi_on_value, "value_type": "percent", "delta_fmt": "raw", "incomplete": incomplete_data, "delta_color_rule": "normal"},
            ]
        else:
            specs2 = []
        # Column 3 - Multiples as % returns -----------------------------------------
        if distributions > 0:
            specs3 = [
                {"label": "Multiple ▶ RVPI (Residual Value to Paid-In)", "value": rvpi, "value_type": "percent", "delta_fmt": "raw", "incomplete": incomplete_data, "delta_color_rule": "off"},
                {"label": "Multiple ▶ DPI (Distributions to Paid-In)", "value": dpi, "value_type": "percent", "delta_fmt": "raw", "incomplete": incomplete_data, "delta_color_rule": "off"},
                {"label": "Multiple ▶ TVPI (Total Value to Paid-In)", "value": tvpi, "value_type": "percent", "delta_fmt": "raw", "incomplete": incomplete_data, "delta_color_rule": "normal"}
            ]
        else:
            specs3 = [
                {"label": "Multiple ▶ TVPI (Total Value to Paid-In)", "value": tvpi, "value_type": "percent", "delta_fmt": "raw", "incomplete": incomplete_data, "delta_color_rule": "normal"}
            ]

        show_metrics_bulk(c1, specs1)
        show_metrics_bulk(c2, specs2)
        show_metrics_bulk(c3, specs3)
    else:
        # Column 1 - Cash & P&L figures -----------------------------------------
        specs1 = [
            {"label": "P&L ▶ Equity", "value": equity, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
        ]
        specs2 = [
            {"label": "P&L ▶ Gross (Before Fees)", "value": gross_earnings, "unit": cash_asset, "incomplete": incomplete_data, "delta_fmt": "raw", "delta_color_rule": "normal"},
        ]
        specs3 = [
            {"label": "P&L ▶ Net (After Fees)", "value": net_earnings, "unit": cash_asset, "incomplete": incomplete_data, "delta_fmt": "raw", "delta_color_rule": "normal"},
        ]
        show_metrics_bulk(c1, specs1)
        show_metrics_bulk(c2, specs2)
        show_metrics_bulk(c3, specs3)

# -----------------------------------------------------------------------------
# 6) Advanced trades details helper
# -----------------------------------------------------------------------------

def _display_trades_details(summary_capital: dict, trades_summary: dict, cash_asset:str, df_raw: pd.DataFrame, advanced_display: bool = False) -> None:  # noqa: D401
    """
    Show an advanced *trades summary* in three metric columns.

    Fetches the combined summary from ``/overview/trades`` (via
    ``get_trades_overview``), then prints a grid of **st.metric** widgets
    comparing *total*, *buy*, and *sell* trades.  Any mismatch in the
    total amount is flagged with a warning icon (⚠️) in front of the figure.
    """
    equity = summary_capital.get("equity", 0.0)
    avg_trade_summary, period_agg = get_tempo_avg_trade_summary(df_raw, equity)
    # ------------------------------------------------------------------
    buy_traded = trades_summary["BUY"]["notional"]
    sell_traded = trades_summary["SELL"]["notional"]
    global_traded = buy_traded + sell_traded
    buy_orders_count = trades_summary["BUY"]["count"]
    sell_orders_count = trades_summary["SELL"]["count"]
    global_orders = trades_summary["TOTAL"]["count"]
    buy_paid_fees = trades_summary["BUY"]["fee"]
    sell_paid_fees = trades_summary["SELL"]["fee"]
    global_paid_fees = trades_summary["TOTAL"]["fee"]
    avg_buy_price_order = buy_traded / buy_orders_count if buy_orders_count > 0 else 0
    avg_sell_price_order = sell_traded / sell_orders_count if sell_orders_count > 0 else 0
    avg_trade_price_order = global_traded / global_orders if global_orders > 0 else 0
    avg_buy_capital_churn_rate = avg_trade_summary["buy"]["total_notional"]
    avg_sell_capital_churn_rate = avg_trade_summary["sell"]["total_notional"]
    avg_global_capital_churn_rate = avg_trade_summary["global"]["total_notional"]
    avg_buy_equity_churn_rate = 100 * avg_buy_capital_churn_rate / equity if equity > 0 else 0
    avg_sell_equity_churn_rate = 100 * avg_sell_capital_churn_rate / equity if equity > 0 else 0
    avg_global_equity_churn_rate = 100 * avg_global_capital_churn_rate / equity if equity > 0 else 0
    avg_buy_order_churn_rate = avg_trade_summary["buy"]["order_count"]
    avg_sell_order_churn_rate = avg_trade_summary["sell"]["order_count"]
    avg_global_order_churn_rate = avg_trade_summary["global"]["order_count"]
    avg_buy_fee_burn_rate = avg_trade_summary["buy"]["total_fee"]
    avg_sell_fee_burn_rate = avg_trade_summary["sell"]["total_fee"]
    avg_global_fee_burn_rate = avg_trade_summary["global"]["total_fee"]

    # ------------------------------------------------------------------
    # Render three metric columns (equity / cash / assets)
    # ------------------------------------------------------------------
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    if advanced_display:
        specs1 = [
            {"label": "GLOBAL ▶ Notional Traded", "value": global_traded, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "GLOBAL ▶ Orders Count", "value": global_orders, "delta_fmt": "raw", "delta_color_rule": "off", "value_type": "integer"},
            {"label": "GLOBAL ▶ Avg. Order Size", "value": avg_trade_price_order, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "GLOBAL ▶ Paid Fees", "value": global_paid_fees, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "GLOBAL ▶ Capital Churn Rate", "value": avg_global_capital_churn_rate, "unit": f"{cash_asset} / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
            {"label": "GLOBAL ▶ Equity Churn Rate", "value": avg_global_equity_churn_rate, "unit": f"% / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
            {"label": "GLOBAL ▶ Order Churn Rate", "value": avg_global_order_churn_rate, "unit": f"orders / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
            {"label": "GLOBAL ▶ Fee Burn Rate", "value": avg_global_fee_burn_rate, "unit": f"{cash_asset} / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
        ]
        specs2 = [
            {"label": "BUY ▶ Notional Invested", "value": buy_traded, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "BUY ▶ Orders Count", "value": buy_orders_count, "delta_fmt": "raw", "delta_color_rule": "off", "value_type": "integer"},
            {"label": "BUY ▶ Avg. Order Size", "value": avg_buy_price_order, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "BUY ▶ Paid Fees", "value": buy_paid_fees, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "BUY ▶ Capital Churn Rate", "value": avg_buy_capital_churn_rate, "unit": f"{cash_asset} / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
            {"label": "BUY ▶ Equity Churn Rate", "value": avg_buy_equity_churn_rate, "unit": f"% / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
            {"label": "BUY ▶ Order Churn Rate", "value": avg_buy_order_churn_rate, "unit": f"orders / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
            {"label": "BUY ▶ Avg. Fee Burn Rate", "value": avg_buy_fee_burn_rate, "unit": f"{cash_asset} / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
        ]
        specs3 = [
            {"label": "SELL ▶ Notional Divested", "value": sell_traded, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "SELL ▶ Orders Count", "value": sell_orders_count, "delta_fmt": "raw", "delta_color_rule": "off", "value_type": "integer"},
            {"label": "SELL ▶ Avg. Order Size", "value": avg_sell_price_order, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "SELL ▶ Paid Fees", "value": sell_paid_fees, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
            {"label": "SELL ▶ Capital Churn Rate", "value": avg_sell_capital_churn_rate, "unit": f"{cash_asset} / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
            {"label": "SELL ▶ Equity Churn Rate", "value": avg_sell_equity_churn_rate, "unit": f"% / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
            {"label": "SELL ▶ Order Churn Rate", "value": avg_sell_order_churn_rate, "unit": f"orders / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
            {"label": "SELL ▶ Avg. Fee Burn Rate", "value": avg_sell_fee_burn_rate, "unit": f"{cash_asset} / {period_agg}", "delta_fmt": "raw", "delta_color_rule": "inverse"},
        ]

        show_metrics_bulk(c1, specs1)
        show_metrics_bulk(c2, specs2)
        show_metrics_bulk(c3, specs3)
    else:
        specs1 = [
            {"label": "GLOBAL ▶ Notional Traded", "value": global_traded, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
        ]
        specs2 = [
            {"label": "GLOBAL ▶ Orders Count", "value": global_orders, "delta_fmt": "raw", "delta_color_rule": "off", "value_type": "integer"},
        ]
        specs3 = [
            {"label": "GLOBAL ▶ Paid Fees", "value": global_paid_fees, "unit": cash_asset, "delta_fmt": "raw", "delta_color_rule": "off"},
        ]
        show_metrics_bulk(c1, specs1)
        show_metrics_bulk(c2, specs2)
        show_metrics_bulk(c3, specs3)

# -----------------------------------------------------------------------------
# 7) Advanced orders details helper
# -----------------------------------------------------------------------------

def tvpi_gauge(
    tvpi: float,
    bands=((0, 0.5,  CHART_COLORS['red_dark']),
            (0.5, 0.8,  CHART_COLORS['red']),
            (0.8, 1.0, CHART_COLORS['orange']),
            (1.0, 1.25, CHART_COLORS['yellow']),
            (1.25, 2.0, CHART_COLORS['lime']),
            (2.0, 5.0, CHART_COLORS['green']),
            (5.0, 10.0, CHART_COLORS['blue']),
            (10.0, float("inf"), CHART_COLORS['purple']))
    ):
    """
    Create a horizontal bar chart showing the TVPI (Total Value to Paid-In)
    multiple with colour-coded bands.

    Parameters
    ----------
    tvpi : float
        The TVPI value to display.
    bands : tuple of tuples, default predefined bands
        Each tuple defines a band as (lower_bound, upper_bound, colour).

    Returns
    -------
    go.Figure
        A Plotly figure object with the TVPI gauge.
    """
    # Determine the maximum axis value based on the TVPI
    # This ensures the axis can accommodate the TVPI value.
    if tvpi <= 1.6:
        max_axis = 2
    elif tvpi <= 4:
        max_axis = 5
    elif tvpi <= 8:
        max_axis = 10
    else:
        max_axis = math.ceil((tvpi+2)/10)*10  # Ensure the axis can accommodate the TVPI value
    traces   = []
    prev_hi  = 0

    for lo, hi, colour in bands:
        if tvpi <= lo:
            break
        segment_end = min(tvpi, hi)
        width       = segment_end - max(prev_hi, lo)
        if width > 0:
            traces.append(
                go.Bar(
                    x=[width], y=["TVPI"],
                    orientation="h",
                    marker_color=colour,
                    base=prev_hi,
                    hoverinfo="skip", showlegend=False
                )
            )
        prev_hi = hi
        if segment_end >= tvpi:
            break

    # grey outline to show full scale
    traces.append(
        go.Bar(
            x=[max_axis], y=["TVPI"],
            orientation="h",
            marker_color="rgba(0,0,0,0)",
            marker_line=dict(color="#888", width=1),
            base=0,
            hoverinfo="skip", showlegend=False
        )
    )

    fig = go.Figure(traces)
    fig.update_layout(
        barmode="stack",
        bargap=0,                 # no gap = one thick bar
        height=180,               # increase for extra thickness
        xaxis=dict(range=[0, max_axis], title="Multiple (×)", fixedrange=True),
        yaxis_showticklabels=False,
        margin=dict(l=0, r=0, t=10, b=20)
    )

    # Optional: hide axis line for a cleaner look
    fig.update_xaxes(showline=False)

    return fig