"""Phase 6 data step (prompt 16): validate every price file the pre-registration needs. DATA QUALITY ONLY.

Run:  uv run --group crosscheck python scripts/validate_phase6_data.py
- 8 tickers × 3 Tiingo files (warm-up 2008–2009, development 2010–2016, validation 2017–2020): the same 9 checks
  as Step 2.3, plus the warm-up → development → validation join on the NYSE calendar.
- Yahoo cross-check: one cached yfinance request per ticker for 2008-01-01 → 2020-12-31, compared per file.
- Possible unsupported corporate actions: split factors not near a simple ratio, unusually large dividends.
- Writes reports/data_validation/phase6_all_stocks_2008-2020.md — counts, dates and % only, no price series.
NOT reported (Goggy 2026-10-25, D8): the "after the table end" adjustment estimate and the later-split ratio
implied by Yahoo's basis — both would summarise corporate actions from the locked final-test period.
No strategy, backtest, metric or summary statistic of 2017–2020 prices is computed here.
Exit code 1 if any ERROR.
"""

import itertools
import statistics
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from quant_research.data.crosscheck import crosscheck, load_or_fetch_yahoo
from quant_research.data.validation import (
    Severity,
    load_raw_csv,
    nearest_simple_ratio,
    validate_prices,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw" / "tiingo"
YAHOO_CACHE = PROJECT_ROOT / "data" / "cache" / "yfinance"
REPORT = PROJECT_ROOT / "reports" / "data_validation" / "phase6_all_stocks_2008-2020.md"
TICKERS = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "T", "SPY"]
FILES = [
    ("warm-up", date(2008, 1, 1), date(2009, 12, 31)),
    ("development", date(2010, 1, 1), date(2016, 12, 31)),
    ("validation", date(2017, 1, 1), date(2020, 12, 31)),
]
YAHOO_START, YAHOO_END = date(2008, 1, 1), date(2020, 12, 31)
SPECIAL_DIVIDEND_FACTOR = (
    2.0  # a dividend > 2 × the ticker's median dividend is flagged for a human look
)


def main() -> int:
    rows, joins, flags, yahoo_rows, errors, flat = [], [], [], [], [], []
    for t in TICKERS:
        yahoo = load_or_fetch_yahoo(t, YAHOO_START, YAHOO_END, YAHOO_CACHE)
        if max(yahoo["date"]) > YAHOO_END:
            errors.append(f"{t}: Yahoo cache has dates after {YAHOO_END}")
        parts = []
        for label, start, end in FILES:
            path = RAW / f"{t}_{start}_{end}.csv"
            df = load_raw_csv(path)
            parts.append(df)
            report = validate_prices(
                df, t, start, end, downloaded=None
            )  # no after-end estimate (D8)
            count = {s: report.count(s) for s in Severity}
            errors += [
                f"{t} {label}: {i.date} {i.check}: {i.message}"
                for i in report.issues
                if i.severity == Severity.ERROR
            ]
            splits = [
                (d, f, nearest_simple_ratio(f))
                for d, f in zip(df["date"], df["split_factor"], strict=True)
                if abs(f - 1.0) > 1e-12
            ]
            divs = df.loc[df["div_cash_usd"] > 0, ["date", "div_cash_usd"]]
            warnings = [
                f"{i.date} {i.check}: {i.message}"
                for i in report.issues
                if i.severity == Severity.WARNING
            ]
            rows.append(
                (
                    t,
                    label,
                    len(df),
                    report.stats["expected_sessions"],
                    count,
                    splits,
                    len(divs),
                    warnings,
                )
            )
            for d, f, ratio in splits:
                if abs(f - float(ratio)) / float(ratio) > 1e-4:
                    flags.append(
                        f"{t} {d}: split_factor {f} is not near a simple ratio — possible distribution / spin-off"
                    )
            if max(df["date"]) >= date(2021, 1, 1):
                errors.append(f"{t} {label}: contains dates ≥ 2021-01-01")
            # Yahoo cross-check for this file's dates
            ys = yahoo[(yahoo["date"] >= start) & (yahoo["date"] <= end)].reset_index(drop=True)
            try:
                c = crosscheck(df, ys, allow_constant_later_factor=True)
                yahoo_rows.append((t, label, c, None))
            except ValueError as exc:
                yahoo_rows.append((t, label, None, str(exc)))
        joined = pd.concat(parts, ignore_index=True)
        jr = validate_prices(joined, t, FILES[0][1], FILES[-1][2], downloaded=None)
        join_errors = [i for i in jr.issues if i.severity == Severity.ERROR]
        join_warnings = [i for i in jr.issues if i.severity == Severity.WARNING]
        errors += [f"{t} join: {i.date} {i.check}: {i.message}" for i in join_errors]
        boundaries = [(p["date"].iloc[-1], q["date"].iloc[0]) for p, q in itertools.pairwise(parts)]
        joins.append(
            (t, len(joined), jr.stats["expected_sessions"], boundaries, join_errors, join_warnings)
        )
        flags += special_dividends(t, joined)
        flat += flat_bars(t, joined)
        print(f"{t}: files ok" if not [e for e in errors if e.startswith(t)] else f"{t}: ERRORS")
    REPORT.write_text(build_report(rows, joins, flags, yahoo_rows, errors, flat), encoding="utf-8")
    print(
        f"report written: {REPORT.relative_to(PROJECT_ROOT)} ; errors: {len(errors)} ; flags: {len(flags)}"
    )
    return 1 if errors else 0


def special_dividends(t: str, joined: pd.DataFrame) -> list[str]:
    """Dividends > 2 × the median, on ONE share basis (each ÷ every snapped split after it in these files)."""
    splits = [
        (d, float(nearest_simple_ratio(f)))
        for d, f in zip(joined["date"], joined["split_factor"], strict=True)
        if abs(f - 1.0) > 1e-12
    ]
    same_basis = []
    for d, v in zip(joined["date"], joined["div_cash_usd"], strict=True):
        if v > 0:
            later = 1.0
            for split_day, ratio in splits:
                if split_day > d:
                    later *= ratio
            same_basis.append((d, v / later))
    if not same_basis:
        return []
    median = statistics.median(v for _, v in same_basis)
    return [
        f"{t} {d}: dividend {v / median:.1f}× the median (same share basis) — possible special distribution"
        for d, v in same_basis
        if v > SPECIAL_DIVIDEND_FACTOR * median
    ]


def flat_bars(t: str, joined: pd.DataFrame) -> list[tuple]:
    """Rows with open = high = low = close — a stale / repeated bar. Reported, never fixed."""
    med = statistics.median(joined["volume_raw"])
    cols = ["date", "open_raw", "high_raw", "low_raw", "close_raw", "volume_raw"]
    return [
        (t, d, vol / med)
        for d, o, h, lo, c, vol in joined[cols].itertuples(index=False, name=None)
        if o == h == lo == c
    ]


def build_report(rows, joins, flags, yahoo_rows, errors, flat) -> str:
    out = [
        "# Phase 6 data validation — 8 stocks, 2008–2020 (prompt 16)",
        "",
        "> Data quality only. Counts, dates and % only — no price series (Tiingo licence). No strategy, backtest,",
        "> metric or summary statistic of 2017–2020 prices is computed. Not reported (Goggy 2026-10-25, D8): the",
        "> adjustment estimate after each file's end and the later-split ratio implied by Yahoo's basis, because both",
        "> would summarise corporate actions from the locked final-test period.",
        "",
        f"**ERRORS: {len(errors)}**" + (" — see §6." if errors else " — every file passed."),
        "",
        "## 1. Every file (same 9 checks as Step 2.3)",
        "",
        "| Ticker | File | Rows | NYSE sessions | ERROR | WARNING | INFO | Splits (date, factor → ratio) | Dividends |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t, label, n, sessions, count, splits, divs, _ in rows:
        sp = "; ".join(f"{d} {f} → {r.numerator}:{r.denominator}" for d, f, r in splits) or "none"
        out.append(
            f"| {t} | {label} | {n} | {sessions} | {count[Severity.ERROR]} | {count[Severity.WARNING]} | "
            f"{count[Severity.INFO]} | {sp} | {divs} |"
        )
    warn = [(t, label, w) for t, label, *_, ws in rows for w in ws]
    out += ["", "**Warnings per file:** " + ("none." if not warn else "")]
    out += [f"- {t} {label}: {w}" for t, label, w in warn]
    out += [
        "",
        "## 2. Joins: warm-up → development → validation (NYSE calendar, 2008-01-01 → 2020-12-31)",
        "",
        "| Ticker | Rows joined | NYSE sessions | Boundaries (last → first) | ERROR | WARNING |",
        "|---|---|---|---|---|---|",
    ]
    for t, n, sessions, bounds, je, jw in joins:
        b = "; ".join(f"{a} → {c}" for a, c in bounds)
        out.append(f"| {t} | {n} | {sessions} | {b} | {len(je)} | {len(jw)} |")
    join_warn = [(t, w) for t, *_, jw in joins for w in jw]
    out += ["", "**Join warnings:** " + ("none." if not join_warn else "")]
    out += [f"- {t} {w.date} {w.check}: {w.message}" for t, w in join_warn]
    out += [
        "",
        "## 3. Yahoo cross-check (yfinance, auto_adjust=False, one request per ticker 2008-01-01 → 2020-12-31)",
        "",
        (
            "| Ticker | File | Days only-Tiingo / only-Yahoo | Split basis explained | Splits same | Dividends T / Y, max diff |"
            " Closes max / median diff, days > 0.5% |"
        ),
        "|---|---|---|---|---|---|---|",
    ]
    for t, label, c, err in yahoo_rows:
        if c is None:
            out.append(f"| {t} | {label} | — | **NO: {err}** | — | — | — |")
            continue
        d, dv, cl = c["trading_days"], c["dividends"], c["closes"]
        out.append(
            f"| {t} | {label} | {len(d['only_tiingo'])} / {len(d['only_yahoo'])} | "
            + (
                "yes (constant non-split factor, value not shown — D8)"
                if c["basis"]["non_simple_later_factor"]
                else "yes"
            )
            + " | "
            f"{'yes' if c['splits']['same_dates_and_ratios'] else '**NO**'} | {dv['tiingo_count']} / {dv['yahoo_count']}, "
            f"{dv.get('max_abs_pct', 0):.4%} | {cl['max_abs_pct']:.3%} / {cl['median_abs_pct']:.4%}, {cl['count_over_threshold']} |"
        )
    big = [
        (t, label, n)
        for t, label, c, _ in yahoo_rows
        if c is not None
        for n in c["close_differences_explained"]
    ]
    out += [
        "",
        "**Close differences > 0.5% (tested against the data):** " + ("none." if not big else ""),
    ]
    out += [f"- {t} {label} {n['date']}: {n['pct']:+.3%} → {n['note']}" for t, label, n in big]
    out += [
        "",
        "## 4. Flat bars (open = high = low = close) — stale / repeated bars, reported, NOT fixed",
        "",
    ]
    out += (
        [f"- {t} {d}: flat bar, volume {v:.1f}× the ticker's median" for t, d, v in flat]
        if flat
        else ["- none."]
    )
    out += [
        "",
        "## 5. Possible unsupported corporate actions (flagged for a human look, not handled)",
        "",
    ]
    out += (
        [f"- {f}" for f in flags]
        if flags
        else [
            "- none found (all split factors near simple ratios; no dividend > 2× the median on one share basis)."
        ]
    )
    out += ["", "## 6. Errors", ""]
    out += [f"- {e}" for e in errors] if errors else ["- none."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    from _help import handle_help  # --help: describe and exit, do nothing else

    handle_help(__doc__)
    sys.exit(main())
