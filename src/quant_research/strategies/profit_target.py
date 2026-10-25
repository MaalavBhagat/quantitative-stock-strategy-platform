"""S1 fixed profit target and S2 pullback from peak (EXPERIMENT_PLAN §2, Phase 5 Steps 5.1–5.2).

Both, decided at each close, filled at the NEXT open (engine rule):
- Day 1 close → buy max_affordable. Entry price E = fill price of that ENTRY buy (from the
  strategy's own past fills). Dividend top-ups (cash ≥ reinvest_min while invested) do NOT change E.
- Invested: close ≥ E × (1 + X) → sell ALL. Sale price S = that sell's fill price.
- In cash (no top-ups — there is no position):
    S1: close ≤ S × (1 − Y) → buy max_affordable; new E = its fill price.
    S2: P = highest CLOSE from the sale-fill day onwards; close ≤ P × (1 − Y) → buy; new E = fill.
- Never rebought → stays in cash to the end ("stranded", honest missed upside).
If an order is not filled (rejected / expired), nothing changes and the rule is checked again.
Splits (Goggy 2026-10-25, EXPERIMENT_PLAN §10): E, S and P are raw prices per share at the time. On a
split day they are divided by the snapped split ratio (7.000007 → 7) BEFORE that day's fills are read,
so every comparison stays in post-split units (otherwise a 7:1 split looks like an 86% "dip").
"""

from datetime import date
from decimal import Decimal

import pandas as pd

from quant_research.backtesting.engine import PortfolioView
from quant_research.execution.orders import OrderIntent
from quant_research.portfolio.money import require_decimal, to_decimal_price
from quant_research.ratios import nearest_simple_ratio


class _ProfitTargetBase:
    def __init__(self, ticker: str, x: Decimal, y: Decimal, reinvest_min_cash_usd: Decimal) -> None:
        self.ticker = ticker.upper()
        self.x = require_decimal(x, "profit_target_x")
        self.y = require_decimal(y, "rebuy_dip_y")
        self.reinvest_min_cash_usd = require_decimal(reinvest_min_cash_usd, "reinvest_min_cash_usd")
        self.state = "start"  # start → invested ⇄ cash
        self.entry_price: Decimal | None = None  # E
        self.sale_price: Decimal | None = None  # S
        self._pending: str | None = (
            None  # "entry" / "topup" / "sell" — order sent, waiting for its fill
        )
        self._fills_seen = 0

    # ---------- hooks ----------
    def _apply_split(self, ratio: Decimal) -> None:
        """Keep remembered levels in post-split units (shares × ratio → price per share ÷ ratio)."""
        if self.entry_price is not None:
            self.entry_price = self.entry_price / ratio
        if self.sale_price is not None:
            self.sale_price = self.sale_price / ratio

    def _on_sale(self, day: date, close: Decimal) -> None:
        """Called at the close of the day the sale filled."""

    def _rebuy(self, close: Decimal) -> bool:
        raise NotImplementedError

    # ---------- main ----------
    def _absorb_new_fills(self, view: PortfolioView, close: Decimal, day: date) -> None:
        new = view.fills[self._fills_seen :]
        self._fills_seen = len(view.fills)
        for fill in new:
            if fill.side == "buy" and self._pending == "entry":
                self.entry_price, self.state = fill.fill_price_usd, "invested"
            elif fill.side == "sell" and self._pending == "sell":
                self.sale_price, self.state = fill.fill_price_usd, "cash"
                self._on_sale(day, close)
            # a top-up buy changes nothing (E stays the entry fill price)
            self._pending = None
        if not new:
            self._pending = None  # yesterday's order was rejected / not filled → re-check the rules

    def on_close(
        self, day: date, history: pd.DataFrame, portfolio_view: PortfolioView
    ) -> list[OrderIntent]:
        close = to_decimal_price(float(history["close_raw"].iloc[-1]))
        split = float(history["split_factor"].iloc[-1])
        if (
            abs(split - 1.0) > 1e-12
        ):  # split at today's open — before today's fills (which are post-split)
            snapped = nearest_simple_ratio(split)
            self._apply_split(Decimal(snapped.numerator) / Decimal(snapped.denominator))
        self._absorb_new_fills(portfolio_view, close, day)
        if self.state == "start":
            self._pending = "entry"
            return [OrderIntent("buy", self.ticker, "max_affordable")]
        if self.state == "invested":
            if close >= self.entry_price * (1 + self.x):  # type: ignore[operator]
                self._pending = "sell"
                return [OrderIntent("sell", self.ticker, "all")]
            if portfolio_view.cash_usd >= self.reinvest_min_cash_usd:
                self._pending = "topup"
                return [OrderIntent("buy", self.ticker, "max_affordable")]
            return []
        if self._rebuy(close):  # state == "cash"
            self._pending = "entry"
            return [OrderIntent("buy", self.ticker, "max_affordable")]
        return []


class FixedProfitTarget(_ProfitTargetBase):
    """S1: rebuy when close ≤ S × (1 − Y)."""

    def _rebuy(self, close: Decimal) -> bool:
        return close <= self.sale_price * (1 - self.y)  # type: ignore[operator]


class PullbackFromPeak(_ProfitTargetBase):
    """S2: rebuy when close ≤ P × (1 − Y), P = highest close since the sale-fill day (inclusive)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.peak_close: Decimal | None = None  # P

    def _apply_split(self, ratio: Decimal) -> None:
        super()._apply_split(ratio)
        if self.peak_close is not None:
            self.peak_close = self.peak_close / ratio

    def _on_sale(self, day: date, close: Decimal) -> None:
        self.peak_close = close  # the sale-fill day's close starts the running high

    def _rebuy(self, close: Decimal) -> bool:
        self.peak_close = max(self.peak_close, close)  # type: ignore[type-var]
        return close <= self.peak_close * (1 - self.y)
