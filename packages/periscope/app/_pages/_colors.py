"""_row_colors.py

Colour utilities for the **Orders** dataframe.

The module provides:
* Emoji *status lights* (`_STATUS_LIGHT`) used in the Order-Details header.
* A base background palette (`_BG0`) mapping order status → colour.
* Functions to:
  - Darken colours over time so recently updated rows stand out and older
    rows gradually fade (`_color_interp`, `_create_color_rows_degradation`).
  - Pick an appropriate foreground (text) colour for legibility
    (`contrast_text_color`).
  - Generate a list of CSS style strings for the Streamlit Styler
    (`_row_style`).

Only **comments and docstrings** were added – functional behaviour is
unchanged.
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Standard library
# -----------------------------------------------------------------------------
import time
from typing import Tuple, Dict, List
from datetime import datetime, timezone

# Third-party
import pandas as pd

from ._helpers import (
                TS_FMT,
                LOCAL_TZ,
)

# -----------------------------------------------------------------------------
# PUBLIC CONSTANTS – status → emoji / colour
# -----------------------------------------------------------------------------
# Emoji used in headers (Order Details page) to indicate status at a glance.
_STATUS_LIGHT: dict[str, str] = {
    "new": "🟣",  # purple
    "partially_filled": "🔵",  # blue
    "filled": "🟢",  # green
    "partially_canceled": "🟡",  # yellow
    "partially_rejected": "🟡",  # yellow
    "partially_expired": "🟡",  # yellow
    "canceled": "🔴",  # red
    "rejected": "🔴",
    "expired": "🔴",
}

# Base background colour per status (freshest shade). These will be faded
# toward black depending on row age.
_BG0: dict[str, str] = {
    "new": "#aa55ff",  # purple
    "partially_filled": "#11AAFF",  # blue
    "filled": "#00ff00",  # green
    "partially_canceled": "#fff700",  # yellow
    "partially_rejected": "#fff700",  # yellow
    "partially_expired": "#fff700",  # yellow
    "canceled": "#ff5555",  # red
    "rejected": "#ff5555",
    "expired": "#ff5555",
}

# -----------------------------------------------------------------------------
# Helper functions (internal)
# -----------------------------------------------------------------------------

def _color_interp(c0: str, t: float) -> str:  # noqa: D401 – short desc ok
    """Return a **darkened** version of *c0* by blending with black.

    Parameters
    ----------
    c0 : str
        Hex colour "#RRGGBB" (no shorthand allowed).
    t : float
        Fraction 0 ≤ `t` ≤ 1. 0 ⇒ original colour; 1 ⇒ black.

    Notes
    -----
    The blend is performed per RGB channel: ``out = round(channel * (1-t))``.
    """
    r0, g0, b0 = int(c0[1:3], 16), int(c0[3:5], 16), int(c0[5:7], 16)
    r = round(r0 * (1 - t))
    g = round(g0 * (1 - t))
    b = round(b0 * (1 - t))
    return f"#{r:02x}{g:02x}{b:02x}"


def contrast_text_color(bg_hex: str) -> str:  # noqa: D401
    """Pick black or white text for best contrast on *bg_hex*.

    Uses the YIQ perceptual luminance formula and returns **black** if the
    background is light, **white** otherwise.
    """
    h = bg_hex.lstrip("#")
    if len(h) == 3:  # allow shorthand e.g. #fff
        h = "".join(ch * 2 for ch in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    yiq = (r * 299 + g * 587 + b * 114) / 1000
    return "#000000" if yiq >= 128 else "#ffffff"


def _create_color_rows_degradation(levels: int = 3) -> Tuple[Dict[int, dict], Dict[int, dict]]:
    """Generate *levels* fade steps for background & foreground palettes.

    ``levels`` must be ≥ 2.

    Returns
    -------
    (bg, fg) : tuple
        Two dicts mapping ``step → {status → colour}`` – one for
        backgrounds, one for foregrounds.
    """
    if levels < 2:
        raise ValueError("`N_VISUAL_DEGRADATIONS` must be at least 2")

    # Background palettes ------------------------------------------------
    bg: Dict[int, dict[str, str]] = {0: _BG0}
    for j in range(1, levels):
        if j == levels - 1:
            # last bucket = solid black (fully faded)
            bg[j] = {k: "#000000" for k in _BG0}
        else:
            fade = j / (levels - 1)  # fraction 0<fade<1
            bg[j] = {k: _color_interp(c, fade) for k, c in _BG0.items()}

    # Foreground palettes -------------------------------------------------
    fg: Dict[int, dict[str, str]] = {
        lvl: {k: contrast_text_color(c) for k, c in pal.items()} for lvl, pal in bg.items()
    }
    return bg, fg

# -----------------------------------------------------------------------------
# Main styling hook used by dataframe.style.apply
# -----------------------------------------------------------------------------

def _row_style(
    row: pd.Series,
    *,
    levels: int = 3,
    fresh_window_s: float = 60,
) -> list[str]:
    """Return a list of CSS style strings for the given *row*.

    Styles rows based on how recent the update was:
    - age <= fresh_window_s → bucket 0 (fresh)
    - age // fresh_window_s → bucket index for fading
    - negative or out-of-range bucket → default (no style)
    """
    # Build fade palettes
    bg_maps, fg_maps = _create_color_rows_degradation(levels)

    upd = row["Updated"]
    # 1) Try timestamp or datetime
    try:
        if isinstance(upd, pd.Timestamp):
            t_update = upd.timestamp()
        else:
            # numeric string or number
            t_val = float(upd)
            # if ms => large value; unify to seconds
            if t_val > 1e11:
                t_val /= 1000.0
            t_update = t_val
    except Exception:
        # 2) Fallback: parse human string in local timezone
        try:
            now = datetime.now(LOCAL_TZ)
            # Parse string and attach local tz
            parsed = datetime.strptime(upd, TS_FMT)
            parsed = parsed.replace(year=now.year, tzinfo=LOCAL_TZ)
            # Handle year rollover if needed
            if now.month == 1 and parsed.month == 12:
                parsed = parsed.replace(year=parsed.year - 1)
            t_update = parsed.timestamp()
        except Exception:
            return [""] * len(row)

    # Compute age in seconds, clamp negatives
    age = time.time() - t_update
    if age < 0:
        age = 0

    # Determine bucket
    bucket = int(age // fresh_window_s)
    if bucket < 0 or bucket >= levels:
        return [""] * len(row)

    # Lookup colours
    status_key = str(row["Status"]).lower().replace(" ", "_")
    bg = bg_maps[bucket].get(status_key)
    if not bg:
        return [""] * len(row)
    fg = fg_maps[bucket].get(status_key, contrast_text_color(bg))
    style = f"background-color:{bg};color:{fg}"
    return [style] * len(row)

# def _row_style(
#     row: pd.Series,
#     *,
#     levels: int = 3,
#     fresh_window_s: float = 60,
# ) -> List[str]:
#     """Return a list of CSS style strings for the given *row*.

#     The style (background & text colour) depends on **how recent** the row is:
#     * Rows updated ≤ *fresh_window_s* ago → bucket 0 (no fade).
#     * Each additional *fresh_window_s* pushes the row one bucket darker.
#     * Beyond the last bucket → no styling (use default table colours).

#     Parameters
#     ----------
#     row : pd.Series
#         Row from the Styler apply call.
#     levels : int, optional
#         Number of fade buckets (≥ 2). Defaults to 3.
#     fresh_window_s : float, optional
#         Time span (seconds) that defines one bucket.
#     """

#     # Build the colour palettes on the fly (cheap for small `levels`).
#     bg_maps, fg_maps = _create_color_rows_degradation(levels)

#     # ------------------------------------------------------------------
#     # Compute row age in seconds from the "Updated" column.
#     # ------------------------------------------------------------------
#     try:
#         upd = row["Updated"]
#         t_update = (
#             upd.timestamp() if isinstance(upd, pd.Timestamp) else pd.to_datetime(upd).timestamp()
#         )
#     except ValueError:
#     # 2️⃣ Fallback: handle bare "MM/DD HH:MM:SS"
#         try:
#             # attach current UTC year
#             now_utc = datetime.now(timezone.utc)

#             parsed   = datetime.strptime(row["Updated"], TS_FMT).replace(
#                 year=now_utc.year, tzinfo=timezone.utc
#             )

#             # if we’re in January and the parsed date is in December,
#             # roll it back one year (cross-year edge-case)
#             if now_utc.month == 1 and parsed.month == 12:
#                 parsed = parsed.replace(year=parsed.year - 1)

#             t_update = parsed.timestamp()

#         except Exception:
#             # Column missing or unparsable timestamp – no styling.
#             return [""] * len(row)

#     age = time.time() - t_update

#     # Bucket index -------------------------------------------------------
#     bucket = int(age // fresh_window_s)
#     if bucket >= len(bg_maps):
#         # Too old → fall back to default styling.
#         return [""] * len(row)

#     # Choose background & foreground colours ----------------------------
#     bg_map = bg_maps[bucket]
#     fg_map = fg_maps[bucket]

#     key = str(row["Status"]).lower().replace(" ", "_")  # normalize to status key
#     bg = bg_map.get(key, "")
#     if not bg:
#         return [""] * len(row)  # unknown status → default style

#     fg = fg_map.get(key, contrast_text_color(bg))

#     style = f"background-color:{bg};color:{fg}"
#     return [style] * len(row)  # same style for all cells in the row