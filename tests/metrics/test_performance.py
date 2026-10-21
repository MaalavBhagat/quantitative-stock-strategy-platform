"""Performance metrics — tiny hand-calculated series (working in comments)."""

import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from quant_research.backtesting.engine import EngineSettings, run_engine
from quant_research.backtesting.synthetic import make_prices
from quant_research.metrics.performance import (
    annual_volatility,
    cagr,
    calendar_year_returns,
    max_drawdown,
    pct_days_fully_in_cash,
    round_trips,
    sharpe,
    summarise,
    total_return,
    worst_calendar_year,
)
from quant_research.strategies.buy_and_hold import BuyAndHold

D = Decimal


def test_total_return():
    # 100 → 120 : 120 / 100 − 1 = 0.20
    assert total_return(100, 120) == pytest.approx(0.20, abs=1e-15)


def test_cagr_exact_four_years():
    # 2012-01-01 → 2016-01-01 = 1,461 calendar days → 365.25 / 1,461 = 0.25 exactly
    # 100 → 146.41 = 1.1⁴ → CAGR = 1.4641^0.25 − 1 = 0.10
    assert cagr(100, 146.41, date(2012, 1, 1), date(2016, 1, 1)) == pytest.approx(0.10, abs=1e-12)


def test_max_drawdown_with_dates():
    days = [date(2014, 1, d) for d in (2, 3, 6, 7, 8, 9)]
    # values 100, 110, 99, 120, 90, 130: falls 110 → 99 = −10% ; 120 → 90 = −25% (the worst)
    dd = max_drawdown(days, [100, 110, 99, 120, 90, 130])
    assert dd.max_drawdown == pytest.approx(-0.25, abs=1e-15)
    assert (dd.peak_day, dd.trough_day) == (date(2014, 1, 7), date(2014, 1, 8))


def test_max_drawdown_never_falls():
    days = [date(2014, 1, d) for d in (2, 3, 6)]
    dd = max_drawdown(days, [100, 101, 102])
    assert (dd.max_drawdown, dd.peak_day, dd.trough_day) == (0.0, None, None)


def test_annual_volatility():
    # values 100, 110, 99 → returns +0.10, −0.10 ; mean 0
    # sample stdev = √((0.01 + 0.01) / 1) = 0.141421356… ; × √252 = 2.244994432…
    assert annual_volatility([100, 110, 99]) == pytest.approx(
        math.sqrt(0.02) * math.sqrt(252), rel=1e-12
    )
    assert annual_volatility([100, 110, 99]) == pytest.approx(2.2449944320643649, rel=1e-12)


def test_sharpe_rf_zero():
    # values 100, 101, 103.02 → returns 0.01, 0.02 ; mean 0.015
    # sample stdev = √((0.005² + 0.005²) / 1) = 0.0070710678 ; Sharpe = 0.015 / 0.0070710678 × √252 = 33.6749…
    assert sharpe([100, 101, 103.02]) == pytest.approx(
        0.015 / math.sqrt(0.00005) * math.sqrt(252), rel=1e-9
    )
    assert sharpe([100, 101, 103.02]) == pytest.approx(33.67491648096547, rel=1e-9)


def test_calendar_years_and_worst_year():
    days = [date(2014, 6, 30), date(2014, 12, 31), date(2015, 6, 30), date(2015, 12, 31)]
    values = [110, 120, 90, 108]
    # 2014: 120 / initial 100 − 1 = +0.20 ; 2015: 108 / 120 − 1 = −0.10 (worst)
    years = calendar_year_returns(days, values, 100)
    assert years[2014] == pytest.approx(0.20, abs=1e-15) and years[2015] == pytest.approx(
        -0.10, abs=1e-15
    )
    assert worst_calendar_year(days, values, 100) == (2015, pytest.approx(-0.10, abs=1e-15))


def test_pct_days_fully_in_cash():
    # market value 0, 0, 50, 50 → 2 of 4 days fully in cash = 0.5
    assert pct_days_fully_in_cash([0, 0, 50, 50]) == 0.5


@dataclass
class FakeFill:
    side: str
    position_after: Decimal


def test_round_trips_count_full_exits_only():
    fills = [
        FakeFill("buy", D(10)),
        FakeFill("sell", D(4)),  # partial — not a round trip
        FakeFill("sell", D(0)),  # full exit → 1
        FakeFill("buy", D(5)),
        FakeFill("sell", D(0)),  # full exit → 2
        FakeFill("buy", D(5)),  # still open at the end
    ]
    assert round_trips(fills) == 2


def test_summarise_matches_ledger_and_aud_conversion():
    prices = make_prices(opens=[100, 100, 110, 99, 120], dividends={3: 1.0})
    r = run_engine(
        prices,
        "TEST",
        BuyAndHold("TEST", D(100)),
        EngineSettings("stake", "normal", "whole", D(10)),
        D("10000.00"),
    )
    # constant made-up rate 0.5 → every AUD value is USD × 2, so the AUD drawdown equals the USD drawdown
    s = summarise(r, D("10000.00"), D("20000"), D("19000"), lambda d: D("0.5"))
    p = r.portfolio
    # buy 1: (10,000 − 3) / 100.05 → 99 whole shares, cost 9,904.95 → cash 92.05
    # dividend 99 × 1.00 = 99.00 − withholding 14.85 = 84.15 → cash 176.20 ≥ 100 → reinvest
    # buy 2 at next open 120.06: (176.20 − 3) / 120.06 → 1 share → two Stake fees = 6.00
    assert len(r.fills) == 2
    assert s.total_fees_usd == float(p.total_fees_usd) == 6.0
    assert (s.dividends_gross_usd, s.withholding_usd, s.dividends_net_usd) == (
        float(p.dividends_gross_usd),
        float(p.withholding_usd),
        float(p.dividends_net_usd),
    )
    assert s.total_spread_cost_usd == float(r.fills[0].spread_cost_usd + r.fills[1].spread_cost_usd)
    assert s.max_drawdown_aud.max_drawdown == pytest.approx(s.max_drawdown.max_drawdown, abs=1e-12)
    # AUD: 20,000 → 19,000 = −5%
    assert s.total_return_aud == pytest.approx(-0.05, abs=1e-15)
    assert s.pct_days_fully_in_cash == pytest.approx(1 / 5)  # day 1 only (bought at day 2 open)
    assert s.round_trips == 0
