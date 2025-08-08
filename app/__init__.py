"""Package init: sets global Streamlit config and shares constants."""
from __future__ import annotations

import streamlit as st

# This runs once per session and applies to all pages.
st.set_page_config(
    page_title="mockexchange-deck",
    page_icon="📊",
    layout="wide",
)

APP_NAME = "mockexchange-deck"
APP_ICON = "📊"
VERSION = "0.1.0"
