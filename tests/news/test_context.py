"""Tests for the new indicator functions and the market context features (hand-checked, synthetic data)."""

import math
from datetime import date

import pytest

from quant_research.backtesting.synthetic import make_prices
from quant_research.news.context import daily, market_context, stock_context
from quant_research.strategies.indicators import (
    momentum,
    ratio_to_median,
    realised_volatility,
    split_adjusted_volumes,
)


def test_realised_volatility_by_hand():
    # values 100, 110, 99, 99 → returns +0.10, −0.10, 0.00 → mean 0, var (0.01 + 0.01 + 0)/2 = 0.01 → 0.1 × √252
    assert realised_volatility([100, 110, 99, 99], window=3) == pytest.approx(0.1 * math.sqrt(252))
    assert realised_volatility([100, 110, 99], window=3) is None  # needs window + 1 values


def test_momentum_and_ratio_to_median():
    assert momentum([50, 60, 75], lookback=2) == pytest.approx(0.5)  # 75 ÷ 50 − 1
    assert momentum([50, 60], lookback=2) is None
    # median(30, 20, 40) = 30
    assert ratio_to_median([10, 30, 20, 40], window=3) == pytest.approx(40 / 30)
    assert ratio_to_median([0, 0, 0], window=3) is None


def test_split_adjusted_volumes_as_of_t():
    df = make_prices([100, 100, 50, 50], splits={2: 2.0})  # 2:1 split at row 2's open
    df["volume_raw"] = [1000, 1000, 2000, 2000]
    # earlier volumes are restated in post-split shares; before the split happened they are unchanged
    assert split_adjusted_volumes(df) == [2000, 2000, 2000, 2000]
    assert split_adjusted_volumes(df.iloc[:2]) == [1000, 1000]


def test_market_context_needs_warm_up_and_ignores_a_split():
    rising = [100 + i for i in range(260)]
    ctx = market_context(make_prices(rising))
    assert ctx.above_200d is True and ctx.sma200_slope_20d > 0 and ctx.volatility_20d > 0
    short = market_context(make_prices(rising[:150]))
    assert short.above_200d is None and short.sma200_slope_20d is None  # "not available"
    # the same prices with a 2:1 split halfway (raw prices halve) give the same context
    split = [p / 2 if i >= 130 else p for i, p in enumerate(rising)]
    ctx_split = market_context(make_prices(split, splits={130: 2.0}))
    assert ctx_split.above_200d == ctx.above_200d
    assert ctx_split.sma200_slope_20d == pytest.approx(ctx.sma200_slope_20d)
    assert ctx_split.volatility_20d == pytest.approx(ctx.volatility_20d)


def test_stock_context_values_and_not_available():
    df = make_prices([100.0] * 59 + [120.0, 132.0])
    df["volume_raw"] = [1000] * 60 + [3000]
    s = stock_context(df)
    assert s.momentum_60d == pytest.approx(132 / 100 - 1)
    assert s.volume_vs_50d_median == pytest.approx(3.0)
    assert stock_context(df.iloc[:30]).momentum_60d is None


def test_daily_features_see_rows_up_to_t_only():
    df = make_prices([100 + i for i in range(30)], start=date(2014, 6, 2))
    seen = daily(df, lambda h: h["date"].max(), date(2014, 6, 10), date(2014, 6, 20))
    in_range = [d for d in df["date"] if date(2014, 6, 10) <= d <= date(2014, 6, 20)]
    assert seen == in_range  # on day T the function saw nothing after T
