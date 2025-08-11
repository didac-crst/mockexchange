# __init__.py
from importlib.metadata import version, PackageNotFoundError
from .logging_config import logger
from ._types import AssetBalance, Order
from .engine_actors import start_engine, ExchangeEngineActor  # <-- required
from .constants import OrderSide, OrderType, OrderState, OPEN_STATUS_STR, CLOSED_STATUS_STR, ALL_STATUS_STR, ALL_SIDES_STR, ALL_TYPES_STR

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