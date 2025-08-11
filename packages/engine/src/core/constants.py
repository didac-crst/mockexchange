# constants.py

from enum import Enum

class OrderSide(str, Enum):
    BUY  = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT  = "limit"

class OrderState(str, Enum):
    NEW                  = "new"
    PARTIALLY_FILLED     = "partially_filled"
    FILLED               = "filled"
    PARTIALLY_CANCELED   = "partially_canceled"
    CANCELED             = "canceled"
    PARTIALLY_EXPIRED    = "partially_expired"
    EXPIRED              = "expired"
    PARTIALLY_REJECTED   = "partially_rejected"
    REJECTED             = "rejected"

    @property
    def label(self) -> str:
        """Return a human-readable label for the order state."""
        return self.value.replace("_"," ").title()

# OPEN_STATUS / CLOSED_STATUS: for in-process comparisons (Enum members)
# *_STR: for any serialization/validation at the boundary (raw strings)

# which states count as “open”:
OPEN_STATUS = frozenset({
    OrderState.NEW,
    OrderState.PARTIALLY_FILLED,
})

# everything else is "closed":
CLOSED_STATUS = frozenset(OrderState) - OPEN_STATUS

# all possible states:
ALL_SIDES_STR = frozenset(s.value for s in OrderSide)
ALL_TYPES_STR = frozenset(s.value for s in OrderType)
ALL_STATUS_STR = frozenset(s.value for s in OrderState)
OPEN_STATUS_STR   = frozenset(s.value for s in OPEN_STATUS)
CLOSED_STATUS_STR = frozenset(s.value for s in CLOSED_STATUS)