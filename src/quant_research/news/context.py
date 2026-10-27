"""Market context features (Phase 9, Step 9.1), point-in-time as of each close T. Floats are fine (D1).

Each feature on day T uses rows dated ≤ T only, in split-adjusted-as-of-T units (strategies.indicators — no copies).
Too little history for a feature → None ("not available"); nothing is estimated.
"""

from dataclasses import dataclass
from datetime import date

import pandas as pd

from quant_research.strategies.indicators import (
    momentum,
    ratio_to_median,
    realised_volatility,
    sma,
    split_adjusted_closes,
    split_adjusted_volumes,
)

TAIL = (
    260  # rows of history needed for the longest feature (200-day average 20 days ago) plus margin
)


@dataclass(frozen=True)
class MarketContext:
    """Broad market on day T (from SPY)."""

    day: date
    above_200d: bool | None  # close_T > SMA200_T
    sma200_slope_20d: (
        float | None
    )  # SMA200_T ÷ SMA200_(T−20) − 1 (same averages as S4's trend filter)
    volatility_20d: float | None  # annualised


@dataclass(frozen=True)
class StockContext:
    day: date
    momentum_60d: float | None
    volatility_20d: float | None
    volume_vs_50d_median: (
        float | None
    )  # volume_T ÷ median of the 50 volumes ending at T (split-adjusted)


def market_context(spy_history: pd.DataFrame) -> MarketContext:
    """Context for the LAST row of `spy_history` (rows ≤ T only — the caller passes history up to T)."""
    tail = spy_history.tail(TAIL)
    closes = split_adjusted_closes(tail)
    now, before = sma(closes, 200), sma(closes, 200, 20)
    return MarketContext(
        day=tail["date"].iloc[-1],
        above_200d=None if now is None else closes[-1] > now,
        sma200_slope_20d=None if now is None or before is None else now / before - 1,
        volatility_20d=realised_volatility(closes, 20),
    )


def stock_context(history: pd.DataFrame) -> StockContext:
    tail = history.tail(TAIL)
    closes = split_adjusted_closes(tail)
    return StockContext(
        day=tail["date"].iloc[-1],
        momentum_60d=momentum(closes, 60),
        volatility_20d=realised_volatility(closes, 20),
        volume_vs_50d_median=ratio_to_median(split_adjusted_volumes(tail), 50),
    )


def daily(history: pd.DataFrame, fn, start: date, end: date) -> list:
    """fn(history up to T) for every T in [start, end] — each call sees rows ≤ T only."""
    df = history.sort_values("date").reset_index(drop=True)
    out = []
    for i, d in enumerate(df["date"]):
        if start <= d <= end:
            out.append(fn(df.iloc[: i + 1]))
    return out
