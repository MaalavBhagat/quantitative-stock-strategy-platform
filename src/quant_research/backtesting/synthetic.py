"""Made-up price tables for tests (no real market data, no internet)."""

from datetime import date, timedelta

import pandas as pd


def weekdays(start: date, n: int) -> list[date]:
    """n Monday–Friday dates from `start` (synthetic — not the NYSE calendar)."""
    days, d = [], start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def make_prices(
    opens: list[float],
    closes: list[float] | None = None,
    start: date = date(2014, 6, 2),
    dividends: dict[int, float] | None = None,
    splits: dict[int, float] | None = None,
) -> pd.DataFrame:
    """Table in the loader's raw format. dividends/splits map row index → amount/factor."""
    opens = [float(x) for x in opens]
    closes = [float(x) for x in (closes if closes is not None else opens)]
    n = len(opens)
    days = weekdays(start, n)
    high = [max(o, c) * 1.01 for o, c in zip(opens, closes)]
    low = [min(o, c) * 0.99 for o, c in zip(opens, closes)]
    return pd.DataFrame(
        {
            "date": days,
            "open_raw": opens,
            "high_raw": high,
            "low_raw": low,
            "close_raw": closes,
            "volume_raw": [1_000_000] * n,
            "div_cash_usd": [float((dividends or {}).get(i, 0.0)) for i in range(n)],
            "split_factor": [float((splits or {}).get(i, 1.0)) for i in range(n)],
        }
    )
