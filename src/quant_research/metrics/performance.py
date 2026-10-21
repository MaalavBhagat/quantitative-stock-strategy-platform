"""Performance metrics from a run's daily equity and logs (Phase 4, Step 4.5; EXPERIMENT_PLAN §5).

Floats are fine here (D1: Decimal only inside the ledger). Inputs come from the engine result.
Conventions: CAGR uses calendar days / 365.25; volatility = stdev of daily simple returns
(sample, n − 1) × √252; Sharpe = mean daily return / stdev × √252 with risk-free 0%
[ASSUMPTION, EXPERIMENT_PLAN §5]; drawdown on the daily total value at the close.
"""

import itertools
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

TRADING_DAYS_PER_YEAR = 252


def daily_returns(values: Sequence[float]) -> list[float]:
    return [b / a - 1 for a, b in itertools.pairwise(values)]


def total_return(initial: float, final: float) -> float:
    return final / initial - 1


def cagr(initial: float, final: float, first_day: date, last_day: date) -> float:
    days = (last_day - first_day).days
    if days <= 0:
        raise ValueError("CAGR needs at least one calendar day")
    return (final / initial) ** (365.25 / days) - 1


@dataclass(frozen=True)
class Drawdown:
    max_drawdown: float  # negative number, e.g. −0.25 = −25%
    peak_day: date | None
    trough_day: date | None


def max_drawdown(days: Sequence[date], values: Sequence[float]) -> Drawdown:
    peak_value, peak_day = values[0], days[0]
    worst, worst_peak, worst_trough = 0.0, None, None
    for d, v in zip(days, values, strict=True):
        if v > peak_value:
            peak_value, peak_day = v, d
        dd = v / peak_value - 1
        if dd < worst:
            worst, worst_peak, worst_trough = dd, peak_day, d
    return Drawdown(worst, worst_peak, worst_trough)


def _stdev(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    mean = sum(xs) / len(xs)
    return math.sqrt(sum((x - mean) ** 2 for x in xs) / (len(xs) - 1))


def annual_volatility(values: Sequence[float]) -> float:
    return _stdev(daily_returns(values)) * math.sqrt(TRADING_DAYS_PER_YEAR)


def sharpe(values: Sequence[float]) -> float:
    r = daily_returns(values)
    sd = _stdev(r)
    if not sd or math.isnan(sd):
        return float("nan")
    return (sum(r) / len(r)) / sd * math.sqrt(TRADING_DAYS_PER_YEAR)


def calendar_year_returns(
    days: Sequence[date], values: Sequence[float], initial: float
) -> dict[int, float]:
    """Each year: last value of the year ÷ last value of the previous year (first year: ÷ initial) − 1."""
    year_end: dict[int, float] = {}
    for d, v in zip(days, values, strict=True):
        year_end[d.year] = v
    out, previous = {}, initial
    for year in sorted(year_end):
        out[year] = year_end[year] / previous - 1
        previous = year_end[year]
    return out


def worst_calendar_year(
    days: Sequence[date], values: Sequence[float], initial: float
) -> tuple[int, float]:
    years = calendar_year_returns(days, values, initial)
    year = min(years, key=years.get)  # type: ignore[arg-type]
    return year, years[year]


def pct_days_fully_in_cash(market_values: Sequence[float]) -> float:
    return sum(1 for mv in market_values if mv == 0) / len(market_values)


def round_trips(fills: Sequence[object]) -> int:
    """Completed buy → sell-everything cycles = sells after which zero shares are held."""
    return sum(1 for f in fills if f.side == "sell" and f.position_after == 0)  # type: ignore[attr-defined]


@dataclass(frozen=True)
class PerformanceSummary:
    first_day: date
    last_day: date
    initial_usd: float
    final_usd: float  # value at last close
    liquidation_usd: float
    final_aud_after_fx: float | None
    total_return_usd: float
    cagr_usd: float
    total_return_aud: float | None
    cagr_aud: float | None
    max_drawdown: Drawdown
    max_drawdown_aud: Drawdown | None
    annual_volatility: float
    sharpe: float
    worst_year: tuple[int, float]
    total_fees_usd: float
    total_spread_cost_usd: float
    dividends_gross_usd: float
    withholding_usd: float
    dividends_net_usd: float
    pct_days_fully_in_cash: float
    round_trips: int


def summarise(
    result: object,
    initial_usd: Decimal,
    initial_aud: Decimal | None = None,
    final_aud_after_fx: Decimal | None = None,
    usd_per_aud_on: Callable[[date], Decimal] | None = None,
) -> PerformanceSummary:
    """Metrics for one EngineResult. AUD equity = USD equity ÷ usd_per_aud of that day."""
    eq = result.equity  # type: ignore[attr-defined]
    days = [e.day for e in eq]
    values = [float(e.total_value_usd) for e in eq]
    init = float(initial_usd)
    p = result.portfolio  # type: ignore[attr-defined]
    aud_total = aud_cagr = None
    dd_aud = None
    if usd_per_aud_on is not None and initial_aud is not None and final_aud_after_fx is not None:
        aud_values = [v / float(usd_per_aud_on(d)) for d, v in zip(days, values, strict=True)]
        dd_aud = max_drawdown(days, aud_values)
        aud_total = total_return(float(initial_aud), float(final_aud_after_fx))
        aud_cagr = cagr(float(initial_aud), float(final_aud_after_fx), days[0], days[-1])
    return PerformanceSummary(
        first_day=days[0],
        last_day=days[-1],
        initial_usd=init,
        final_usd=values[-1],
        liquidation_usd=float(result.liquidation_value_usd),  # type: ignore[attr-defined]
        final_aud_after_fx=float(final_aud_after_fx) if final_aud_after_fx is not None else None,
        total_return_usd=total_return(init, values[-1]),
        cagr_usd=cagr(init, values[-1], days[0], days[-1]),
        total_return_aud=aud_total,
        cagr_aud=aud_cagr,
        max_drawdown=max_drawdown(days, values),
        max_drawdown_aud=dd_aud,
        annual_volatility=annual_volatility(values),
        sharpe=sharpe(values),
        worst_year=worst_calendar_year(days, values, init),
        total_fees_usd=float(p.total_fees_usd),
        total_spread_cost_usd=float(sum((f.spread_cost_usd for f in result.fills), Decimal(0))),  # type: ignore[attr-defined]
        dividends_gross_usd=float(p.dividends_gross_usd),
        withholding_usd=float(p.withholding_usd),
        dividends_net_usd=float(p.dividends_net_usd),
        pct_days_fully_in_cash=pct_days_fully_in_cash([float(e.market_value_usd) for e in eq]),
        round_trips=round_trips(result.fills),  # type: ignore[attr-defined]
    )
