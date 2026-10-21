"""Edge cases (Step 4.6) — synthetic data, hand calculations in comments."""

from decimal import Decimal

import pytest

from quant_research.backtesting.engine import EngineSettings, run_engine
from quant_research.backtesting.synthetic import make_prices
from quant_research.execution.fills import Rejection, fill_order
from quant_research.execution.intrabar import resolve_intrabar
from quant_research.execution.orders import OrderIntent
from quant_research.portfolio.ledger import Portfolio
from quant_research.strategies.buy_and_hold import BuyAndHold

D = Decimal
T = "TEST"
FRACTIONAL = EngineSettings("stake", "normal", "fractional", D(10))
WHOLE = EngineSettings("stake", "normal", "whole", D(10))


def s0():
    return BuyAndHold(T, D(100))


def cash_identity(p: Portfolio) -> bool:
    return (
        p.initial_cash_usd
        - p.total_spent_usd
        - p.total_fees_usd
        + p.total_received_usd
        + p.dividends_net_usd
        == p.cash_usd
    )


def test_sideways_series_loses_exactly_the_costs():
    r = run_engine(make_prices(opens=[100] * 6), T, s0(), FRACTIONAL, D("10000.00"))
    # fill 100.05 ; qty (10,000 − 3) / 100.05 = 99.92003998… → 99.920039 ; cost 9,996.9999… → 9,997.00 → cash 0.00
    # at close 100: 99.920039 × 100 = 9,992.0039 → 9,992.00 (cost of entry: 3.00 fee + 5.00 spread)
    # liquidation: 99.920039 × 99.95 = 9,987.0078… → 9,987.00 − 3.00 = 9,984.00
    assert (r.last_close_value_usd, r.liquidation_value_usd) == (D("9992.00"), D("9984.00"))
    assert cash_identity(r.portfolio)


def test_rising_and_falling_series():
    up = run_engine(
        make_prices(opens=[100, 100, 110, 121, 133.1]), T, s0(), FRACTIONAL, D("10000.00")
    )
    down = run_engine(
        make_prices(opens=[100, 100, 90, 81, 72.9]), T, s0(), FRACTIONAL, D("10000.00")
    )
    # same 99.920039 shares bought at 100.05 ; last close 133.1 vs 72.9
    # up:   99.920039 × 133.1 = 13,299.357… → 13,299.35 ; down: 99.920039 × 72.9 = 7,284.170… → 7,284.17
    assert (up.last_close_value_usd, down.last_close_value_usd) == (D("13299.35"), D("7284.17"))
    assert cash_identity(up.portfolio) and cash_identity(down.portfolio)


@pytest.mark.parametrize(("open_day2", "gap"), [(110, D("0.1")), (90, D("-0.1"))])
def test_gap_up_and_gap_down_fill_at_the_open(open_day2, gap):
    prices = make_prices(opens=[100, open_day2, open_day2], closes=[100, open_day2, open_day2])
    r = run_engine(prices, T, s0(), WHOLE, D("10000.00"))
    (f,) = r.fills
    # close 100 → next open 110 / 90 → gap ±10%, fill at that open × 1.0005 (never at 100)
    assert (f.gap_pct, f.reference_price_usd) == (gap, D(open_day2))


def test_split_and_dividend_on_the_same_day_while_holding():
    prices = make_prices(opens=[100, 100, 50, 50], dividends={2: 0.25}, splits={2: 2.0})
    r = run_engine(prices, T, s0(), WHOLE, D("10000.00"))
    p = r.portfolio
    # 99 shares bought day 2 (see test_performance) ; day 3: split → 198 ; dividend on 198 shares
    # gross 198 × 0.25 = 49.50 ; withholding 7.425 → 7.43 ; net 42.07 → cash 92.05 + 42.07 = 134.12 ≥ 100
    # → S0 reinvests at day 4 open 50.025: (134.12 − 3) / 50.025 = 2.62 → 2 shares
    split, div = p.entries[1], p.entries[2]
    assert (split.type, split.quantity, div.type, div.quantity) == (
        "SPLIT",
        D(198),
        "DIVIDEND",
        D(198),
    )
    assert p.dividends_net_usd == D("42.07")
    assert p.position(T).quantity == D(200)
    assert cash_identity(p)


def test_whole_mode_cash_just_short_of_one_share():
    # fill 100 × 1.0005 = 100.05 ; one share needs 100.05 + 3.00 fee = 103.05
    short = Portfolio("103.04", share_mode="whole")
    r = fill_order(
        OrderIntent("buy", T, "max_affordable"),
        make_prices(opens=[100])["date"][0],
        D(100),
        short,
        "stake",
        "normal",
        "whole",
        D(10),
    )
    assert isinstance(r, Rejection) and "no shares affordable" in r.reason
    enough = Portfolio("103.05", share_mode="whole")
    r = fill_order(
        OrderIntent("buy", T, "max_affordable"),
        make_prices(opens=[100])["date"][0],
        D(100),
        enough,
        "stake",
        "normal",
        "whole",
        D(10),
    )
    assert r.quantity == D(1) and enough.cash_usd == D("0.00")


# ---------- ambiguous bars: assume the WORSE order ----------
def test_both_levels_in_bar_not_holding_only_buy():
    # bar O 100 H 106 L 94 C 100 ; buy at 95, sell at 105 → both inside
    # worse order when flat: high first (nothing to sell), then low → only the BUY at 95
    assert resolve_intrabar(D(100), D(106), D(94), D(100), D(95), D(105), holding=False) == [
        ("buy", D(95))
    ]


def test_both_levels_in_bar_holding_only_sell():
    # holding: low first (nothing to rebuy), then high → only the SELL at 105 ; no same-day round trip
    assert resolve_intrabar(D(100), D(106), D(94), D(100), D(95), D(105), holding=True) == [
        ("sell", D(105))
    ]


def test_single_level_and_no_level():
    assert resolve_intrabar(D(100), D(104), D(94), D(100), D(95), D(105), holding=False) == [
        ("buy", D(95))
    ]
    assert resolve_intrabar(D(100), D(104), D(96), D(100), D(95), D(105), holding=False) == []
    assert resolve_intrabar(D(100), D(104), D(96), D(100), D(95), D(105), holding=True) == []


def test_gap_through_a_level_fills_at_the_open():
    # gap down: open 92 already below buy level 95 → buy at the open 92
    assert resolve_intrabar(D(92), D(93), D(90), D(91), D(95), None, holding=False) == [
        ("buy", D(92))
    ]
    # gap up: open 108 above sell level 105 → sell at the open 108
    assert resolve_intrabar(D(108), D(110), D(107), D(109), None, D(105), holding=True) == [
        ("sell", D(108))
    ]


def test_inconsistent_bar_is_an_error():
    with pytest.raises(ValueError, match="inconsistent bar"):
        resolve_intrabar(D(100), D(99), D(94), D(100), D(95), D(105), holding=False)
