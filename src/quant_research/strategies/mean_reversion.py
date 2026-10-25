"""S3 — mean reversion (EXPERIMENT_PLAN §2, Phase 5 Step 5.3; tests H4).

z_T = (P_T − mean of the last w values) ÷ sample std (ddof = 1) of those values; P = split-adjusted-as-of-T
closes; the window includes day T. Decided at the close, filled at the next open:
- Day 1 close → buy max_affordable (starts invested, like S1/S2).
- Invested and z ≥ +k → sell ALL. Otherwise dividend top-up when cash ≥ reinvest_min.
- In cash and z ≤ −k → buy max_affordable. No top-ups in cash.
- Not enough history for z (shorter than w) → no signal.
"""

from datetime import date
from decimal import Decimal

import pandas as pd

from quant_research.backtesting.engine import PortfolioView
from quant_research.execution.orders import OrderIntent
from quant_research.portfolio.money import require_decimal
from quant_research.strategies.indicators import split_adjusted_closes, zscore


class MeanReversion:
    def __init__(
        self, ticker: str, k: Decimal, window: int, reinvest_min_cash_usd: Decimal
    ) -> None:
        self.ticker = ticker.upper()
        self.k = float(require_decimal(k, "mr_k"))
        self.window = int(window)
        self.reinvest_min_cash_usd = require_decimal(reinvest_min_cash_usd, "reinvest_min_cash_usd")
        self.state = "start"
        self._pending: str | None = None
        self._fills_seen = 0

    def _absorb_new_fills(self, view: PortfolioView) -> None:
        new = view.fills[self._fills_seen :]
        self._fills_seen = len(view.fills)
        for fill in new:
            if fill.side == "buy" and self._pending == "entry":
                self.state = "invested"
            elif fill.side == "sell" and self._pending == "sell":
                self.state = "cash"
            self._pending = None
        if not new:
            self._pending = None

    def on_close(
        self, day: date, history: pd.DataFrame, portfolio_view: PortfolioView
    ) -> list[OrderIntent]:
        self._absorb_new_fills(portfolio_view)
        if self.state == "start":
            self._pending = "entry"
            return [OrderIntent("buy", self.ticker, "max_affordable")]
        z = zscore(split_adjusted_closes(history), self.window)
        if self.state == "invested":
            if z is not None and z >= self.k:
                self._pending = "sell"
                return [OrderIntent("sell", self.ticker, "all")]
            if portfolio_view.cash_usd >= self.reinvest_min_cash_usd:
                self._pending = "topup"
                return [OrderIntent("buy", self.ticker, "max_affordable")]
            return []
        if z is not None and z <= -self.k:
            self._pending = "entry"
            return [OrderIntent("buy", self.ticker, "max_affordable")]
        return []
