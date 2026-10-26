"""Trading indicators per calendar year from Tiingo RAW daily data (Phase 7, Step 7.2). Floats are fine (D1).

Input: date, high_raw, low_raw, close_raw, volume_raw, div_cash_usd, split_factor (all rows ≤ 2020-12-31; D8).
Never uses close_adj (it contains later splits and dividends = look-ahead). Prices are "split-adjusted as of T":
on day T, every earlier price is divided by the snapped split ratios between it and T (strategies.indicators).
Spreads: not in free daily data — only the ASSUMED levels (tight 0.02% / normal 0.05% / wide 0.10% per side) exist.
"""

import math
import statistics
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from quant_research.metrics.performance import TRADING_DAYS_PER_YEAR, max_drawdown
from quant_research.ratios import nearest_simple_ratio
from quant_research.strategies.indicators import split_adjusted_closes


@dataclass(frozen=True)
class YearTrading:
    year: int
    days: int
    median_dollar_volume_usd: float  # median of close_raw × volume_raw
    volatility_annualised: float | None  # sample stdev of daily split-aware returns × √252
    median_daily_range: float  # median of (high_raw − low_raw) ÷ close_raw
    max_drawdown: float  # within the year, on split-adjusted closes (price only, no dividends)
    dividend_yield_ttm: (
        float | None
    )  # dividends with ex-date in the 365 days to the year's last day ÷ that close


def _ratio(f: float) -> float:
    return 1.0 if abs(f - 1.0) < 1e-12 else float(nearest_simple_ratio(f))


def split_aware_returns(df: pd.DataFrame) -> list[float]:
    """Daily simple returns: close_T ÷ (close_(T−1) ÷ split ratio on T) − 1 (so a split is not a price move)."""
    closes, factors = list(df["close_raw"]), list(df["split_factor"])
    return [closes[i] / (closes[i - 1] / _ratio(factors[i])) - 1 for i in range(1, len(closes))]


def trailing_dividends(df: pd.DataFrame, day: date, window_days: int = 365) -> float | None:
    """Sum of dividends with ex-date in (day − window, day], each in the share units of `day`.

    None if the data does not reach back to the window start (cannot know the full 12 months).
    """
    first_needed = day - timedelta(days=window_days)
    if min(df["date"]) > first_needed:
        return None
    rows = df[df["date"] <= day]
    total = 0.0
    later_ratio = 1.0
    for d, div, f in zip(
        reversed(list(rows["date"])),
        reversed(list(rows["div_cash_usd"])),
        reversed(list(rows["split_factor"])),
        strict=True,
    ):
        if d <= first_needed:
            break
        if div:
            total += (
                float(div) / later_ratio
            )  # a split AFTER the ex-date reduces the per-share amount
        later_ratio *= _ratio(float(f))  # the split on day d applies to rows before d
    return total


def year_indicators(df: pd.DataFrame, year: int) -> YearTrading:
    """Indicators for one calendar year. Uses the last row before the year (if present) for the first return."""
    df = df.sort_values("date").reset_index(drop=True)
    in_year = df[[d.year == year for d in df["date"]]]
    if in_year.empty:
        raise ValueError(f"no rows in {year}")
    first_i = int(in_year.index[0])
    with_prev = df.iloc[max(first_i - 1, 0) : int(in_year.index[-1]) + 1]
    rets = split_aware_returns(with_prev)
    vol = statistics.stdev(rets) * math.sqrt(TRADING_DAYS_PER_YEAR) if len(rets) >= 2 else None
    dollar_volume = [
        float(c) * float(v)
        for c, v in zip(in_year["close_raw"], in_year["volume_raw"], strict=True)
    ]
    ranges = [
        (float(h) - float(lo)) / float(c)
        for h, lo, c in zip(
            in_year["high_raw"], in_year["low_raw"], in_year["close_raw"], strict=True
        )
    ]
    adjusted = split_adjusted_closes(in_year)  # in the share units of the year's last day
    dd = max_drawdown(list(in_year["date"]), adjusted).max_drawdown
    last_day, last_close = in_year["date"].iloc[-1], float(in_year["close_raw"].iloc[-1])
    divs = trailing_dividends(df, last_day)
    return YearTrading(
        year=year,
        days=len(in_year),
        median_dollar_volume_usd=statistics.median(dollar_volume),
        volatility_annualised=vol,
        median_daily_range=statistics.median(ranges),
        max_drawdown=dd,
        dividend_yield_ttm=None if divs is None else divs / last_close,
    )
