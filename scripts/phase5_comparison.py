"""Phase 5, Step 5.7: comparison of S0–S4 on the development period, from the SAVED run records.

Run:  uv run python scripts/phase5_comparison.py
- Uses exactly the runs behind the two reports: S1/S2 report = records at commit 987c81c; S3/S4 report = records
  at commit 8f3cf46 (main runs; the 64 reproductions only for the proof already in that report).
- Consistency proof: every run must have identical capital, period, data files + download dates, broker, spread,
  share mode, FX source + rates, reinvest rule, min order and S0 benchmark. Any difference → STOP (exit 1).
- Reproducibility: re-runs 5 randomly chosen saved configs (seed fixed) → final values must be identical.
- Writes reports/experiments/phase5_comparison_dev_2010-2016.md — SUMMARY NUMBERS ONLY. No winner, no ranking.
SIMULATED, HISTORICAL, DEVELOPMENT PERIOD — exploration only, not evidence.
"""

import csv
import json
import random
import statistics
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import yaml

from quant_research.backtesting.run import DEFAULT_RUNS_DIR, parse_config, run_backtest
from quant_research.data.fx import load_usd_per_aud
from quant_research.strategies.registry import make_strategy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT = PROJECT_ROOT / "reports" / "experiments" / "phase5_comparison_dev_2010-2016.md"
REPORT_COMMITS = {"987c81c": "S1/S2 report", "8f3cf46": "S3/S4 report"}
LABELS = {
    "s0_buy_and_hold": "S0",
    "s1_profit_target": "S1",
    "s2_pullback": "S2",
    "s3_mean_reversion": "S3",
    "s4_trend_s1": "S4-S1",
    "s4_trend_s2": "S4-S2",
}
USE = {"987c81c": ("S0", "S1", "S2"), "8f3cf46": ("S0", "S3", "S4-S1", "S4-S2")}
SAME = [  # (what, how to read it from a record)
    ("initial capital (AUD)", lambda r: r["config"]["initial_aud"]),
    ("period", lambda r: (r["config"]["start"], r["config"]["end"])),
    ("price file + download time", lambda r: (r["data_provenance"]["file_name"], r["data_provenance"]["downloaded_at_utc"])),
    ("broker", lambda r: r["config"]["broker"]),
    ("spread level", lambda r: r["config"]["spread_level"]),
    ("share mode", lambda r: r["config"]["share_mode"]),
    ("FX source + files", lambda r: (r["config"]["fx_source"], tuple(r["fx_files"]))),
    ("FX rates used (start, end)", lambda r: (r["summary"]["usd_per_aud_start"], r["summary"]["usd_per_aud_end"])),
    ("start cash (USD)", lambda r: r["summary"]["start_cash_usd"]),
    ("reinvest rule (US$)", lambda r: r["config"]["reinvest_min_cash_usd"]),
    ("min order (US$)", lambda r: r["config"]["min_order_usd"]),
    ("final test locked", lambda r: r["config"]["final_test_unlocked"]),
    ("uncommitted code changes (git_dirty)", lambda r: r["git_dirty"]),
]  # fmt: skip
STRATEGY_ORDER = ["S1", "S2", "S3", "S4-S1", "S4-S2"]
SEED = 20261025


@dataclass
class Rec:
    path: Path
    record: dict
    label: str
    ticker: str

    @property
    def total_return(self) -> float:
        s = self.record["summary"]
        return float(Decimal(s["last_close_value_usd"]) / Decimal(s["start_cash_usd"]) - 1)

    def csv(self, name: str) -> list[dict]:
        with (self.path.parent / name).open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    @property
    def days_in_cash(self) -> float:
        eq = self.csv("equity.csv")
        return sum(Decimal(e["market_value_usd"]) == 0 for e in eq) / len(eq)

    @property
    def round_trips(self) -> int:
        return sum(f["side"] == "sell" for f in self.csv("fills.csv"))

    @property
    def stranded(self) -> bool:
        fills = self.csv("fills.csv")
        return bool(fills) and fills[-1]["side"] == "sell"


def load_records() -> list[Rec]:
    recs = []
    for path in sorted(DEFAULT_RUNS_DIR.glob("*/run.json")):  # main runs only (not _reproductions)
        r = json.loads(path.read_text(encoding="utf-8"))
        commit = str(r["git_commit"])[:7]
        label = LABELS[r["config"]["strategy"]]
        if commit in USE and label in USE[commit]:
            recs.append(Rec(path, r, label, r["config"]["ticker"]))
    return recs


def main() -> int:
    recs = load_records()
    counts = {
        c: sum(str(r.record["git_commit"]).startswith(c) for r in recs) for c in REPORT_COMMITS
    }
    print("records used:", counts)
    if counts != {"987c81c": 66, "8f3cf46": 78}:
        print("STOP — expected 66 + 78 records")
        return 1
    # sell orders must all be "sell all" → every sell is a full exit (round trip)
    for r in recs:
        if any(o["side"] == "sell" and o["size"] != "all" for o in r.csv("orders.csv")):
            print(
                f"STOP — {r.path.parent.name} has a partial sell; round-trip count would be wrong"
            )
            return 1
    problems = []
    for ticker in sorted({r.ticker for r in recs}):
        group = [r for r in recs if r.ticker == ticker]
        for what, read in SAME:
            values = {json.dumps(read(r.record), default=str) for r in group}
            if len(values) != 1:
                problems.append(f"{ticker}: {what} differs: {sorted(values)}")
        s0_values = {r.record["summary"]["last_close_value_usd"] for r in group if r.label == "S0"}
        if len(s0_values) != 1:
            problems.append(f"{ticker}: S0 benchmark differs between reports: {s0_values}")
    if problems:
        print("STOP — consistency proof failed:\n  " + "\n  ".join(problems))
        return 1
    print("consistency proof: all fields identical within each ticker")
    repro = reproduce(recs)
    if any(not ok for *_, ok in repro):
        print("STOP — reproduction differs:", [x for x in repro if not x[-1]])
        return 1
    print("reproducibility: 5 of 5 identical")
    REPORT.write_text(build_report(recs, repro), encoding="utf-8")
    print(f"report written: {REPORT.relative_to(PROJECT_ROOT)}")
    return 0


def reproduce(recs: list[Rec]) -> list[tuple]:
    """Re-run 5 randomly chosen saved configs (fixed seed) → compare final values to the saved records."""
    picks = random.Random(SEED).sample(sorted(recs, key=lambda r: r.path.parent.name), 5)
    fx = load_usd_per_aud()
    out_dir = (
        DEFAULT_RUNS_DIR / "_reproductions" / f"phase5_check_{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
    )
    rows = []
    for rec in picks:
        raw = yaml.safe_load((rec.path.parent / "config.yaml").read_text(encoding="utf-8"))
        # records written before 2026-10-25 stored dates as text — convert ONLY the date fields back
        for key in ("start", "end", "warmup_start"):
            if isinstance(raw.get(key), str):
                raw[key] = date.fromisoformat(raw[key])
        config = parse_config(raw)
        new = run_backtest(config, make_strategy(config), fx_series=fx, runs_dir=out_dir)
        saved = rec.record["summary"]
        same = (
            str(new.summary["last_close_value_usd"]) == saved["last_close_value_usd"]
            and str(new.summary["end_aud_after_liquidation"]) == saved["end_aud_after_liquidation"]
        )
        rows.append(
            (rec.path.parent.name, saved["last_close_value_usd"], str(new.summary["last_close_value_usd"]),
             saved["end_aud_after_liquidation"], str(new.summary["end_aud_after_liquidation"]), same)
        )  # fmt: skip
    return rows


def pts(x: float) -> str:
    return f"{x * 100:+.1f}"


def build_report(recs: list[Rec], repro: list[tuple]) -> str:
    tickers = sorted({r.ticker for r in recs})
    s0 = {t: next(r for r in recs if r.ticker == t and r.label == "S0") for t in tickers}
    tried = {
        label: len(
            {r.path.parent.name for r in recs if r.label == label and r.ticker == tickers[0]}
        )
        for label in STRATEGY_ORDER
    }
    lines = [
        "# Phase 5 comparison — S0 to S4, development period 2010–2016",
        "",
        "> **SIMULATED, HISTORICAL, DEVELOPMENT PERIOD — exploration only, not evidence (EXPERIMENT_PLAN §4).**",
        "> Computed by `scripts/phase5_comparison.py` from the SAVED run records (nothing typed by hand).",
        "> No winner is picked and strategies are NOT ranked by return or by number of trades (roadmap 5.7).",
        "",
        "## 1. Consistency proof",
        "",
        (
            f"Runs used: {sum(1 for r in recs if str(r.record['git_commit']).startswith('987c81c'))} from the S1/S2 report "
            f"(commit 987c81c) + {sum(1 for r in recs if str(r.record['git_commit']).startswith('8f3cf46'))} from the S3/S4 "
            "report (commit 8f3cf46). Within each ticker, every one of these is **identical** across all runs:"
        ),
        "",
        "| Field | AAPL | XOM |",
        "|---|---|---|",
    ]
    for what, read in SAME:
        lines.append(f"| {what} | " + " | ".join(str(read(s0[t].record)) for t in tickers) + " |")
    lines += [
        "| S0 benchmark final value (USD) | "
        + " | ".join(s0[t].record["summary"]["last_close_value_usd"] for t in tickers)
        + " |",
        "",
        "One difference by design: S3 and S4 runs also read a 2008–2009 **warm-up** file "
        + ", ".join(
            sorted(
                {
                    r.record["warmup_provenance"]["file_name"]
                    for r in recs
                    if r.record.get("warmup_provenance")
                }
            )
        )
        + " for indicators only. The S3/S4 report proved that S0/S1/S2 give identical results with warm-up rows present",
        '(66 of 66 to the cent). Every sell in every run is a full exit (size "all"), so round trips = number of sells.',
        "",
        "## 2. Roll-up per ticker (excess = strategy total return − S0 total return, percentage points, USD)",
        "",
    ]
    for t in tickers:
        lines += [f"**{t}** — S0 total return {s0[t].total_return:.2%}", "",
                  ("| Strategy | Settings tried | Beat S0 | Median excess | Best excess | Worst excess | Stranded at end | "
                  "Median % days in cash | Median round trips |"),
                  "|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
        for label in STRATEGY_ORDER:
            rs = [r for r in recs if r.ticker == t and r.label == label]
            ex = [r.total_return - s0[t].total_return for r in rs]
            lines.append(
                f"| {label} | {len(rs)} | {sum(e > 0 for e in ex)} | {pts(statistics.median(ex))} | {pts(max(ex))} | "
                f"{pts(min(ex))} | {sum(r.stranded for r in rs)} | {statistics.median(r.days_in_cash for r in rs):.0%} | "
                f"{statistics.median(r.round_trips for r in rs):g} |"
            )
        lines.append("")
    total = sum(tried.values())
    beat_all = {
        t: sum(
            r.total_return > s0[t].total_return for r in recs if r.ticker == t and r.label != "S0"
        )
        for t in tickers
    }
    lines += [
        "## 3. How many settings we tried — and why a win here is not evidence",
        "",
        f"Settings tried per stock: {total} ({', '.join(f'{k} {v}' for k, v in tried.items())}). "
        + "; ".join(f"{t}: {beat_all[t]} of {total} beat S0" for t in tickers)
        + ".",
        "",
        "In plain words: when you try 70 different settings on the same seven years of two stocks, some of them",
        "will beat buy-and-hold by luck alone — the same way that if 70 people each toss a coin ten times, a few",
        "will get eight heads. So a development-period win is a **hypothesis to test**, not evidence that the idea",
        "works. That is why the next step tests ALL settings (not just the ones that looked good) on new years",
        "(validation 2017–2020) and more stocks, with the rules fixed in advance (research/PREREGISTRATION.md).",
        "The large S4-S2 AAPL result rests on a few big dips (see the S3/S4 report) and gets no special treatment.",
        "",
        "## 4. Reproducibility check (5 saved configs chosen at random, seed 20261025, re-run from config.yaml)",
        "",
        "| Saved run | Final USD saved | Final USD re-run | Final AUD saved | Final AUD re-run | Identical |",
        "|---|---|---|---|---|---|",
        *[
            f"| {a} | {b} | {c} | {d} | {e} | {'yes' if ok else 'NO'} |"
            for a, b, c, d, e, ok in repro
        ],
        "",
        "Re-runs are kept under /data/runs/_reproductions/phase5_check_*/ (git-ignored).",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    from _help import handle_help  # --help: describe and exit, do nothing else

    handle_help(__doc__)
    sys.exit(main())
