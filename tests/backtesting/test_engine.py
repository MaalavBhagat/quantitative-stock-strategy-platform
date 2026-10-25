"""Engine timeline, look-ahead guard and order handling (Steps 4.1–4.3) — synthetic data only."""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from quant_research.backtesting.engine import EngineSettings, PortfolioView, run_engine
from quant_research.backtesting.lookahead import check_no_lookahead
from quant_research.backtesting.synthetic import make_prices
from quant_research.execution.orders import OrderIntent

D = Decimal
T = "TEST"
FRACTIONAL = EngineSettings("stake", "normal", "fractional", D(10))
WHOLE = EngineSettings("stake", "normal", "whole", D(10))


class Scripted:
    """Test-only strategy: returns pre-set intents on given row numbers."""

    def __init__(self, plan: dict[int, list[OrderIntent]]):
        self.plan, self.i = plan, -1

    def on_close(self, day, history, portfolio_view):
        self.i += 1
        return self.plan.get(self.i, [])


class UpDown:
    """Test-only, data-dependent: buy max if close rose, sell all if it fell."""

    def on_close(self, day, history, view: PortfolioView):
        if len(history) < 2:
            return []
        today, yesterday = history["close_raw"].iloc[-1], history["close_raw"].iloc[-2]
        if today > yesterday and view.quantity == 0:
            return [OrderIntent("buy", T, "max_affordable")]
        if today < yesterday and view.quantity > 0:
            return [OrderIntent("sell", T, "all")]
        return []


def test_signal_at_close_fills_at_next_open_not_same_close():
    prices = make_prices(opens=[100, 120, 130], closes=[105, 125, 135])
    r = run_engine(prices, T, Scripted({0: [OrderIntent("buy", T, D(10))]}), WHOLE, D("10000.00"))
    (f,) = r.fills
    # created at day 0 close (105) → filled day 1 at OPEN 120 × 1.0005 = 120.06 (never 105)
    assert (f.day, f.reference_price_usd, f.fill_price_usd) == (
        prices["date"][1],
        D(120),
        D("120.06"),
    )
    assert r.orders[0].created_day == prices["date"][0] and r.orders[0].intended_day == f.day


def test_split_dividend_then_order_on_the_same_day():
    prices = make_prices(opens=[100, 100, 50, 50], dividends={2: 0.5}, splits={2: 2.0})
    plan = {0: [OrderIntent("buy", T, D(10))], 1: [OrderIntent("sell", T, D(5))]}
    r = run_engine(prices, T, Scripted(plan), WHOLE, D("10000.00"))
    p = r.portfolio
    # day 1: BUY 10 ; day 2 OPEN: SPLIT 10 → 20, DIVIDEND on 20 shares, THEN the sell of 5
    assert [e.type for e in p.entries] == ["BUY", "SPLIT", "DIVIDEND", "SELL"]
    split, div, sell = p.entries[1:]
    assert (split.quantity, div.quantity, sell.quantity) == (D(20), D(20), D(5))
    assert {split.date, div.date, sell.date} == {prices["date"][2]}
    # dividend 20 × 0.50 = 10.00 ; withholding 1.50 ; net 8.50
    assert p.dividends_net_usd == D("8.50")
    assert p.position(T).quantity == D(15)


def test_steps_happen_in_order_each_day():
    # valuation (step 3) must see the fill (step 2) of the same morning: equity on day 1 holds shares
    prices = make_prices(opens=[100, 100, 100])
    r = run_engine(prices, T, Scripted({0: [OrderIntent("buy", T, D(10))]}), WHOLE, D("10000.00"))
    assert r.equity[0].market_value_usd == D("0.00")
    # day 1: 10 shares × close 100 = 1,000.00 ; cash 10,000 − 1,000.50 − 3.00 = 8,996.50
    assert (r.equity[1].market_value_usd, r.equity[1].cash_usd) == (D("1000.00"), D("8996.50"))


def test_rejections_are_logged_and_the_run_continues():
    prices = make_prices(opens=[100, 100, 100, 100])
    plan = {
        0: [OrderIntent("sell", T, "all")],  # nothing held → rejected
        1: [OrderIntent("buy", T, D(1000))],  # 100,050 + fee > cash → rejected
        2: [OrderIntent("buy", T, D("0.05"))],  # 5.0025 < US$10 minimum → rejected
    }
    r = run_engine(
        prices,
        T,
        Scripted({**plan, 2: plan[2] + [OrderIntent("buy", T, D(10))]}),
        FRACTIONAL,
        D("10000.00"),
    )
    statuses = [(o.status, o.reason is not None) for o in r.orders]
    assert statuses == [
        ("REJECTED", True),
        ("REJECTED", True),
        ("REJECTED", True),
        ("FILLED", False),
    ]
    assert "no TEST shares held" in r.orders[0].reason
    assert "cash" in r.orders[1].reason
    assert "below minimum" in r.orders[2].reason
    assert r.portfolio.position(T).quantity == D(10)


def test_orders_after_the_last_day_expire():
    prices = make_prices(opens=[100, 100])
    r = run_engine(prices, T, Scripted({1: [OrderIntent("buy", T, D(1))]}), WHOLE, D("10000.00"))
    (o,) = r.orders
    assert (o.status, o.intended_day, r.fills) == ("EXPIRED", None, [])
    assert r.portfolio.cash_usd == D("10000.00")


def test_gap_fill_at_the_open():
    prices = make_prices(opens=[100, 80], closes=[100, 85])
    r = run_engine(prices, T, Scripted({0: [OrderIntent("buy", T, D(1))]}), WHOLE, D("10000.00"))
    # previous close 100, next open 80 → gap −20% ; fill at 80 × 1.0005 = 80.04
    (f,) = r.fills
    assert (f.gap_pct, f.fill_price_usd) == (D("-0.2"), D("80.04"))


def test_last_close_and_liquidation_value():
    prices = make_prices(opens=[100, 100, 110], closes=[100, 100, 110])
    r = run_engine(prices, T, Scripted({0: [OrderIntent("buy", T, D(10))]}), WHOLE, D("10000.00"))
    # cash 8,996.50 ; at last close 10 × 110 = 1,100.00 → value 10,096.50
    # liquidation: sell fill 110 × 0.9995 = 109.945 → 1,099.45 − fee 3.00 = 1,096.45 → 10,092.95
    assert r.last_close_value_usd == D("10096.50")
    assert r.liquidation_value_usd == D("10092.95")
    assert r.portfolio.position(T).quantity == D(10)  # nothing was actually sold


def test_cash_identity_exact_after_multi_day_run():
    closes = [100, 103, 101, 104, 99, 98, 102, 105, 103, 107, 104, 108]
    prices = make_prices(
        opens=[c - 0.5 for c in closes], closes=closes, dividends={5: 0.41, 9: 0.43}
    )
    r = run_engine(prices, T, UpDown(), FRACTIONAL, D("10000.00"))
    p = r.portfolio
    assert len(r.fills) >= 4
    assert (
        p.initial_cash_usd
        - p.total_spent_usd
        - p.total_fees_usd
        + p.total_received_usd
        + p.dividends_net_usd
        == p.cash_usd
    )


def test_strategy_gets_a_truncated_copy():
    prices = make_prices(opens=[100, 101, 102, 103])
    lengths = []

    class Vandal:
        def on_close(self, day, history, view):
            lengths.append(len(history))
            assert history["date"].iloc[-1] == day
            history.loc[:, "close_raw"] = 0.0  # tries to damage the data
            return []

    r = run_engine(prices, T, Vandal(), WHOLE, D("10000.00"))
    assert lengths == [1, 2, 3, 4]
    assert [e.market_value_usd for e in r.equity] == [D("0.00")] * 4
    assert prices["close_raw"].tolist() == [100, 101, 102, 103]  # caller's table untouched


def test_portfolio_view_is_read_only():
    seen = []

    class Poker:
        def on_close(self, day, history, view):
            seen.append(view)
            with pytest.raises(AttributeError):
                view.cash_usd = D("1000000")  # type: ignore[misc]
            return []

    run_engine(make_prices(opens=[100]), T, Poker(), WHOLE, D("10000.00"))
    assert seen[0].cash_usd == D("10000.00")


@pytest.mark.parametrize("cut", [2, 5, 8])
def test_lookahead_harness_passes_for_honest_strategies(cut):
    closes = [100, 103, 101, 104, 99, 98, 102, 105, 103, 107, 104, 108]
    prices = make_prices(opens=[c - 0.5 for c in closes], closes=closes, dividends={4: 0.4})
    check_no_lookahead(UpDown, prices, cut, T, FRACTIONAL, D("10000.00"))
    check_no_lookahead(
        lambda: Scripted({0: [OrderIntent("buy", T, "max_affordable")]}),
        prices,
        cut,
        T,
        WHOLE,
        D("10000.00"),
    )


def test_lookahead_harness_catches_a_cheating_strategy():
    closes = [100, 103, 101, 104, 99, 98, 102, 105]
    prices = make_prices(opens=closes, closes=closes)
    full_table = {"t": prices}

    class Cheater:
        """Peeks at TOMORROW's close through a side channel (not via `history`)."""

        def on_close(self, day, history, view):
            table = full_table["t"]
            i = len(history) - 1
            if (
                i + 1 < len(table)
                and table["close_raw"].iloc[i + 1] > history["close_raw"].iloc[-1]
            ):
                return [OrderIntent("buy", T, D(1))]
            return []

    def make():
        return Cheater()

    original_run = check_no_lookahead.__globals__["run_engine"]

    def run_with_side_channel(prices_arg, *args):
        full_table["t"] = prices_arg  # the cheater sees whichever table is being run
        return original_run(prices_arg, *args)

    check_no_lookahead.__globals__["run_engine"] = run_with_side_channel
    try:
        with pytest.raises(AssertionError, match="changed"):
            check_no_lookahead(make, prices, 3, T, WHOLE, D("10000.00"))
    finally:
        check_no_lookahead.__globals__["run_engine"] = original_run


def test_bugs_raise_errors():
    prices = make_prices(opens=[100, 100])
    with pytest.raises(ValueError, match="unknown ticker"):
        run_engine(
            prices, T, Scripted({0: [OrderIntent("buy", "MSFT", D(1))]}), WHOLE, D("10000.00")
        )
    broken = prices.copy()
    broken.loc[1, "open_raw"] = float("nan")
    with pytest.raises(ValueError, match="missing open"):
        run_engine(broken, T, Scripted({0: [OrderIntent("buy", T, D(1))]}), WHOLE, D("10000.00"))
    with pytest.raises(ValueError, match="missing columns"):
        run_engine(
            pd.DataFrame({"date": [date(2014, 6, 2)]}), T, Scripted({}), WHOLE, D("10000.00")
        )


def test_warmup_rows_are_seen_but_not_traded_or_measured():
    from quant_research.strategies.buy_and_hold import BuyAndHold

    warm = make_prices(opens=[50, 60, 70, 80, 90, 100, 100, 110])
    main = warm.iloc[5:].reset_index(drop=True)  # same rows from index 5 on
    seen = []

    class Recorder(BuyAndHold):
        def on_close(self, day, history, view):
            seen.append(len(history))
            return super().on_close(day, history, view)

    with_warmup = run_engine(
        warm, T, Recorder(T, D(100)), FRACTIONAL, D("10000.00"), trade_start=warm["date"][5]
    )
    # strategy first called on the trade-start day with 6 rows of history (5 warm-up + that day)
    assert seen[0] == 6
    plain = run_engine(main, T, BuyAndHold(T, D(100)), FRACTIONAL, D("10000.00"))
    # nothing traded or measured before trade_start → identical equity and fills (S0 ignores history)
    assert [e.day for e in with_warmup.equity] == [e.day for e in plain.equity]
    assert [e.total_value_usd for e in with_warmup.equity] == [
        e.total_value_usd for e in plain.equity
    ]
    assert [(f.day, f.quantity, f.fill_price_usd) for f in with_warmup.fills] == [
        (f.day, f.quantity, f.fill_price_usd) for f in plain.fills
    ]


def test_trade_start_after_all_rows_is_an_error():
    prices = make_prices(opens=[100, 100])
    with pytest.raises(ValueError, match="trade_start"):
        run_engine(prices, T, Scripted({}), WHOLE, D("10000.00"), trade_start=date(2030, 1, 1))
