"""Exact money helpers — hand calculations above each assert (PROJECT_GUIDE §5)."""

from decimal import Decimal

import pytest

from quant_research.portfolio.money import (
    require_decimal,
    round_pay,
    round_receive,
    round_shares_down,
    shares_affordable,
    to_decimal_price,
)


def test_to_decimal_price_uses_short_text_form():
    # 0.1 as a float is really 0.1000000000000000055…; we want exactly 0.1.
    assert to_decimal_price(0.1) == Decimal("0.1")
    # 93.7 (a real-looking close) → exactly 93.7
    assert to_decimal_price(93.7) == Decimal("93.7")
    assert to_decimal_price(150) == Decimal(150)


def test_to_decimal_price_rejects_nan_inf_and_bool():
    with pytest.raises(ValueError):
        to_decimal_price(float("nan"))
    with pytest.raises(ValueError):
        to_decimal_price(float("inf"))
    with pytest.raises(TypeError):
        to_decimal_price(True)


def test_require_decimal_rejects_float_with_hint():
    with pytest.raises(TypeError, match="to_decimal_price"):
        require_decimal(100.5, "price_usd")


def test_require_decimal_accepts_decimal_int_str():
    assert require_decimal(Decimal("1.5"), "x") == Decimal("1.5")
    assert require_decimal(3, "x") == Decimal(3)
    assert require_decimal("2.25", "x") == Decimal("2.25")
    with pytest.raises(ValueError):
        require_decimal("abc", "x")


def test_rounding_against_us():
    # pay 30.999 → round UP → 31.00 ; receive 30.999 → round DOWN → 30.99
    assert round_pay(Decimal("30.999")) == Decimal("31.00")
    assert round_receive(Decimal("30.999")) == Decimal("30.99")
    # already whole cents stay the same
    assert round_pay(Decimal("12.30")) == Decimal("12.30")
    assert round_receive(Decimal("12.30")) == Decimal("12.30")


def test_round_shares_down():
    # fractional: 1.23456789 → 6 dp, down → 1.234567 ; whole: 3.99 → 3
    assert round_shares_down(Decimal("1.23456789"), "fractional") == Decimal("1.234567")
    assert round_shares_down(Decimal("3.99"), "whole") == Decimal(3)


def test_shares_affordable_whole_vs_fractional():
    # cash 1000, price 300, fee 3 → 997 left for shares
    # whole: floor(997 / 300) = 3 shares (cost 900.00)
    assert shares_affordable(Decimal(1000), Decimal(300), Decimal(3), "whole") == Decimal(3)
    # fractional: 997 / 300 = 3.3233333… → 3.323333 ; cost 3.323333 × 300 = 996.9999 → 997.00 ≤ 997
    assert shares_affordable(Decimal(1000), Decimal(300), Decimal(3), "fractional") == Decimal(
        "3.323333"
    )


def test_shares_affordable_fee_bigger_than_cash():
    # cash 2, fee 3 → nothing affordable
    assert shares_affordable(Decimal(2), Decimal(10), Decimal(3), "fractional") == Decimal(0)
