"""Registry of Streamlit pages so main.py can route dynamically."""
from typing import Callable

from . import orders, portfolio, performance

Page = Callable[[], None]

registry: dict[str, Page] = {
    "portfolio": portfolio.render,
    "orders": orders.render,
    "performance": performance.render,  # Reusing performance page
}

__all__ = ["registry"]