"""C1 Market-trend gate, C2 Market-gated pullback, E1 Earnings cool-off — synthetic data only, hand-worked.

Stake US$3 fee, normal spread (buy = open × 1.0005, sell = open × 0.9995), WHOLE shares, US$10,000.
Short windows in tests (the real ones are 200 / 20): written next to each case.
"""

from datetime import date, datetime
from decimal import Decimal

import pandas as pd
import pytest

from quant_research.backtesting.engine import EngineSettings, run_engine
from quant_research.backtesting.lookahead import (
    check_events_no_lookahead,
    check_market_no_lookahead,
    check_no_lookahead,
)
from quant_research.backtesting.run import parse_config
from quant_research.backtesting.synthetic import make_prices
from quant_research.news.events import EASTERN, Event, _schedule
from quant_research.strategies.information import (
    EarningsCoolOff,
    MarketGatedPullback,
    MarketTrendGate,
    MissingMarketDayError,
    earnings_usable_days,
    in_cool_off,
)
from quant_research.strategies.profit_target import TrendFilteredPullback
from quant_research.strategies.registry import make_strategy

D = Decimal
T = "TEST"
WHOLE = EngineSettings("stake", "normal", "whole", D(10))
CASH = D("10000.00")


def run(prices: pd.DataFrame, strategy) -> list[tuple[int, str, Decimal]]:
    r = run_engine(prices, T, strategy, WHOLE, CASH)
    days = list(prices["date"])
    return [(days.index(f.day), f.side, f.quantity) for f in r.fills]


def created(prices: pd.DataFrame, strategy) -> list[tuple[int, str]]:
    r = run_engine(prices, T, strategy, WHOLE, CASH)
    days = list(prices["date"])
    return [(days.index(o.created_day), o.intent.side) for o in r.orders]


# ---------- C1 Market-trend gate ----------
# SPY condition with SMA window 3, slope lag 1: close_T > SMA3_T > SMA3_(T−1)
#   idx   0   1   2   3   4   5   6   7   8   9  10  11  12
SPY_C1 = [10, 10, 10, 10, 11, 12, 13, 12, 11, 10, 11, 12, 13]
# T3: 10 > 10? no · T4: 11 > 10.33 > 10 yes · T5: 12 > 11 > 10.33 yes · T6: 13 > 12 > 11 yes · T7: 12 > 12.33? no
# T8: 11 > 12? no · T9: 10 no · T10: 11 > 10.67 but 10.67 > 11? no · T11: 12 > 11 > 10.67 yes · T12: 13 > 12 > 11 yes
CONDITION = [False] * 4 + [True] * 3 + [False] * 4 + [True] * 2


def c1(market: pd.DataFrame) -> MarketTrendGate:
    return MarketTrendGate(T, market, D(100), sma_window=3, slope_lag=1)


def test_c1_switches_exactly_when_the_spy_condition_flips():
    stock = make_prices([100] * 13)
    spy = make_prices(SPY_C1)
    # orders are created at the close of the flip days (4: on, 7: off, 11: on), filled at the next open
    assert created(stock, c1(spy)) == [(4, "buy"), (7, "sell"), (11, "buy")]
    # idx5 open 100 → 100.05 ; (10,000 − 3) / 100.05 → 99 shares ; 9,904.95 + 3 → cash 92.05 (< US$100: no top-up)
    # idx8 open 100 → 99.95 ; 99 × 99.95 = 9,895.05 − 3 → cash 9,984.10
    # idx12 open 100.05 ; (9,984.10 − 3) / 100.05 → 99 shares ; 9,907.95 → cash 76.15
    r = run_engine(stock, T, c1(spy), WHOLE, CASH)
    days = list(stock["date"])
    assert [(days.index(f.day), f.side, f.quantity) for f in r.fills] == [
        (5, "buy", D(99)),
        (8, "sell", D(99)),
        (12, "buy", D(99)),
    ]
    assert r.portfolio.cash_usd == D("76.15")


def test_c1_starts_in_cash_while_the_condition_is_false():
    # the condition is false (or not computable) on idx 0–3 → no day-1 buy (decision 4)
    stock = make_prices([100] * 13)
    first = created(stock, c1(make_prices(SPY_C1)))[0]
    assert first == (4, "buy")


def test_c1_reinvests_dividends_only_while_holding():
    # dividend US$1.00 / share at idx6's open while holding 99 shares: 99.00 gross − 15% (14.85) = 84.15 net
    # cash 92.05 + 84.15 = 176.20 ≥ 100 → top-up order at idx6 close → idx7 open: (176.20 − 3) / 100.05 → 1 share
    # idx7 close: condition off → sell all 100 at idx8
    stock = make_prices([100] * 13, dividends={6: 1.0})
    assert run(stock, c1(make_prices(SPY_C1)))[:3] == [
        (5, "buy", D(99)),
        (7, "buy", D(1)),
        (8, "sell", D(100)),
    ]


def test_c1_stops_when_spy_has_no_row_for_a_trading_day():
    stock = make_prices([100] * 13)
    spy = make_prices(SPY_C1).drop(index=6)
    with pytest.raises(MissingMarketDayError, match="no row"):
        run_engine(stock, T, c1(spy), WHOLE, CASH)


def test_c1_passes_the_price_and_market_spy_checks():
    stock = make_prices([100 + (i % 4) for i in range(13)])
    spy = make_prices(SPY_C1)
    for cut in range(2, 12):
        check_no_lookahead(lambda: c1(spy), stock, cut, T, WHOLE, CASH)
        check_market_no_lookahead(c1, stock, spy, cut, T, WHOLE, CASH)


# ---------- C2 Market-gated pullback ----------
# Stock (opens = closes), X = Y = 5%. Stock's own trend filter off (SMA window 50 > history → never "strong uptrend").
#   idx      0    1    2    3    4    5   6   7
STOCK_C2 = [100, 100, 106, 106, 100, 99, 99, 99]
# idx0 close → entry ; idx1 open 100 → E = 100.05, sell level 105.0525 ; idx2 close 106 → sell ; idx3 open → sold,
# P = idx3 close 106 → rebuy level 100.70 ; idx4 close 100 ≤ 100.70 → rebuy signal (twin rebuys at idx5)
# SPY vs its 3-day average:  idx4: 9 ≤ 9.67 · idx5: 9 ≤ 9.33 → blocked ; idx6: 12 > 10 → rebuy → filled idx7
SPY_C2 = [10, 10, 10, 10, 9, 9, 12, 12]


def c2(market: pd.DataFrame) -> MarketGatedPullback:
    return MarketGatedPullback(
        T, D("0.05"), D("0.05"), D(100), market=market, market_window=3, sma_window=50, slope_lag=2
    )


def twin() -> TrendFilteredPullback:
    return TrendFilteredPullback(T, D("0.05"), D("0.05"), D(100), sma_window=50, slope_lag=2)


def test_c2_blocks_rebuys_only_while_spy_is_below_its_average():
    stock = make_prices(STOCK_C2)
    assert [(i, s) for i, s, _ in run(stock, twin())] == [(1, "buy"), (3, "sell"), (5, "buy")]
    # entry on day 1 is NOT blocked (SPY average not computable yet — decision 3); rebuy waits for SPY > average
    assert [(i, s) for i, s, _ in run(stock, c2(make_prices(SPY_C2)))] == [
        (1, "buy"),
        (3, "sell"),
        (7, "buy"),
    ]


def test_c2_is_its_twin_when_spy_stays_above_its_average():
    stock = make_prices(STOCK_C2)
    rising = make_prices([10 + i for i in range(8)])
    assert run(stock, c2(rising)) == run(stock, twin())


def test_c2_passes_the_price_and_market_spy_checks():
    stock = make_prices(STOCK_C2)
    spy = make_prices(SPY_C2)
    for cut in range(1, 7):
        check_no_lookahead(lambda: c2(spy), stock, cut, T, WHOLE, CASH)
        check_market_no_lookahead(c2, stock, spy, cut, T, WHOLE, CASH)


# ---------- E1 Earnings cool-off (real NYSE calendar: the availability rule needs it) ----------
def nyse_prices(closes: list[float], first: date) -> pd.DataFrame:
    """Synthetic prices on REAL NYSE trading days from `first` (holidays skipped)."""
    days = [d for d in sorted(_schedule()) if d >= first][: len(closes)]
    df = make_prices(closes)
    df["date"] = days
    return df


def et(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=EASTERN)


# idx: 0 Mon 1 Jul 2019 · 1 Tue 2 Jul · 2 Wed 3 Jul (early close 13:00) · [Thu 4 Jul holiday] · 3 Fri 5 Jul ·
#      4 Mon 8 Jul · 5 Tue 9 · 6 Wed 10 · 7 Thu 11 · 8 Fri 12 · 9 Mon 15 · 10 Tue 16
STOCK_E1 = [100, 100, 100, 106, 106, 106, 106, 100, 100, 100, 100]
EVENTS = [
    # earnings 8-K accepted Wed 3 Jul 14:00 ET — AFTER that day's 13:00 early close; Thu is a holiday → usable Fri 5 Jul
    Event("A", "8-K", et(2019, 7, 3, 14, 0), ("earnings",)),
    # earnings 8-K/A (its own event) accepted Thu 11 Jul 09:00 ET, before the open → usable Thu 11 Jul
    Event("B", "8-K/A", et(2019, 7, 11, 9, 0), ("earnings",)),
    # not earnings → never starts a cool-off
    Event("C", "8-K", et(2019, 7, 15, 9, 0), ("leadership change",)),
]


def e1(events=EVENTS) -> EarningsCoolOff:
    return EarningsCoolOff(
        T, D("0.05"), D("0.05"), D(100), events=events, sma_window=50, slope_lag=2
    )


def test_e1_usable_days_follow_the_availability_rule():
    assert earnings_usable_days(EVENTS) == [date(2019, 7, 5), date(2019, 7, 11)]


def test_e1_ignores_signals_for_exactly_two_trading_days():
    stock = nyse_prices(STOCK_E1, date(2019, 7, 1))
    # twin: entry idx1 (E = 100.05) ; idx3 close 106 ≥ 105.0525 → sold idx4 ; P = 106 ; idx7 close 100 ≤ 100.70 → idx8
    assert [(i, s) for i, s, _ in run(stock, twin())] == [(1, "buy"), (4, "sell"), (8, "buy")]
    # E1: event A usable Fri 5 Jul (idx3) → sell signals ignored at idx3 (Fri) and idx4 (Mon, over the weekend) ;
    #     idx5 (day 3) signal → sold idx6 ; P = idx6 close 106.
    #     event B usable Thu 11 Jul (idx7) → rebuy ignored at idx7 and idx8 ; idx9 rebuy → filled idx10.
    #     event C (leadership change) does not block anything.
    assert [(i, s) for i, s, _ in run(stock, e1())] == [(1, "buy"), (6, "sell"), (10, "buy")]


def test_in_cool_off_counts_trading_days_not_calendar_days():
    days = [date(2019, 7, d) for d in (1, 2, 3, 5, 8, 9)]  # 4 Jul holiday, 6–7 Jul weekend
    usable = [date(2019, 7, 5)]
    assert [in_cool_off(days[: i + 1], usable) for i in range(len(days))] == [
        False, False, False, True, True, False,
    ]  # fmt: skip


def test_e1_passes_the_price_and_events_spy_checks():
    stock = nyse_prices(STOCK_E1, date(2019, 7, 1))
    for cut in range(1, 10):
        check_no_lookahead(e1, stock, cut, T, WHOLE, CASH)
    days = list(stock["date"])

    def decide(day, events):  # the cool-off decision itself
        return in_cool_off([d for d in days if d <= day], earnings_usable_days(events))

    check_events_no_lookahead(decide, days, EVENTS)

    def orders_up_to(day, events):  # the whole strategy: every order it created up to `day`
        r = run_engine(stock, T, e1(events), WHOLE, CASH)
        return [(o.created_day, o.intent) for o in r.orders if o.created_day <= day]

    check_events_no_lookahead(orders_up_to, days, EVENTS)


def test_e1_without_events_is_its_twin():
    stock = nyse_prices(STOCK_E1, date(2019, 7, 1))
    assert run(stock, e1([])) == run(stock, twin())


# ---------- config + registry ----------
BASE = {
    "run_name": "t", "ticker": "AAA", "start": date(2017, 1, 3), "end": date(2020, 12, 31), "broker": "stake",
    "spread_level": "normal", "share_mode": "fractional", "initial_aud": "10000",
}  # fmt: skip


def test_configs_and_registry_build_c1_c2_e1():
    spy = make_prices(SPY_C1)
    cfg = parse_config({**BASE, "strategy": "c1_market_gate"})
    assert isinstance(make_strategy(cfg, market=spy), MarketTrendGate)
    for name, cls in (
        ("c2_market_gated_pullback", MarketGatedPullback),
        ("e1_earnings_cooloff", EarningsCoolOff),
    ):
        cfg = parse_config(
            {**BASE, "strategy": name, "profit_target_x": "0.02", "rebuy_dip_y": "0.04"}
        )
        assert isinstance(make_strategy(cfg, market=spy, events=EVENTS), cls)
        with pytest.raises(ValueError, match="needs profit_target_x"):
            parse_config({**BASE, "strategy": name})
        with pytest.raises(ValueError, match="outside the grid"):
            parse_config(
                {**BASE, "strategy": name, "profit_target_x": "0.06", "rebuy_dip_y": "0.04"}
            )
    with pytest.raises(ValueError, match="only for"):
        parse_config({**BASE, "strategy": "c1_market_gate", "profit_target_x": "0.02"})


def test_registry_refuses_to_load_spy_or_events_for_the_locked_period():
    from quant_research.backtesting.run import FinalTestLockedError

    for name, extra in (("c1_market_gate", {}), ("e1_earnings_cooloff", {"profit_target_x": "0.02", "rebuy_dip_y": "0.04"})):  # fmt: skip
        cfg = parse_config({**BASE, "strategy": name, "end": date(2021, 3, 1), **extra})
        with pytest.raises(FinalTestLockedError):
            make_strategy(cfg)
