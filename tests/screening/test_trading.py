"""Tests for quant_research.screening.trading — tiny made-up series, hand-calculated answers."""

import math
from datetime import date

import pandas as pd
import pytest

from quant_research.screening.trading import (
    split_aware_returns,
    trailing_dividends,
    year_indicators,
)

COLS = ["date", "high_raw", "low_raw", "close_raw", "volume_raw", "div_cash_usd", "split_factor"]
ROWS = [
    (date(2019, 1, 2), 51, 49, 50, 10, 0.0, 1.0),
    (date(2019, 6, 3), 91, 89, 90, 10, 0.5, 1.0),  # dividend 0.50 before the split
    (date(2019, 12, 31), 101, 99, 100, 10, 0.0, 1.0),
    (date(2020, 1, 2), 112, 108, 110, 20, 0.0, 1.0),
    (date(2020, 1, 3), 56, 54, 55, 40, 0.0, 2.0),  # 2:1 split: raw close halves, no real move
    (date(2020, 1, 6), 45, 43, 44, 100, 0.25, 1.0),  # dividend 0.25 after the split
]


def frame(rows=ROWS) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=COLS)


def test_split_is_not_a_price_move():
    # 110/100 − 1 = +0.10 · 55 / (110 / 2) − 1 = 0 · 44/55 − 1 = −0.20
    assert split_aware_returns(frame().iloc[2:]) == pytest.approx([0.10, 0.0, -0.20])


def test_trailing_dividends_in_share_units_of_the_day():
    # window (2019-01-06, 2020-01-06]: 0.50 ÷ 2 (split after it) + 0.25 = 0.50
    assert trailing_dividends(frame(), date(2020, 1, 6)) == pytest.approx(0.50)


def test_trailing_dividends_none_when_history_too_short():
    assert trailing_dividends(frame(ROWS[2:]), date(2020, 1, 6)) is None


def test_year_indicators_by_hand():
    y = year_indicators(frame(), 2020)
    assert y.days == 3
    assert y.median_dollar_volume_usd == pytest.approx(2200)  # 2200, 2200, 4400
    # stdev(0.10, 0, −0.20): mean −1/30; squares sum .046667; ÷ 2 = .023333; √ × √252
    assert y.volatility_annualised == pytest.approx(math.sqrt(0.07 / 3) * math.sqrt(252))
    assert y.median_daily_range == pytest.approx(4 / 110)  # 4/110, 2/55, 2/44
    # adjusted closes 55, 55, 44 (raw closes would wrongly give −0.60)
    assert y.max_drawdown == pytest.approx(-0.20)
    assert y.dividend_yield_ttm == pytest.approx(0.50 / 44)


def test_first_year_without_previous_day_uses_in_year_returns_only():
    y = year_indicators(frame(ROWS[3:]), 2020)  # no 2019 row → returns 0, −0.20 only
    assert y.volatility_annualised == pytest.approx(math.sqrt(0.02) * math.sqrt(252))
    assert y.dividend_yield_ttm is None


def test_year_without_rows_is_an_error():
    with pytest.raises(ValueError, match="no rows"):
        year_indicators(frame(), 2018)
