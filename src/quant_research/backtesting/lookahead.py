"""Reusable look-ahead test harness (Phase 4, Step 4.2).

Run every strategy we add through `check_no_lookahead`: it runs the strategy, then changes ALL
data after day T (prices, dividends, splits) and runs again. Every decision up to and including
T's close — and every order those decisions created — must be identical. It also checks that
no order is filled on the same day it was created (fills happen at the NEXT open at the earliest).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd

from quant_research.backtesting.engine import (
    EngineResult,
    EngineSettings,
    PortfolioView,
    Strategy,
    run_engine,
)
from quant_research.execution.orders import OrderIntent


@dataclass
class Spy:
    """Wraps a strategy and records what it saw and decided each day."""

    inner: Strategy
    seen_last_dates: list[date]
    decisions: list[tuple[date, tuple[OrderIntent, ...]]]

    def on_close(
        self, day: date, history: pd.DataFrame, portfolio_view: PortfolioView
    ) -> list[OrderIntent]:
        self.seen_last_dates.append(history["date"].iloc[-1])
        intents = self.inner.on_close(day, history, portfolio_view)
        self.decisions.append((day, tuple(intents or [])))
        return intents


def scramble_after(prices: pd.DataFrame, cut: int, factor: float = 3.0) -> pd.DataFrame:
    """Copy of `prices` with every row AFTER index `cut` changed (prices × factor, new dividends)."""
    changed = prices.copy()
    after = changed.index > cut
    for col in ("open_raw", "high_raw", "low_raw", "close_raw"):
        if col in changed.columns:
            changed.loc[after, col] = changed.loc[after, col] * factor
    changed.loc[after, "div_cash_usd"] = 0.77
    return changed


def run_with_spy(
    make_strategy: Callable[[], Strategy],
    prices: pd.DataFrame,
    ticker: str,
    settings: EngineSettings,
    cash: Decimal,
) -> tuple[Spy, EngineResult]:
    spy = Spy(make_strategy(), [], [])
    return spy, run_engine(prices, ticker, spy, settings, cash)


def check_no_lookahead(
    make_strategy: Callable[[], Strategy],
    prices: pd.DataFrame,
    cut: int,
    ticker: str,
    settings: EngineSettings,
    cash: Decimal,
) -> None:
    """Raise AssertionError if anything up to row `cut` depends on data after it."""
    spy_a, res_a = run_with_spy(make_strategy, prices, ticker, settings, cash)
    spy_b, res_b = run_with_spy(make_strategy, scramble_after(prices, cut), ticker, settings, cash)
    cut_day = prices["date"].iloc[cut]
    # no order may fill on the day it was created (signal at T close → fill at T+1 open at the earliest)
    for res in (res_a, res_b):
        for o in res.orders:
            if o.status != "EXPIRED":
                assert o.intended_day is not None and o.intended_day > o.created_day, (
                    f"order created {o.created_day} was handled on {o.intended_day} — same-day fill"
                )
    # the strategy never saw a row later than the day it was deciding on
    for spy in (spy_a, spy_b):
        for (day, _), seen in zip(spy.decisions, spy.seen_last_dates):
            assert seen == day, f"strategy on {day} saw data up to {seen}"
    # decisions up to T identical
    a = [d for d in spy_a.decisions if d[0] <= cut_day]
    b = [d for d in spy_b.decisions if d[0] <= cut_day]
    assert a == b, "decisions up to the cut changed when only later data changed"
    # orders created up to T identical (fill outcomes may differ — they happen after T)
    orders_a = [(o.created_day, o.intent) for o in res_a.orders if o.created_day <= cut_day]
    orders_b = [(o.created_day, o.intent) for o in res_b.orders if o.created_day <= cut_day]
    assert orders_a == orders_b, "orders created up to the cut changed when only later data changed"
    # equity up to T identical
    eq_a = [e for e in res_a.equity if e.day <= cut_day]
    eq_b = [e for e in res_b.equity if e.day <= cut_day]
    assert eq_a == eq_b, "equity up to the cut changed when only later data changed"


def check_events_no_lookahead(
    decide: Callable[[date, list], object],
    days: list[date],
    events: list,
    schedule: dict | None = None,
) -> None:
    """Events version of the spy check (Phase 9, Step 9.4).

    `decide(day, events)` gets the FULL event list and must itself use only events available at `day`'s close.
    For every event: move it one calendar day later and re-decide; every decision on a day BEFORE the event's
    original usable day must be unchanged. A decision that peeks at an event too early (e.g. counts an
    after-close filing on its own day) changes and raises AssertionError.
    """
    from dataclasses import replace
    from datetime import timedelta

    from quant_research.news.events import usable_close_day

    base = {d: decide(d, list(events)) for d in days}
    for k, event in enumerate(events):
        first = usable_close_day(event.accepted_et, schedule)
        moved = list(events)
        moved[k] = replace(event, accepted_et=event.accepted_et + timedelta(days=1))
        for d in days:
            if d >= first:
                break
            after = decide(d, moved)
            if after != base[d]:
                raise AssertionError(
                    f"decision on {d} changed when event {event.accession} (usable from {first}) was moved later: "
                    f"{base[d]!r} → {after!r} — look-ahead"
                )


def check_market_no_lookahead(
    make_strategy: Callable[[pd.DataFrame], Strategy],
    prices: pd.DataFrame,
    market: pd.DataFrame,
    cut: int,
    ticker: str,
    settings: EngineSettings,
    cash: Decimal,
) -> None:
    """Market-data version of the spy check (Phase 9, C1 / C2): change every SPY row AFTER the stock's day `cut`
    (prices × 3, new dividends) and run again — every decision, order and equity row up to that day must be identical.
    `make_strategy(market)` builds the strategy from a market table."""
    cut_day = prices["date"].iloc[cut]
    market_cut = int(market.index[market["date"] <= cut_day][-1])
    spy_a, res_a = run_with_spy(lambda: make_strategy(market), prices, ticker, settings, cash)
    spy_b, res_b = run_with_spy(
        lambda: make_strategy(scramble_after(market, market_cut)), prices, ticker, settings, cash
    )
    a = [d for d in spy_a.decisions if d[0] <= cut_day]
    b = [d for d in spy_b.decisions if d[0] <= cut_day]
    assert a == b, (
        "decisions up to the cut changed when only later MARKET data changed — look-ahead"
    )
    orders_a = [(o.created_day, o.intent) for o in res_a.orders if o.created_day <= cut_day]
    orders_b = [(o.created_day, o.intent) for o in res_b.orders if o.created_day <= cut_day]
    assert orders_a == orders_b, "orders up to the cut changed when only later MARKET data changed"
    eq_a = [e for e in res_a.equity if e.day <= cut_day]
    eq_b = [e for e in res_b.equity if e.day <= cut_day]
    assert eq_a == eq_b, "equity up to the cut changed when only later MARKET data changed"
