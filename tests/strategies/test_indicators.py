"""Indicators — hand-worked tiny series (working in comments)."""

import math

import pandas as pd
import pytest

from quant_research.strategies.indicators import sma, split_adjusted_closes, strong_uptrend, zscore


def table(closes, splits=None, close_adj=None):
    n = len(closes)
    df = pd.DataFrame({"close_raw": [float(c) for c in closes], "split_factor": [1.0] * n})
    for i, f in (splits or {}).items():
        df.loc[i, "split_factor"] = f
    if close_adj is not None:
        df["close_adj"] = close_adj
    return df


def test_split_on_day_10_divides_days_1_to_9():
    # closes 100 × 9 days, then a 2:1 split on day 10 (index 9): raw 50 → days 1–9 become 100 ÷ 2 = 50
    h = table([100] * 9 + [50], splits={9: 2.0})
    assert split_adjusted_closes(h) == [50.0] * 10


def test_snapped_ratio_is_used():
    # factor 7.000007 snaps to 7 → 700 ÷ 7 = 100 exactly
    assert split_adjusted_closes(table([700, 100], splits={1: 7.000007})) == [100.0, 100.0]


def test_split_after_t_changes_nothing_up_to_t_and_close_adj_is_not_used():
    # close_adj already reflects a LATER 4:1 split (values ÷ 4) — using it would be look-ahead
    full = table([100, 102, 104, 26, 27], splits={3: 4.0}, close_adj=[25, 25.5, 26, 26, 27])
    up_to_t = full.iloc[:3]  # T = index 2, before the split
    assert split_adjusted_closes(up_to_t) == [100.0, 102.0, 104.0]  # raw, not close_adj
    assert split_adjusted_closes(full)[:3] == [25.0, 25.5, 26.0]  # only once the split has happened


def test_zscore_window_includes_today_sample_std():
    # [1, 2, 3, 4, 10], w = 5: mean 4 ; deviations −3, −2, −1, 0, 6 → squares sum 50 ; ÷ (5 − 1) = 12.5
    # std √12.5 = 3.5355339 ; z = (10 − 4) / 3.5355339 = 1.6970563
    assert zscore([1, 2, 3, 4, 10], 5) == pytest.approx(6 / math.sqrt(12.5), rel=1e-12)
    # w = 3 uses only [3, 4, 10]: mean 17/3 ; squares sum 28.6667 ; ÷ 2 = 14.3333 ; z = 4.3333 / 3.7859 = 1.1446
    assert zscore([1, 2, 3, 4, 10], 3) == pytest.approx(
        (10 - 17 / 3) / math.sqrt(86 / 3 / 2), rel=1e-12
    )


def test_zscore_not_enough_data_or_flat():
    assert zscore([1, 2], 3) is None
    assert zscore([5, 5, 5], 3) is None


def test_sma_and_lag():
    v = list(range(1, 11))  # 1 … 10
    # last 5 = 6..10 → 8 ; lag 2 → 4..8 → 6
    assert (sma(v, 5), sma(v, 5, 2)) == (8, 6)
    assert sma(v, 11) is None


def test_strong_uptrend_needs_price_above_and_sma_rising():
    # rising: P 10 > SMA5 8 > SMA5(T−2) 6 → True
    assert strong_uptrend(list(range(1, 11)), 5, 2) is True
    # price below its average: SMA5 = (6+7+8+9+5)/5 = 7 ; P 5 < 7 → False
    assert strong_uptrend([1, 2, 3, 4, 5, 6, 7, 8, 9, 5], 5, 2) is False
    # price above but SMA FALLING: SMA5 = (5+4+3+2+9)/5 = 4.6 ; SMA5(T−2) = (7+6+5+4+3)/5 = 5 → False
    assert strong_uptrend([10, 9, 8, 7, 6, 5, 4, 3, 2, 9], 5, 2) is False
    # not enough history → False (no filter)
    assert strong_uptrend([1, 2, 3], 5, 2) is False
