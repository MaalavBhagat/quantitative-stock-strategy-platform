"""S1 fixed profit target + S2 pullback from peak — hand-calculated synthetic series.

Settings: Stake (US$3 fee), normal spread 0.05% (buy fill = open × 1.0005, sell fill = open × 0.9995),
WHOLE shares, start cash US$10,000.00, X = Y = 0.05. Prices are made up.
"""

from decimal import Decimal

import pytest

from quant_research.backtesting.engine import EngineSettings, run_engine
from quant_research.backtesting.lookahead import check_no_lookahead
from quant_research.backtesting.synthetic import make_prices
from quant_research.strategies.profit_target import FixedProfitTarget, PullbackFromPeak

D = Decimal
T = "TEST"
WHOLE = EngineSettings("stake", "normal", "whole", D(10))
FRACTIONAL = EngineSettings("stake", "normal", "fractional", D(10))
CASH = D("10000.00")


def s1(reinvest="100"):
    return FixedProfitTarget(T, D("0.05"), D("0.05"), D(reinvest))


def s2(reinvest="100"):
    return PullbackFromPeak(T, D("0.05"), D("0.05"), D(reinvest))


def trades(result):
    return [(f.day, f.side, f.quantity, f.fill_price_usd) for f in result.fills]


def test_s1_full_sell_then_rebuy_cycle():
    #        day0  day1  day2  day3  day4  day5
    opens = [100, 100, 103, 107, 103, 100]
    closes = [100, 100, 106, 104, 101, 100]
    prices = make_prices(opens=opens, closes=closes)
    days = prices["date"]
    r = run_engine(prices, T, s1(), WHOLE, CASH)
    # day0 close → entry order. day1 open 100 → fill 100.05 = E ; (10,000 − 3) / 100.05 → 99 shares
    #   cost 99 × 100.05 = 9,904.95 → cash 92.05 ; sell level E × 1.05 = 105.0525
    # day2 close 106 ≥ 105.0525 → sell order (filled at day3 OPEN, not at day2's close)
    # day3 open 107 → sell fill 107 × 0.9995 = 106.9465 = S ; proceeds 99 × 106.9465 = 10,587.7035 → 10,587.70
    #   − fee 3 → cash 92.05 + 10,584.70 = 10,676.75 ; rebuy level S × 0.95 = 101.599175 ; close 104 → no
    # day4 close 101 ≤ 101.599175 → buy order
    # day5 open 100 → fill 100.05 = new E ; (10,676.75 − 3) / 100.05 → 106 shares, cost 10,605.30
    #   cash 10,676.75 − 10,605.30 − fee 3.00 = 68.45
    assert trades(r) == [
        (days[1], "buy", D(99), D("100.05")),
        (days[3], "sell", D(99), D("106.9465")),
        (days[5], "buy", D(106), D("100.05")),
    ]
    assert r.portfolio.cash_usd == D("68.45")
    assert [o.created_day for o in r.orders] == [days[0], days[2], days[4]]


def test_s1_stranded_and_s2_rebuys_higher_than_it_sold():
    #        day0 day1 day2 day3 day4 day5 day6 day7
    opens = [100, 100, 103, 107, 110, 114, 110, 112]
    closes = [100, 100, 106, 108, 115, 109, 112, 113]
    prices = make_prices(opens=opens, closes=closes)
    days = prices["date"]
    # Same first cycle as above: E = 100.05, sell order day2, S = 106.9465 at day3 → cash 10,676.75
    # S1: rebuy level 101.599175 — closes 108, 115, 109, 112, 113 never reach it → STRANDED in cash
    r1 = run_engine(prices, T, s1(reinvest="1000"), WHOLE, CASH)
    assert [f.side for f in r1.fills] == ["buy", "sell"]
    assert r1.portfolio.position(T).quantity == 0 and r1.portfolio.cash_usd == D("10676.75")
    # S2: P starts at the sale-fill day's close (day3) 108 ; day4 close 115 → P = 115 ; level 115 × 0.95 = 109.25
    #   day5 close 109 ≤ 109.25 → buy order ; day6 open 110 → fill 110.055 (> S 106.9465: rebuys HIGHER)
    #   (10,676.75 − 3) / 110.055 → 96 shares ; cost 96 × 110.055 = 10,565.28 → cash 108.47
    #   (reinvest minimum set to 1,000 here so no top-up attempt clutters the example)
    r2 = run_engine(prices, T, s2(reinvest="1000"), WHOLE, CASH)
    assert trades(r2)[2] == (days[6], "buy", D(96), D("110.055"))
    assert r2.fills[2].fill_price_usd > r2.fills[1].fill_price_usd
    assert r2.portfolio.cash_usd == D("108.47")


def test_s2_full_cycle_matches_s1_when_no_new_high():
    # In the first series the price never makes a new high after the sale: P = day3 close 104
    # S2 level 104 × 0.95 = 98.8 → day4 close 101 is NOT ≤ 98.8 → S2 does not rebuy (S1 did, at 101.599)
    prices = make_prices(
        opens=[100, 100, 103, 107, 103, 100], closes=[100, 100, 106, 104, 101, 100]
    )
    r = run_engine(prices, T, s2(), WHOLE, CASH)
    assert [f.side for f in r.fills] == ["buy", "sell"]


def test_entry_price_unchanged_by_dividend_top_up():
    #        day0 day1 day2 day3 day4
    opens = [100, 100, 100, 100, 104]
    closes = [100, 100, 100, 104, 105.06]
    prices = make_prices(opens=opens, closes=closes, dividends={2: 2.00})
    days = prices["date"]
    r = run_engine(prices, T, s1(), WHOLE, CASH)
    # day1: E = 100.05, 99 shares, cash 92.05
    # day2 dividend 99 × 2.00 = 198.00 − withholding 29.70 = 168.30 → cash 260.35 ≥ 100 → top-up order
    # day3 open 100 → top-up fill 100.05 ; (260.35 − 3) / 100.05 → 2 shares, cost 200.10 → cash 57.25
    #   E stays 100.05 (the ENTRY fill) → sell level 105.0525
    #   (average cost would be (9,904.95 + 3 + 200.10 + 3) / 101 = 100.109… → level 105.11… — NOT used)
    # day4 close 105.06 ≥ 105.0525 → sell order created on day4
    assert [(f.day, f.side, f.quantity) for f in r.fills] == [
        (days[1], "buy", D(99)),
        (days[3], "buy", D(2)),
    ]
    assert r.orders[-1].created_day == days[4] and r.orders[-1].intent.side == "sell"


def test_no_top_ups_while_in_cash():
    # after the sale (day3) cash is ~10,676 ≥ 100 but there is no position → no top-up buys;
    # closes stay above S × 0.95 = 101.599 → no rebuy either
    prices = make_prices(
        opens=[100, 100, 103, 107, 106, 106, 106], closes=[100, 100, 106, 104, 105, 105, 105]
    )
    r = run_engine(prices, T, s1(), WHOLE, CASH)
    assert [f.side for f in r.fills] == ["buy", "sell"]
    assert len(r.orders) == 2


def test_thresholds_use_close_not_intraday_high():
    # day2 high is 103 × 1.01 ≈ 107 ≥ 105.05 but the CLOSE 104 is below → no sell
    prices = make_prices(opens=[100, 100, 103, 104], closes=[100, 100, 104, 104])
    r = run_engine(prices, T, s1(), WHOLE, CASH)
    assert [f.side for f in r.fills] == ["buy"]


@pytest.mark.parametrize("make", [s1, s2])
@pytest.mark.parametrize("cut", [2, 4, 6])
def test_s1_s2_pass_the_lookahead_check(make, cut):
    closes = [100, 100, 106, 108, 115, 109, 112, 101, 99, 106, 104]
    opens = [100, 100, 103, 107, 110, 114, 110, 111, 100, 104, 105]
    prices = make_prices(opens=opens, closes=closes, dividends={1: 2.0, 9: 1.0})
    check_no_lookahead(make, prices, cut, T, FRACTIONAL, CASH)
    check_no_lookahead(make, prices, cut, T, WHOLE, CASH)
