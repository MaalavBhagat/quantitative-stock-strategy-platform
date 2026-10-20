"""Order intents — what a strategy may ask for (Phase 4, Step 4.2).

An intent has NO price field: strategies cannot choose their fill price. Fills happen at the next
open (quant_research.execution.fills).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from quant_research.portfolio.money import require_decimal

Side = Literal["buy", "sell"]
SizeWord = Literal["all", "max_affordable"]


@dataclass(frozen=True)
class OrderIntent:
    """buy/sell `size` of `ticker`: a number of shares, "all" (sell) or "max_affordable" (buy)."""

    side: Side
    ticker: str
    size: Decimal | SizeWord

    def __post_init__(self) -> None:
        if self.side not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got {self.side!r}")
        if not isinstance(self.ticker, str) or not self.ticker.strip():
            raise ValueError("ticker must be a non-empty string")
        object.__setattr__(self, "ticker", self.ticker.strip().upper())
        if isinstance(self.size, str) and self.size in ("all", "max_affordable"):
            if self.side == "buy" and self.size == "all":
                raise ValueError('size "all" is only for sells — use "max_affordable" to buy')
            if self.side == "sell" and self.size == "max_affordable":
                raise ValueError('size "max_affordable" is only for buys — use "all" to sell')
            return
        qty = require_decimal(self.size, "size")
        if qty <= 0:
            raise ValueError(f"size must be > 0 shares, got {qty}")
        object.__setattr__(self, "size", qty)
