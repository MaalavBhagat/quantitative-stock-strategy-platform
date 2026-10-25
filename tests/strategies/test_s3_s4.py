"""S3 mean reversion + S4 trend filter — hand-worked synthetic series.

Stake US$3 fee, normal spread (buy = open × 1.0005, sell = open × 0.9995), WHOLE shares, US$10,000.
"""

from decimal import Decimal

import pytest

from quant_research.backtesting.engine import EngineSettings, run_engine
from quant_research.backtesting.lookahead import check_no_lookahead
from quant_research.backtesting.synthetic import make_prices
from quant_research.strategies.mean_reversion import MeanReversion
from quant_research.strategies.profit_target import (
    FixedProfitTarget,
    TrendFilteredProfitTarget,
    TrendFilteredPullback,
)

D = Decimal
T = "TEST"
WHOLE = EngineSettings("stake", "normal", "whole", D(10))
FRACTIONAL = EngineSettings("stake", "normal", "fractional", D(10))
CASH = D("10000.00")


def s3():
    return MeanReversion(T, D("1.0"), 3, D(100))


def s4_s1():
    return TrendFilteredProfitTarget(T, D("0.05"), D("0.05"), D(100), sma_window=5, slope_lag=2)


def s4_s2():
    return TrendFilteredPullback(T, D("0.05"), D("0.05"), D(100), sma_window=5, slope_lag=2)


def test_s3_sell_then_rebuy_cycle():
    #        d0  d1  d2  d3  d4  d5  d6
    opens = [10, 10, 10, 10, 13, 12, 8]
    closes = [10, 10, 10, 13, 12, 8, 8]
    prices = make_prices(opens=opens, closes=closes)
    days = prices["date"]
    r = run_engine(prices, T, s3(), WHOLE, CASH)
    # d0 close → entry order. d1 open 10 → 10.005 ; (10,000 − 3) / 10.005 → 999 shares ; 9,994.995 → 9,995.00
    #   → cash 2.00. d1: z needs 3 values → none. d2: [10,10,10] std 0 → none.
    # d3: [10,10,13] mean 11, dev −1 −1 2, sum sq 6 ÷ 2 = 3, std 1.732 ; z = 2 / 1.732 = 1.155 ≥ 1 → sell order
    # d4 open 13 → sell 12.9935 ; 999 × 12.9935 = 12,980.5065 → 12,980.50 − 3 → cash 12,979.50
    #   d4 close: [10,13,12] mean 11.667, z = (12 − 11.667) / … > 0 → no buy
    # d5: [13,12,8] mean 11, dev 2 1 −3, sum sq 14 ÷ 2 = 7, std 2.6458 ; z = −3 / 2.6458 = −1.134 ≤ −1 → buy order
    # d6 open 8 → 8.004 ; (12,979.50 − 3) / 8.004 → 1,621 shares ; 12,974.484 → 12,974.49 → cash 2.01
    assert [(f.day, f.side, f.quantity) for f in r.fills] == [
        (days[1], "buy", D(999)),
        (days[4], "sell", D(999)),
        (days[6], "buy", D(1621)),
    ]
    assert r.portfolio.cash_usd == D("2.01")


def trend_series():
    # idx 0–6 warm-up 90…96 (strategy only sees them), trading from idx 7. opens = closes.
    closes = [90, 91, 92, 93, 94, 95, 96, 100, 100, 106, 107, 105.5, 105.1, 105.06, 105]
    return make_prices(opens=closes, closes=closes)


def test_s4_blocks_sell_in_uptrend_then_sells_when_it_ends():
    prices = trend_series()
    days = prices["date"]
    start = days[7]
    # idx 7 close → entry ; idx 8 open 100 → E = 100.05 → sell level 105.0525
    # S1: idx 9 close 106 ≥ 105.0525 → sell order on idx 9
    r1 = run_engine(
        prices,
        T,
        FixedProfitTarget(T, D("0.05"), D("0.05"), D(100)),
        WHOLE,
        CASH,
        trade_start=start,
    )
    assert [(o.created_day, o.intent.side) for o in r1.orders][1] == (days[9], "sell")
    # S4 (SMA5, slope vs 2 days ago):
    # idx 9:  SMA5 (95,96,100,100,106) 99.4 ; lag (93…100) 95.6 ; 106 > 99.4 > 95.6 → uptrend → NO sell
    # idx 10: SMA5 101.8 ; lag 97.0 ; 107 > 101.8 > 97 → blocked
    # idx 11: SMA5 103.7 ; lag 99.4 ; 105.5 > 103.7 > 99.4 → blocked
    # idx 12: SMA5 104.72 ; lag 101.8 ; 105.1 > 104.72 → blocked
    # idx 13: SMA5 (106,107,105.5,105.1,105.06) 105.732 ; 105.06 < 105.732 → not an uptrend ; 105.06 ≥ 105.0525 → SELL
    r4 = run_engine(prices, T, s4_s1(), WHOLE, CASH, trade_start=start)
    sells = [o.created_day for o in r4.orders if o.intent.side == "sell"]
    assert sells == [days[13]]


def test_s4_allows_sell_without_uptrend():
    # falling warm-up 110…104, then trading: idx 7 close 100 → entry ; idx 8 open 100 → E 100.05 (level 105.0525)
    # idx 9 close 106: SMA5 (105,104,100,100,106) = 103.0 ; SMA5 two days earlier (107,106,105,104,100) = 104.4
    #   → average FALLING → no strong uptrend → the sell is allowed, exactly like S1 (order on idx 9)
    closes = [110, 109, 108, 107, 106, 105, 104, 100, 100, 106, 107]
    prices = make_prices(opens=closes, closes=closes)
    days = prices["date"]
    r4 = run_engine(prices, T, s4_s1(), WHOLE, CASH, trade_start=days[7])
    assert [o.created_day for o in r4.orders if o.intent.side == "sell"] == [days[9]]


@pytest.mark.parametrize("make", [s3, s4_s1, s4_s2])
@pytest.mark.parametrize("cut", [3, 7, 11])
def test_s3_s4_pass_the_lookahead_check(make, cut):
    closes = [90, 92, 95, 99, 104, 103, 109, 115, 108, 100, 97, 104, 111, 106, 99]
    opens = [c - 0.5 for c in closes]
    prices = make_prices(opens=opens, closes=closes, dividends={4: 1.0, 12: 1.0}, splits={8: 2.0})
    check_no_lookahead(make, prices, cut, T, FRACTIONAL, CASH)
    check_no_lookahead(make, prices, cut, T, WHOLE, CASH)
