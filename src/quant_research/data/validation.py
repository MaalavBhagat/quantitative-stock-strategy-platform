"""Data-quality checks for daily price tables (Phase 2, Step 2.3).

Checks report problems; they never change the data (PROJECT_GUIDE §6).
Severity: ERROR = the run must stop · WARNING = logged, allowed · INFO = noted.
Input: a table with the column names from quant_research.data.tiingo.COLUMN_MAP.
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from fractions import Fraction
from typing import Any

import exchange_calendars as xcals
import pandas as pd

logger = logging.getLogger(__name__)

RAW_PRICE_COLS = ["open_raw", "high_raw", "low_raw", "close_raw"]
ADJ_PRICE_COLS = ["open_adj", "high_adj", "low_adj", "close_adj"]
VOLUME_COLS = ["volume_raw", "volume_adj"]
VALUE_COLS = RAW_PRICE_COLS + ADJ_PRICE_COLS + VOLUME_COLS + ["div_cash_usd", "split_factor"]

BIG_MOVE_PCT = 0.25  # |raw close-to-close change| above this is reported
SPLIT_RATIO_REL_TOL = 1e-4  # split factor must be this close to a simple ratio
RATIO_STEP_REL_TOL = 1e-8  # adj/raw ratio may move only by float noise on non-event days
OHLC_REL_TOL = 1e-9  # float noise allowed in OHLC ordering checks (adjusted prices)


class Severity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True)
class Issue:
    ticker: str
    date: date | None
    check: str
    severity: Severity
    message: str


@dataclass
class ValidationReport:
    ticker: str
    issues: list[Issue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def count(self, severity: Severity) -> int:
        return sum(1 for issue in self.issues if issue.severity == severity)

    @property
    def has_errors(self) -> bool:
        return self.count(Severity.ERROR) > 0

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([vars(issue) for issue in self.issues])


def nyse_sessions(start: date, end: date) -> list[date]:
    """NYSE (XNYS) trading days from start to end inclusive, from exchange_calendars (D4)."""
    # Build the calendar from a little earlier: it cannot start on a non-trading day (e.g. 1 Jan).
    calendar_start = (pd.Timestamp(start) - pd.Timedelta(days=10)).date()
    calendar = xcals.get_calendar("XNYS", start=calendar_start.isoformat())
    sessions = calendar.sessions_in_range(start.isoformat(), end.isoformat())
    return [ts.date() for ts in sessions]


def check_calendar(df: pd.DataFrame, ticker: str, sessions: list[date]) -> list[Issue]:
    """Every expected trading day present, no extra days (both ERROR)."""
    have = set(df["date"])
    expected = set(sessions)
    issues = [
        Issue(ticker, d, "calendar", Severity.ERROR, "trading day missing from data")
        for d in sorted(expected - have)
    ]
    issues += [
        Issue(ticker, d, "calendar", Severity.ERROR, "date is not an NYSE trading day")
        for d in sorted(have - expected)
    ]
    return issues


def check_order_and_duplicates(df: pd.DataFrame, ticker: str) -> list[Issue]:
    issues = [
        Issue(ticker, d, "duplicates", Severity.ERROR, "date appears more than once")
        for d in sorted(set(df.loc[df["date"].duplicated(), "date"]))
    ]
    dates = list(df["date"])
    for i in range(1, len(dates)):
        if dates[i] < dates[i - 1]:
            issues.append(
                Issue(
                    ticker,
                    dates[i],
                    "sorted",
                    Severity.ERROR,
                    f"date comes after {dates[i - 1]} — table not sorted",
                )
            )
            break
    return issues


def check_missing_values(df: pd.DataFrame, ticker: str) -> list[Issue]:
    issues = []
    for col in ["date"] + VALUE_COLS:
        if col not in df.columns:
            issues.append(Issue(ticker, None, "missing", Severity.ERROR, f"column {col} missing"))
            continue
        for idx in df.index[df[col].isna()]:
            issues.append(
                Issue(ticker, df.at[idx, "date"], "missing", Severity.ERROR, f"{col} is missing")
            )
    return issues


def check_positive(df: pd.DataFrame, ticker: str) -> list[Issue]:
    """Prices > 0 and volume ≥ 0 (ERROR); volume = 0 is a WARNING."""
    issues = []
    for col in RAW_PRICE_COLS + ADJ_PRICE_COLS:
        for idx in df.index[df[col] <= 0]:
            issues.append(
                Issue(
                    ticker,
                    df.at[idx, "date"],
                    "positive",
                    Severity.ERROR,
                    f"{col} = {df.at[idx, col]} (must be > 0)",
                )
            )
    for col in VOLUME_COLS:
        for idx in df.index[df[col] < 0]:
            issues.append(
                Issue(ticker, df.at[idx, "date"], "positive", Severity.ERROR, f"{col} < 0")
            )
        for idx in df.index[df[col] == 0]:
            issues.append(
                Issue(ticker, df.at[idx, "date"], "zero_volume", Severity.WARNING, f"{col} = 0")
            )
    return issues


def check_ohlc(df: pd.DataFrame, ticker: str) -> list[Issue]:
    """low ≤ open, close ≤ high — for raw and adjusted prices (ERROR)."""
    issues = []
    for kind in ("raw", "adj"):
        low, high = df[f"low_{kind}"], df[f"high_{kind}"]
        for name in ("open", "close"):
            value = df[f"{name}_{kind}"]
            slack = OHLC_REL_TOL * value.abs()
            bad = (value < low - slack) | (value > high + slack)
            for idx in df.index[bad]:
                issues.append(
                    Issue(
                        ticker,
                        df.at[idx, "date"],
                        "ohlc",
                        Severity.ERROR,
                        f"{name}_{kind} {value[idx]} outside low/high [{low[idx]}, {high[idx]}]",
                    )
                )
    return issues


# Ratios real splits use: n-for-1 and 1-for-n (n ≤ 100), and small pairs like 3:2 (both ≤ 10).
SIMPLE_RATIOS = sorted(
    {Fraction(n, 1) for n in range(1, 101)}
    | {Fraction(1, n) for n in range(1, 101)}
    | {Fraction(p, q) for p in range(1, 11) for q in range(1, 11)}
)


def nearest_simple_ratio(factor: float) -> Fraction:
    """Closest realistic split ratio, e.g. 7.000007 → 7/1, 1.5 → 3/2, 0.25 → 1/4."""
    return min(SIMPLE_RATIOS, key=lambda ratio: abs(factor - float(ratio)) / float(ratio))


def check_splits(df: pd.DataFrame, ticker: str) -> list[Issue]:
    """Each split → INFO; factor not close to a simple ratio → WARNING."""
    issues = []
    for idx in df.index[(df["split_factor"] - 1.0).abs() > 1e-12]:
        factor = float(df.at[idx, "split_factor"])
        ratio = nearest_simple_ratio(factor)
        rel_diff = abs(factor - float(ratio)) / float(ratio)
        d = df.at[idx, "date"]
        issues.append(
            Issue(
                ticker,
                d,
                "split",
                Severity.INFO,
                f"split_factor {factor} (nearest simple ratio {ratio.numerator}:"
                f"{ratio.denominator}, relative difference {rel_diff:.1e})",
            )
        )
        if rel_diff > SPLIT_RATIO_REL_TOL:
            issues.append(
                Issue(
                    ticker,
                    d,
                    "split_ratio",
                    Severity.WARNING,
                    f"split_factor {factor} is not within {SPLIT_RATIO_REL_TOL:.0e} of a simple "
                    f"ratio (nearest {ratio.numerator}:{ratio.denominator})",
                )
            )
    return issues


def check_dividends(df: pd.DataFrame, ticker: str) -> list[Issue]:
    """Negative dividend = ERROR; count + dates recorded as one INFO."""
    issues = [
        Issue(
            ticker,
            df.at[idx, "date"],
            "dividend",
            Severity.ERROR,
            f"div_cash_usd = {df.at[idx, 'div_cash_usd']} (negative)",
        )
        for idx in df.index[df["div_cash_usd"] < 0]
    ]
    paid = df[df["div_cash_usd"] > 0]
    dates = ", ".join(str(d) for d in paid["date"])
    issues.append(
        Issue(
            ticker,
            None,
            "dividend",
            Severity.INFO,
            f"{len(paid)} dividend ex-dates" + (f": {dates}" if dates else ""),
        )
    )
    return issues


def check_big_moves(df: pd.DataFrame, ticker: str) -> list[Issue]:
    """|raw close change| > 25%: INFO if a split is on that date, else WARNING."""
    issues = []
    change = df["close_raw"] / df["close_raw"].shift(1) - 1
    for idx in df.index[change.abs() > BIG_MOVE_PCT]:
        d = df.at[idx, "date"]
        move = f"raw close changed {change[idx]:+.1%}"
        if abs(df.at[idx, "split_factor"] - 1.0) > 1e-12:
            issues.append(
                Issue(
                    ticker,
                    d,
                    "big_move",
                    Severity.INFO,
                    f"{move} — explained by split (factor {df.at[idx, 'split_factor']})",
                )
            )
        else:
            issues.append(Issue(ticker, d, "big_move", Severity.WARNING, f"{move}, no split"))
    return issues


def check_adjustment_ratio(
    df: pd.DataFrame, ticker: str, downloaded: date | None = None
) -> tuple[list[Issue], dict[str, Any]]:
    """r = close_adj / close_raw may change only on (or next to) dividend/split dates.

    Also explains the raw→adjusted gap: how much comes from splits and dividends inside the
    table, and what the ratio on the last day implies about events AFTER the table ends.
    """
    issues: list[Issue] = []
    r = df["close_adj"] / df["close_raw"]
    step = r / r.shift(1)
    is_split = (df["split_factor"] - 1.0).abs() > 1e-12
    is_div = df["div_cash_usd"] > 0
    event = is_split | is_div
    near_event = event | event.shift(-1, fill_value=False) | event.shift(1, fill_value=False)
    unexplained = (step - 1).abs() > RATIO_STEP_REL_TOL
    for idx in df.index[unexplained & ~near_event]:
        issues.append(
            Issue(
                ticker,
                df.at[idx, "date"],
                "adj_ratio",
                Severity.WARNING,
                f"adj/raw ratio changed {step[idx] - 1:+.2e} with no dividend or split nearby",
            )
        )

    # On an event day t the ratio steps up: step[t] = r[t] / r[t-1].
    split_factor_total = float(step[is_split].prod())
    div_factor_total = float(step[is_div & ~is_split].prod())
    r_first, r_last = float(r.iloc[0]), float(r.iloc[-1])
    first_date, last_date = df["date"].iloc[0], df["date"].iloc[-1]
    stats: dict[str, Any] = {
        "ratio_first_day": r_first,
        "ratio_last_day": r_last,
        "gap_factor_in_table": r_last / r_first,
        "gap_from_splits_in_table": split_factor_total,
        "gap_from_dividends_in_table": div_factor_total,
        "gap_after_table_end": 1.0 / r_last,
    }

    # Rough estimate: is the after-end gap more than dividends alone would explain?
    years_in = (last_date - first_date).days / 365.25
    if downloaded is not None and years_in > 0:
        years_after = (downloaded - last_date).days / 365.25
        yearly_div = div_factor_total ** (1 / years_in)
        expected_div_only = yearly_div**years_after
        unexplained_after = (1.0 / r_last) / expected_div_only
        stats["expected_dividends_only_after_end"] = expected_div_only
        stats["unexplained_after_end"] = unexplained_after
        if unexplained_after > 1.5:
            implied = (
                f"implied by the ratio: about a {round(unexplained_after)}:1 split (or several) "
                "after the table ends — rough estimate, not a fact"
            )
        else:
            implied = "implied by the ratio: no split after the table ends (dividends explain it)"
        stats["implied_later_split"] = implied
        issues.append(
            Issue(
                ticker,
                None,
                "adj_ratio",
                Severity.INFO,
                f"after {last_date} the adj/raw gap is ×{1 / r_last:.3f}; dividends at the "
                f"in-table rate would give ×{expected_div_only:.3f} → {implied}",
            )
        )
    issues.append(
        Issue(
            ticker,
            None,
            "adj_ratio",
            Severity.INFO,
            f"inside the table the adj/raw ratio grew ×{r_last / r_first:.4f}: splits "
            f"×{split_factor_total:.4f}, dividends ×{div_factor_total:.4f}",
        )
    )
    if not math.isclose(split_factor_total * div_factor_total, r_last / r_first, rel_tol=1e-6):
        issues.append(
            Issue(
                ticker,
                None,
                "adj_ratio",
                Severity.WARNING,
                "split + dividend steps do not multiply to the total ratio change",
            )
        )
    return issues, stats


def validate_prices(
    df: pd.DataFrame,
    ticker: str,
    start: date,
    end: date,
    downloaded: date | None = None,
    sessions: list[date] | None = None,
) -> ValidationReport:
    """Run every check. `sessions` overrides the NYSE calendar (used in tests)."""
    report = ValidationReport(ticker)
    report.issues += check_missing_values(df, ticker)
    if any(i.message.startswith("column") for i in report.issues):
        return report  # cannot run other checks without the columns
    report.issues += check_order_and_duplicates(df, ticker)
    if sessions is None:
        sessions = nyse_sessions(start, end)
    report.issues += check_calendar(df, ticker, sessions)
    report.issues += check_positive(df, ticker)
    report.issues += check_ohlc(df, ticker)
    report.issues += check_splits(df, ticker)
    report.issues += check_dividends(df, ticker)
    report.issues += check_big_moves(df, ticker)
    ratio_issues, ratio_stats = check_adjustment_ratio(df, ticker, downloaded)
    report.issues += ratio_issues
    report.stats.update(ratio_stats)
    report.stats["rows"] = len(df)
    report.stats["expected_sessions"] = len(sessions)
    for severity in Severity:
        logger.info("%s: %d %s", ticker, report.count(severity), severity.value)
    return report


def load_raw_csv(path: Any) -> pd.DataFrame:
    """Read a saved raw CSV back, with `date` as plain dates. No other changes."""
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d").dt.date
    return df
