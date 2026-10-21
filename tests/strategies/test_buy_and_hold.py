"""S0 buy-and-hold — synthetic data only."""

from decimal import Decimal

import pytest

from quant_research.backtesting.engine import EngineSettings, run_engine
from quant_research.backtesting.lookahead import check_no_lookahead
from quant_research.backtesting.synthetic import make_prices
from quant_research.strategies.buy_and_hold import BuyAndHold

D = Decimal
T = "TEST"
FRACTIONAL = EngineSettings("stake", "normal", "fractional", D(10))
WHOLE = EngineSettings("stake", "normal", "whole", D(10))


def s0() -> BuyAndHold:
    return BuyAndHold(T, D(100))


def test_buys_max_affordable_at_day_2_open():
    prices = make_prices(opens=[100, 120, 130], closes=[105, 125, 135])
    r = run_engine(prices, T, s0(), WHOLE, D("10000.00"))
    (f,) = r.fills
    # day 1 close → day 2 open 120 × 1.0005 = 120.06 ; (10,000 − 3) / 120.06 = 83.27 → 83 shares
    # cost 83 × 120.06 = 9,964.98 + 3.00 → cash 32.02
    assert (f.day, f.reference_price_usd, f.quantity) == (prices["date"][1], D(120), D(83))
    assert r.portfolio.cash_usd == D("32.02")


def test_dividend_reinvested_only_when_cash_reaches_100():
    # whole mode, 83 shares (see above). Small dividend 0.50 → net 83 × 0.50 = 41.50 − 6.23 = 35.27
    # → cash 32.02 + 35.27 = 67.29 < 100 → NO reinvestment
    small = make_prices(opens=[100, 120, 120, 120, 120], dividends={3: 0.50})
    r = run_engine(small, T, s0(), WHOLE, D("10000.00"))
    assert len(r.fills) == 1 and r.portfolio.cash_usd == D("67.29")
    # Big dividend 2.00 → gross 166.00, withholding 24.90, net 141.10 → cash 173.12 ≥ 100
    # → buy at the next open: (173.12 − 3) / 120.06 = 1.41 → 1 whole share (120.06 + 3) → cash 50.06
    big = make_prices(opens=[100, 120, 120, 120, 120], dividends={3: 2.00})
    r = run_engine(big, T, s0(), WHOLE, D("10000.00"))
    assert [f.day for f in r.fills] == [big["date"][1], big["date"][4]]
    assert r.fills[1].quantity == D(1)
    assert r.portfolio.cash_usd == D("50.06")


def test_never_sells():
    closes = [100, 80, 60, 140, 50, 150]
    r = run_engine(make_prices(opens=closes, closes=closes), T, s0(), FRACTIONAL, D("10000.00"))
    assert all(f.side == "buy" for f in r.fills)


@pytest.mark.parametrize("cut", [1, 3, 6])
def test_s0_passes_the_lookahead_check(cut):
    closes = [100, 103, 101, 104, 99, 98, 102, 105, 103]
    prices = make_prices(opens=closes, closes=closes, dividends={2: 3.0, 5: 3.0})
    check_no_lookahead(s0, prices, cut, T, FRACTIONAL, D("10000.00"))
    check_no_lookahead(s0, prices, cut, T, WHOLE, D("10000.00"))
