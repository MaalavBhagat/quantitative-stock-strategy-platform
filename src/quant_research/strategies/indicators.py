"""Indicators for strategies (Phase 5, Steps 5.3–5.4). Floats are fine here (D1: Decimal only in the ledger).

All indicators use SPLIT-ADJUSTED-AS-OF-T closes: built from close_raw and split_factor of the history
up to day T only. Tiingo's close_adj must NOT be used — it already contains splits and dividends that
happen AFTER day T (e.g. AAPL's later ~4:1 split), which would be look-ahead. Not dividend-adjusted.
"""

import math
from collections.abc import Sequence

import pandas as pd

from quant_research.ratios import nearest_simple_ratio


def split_adjusted_closes(history: pd.DataFrame) -> list[float]:
    """Closes up to T in post-split units of day T: each close ÷ every snapped split ratio after it (≤ T).

    On a split day the raw close is already post-split, so only EARLIER closes are divided.
    """
    closes = [float(c) for c in history["close_raw"]]
    factors = [float(f) for f in history["split_factor"]]
    adjusted = [0.0] * len(closes)
    divisor = 1.0
    for i in range(len(closes) - 1, -1, -1):
        adjusted[i] = closes[i] / divisor
        # a split at day i's open → every close BEFORE day i is pre-split
        if abs(factors[i] - 1.0) > 1e-12:
            divisor *= float(nearest_simple_ratio(factors[i]))
    return adjusted


def zscore(values: Sequence[float], window: int) -> float | None:
    """(last value − mean of the last `window` values) ÷ sample std (ddof = 1) of those values.

    The window INCLUDES the last value (day T). None if there are fewer than `window` values or the
    std is 0.
    """
    if window < 2 or len(values) < window:
        return None
    w = values[-window:]
    mean = sum(w) / window
    std = math.sqrt(sum((v - mean) ** 2 for v in w) / (window - 1))
    if std == 0:
        return None
    return (w[-1] - mean) / std


def sma(values: Sequence[float], window: int, lag: int = 0) -> float | None:
    """Simple average of the `window` values ending `lag` days before the last one. None if not enough data."""
    end = len(values) - lag
    if lag < 0 or end < window:
        return None
    w = values[end - window : end]
    return sum(w) / window


def strong_uptrend(values: Sequence[float], sma_window: int = 200, slope_lag: int = 20) -> bool:
    """P_T > SMA_T AND SMA_T > SMA_(T − slope_lag). False when there is not enough history."""
    now, before = sma(values, sma_window), sma(values, sma_window, slope_lag)
    if now is None or before is None:
        return False
    # price above its average AND the average rising (vs slope_lag days ago)
    return values[-1] > now > before
