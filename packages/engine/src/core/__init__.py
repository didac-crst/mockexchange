# __init__.py
from importlib.metadata import PackageNotFoundError, version

from ._types import AssetBalance, Order
from .constants import (
    ALL_SIDES_STR,
    ALL_STATUS_STR,
    ALL_TYPES_STR,
    CLOSED_STATUS_STR,
    OPEN_STATUS_STR,
    OrderSide,
    OrderState,
    OrderType,
)
from .engine_actors import ExchangeEngineActor, start_engine  # <-- required
from .logging_config import logger

try:
    __version__ = version("mockexchange")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

__all__ = [
    "start_engine",
    "ExchangeEngineActor",
    "OrderSide",
    "OrderType",
    "OrderState",
    "AssetBalance",
    "Order",
    "logger",
    "__version__",
    "OPEN_STATUS_STR",
    "CLOSED_STATUS_STR",
    "ALL_STATUS_STR",
    "ALL_SIDES_STR",
    "ALL_TYPES_STR",
]
