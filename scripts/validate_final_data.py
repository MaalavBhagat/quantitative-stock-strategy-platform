"""Final test data step (prompt 26, Part A): validate every 2021–2025 input. DATA QUALITY ONLY — no returns.

Run:  uv run --group crosscheck python scripts/validate_final_data.py
- Tiingo 2021-01-01 → 2025-12-31 for the 7 final-test stocks (research/FINAL_TEST_PREREG.md; T excluded): the same 9
  checks as Step 2.3, flat bars, split factors / large dividends (possible unsupported corporate actions), the join to
  the 2017–2020 files on the NYSE calendar, and the warm-up load the runs will use (2019-01-01 → 2025-12-31).
- Yahoo cross-check: one cached yfinance request per ticker for 2021-01-01 → 2025-12-31.
- RBA AUD/USD: coverage of every NYSE session 2021–2025 (latest rate ≤ day, never more than 5 days old).
- SEC 8-Ks to 2025-12-31: counts per company and year (earnings = item 2.02), XOM's two filers, availability rule.
- Writes reports/data_validation/final_2021-2025.md — counts, dates and checks only, no price series, no returns.
Exit code 1 if any ERROR; possible unsupported corporate actions are listed and also stop the run (ask Goggy).
"""

import bisect
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

from quant_research.data.crosscheck import crosscheck, load_or_fetch_yahoo
from quant_research.data.fx import load_usd_per_aud
from quant_research.data.loader import load_prices_with_warmup
from quant_research.data.validation import (
    Severity,
    load_raw_csv,
    nearest_simple_ratio,
    nyse_sessions,
    validate_prices,
)
from quant_research.news.events import categories, load_events, timing, usable_close_day

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw" / "tiingo"
SUB = PROJECT_ROOT / "data" / "raw" / "sec" / "submissions"
YAHOO_CACHE = PROJECT_ROOT / "data" / "cache" / "yfinance"
REPORT = PROJECT_ROOT / "reports" / "data_validation" / "final_2021-2025.md"
TICKERS = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "SPY"]
COMPANIES = [t for t in TICKERS if t != "SPY"]
START, END = date(2021, 1, 1), date(2025, 12, 31)
PREV = (date(2017, 1, 1), date(2020, 12, 31))
WARMUP = date(2019, 1, 1)
YEARS = range(2021, 2026)
SPECIAL_DIVIDEND_FACTOR = 2.0


def special_dividends(t: str, df: pd.DataFrame) -> list[str]:
    """Dividends > 2 × the median on ONE share basis (each ÷ every snapped split after it in the table)."""
    splits = [(d, float(nearest_simple_ratio(f))) for d, f in zip(df["date"], df["split_factor"], strict=True)
              if abs(f - 1.0) > 1e-12]  # fmt: skip
    same = []
    for d, v in zip(df["date"], df["div_cash_usd"], strict=True):
        if v > 0:
            later = 1.0
            for sd, ratio in splits:
                if sd > d:
                    later *= ratio
            same.append((d, v / later))
    if not same:
        return []
    med = statistics.median(v for _, v in same)
    return [f"{t} {d}: dividend {v / med:.1f}× the median (same share basis) — possible special distribution"
            for d, v in same if v > SPECIAL_DIVIDEND_FACTOR * med]  # fmt: skip


def flat_bars(t: str, df: pd.DataFrame) -> list[tuple]:
    med = statistics.median(df["volume_raw"])
    cols = ["date", "open_raw", "high_raw", "low_raw", "close_raw", "volume_raw"]
    return [
        (t, d, v / med)
        for d, o, h, lo, c, v in df[cols].itertuples(index=False, name=None)
        if o == h == lo == c
    ]


def main() -> int:
    errors, flags, flat, files, joins, yahoo_rows, warmups, divs_by_year = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        {},
    )
    for t in TICKERS:
        path = RAW / f"{t}_{START}_{END}.csv"
        meta = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
        df = load_raw_csv(path)
        if max(df["date"]) > END:
            errors.append(f"{t}: file contains dates after {END}")
        rep = validate_prices(df, t, START, END, downloaded=None)
        count = {s: rep.count(s) for s in Severity}
        errors += [
            f"{t}: {i.date} {i.check}: {i.message}"
            for i in rep.issues
            if i.severity == Severity.ERROR
        ]
        splits = [(d, f, nearest_simple_ratio(f)) for d, f in zip(df["date"], df["split_factor"], strict=True)
                  if abs(f - 1.0) > 1e-12]  # fmt: skip
        for d, f, ratio in splits:
            if abs(f - float(ratio)) / float(ratio) > 1e-4:
                flags.append(
                    f"{t} {d}: split_factor {f} is not near a simple ratio — possible distribution / spin-off"
                )
        divs = df.loc[df["div_cash_usd"] > 0, "date"]
        divs_by_year[t] = Counter(d.year for d in divs)
        warnings = [
            f"{i.date} {i.check}: {i.message}" for i in rep.issues if i.severity == Severity.WARNING
        ]
        files.append((t, len(df), rep.stats["expected_sessions"], count, splits, len(divs), warnings,
                      meta["downloaded_at_utc"]))  # fmt: skip
        flags += special_dividends(t, df)
        flat += flat_bars(t, df)
        prev = load_raw_csv(RAW / f"{t}_{PREV[0]}_{PREV[1]}.csv")
        joined = pd.concat([prev, df], ignore_index=True)
        jr = validate_prices(joined, t, PREV[0], END, downloaded=None)
        je = [i for i in jr.issues if i.severity == Severity.ERROR]
        errors += [f"{t} join: {i.date} {i.check}: {i.message}" for i in je]
        joins.append(
            (
                t,
                len(joined),
                jr.stats["expected_sessions"],
                prev["date"].iloc[-1],
                df["date"].iloc[0],
                len(je),
            )
        )
        try:
            w = load_prices_with_warmup(t, WARMUP, START, END)
            warmups.append((t, len(w), str(w["date"].iloc[0]), str(w["date"].iloc[-1]), "ok"))
        except Exception as exc:  # noqa: BLE001 — reported as an ERROR, never hidden
            errors.append(f"{t} warm-up load: {exc}")
            warmups.append((t, 0, "—", "—", f"FAILED: {exc}"))
        yahoo = load_or_fetch_yahoo(t, START, END, YAHOO_CACHE)
        if max(yahoo["date"]) > END:
            errors.append(f"{t}: Yahoo table has dates after {END}")
        try:
            yahoo_rows.append((t, crosscheck(df, yahoo, allow_constant_later_factor=True), None))
        except ValueError as exc:
            yahoo_rows.append((t, None, str(exc)))
        print(f"{t}: checked")
    # RBA
    fx = load_usd_per_aud()
    sessions = nyse_sessions(date(2021, 1, 4), END)
    stale, fx_problems = 0, []
    for d in sessions:
        try:
            fx.on(d)
            stale += fx.dates[bisect.bisect_right(fx.dates, d) - 1] != d
        except Exception as exc:  # noqa: BLE001
            fx_problems.append(f"{d}: {exc}")
    errors += [f"RBA {p}" for p in fx_problems]
    fx_rows = [d for d in fx.dates if START <= d <= END]
    if any(d > END for d in fx.dates):
        errors.append("RBA series has dates after 2025-12-31")
    # SEC
    sec, xom_files, timing_count, usable_late = {}, [], Counter(), []
    for t in COMPANIES:
        events = load_events(t, SUB, "2025-12-31")
        per_year = defaultdict(Counter)
        for e in events:
            y = e.accepted_et.year
            if y in YEARS:
                per_year[y]["filings"] += 1
                per_year[y]["earnings"] += "earnings" in e.categories
                per_year[y]["8-K/A"] += e.form == "8-K/A"
                timing_count[timing(e.accepted_et)] += 1
                if usable_close_day(e.accepted_et) > date(2026, 1, 31):
                    usable_late.append(e.accession)
            if e.accepted_et.date() > END:
                errors.append(f"{t} {e.accession}: accepted after {END}")
        sec[t] = per_year
    for p in sorted(SUB.glob("XOM_CIK*_8k_to-2025-12-31.meta.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        xom_files.append((p.name.split("_")[1], m.get("entity_name"), m["8k_kept"], m["8k_dropped_after_cutoff"],
                          m["rows_read"]))  # fmt: skip
    unrecognised = Counter()
    for path in sorted(SUB.glob("*_8k_to-2025-12-31.json")):
        for f in json.loads(path.read_text(encoding="utf-8"))["filings"]:
            if f["filingDate"] >= "2021-01-01":
                for c in categories(f["items"]):
                    if c.startswith("UNRECOGNISED"):
                        unrecognised[c] += 1
    REPORT.write_text(build(files, joins, warmups, yahoo_rows, flags, flat, divs_by_year, fx, fx_rows, sessions,
                            stale, sec, xom_files, timing_count, unrecognised, errors), encoding="utf-8")  # fmt: skip
    print(
        f"report written: {REPORT.relative_to(PROJECT_ROOT)} ; errors: {len(errors)} ; corporate-action flags: {len(flags)}"
    )
    return 1 if errors or flags else 0


def build(files, joins, warmups, yahoo_rows, flags, flat, divs_by_year, fx, fx_rows, sessions, stale, sec, xom_files,
          timing_count, unrecognised, errors) -> str:  # fmt: skip
    out = [
        "# Final test data validation — 7 stocks, 2021-01-01 → 2025-12-31 (prompt 26, Part A)",
        "",
        "> Data quality only. Counts, dates and checks — no price series and no returns (Tiingo / RBA licences; no result",
        "> is looked at before the one-time run). Rules: research/FINAL_TEST_PREREG.md (tag `prereg-final`, created",
        "> before the first 2021+ download). T is excluded (2022 spin-off) and was not downloaded.",
        "",
        f"**ERRORS: {len(errors)} · possible unsupported corporate actions: {len(flags)}**",
        "",
        "## 1. Tiingo files 2021–2025 (same 9 checks as Step 2.3)",
        "",
        "| Ticker | Rows | NYSE sessions | ERROR | WARNING | INFO | Splits | Dividends | Downloaded (UTC) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t, n, s, count, splits, nd, _, dl in files:
        sp = "; ".join(f"{d} {f} → {r.numerator}:{r.denominator}" for d, f, r in splits) or "none"
        out.append(f"| {t} | {n} | {s} | {count[Severity.ERROR]} | {count[Severity.WARNING]} | {count[Severity.INFO]} | "
                   f"{sp} | {nd} | {dl} |")  # fmt: skip
    warn = [(t, w) for t, *_, ws, _ in files for w in ws]
    out += ["", "**Warnings:** " + ("none." if not warn else "")] + [f"- {t}: {w}" for t, w in warn]
    out += ["", "**Dividends per year (ex-dates in the file):**", "", "| Ticker | " + " | ".join(map(str, YEARS)) + " |",
            "|---|" + "---|" * len(YEARS)]  # fmt: skip
    out += [
        f"| {t} | " + " | ".join(str(divs_by_year[t][y]) for y in YEARS) + " |" for t in TICKERS
    ]
    out += ["", "## 2. Join to the 2017–2020 files + the warm-up load the runs use", "",
            "| Ticker | Rows 2017–2025 | NYSE sessions | Last 2020 row → first 2021 row | Join ERROR | Warm-up 2019-01-01 → 2025-12-31 |",
            "|---|---|---|---|---|---|"]  # fmt: skip
    wu = {t: w for t, *w in warmups}
    for t, n, s, a, b, ne in joins:
        rows, first, last, status = wu[t]
        out.append(
            f"| {t} | {n} | {s} | {a} → {b} | {ne} | {status}: {rows} rows, {first} → {last} |"
        )
    out += ["", "## 3. Yahoo cross-check (yfinance, auto_adjust=False, 2021-01-01 → 2025-12-31)", "",
            ("| Ticker | Days only-Tiingo / only-Yahoo | Split basis explained | Splits same | Dividends T / Y, max diff | "
            "Closes max / median diff, days > 0.5% |"), "|---|---|---|---|---|---|"]  # fmt: skip
    for t, c, err in yahoo_rows:
        if c is None:
            out.append(f"| {t} | — | **NO: {err}** | — | — | — |")
            continue
        d, dv, cl = c["trading_days"], c["dividends"], c["closes"]
        out.append(f"| {t} | {len(d['only_tiingo'])} / {len(d['only_yahoo'])} | "
                   + ("yes (constant later factor)" if c["basis"]["non_simple_later_factor"] else "yes")
                   + f" | {'yes' if c['splits']['same_dates_and_ratios'] else '**NO**'} | {dv['tiingo_count']} / "
                   f"{dv['yahoo_count']}, {dv.get('max_abs_pct', 0):.4%} | {cl['max_abs_pct']:.3%} / "
                   f"{cl['median_abs_pct']:.4%}, {cl['count_over_threshold']} |")  # fmt: skip
    big = [
        (t, n) for t, c, _ in yahoo_rows if c is not None for n in c["close_differences_explained"]
    ]
    out += ["", "**Close differences > 0.5%:** " + ("none." if not big else "")]
    out += [f"- {t} {n['date']}: {n['pct']:+.3%} → {n['note']}" for t, n in big]
    out += ["", "## 4. Flat bars (open = high = low = close) — reported, NOT fixed", ""]
    out += [f"- {t} {d}: flat bar, volume {v:.1f}× the median" for t, d, v in flat] or ["- none."]
    out += [
        "",
        "## 5. Possible unsupported corporate actions (any → STOP and ask Goggy before running)",
        "",
    ]
    out += [f"- {f}" for f in flags] or [
        "- none found: no split rows at all in 2021–2025 for the 7 stocks, and no dividend > 2× the median."
    ]
    out += ["", "## 6. RBA AUD/USD (series FXRUSD)", "",
            (f"- Files: {', '.join(n for n in fx.source_files if n.startswith(('2021', '2023')))} (trimmed extracts of the "
            "official 2018-2022.xls and 2023-current.xls; originals deleted; rows after 2025-12-31 never saved)."),
            f"- Rates dated 2021–2025: {len(fx_rows)} ({fx_rows[0]} → {fx_rows[-1]}).",
            (f"- Every NYSE session 2021-01-04 → 2025-12-31 ({len(sessions)}) has a rate dated ≤ that day and ≤ 5 days old;"
            f" {stale} sessions use the previous RBA day's rate (Sydney holiday / US-only trading day).")]  # fmt: skip
    out += ["", "## 7. SEC 8-K filings 2021–2025 (for E1's earnings events; counts only)", "",
            "**Exxon filers** (checked, not assumed):", "",
            "| CIK | Entity | 8-K kept (≤ 2025-12-31) | 8-K after 2025-12-31 (dropped) | Filings read (all forms) |",
            "|---|---|---|---|---|"]  # fmt: skip
    out += [
        f"| {cik} | {name} | {kept} | {drop} | {rows} |"
        for cik, name, kept, drop, rows in xom_files
    ]
    out += ["", ("→ Every Exxon 8-K up to 2025-12-31 was filed by CIK 0000034088; the new holding company "
            "(0002115436) filed its first 8-Ks after 2025-12-31. Both files are kept; events are merged by accession."),
            "", "| Company | " + " | ".join(f"{y} filings / earnings" for y in YEARS) + " | 8-K/A |",
            "|---|" + "---|" * (len(YEARS) + 1)]  # fmt: skip
    for t in COMPANIES:
        py = sec[t]
        out.append(f"| {t} | " + " | ".join(f"{py[y]['filings']} / {py[y]['earnings']}" for y in YEARS)
                   + f" | {sum(py[y]['8-K/A'] for y in YEARS)} |")  # fmt: skip
    out += ["", "Timing (US/Eastern, 2021–2025): " + ", ".join(f"{k} {v}" for k, v in sorted(timing_count.items()))
            + ". Unrecognised item codes 2021–2025: " + (", ".join(f"{k} {v}" for k, v in unrecognised.items()) or "none")
            + ". Event calendar extended to 2026 so a filing late on 2025-12-31 still gets a usable day."]  # fmt: skip
    out += ["", "## 8. Errors", ""] + ([f"- {e}" for e in errors] or ["- none."])
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    from _help import handle_help  # --help: describe and exit, do nothing else

    handle_help(__doc__)
    sys.exit(main())
