"""portfolio.py

Streamlit page that visualises the **current portfolio** returned by the
MockExchange back‑end.

Main features
-------------
* Shows total *equity* (or an advanced cash / asset breakdown if the user
  toggles it in the sidebar).
* Builds a tidy DataFrame with per‑asset quantities, fiat values and
  portfolio share.
* Displays an interactive **donut‑pie chart** grouping assets below 1 %
  into a single *Other* slice so the legend stays readable.
* Renders a sortable table with nicely formatted numbers.

This file only adds _docstrings and comments_ – **all runtime logic is
untouched**.
"""

# Standard library -------------------------------------------------------------
from __future__ import annotations

# Third‑party ------------------------------------------------------------------
import pandas as pd
import plotly.express as px
import streamlit as st

# First‑party / project --------------------------------------------------------
from app.services.api import get_balance
from ._helpers import _display_portfolio_details, _format_significant_float, advanced_filter_toggle

# -----------------------------------------------------------------------------
# Page renderer
# -----------------------------------------------------------------------------

def render() -> None:  # noqa: D401 – imperative mood is fine
    """Entry‑point for Streamlit – draw the **Portfolio** page.

    Workflow
    --------
    1. Call the REST helper ``get_balance()`` which returns a dict with
       *equity* and an ``assets_df`` DataFrame.
    2. If no positions exist, show an info box and bail out early.
    3. Offer an *advanced* toggle in the sidebar. When enabled we show a
       granular breakdown through ``_display_advanced_portfolio``.
    4. Compute each asset's market value and relative share.
    5. Plot a donut‑style pie chart, collapsing slices < 1 % into
       **Other**.
    6. Build a pretty, human‑readable table (thousand‑separators, units)
       and display it below the chart.
    """

    # ------------------------------------------------------------------
    # 0) Boilerplate – page title & pull data
    # ------------------------------------------------------------------
    st.set_page_config(page_title="Portfolio")  # browser tab + sidebar label
    st.title("Portfolio")                       # big header inside the page
    params = st.query_params                    # returns a QueryParamsProxy

    data = get_balance()  # dict: ``equity``, ``quote_asset``, ``assets_df``

    # Early exit if portfolio is empty (no cash & no assets)
    if data["assets_df"].empty:
        st.info("No equity or assets found.")
        return

    # ------------------------------------------------------------------
    # 1) Sidebar – advanced display toggle
    # ------------------------------------------------------------------
    advanced_display = advanced_filter_toggle()

    # ------------------------------------------------------------------
    # 2) Portfolio metrics (simple vs advanced)
    # ------------------------------------------------------------------
    _display_portfolio_details(advanced_display=advanced_display)

    # ------------------------------------------------------------------
    # 3) Build a numeric DataFrame with helper columns
    # ------------------------------------------------------------------
    df = data["assets_df"].copy()
    # Market value per asset in quote currency (e.g. USDT)
    df["value"] = df["total"] * df["quote_price"]
    # Portfolio share (0‑1) keeps it numeric for later math / formatting.
    df["share"] = df["value"] / df["value"].sum()
    # Sort descending so the biggest positions appear first.
    df = df.sort_values("value", ascending=False)

    # ------------------------------------------------------------------
    # 4) Donut pie chart (group assets < 1 % into "Other")
    # ------------------------------------------------------------------
    lim_min_share = 0.01  # threshold = 1 %
    major = df[df["share"] >= lim_min_share]
    other = df.loc[df["share"] < lim_min_share, "value"].sum()

    pie_df = major[["asset", "value"]].reset_index(drop=True)
    if other > 0:
        # Append the "Other" slice as a synthetic row
        pie_df.loc[len(pie_df)] = {"asset": "Other", "value": other}

    fig = px.pie(pie_df, names="asset", values="value", hole=0.4)
    fig.update_layout(
        autosize=True,  # fill container width
        height=600,
        margin=dict(t=40, b=40, l=40, r=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------------------------------
    # 5) Pretty table below the chart
    # ------------------------------------------------------------------
    # Helper lambdas to keep formatting one‑liners tidy
    fmt_amt = lambda x: _format_significant_float(x)  # noqa: E731
    fmt_price = lambda x: _format_significant_float(x, data['quote_asset'])  # noqa: E731
    fmt_val = lambda x: _format_significant_float(x, data['quote_asset'])  # noqa: E731
    fmt_pct = lambda x: f"{x*100:,.2f}%"                          # noqa: E731

    df_disp = df.copy()
    df_disp["free"] = df["free"].map(fmt_amt)
    df_disp["used"] = df["used"].map(fmt_amt)
    df_disp["total"] = df["total"].map(fmt_amt)
    df_disp["quote_price"] = df["quote_price"].map(fmt_price)
    df_disp["value"] = df["value"].map(fmt_val)
    df_disp["share"] = df["share"].map(fmt_pct)

    # Dynamic height: ~35 px per row, but cap at 800 px for usability.
    height_calc = min(35 * (1 + len(df_disp)) + 5, 800)

    st.dataframe(
        df_disp,
        hide_index=True,
        use_container_width=True,
        height=height_calc,
        column_order=[
            "asset",
            "free",
            "used",
            "total",
            "quote_price",
            "value",
            "share",
        ],
        column_config={
            "asset": st.column_config.TextColumn("Asset"),
            "free": st.column_config.TextColumn("Free"),
            "used": st.column_config.TextColumn("In orders"),
            "total": st.column_config.TextColumn("Total"),
            "quote_price": st.column_config.TextColumn(
                f"Price ({data['quote_asset']})"
            ),
            "value": st.column_config.TextColumn(
                f"Value ({data['quote_asset']})"
            ),
            "share": st.column_config.TextColumn("Share (%)"),
        },
    )

    # st.write("Debugging - pie_df:", pie_df)
    # st.write("Debugging - data:", data)
    # st.write("Top assets by share", df.sort_values("share", ascending=False).head(5))