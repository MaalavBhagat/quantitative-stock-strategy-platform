"""Order execution at the open (Step 4.3) — synthetic numbers, hand calculations in comments."""

from datetime import date
from decimal import Decimal

import pytest

from quant_research.execution.costs import apply_spread, fee_usd
from quant_research.execution.fills import FillResult, Rejection, fill_order
from quant_research.execution.orders import OrderIntent
from quant_research.portfolio.ledger import Portfolio
from quant_research.portfolio.money import SHARE_STEP, round_pay

D = Decimal
DAY = date(2014, 6, 3)
MIN = D(10)


def fill(p: Portfolio, intent: OrderIntent, open_raw: str, broker: str = "stake", prev=None):
    return fill_order(
        intent, DAY, D(open_raw), p, broker, "normal", p.share_mode, p.min_order_usd, prev
    )


def test_buy_fills_at_open_plus_spread_and_fee():
    p = Portfolio("10000.00", share_mode="whole")
    r = fill(p, OrderIntent("buy", "TEST", D(10)), "100")
    # fill = 100 × 1.0005 = 100.05 ; cost 10 × 100.05 = 1,000.50 ; Stake fee 3.00
    # cash = 10,000 − 1,000.50 − 3.00 = 8,996.50 ; spread cost 0.05 × 10 = 0.50
    assert isinstance(r, FillResult)
    assert (r.reference_price_usd, r.fill_price_usd, r.quantity) == (D(100), D("100.05"), D(10))
    assert (r.spread_cost_usd, r.fee.total_usd, p.cash_usd) == (D("0.50"), D("3.00"), D("8996.50"))


def assert_max_and_affordable(p: Portfolio, r: FillResult, broker: str, cash_before: Decimal):
    # never overspends …
    assert p.cash_usd >= 0
    spent = round_pay(r.quantity * r.fill_price_usd) + r.fee.total_usd
    assert spent <= cash_before
    # … and one more share step would NOT be affordable (with its own, larger fee)
    step = D(1) if p.share_mode == "whole" else SHARE_STEP
    q = r.quantity + step
    assert (
        round_pay(q * r.fill_price_usd) + fee_usd(broker, q * r.fill_price_usd, q).total_usd
        > cash_before
    )


@pytest.mark.parametrize("mode", ["fractional", "whole"])
@pytest.mark.parametrize(
    ("broker", "open_raw"),
    [
        ("stake", "100"),  # flat US$3
        ("ibkr_fixed", "10"),  # per-share fee grows with size: ~999 × 0.005 ≈ 5.00
        ("ibkr_fixed", "0.40"),  # 1% cap binds: 0.005/share > 1% × 0.40
        ("commsec_standard", "100"),  # 0.12% + 0.55% FX — fee grows with value
    ],
)
def test_max_affordable_never_overspends_and_is_maximal(mode, broker, open_raw):
    p = Portfolio("10000.00", share_mode=mode)
    r = fill(p, OrderIntent("buy", "TEST", "max_affordable"), open_raw, broker)
    assert isinstance(r, FillResult)
    assert_max_and_affordable(p, r, broker, D("10000.00"))


def test_ibkr_cap_case_fee_is_one_percent():
    p = Portfolio("1000.00", share_mode="whole")
    r = fill(p, OrderIntent("buy", "TEST", "max_affordable"), "0.40", "ibkr_fixed")
    # fill 0.40 × 1.0005 = 0.4002 ; per-share 0.005 per share = 1.25% of price > 1% cap → fee = 1% of value
    value = r.quantity * r.fill_price_usd
    assert r.fee.total_usd == round_pay(value * D("0.01"))


def test_gap_is_recorded_and_fill_is_at_the_open():
    p = Portfolio("10000.00", share_mode="whole")
    r = fill(p, OrderIntent("buy", "TEST", D(1)), "110", prev=D(100))
    # previous close 100, open 110 → gap +10% ; fill at 110 × 1.0005 = 110.055 (not at 100)
    assert (r.gap_pct, r.fill_price_usd) == (D("0.1"), D("110.055"))


def test_sell_all_with_fee():
    p = Portfolio("10000.00", share_mode="whole")
    fill(p, OrderIntent("buy", "TEST", D(10)), "100")  # cash 8,996.50
    r = fill(p, OrderIntent("sell", "TEST", "all"), "110")
    # sell fill 110 × 0.9995 = 109.945 ; proceeds 10 × 109.945 = 1,099.45 ; fee 3.00
    # cash = 8,996.50 + 1,099.45 − 3.00 = 10,092.95
    assert (r.quantity, r.fill_price_usd, p.cash_usd) == (D(10), D("109.945"), D("10092.95"))


def test_rejection_not_enough_cash():
    p = Portfolio("500.00", share_mode="whole")
    r = fill(p, OrderIntent("buy", "TEST", D(10)), "100")
    # needs 1,000.50 + 3.00 = 1,003.50 > 500.00
    assert isinstance(r, Rejection) and "1003.50" in r.reason
    assert p.entries == () and p.cash_usd == D("500.00")


def test_rejection_not_enough_shares_and_none_held():
    p = Portfolio("10000.00", share_mode="whole")
    r = fill(p, OrderIntent("sell", "TEST", "all"), "100")
    assert isinstance(r, Rejection) and "no TEST shares held" in r.reason
    fill(p, OrderIntent("buy", "TEST", D(5)), "100")
    r = fill(p, OrderIntent("sell", "TEST", D(6)), "100")
    assert isinstance(r, Rejection) and "only 5 held" in r.reason


def test_rejection_below_minimum_order():
    p = Portfolio("10000.00", share_mode="fractional")
    r = fill(p, OrderIntent("buy", "TEST", D("0.05")), "100")
    # 0.05 × 100.05 = 5.0025 < 10 → rejected
    assert isinstance(r, Rejection) and "below minimum" in r.reason


def test_rejection_nothing_affordable():
    p = Portfolio("2.00", share_mode="fractional")
    r = fill(p, OrderIntent("buy", "TEST", "max_affordable"), "100")
    assert isinstance(r, Rejection) and "no shares affordable" in r.reason


def test_bugs_raise_errors_not_rejections():
    p = Portfolio("10000.00", share_mode="whole")
    with pytest.raises(ValueError):
        OrderIntent("buy", "TEST", D(-1))
    with pytest.raises(ValueError):
        OrderIntent("buy", "TEST", "all")
    with pytest.raises(ValueError):
        OrderIntent("hold", "TEST", D(1))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        OrderIntent("buy", "TEST", 1.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="missing open"):
        fill_order(OrderIntent("buy", "TEST", D(1)), DAY, None, p, "stake", "normal", "whole", MIN)
    with pytest.raises(ValueError, match="whole number"):
        fill(p, OrderIntent("buy", "TEST", D("1.5")), "100")
    with pytest.raises(ValueError, match="share_mode"):
        fill_order(
            OrderIntent("buy", "TEST", D(1)), DAY, D(100), p, "stake", "normal", "fractional", MIN
        )


def test_spread_is_the_cost_model_spread():
    # the fill price is exactly costs.apply_spread — no second spread model in fills.py
    p = Portfolio("10000.00", share_mode="whole")
    r = fill(p, OrderIntent("buy", "TEST", D(1)), "123.45")
    assert r.fill_price_usd == apply_spread(D("123.45"), "buy", "normal", D(1)).fill_price_usd
