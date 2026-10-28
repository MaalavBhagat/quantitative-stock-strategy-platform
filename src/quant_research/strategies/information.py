"""Phase 9 information strategies C1, C2, E1 (research/PREREGISTRATION_V2.md §2, tag prereg-v2).

Each one = a twin strategy + one piece of extra information:
- C1 Market-trend gate (twin S0): hold only while SPY is in a strong uptrend (close > 200-day average AND that average
  higher than 20 trading days earlier); otherwise sell all and wait in cash.
- C2 Market-gated pullback (twin S4-S2): S4-S2, but no REBUY while SPY's close is ≤ its 200-day average.
- E1 Earnings cool-off (twin S4-S2): S4-S2, but sell and rebuy signals are ignored at the closes of the day an earnings
  8-K (item 2.02, 8-K/A included) becomes usable (availability rule, news/events.py) and of the next trading day.

No look-ahead: SPY values use only SPY rows dated ≤ T, split-adjusted as of T (strategies/indicators.py); a missing SPY
row for a stock trading day stops the run (nothing is guessed). Events count only from their usable close.
"""

import bisect
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal

import pandas as pd

from quant_research.backtesting.engine import PortfolioView
from quant_research.execution.orders import OrderIntent
from quant_research.news.events import Event, usable_close_day
from quant_research.portfolio.money import require_decimal
from quant_research.strategies.indicators import sma, split_adjusted_closes, strong_uptrend
from quant_research.strategies.profit_target import TrendFilteredPullback

EARNINGS = "earnings"  # category of item 2.02 (news/events.py)
COOL_OFF_DAYS = 2  # the usable day itself + the next trading day (PREREGISTRATION_V2 decision 1)


class MissingMarketDayError(ValueError):
    """SPY has no row for a day the stock trades (D4: date mismatches fail loudly)."""


class MarketData:
    """SPY (or any market) table, handed out only up to and including the day being decided."""

    def __init__(self, table: pd.DataFrame) -> None:
        self.table = table.sort_values("date").reset_index(drop=True)
        self._dates = list(self.table["date"])

    def upto(self, day: date) -> pd.DataFrame:
        end = bisect.bisect_right(self._dates, day)
        if end == 0 or self._dates[end - 1] != day:
            raise MissingMarketDayError(f"market data has no row for {day}")
        return self.table.iloc[:end]


def market_uptrend(spy: pd.DataFrame, sma_window: int = 200, slope_lag: int = 20) -> bool:
    """C1 condition: SPY close > SMA AND SMA > SMA `slope_lag` days earlier. Too little history → False."""
    return strong_uptrend(split_adjusted_closes(spy), sma_window, slope_lag)


def market_above_average(spy: pd.DataFrame, window: int = 200) -> bool:
    """C2 condition: SPY close > its `window`-day average. Too little history → False (rebuy stays blocked)."""
    closes = split_adjusted_closes(spy)
    avg = sma(closes, window)
    return avg is not None and closes[-1] > avg


def earnings_usable_days(
    events: Sequence[Event], schedule: dict[date, datetime] | None = None
) -> list[date]:
    """Usable close day of every earnings event (8-K and 8-K/A alike — an amendment is its own event)."""
    return sorted(
        {usable_close_day(e.accepted_et, schedule) for e in events if EARNINGS in e.categories}
    )


def in_cool_off(
    trading_days: Sequence[date], usable_days: Sequence[date], length: int = COOL_OFF_DAYS
) -> bool:
    """True if one of the last `length` trading days up to T (T included) is an earnings usable day."""
    recent = set(trading_days[-length:])
    return any(u in recent for u in usable_days)


class MarketTrendGate:
    """C1. Stateless: holding / in cash is read from the portfolio view, so a rejected order is simply re-checked."""

    def __init__(
        self,
        ticker: str,
        market: pd.DataFrame,
        reinvest_min_cash_usd: Decimal,
        sma_window: int = 200,
        slope_lag: int = 20,
    ) -> None:
        self.ticker = ticker.upper()
        self.market = MarketData(market)
        self.reinvest_min_cash_usd = require_decimal(reinvest_min_cash_usd, "reinvest_min_cash_usd")
        self.sma_window, self.slope_lag = sma_window, slope_lag

    def on_close(
        self, day: date, history: pd.DataFrame, portfolio_view: PortfolioView
    ) -> list[OrderIntent]:
        on = market_uptrend(self.market.upto(day), self.sma_window, self.slope_lag)
        if portfolio_view.quantity > 0:
            if not on:
                return [OrderIntent("sell", self.ticker, "all")]
            if portfolio_view.cash_usd >= self.reinvest_min_cash_usd:
                return [OrderIntent("buy", self.ticker, "max_affordable")]
            return []
        return [OrderIntent("buy", self.ticker, "max_affordable")] if on else []


class MarketGatedPullback(TrendFilteredPullback):
    """C2: S4-S2 with rebuys blocked while SPY's close ≤ its average (the running high keeps updating)."""

    def __init__(
        self, *args: object, market: pd.DataFrame, market_window: int = 200, **kwargs: object
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.market = MarketData(market)
        self.market_window = market_window
        self._day: date | None = None

    def on_close(
        self, day: date, history: pd.DataFrame, portfolio_view: PortfolioView
    ) -> list[OrderIntent]:
        self._day = day
        self.market.upto(day)  # every day: a missing SPY row stops the run
        return super().on_close(day, history, portfolio_view)

    def _rebuy(self, close: Decimal) -> bool:
        hit = super()._rebuy(close)  # updates the running high P first
        return hit and market_above_average(self.market.upto(self._day), self.market_window)  # type: ignore[arg-type]


class EarningsCoolOff(TrendFilteredPullback):
    """E1: S4-S2 with sell and rebuy signals ignored during an earnings cool-off."""

    def __init__(
        self,
        *args: object,
        events: Sequence[Event],
        schedule: dict[date, datetime] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.usable_days = earnings_usable_days(events, schedule)
        self._cooling = False

    def on_close(
        self, day: date, history: pd.DataFrame, portfolio_view: PortfolioView
    ) -> list[OrderIntent]:
        self._cooling = in_cool_off(list(history["date"].iloc[-COOL_OFF_DAYS:]), self.usable_days)
        return super().on_close(day, history, portfolio_view)

    def _sell_allowed(self, history: pd.DataFrame) -> bool:
        return not self._cooling and super()._sell_allowed(history)

    def _rebuy(self, close: Decimal) -> bool:
        hit = super()._rebuy(close)  # updates the running high P first
        return hit and not self._cooling
