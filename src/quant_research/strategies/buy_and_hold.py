"""S0 — buy-and-hold benchmark (EXPERIMENT_PLAN §2, Phase 4 Step 4.4).

- Day 1 close: buy "max_affordable" → fills at day 2 open (T close → T+1 open rule). So "buy at the
  first open" means "first possible open after the first close" (EXPERIMENT_PLAN §10, 2026-10-21).
- Dividends: reinvest (buy max_affordable at the next open) only once cash ≥ reinvest_min_cash_usd
  (Goggy 2026-10-21: US$100, so a US$3 fee never eats ~12% of a small dividend). Never sells.
"""

from datetime import date
from decimal import Decimal

import pandas as pd

from quant_research.backtesting.engine import PortfolioView
from quant_research.execution.orders import OrderIntent
from quant_research.portfolio.money import require_decimal


class BuyAndHold:
    def __init__(self, ticker: str, reinvest_min_cash_usd: Decimal) -> None:
        self.ticker = ticker.upper()
        self.reinvest_min_cash_usd = require_decimal(reinvest_min_cash_usd, "reinvest_min_cash_usd")
        self._first_order_sent = False

    def on_close(
        self, day: date, history: pd.DataFrame, portfolio_view: PortfolioView
    ) -> list[OrderIntent]:
        if not self._first_order_sent:
            self._first_order_sent = True
            return [OrderIntent("buy", self.ticker, "max_affordable")]
        if portfolio_view.cash_usd >= self.reinvest_min_cash_usd:
            return [OrderIntent("buy", self.ticker, "max_affordable")]
        return []
