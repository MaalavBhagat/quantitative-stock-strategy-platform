"""Read-only data shaping for the Streamlit dashboard (Phase 8). No maths of its own.

Every number comes from a saved run record (/data/runs/…), a saved report, or an existing function in
metrics/ or screening/. Anything not saved or computable by those is shown as NOT_AVAILABLE — never estimated.
D8: nothing dated ≥ 2021-01-01 may be loaded or shown (check_dates guards every table).
"""

import csv
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

from quant_research.metrics.performance import (
    cagr,
    drawdown_series,
    max_drawdown,
    round_trips,
    sharpe,
)
from quant_research.portfolio.money import to_display
from quant_research.strategies import labels

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = PROJECT_ROOT / "data" / "runs"
REPORTS_DIR = PROJECT_ROOT / "reports"
LOCK_DATE = date(2021, 1, 1)  # D8
# The one-time final test (research/FINAL_TEST_PREREG.md) may show 2021-01-04 … 2025-12-31 — on its own page only.
FINAL_LIMIT = date(2026, 1, 1)
BANNER = "SIMULATED, HISTORICAL — not financial advice"
DEMO_BANNER = "SIMULATED on MADE-UP prices — not historical, not a real stock, not financial advice"
DEMO_RUNS_DIR = (
    PROJECT_ROOT / "demo_output" / "runs" / "demo"
)  # written by scripts/demo.py (git-ignored)
NOT_AVAILABLE = "not available"
PERIODS = {
    "validation": "Validation period 2017-01-03 → 2020-12-31",
    "development": "Development period 2010-01-04 → 2016-12-30",
    "screen": "Screening years 2010–2020 (development + validation; point-in-time)",
    "final": "FINAL TEST 2021-01-04 → 2025-12-31 (run once, rules fixed in advance)",
    "demo": "DEMO — synthetic stock \"DEMO\" from scripts/demo.py",
}
LABELS = labels.IDS  # config strategy name → ID (display names: strategies/labels.py)
# The development records the reports use (same as scripts/report_validation.py DEV_COMMITS).
DEV_COMMITS = {"987c81c": ("S0", "S1", "S2"), "8f3cf46": ("S0", "S3", "S4-S1", "S4-S2")}


class LockedPeriodError(RuntimeError):
    """Something dated in the locked final-test period (≥ 2021-01-01, D8) was about to be shown."""


def check_dates(days: Iterable[date], what: str, limit: date = LOCK_DATE) -> None:
    late = [d for d in days if d >= limit]
    if late:
        raise LockedPeriodError(
            f"{what}: {len(late)} rows dated ≥ {limit} (first {min(late)}) — D8 lock"
        )


def banner(period: str) -> str:
    return f"{DEMO_BANNER if period == 'demo' else BANNER} · {PERIODS[period]}"


def show(value: Any, fmt: str = "{}") -> str:
    """Formatted value, or NOT_AVAILABLE for None."""
    return NOT_AVAILABLE if value is None else fmt.format(value)


def _csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def setting_of(cfg: dict[str, Any]) -> str:
    """Readable setting: 'X 2% / Y 4%', 'k 2.0 / w 20', or '—' for S0 (same fields as the reports)."""
    if cfg.get("profit_target_x") not in (None, "None"):
        return f"X {float(cfg['profit_target_x']):.0%} / Y {float(cfg['rebuy_dip_y']):.0%}"
    if cfg.get("mr_k") not in (None, "None"):
        return f"k {cfg['mr_k']} / w {cfg['mr_window']}"
    return "—"


@dataclass
class RunRecord:
    path: Path
    record: dict[str, Any]
    period: str
    equity: list[dict[str, str]] = field(default_factory=list)
    fills: list[dict[str, str]] = field(default_factory=list)
    orders: list[dict[str, str]] = field(default_factory=list)

    @property
    def config(self) -> dict[str, Any]:
        return self.record["config"]

    @property
    def summary(self) -> dict[str, Any]:
        return self.record["summary"]

    @property
    def label(self) -> str:
        return LABELS[self.config["strategy"]]

    @property
    def title(self) -> str:
        """'AAPL · Trend filter + pullback (S4-S2) · X 2% / Y 4%' — for page headings and reports."""
        return f"{self.ticker} · {labels.display(self.label)} · {self.setting}"

    @property
    def ticker(self) -> str:
        return self.config["ticker"]

    @property
    def setting(self) -> str:
        return setting_of(self.config)

    @property
    def days(self) -> list[date]:
        return [date.fromisoformat(e["day"]) for e in self.equity]

    @property
    def values(self) -> list[float]:
        return [float(e["total_value_usd"]) for e in self.equity]

    @property
    def fill_objects(self) -> list[SimpleNamespace]:
        """Fills as objects with .day / .side / .position_after — the shape metrics/ functions read."""
        return [
            SimpleNamespace(
                day=date.fromisoformat(f["day"]),
                side=f["side"],
                position_after=Decimal(f["position_after"]),
            )
            for f in self.fills
        ]

    @property
    def total_return(self) -> float:
        return (
            float(self.summary["last_close_value_usd"]) / float(self.summary["start_cash_usd"]) - 1
        )


def load_run(run_json: Path, period: str) -> RunRecord:
    """One saved run (run.json + equity / fills / orders CSVs). Raises LockedPeriodError on any date ≥ 2021 —
    or, for period "final" (the one-time final test), on any date ≥ 2026."""
    record = json.loads(run_json.read_text(encoding="utf-8"))
    run = RunRecord(
        run_json,
        record,
        period,
        _csv(run_json.parent / "equity.csv"),
        _csv(run_json.parent / "fills.csv"),
        _csv(run_json.parent / "orders.csv"),
    )
    limit = FINAL_LIMIT if period == "final" else LOCK_DATE
    check_dates(
        [date.fromisoformat(str(record["config"]["end"]))],
        f"{run_json.parent.name} config end",
        limit,
    )
    check_dates(run.days, f"{run_json.parent.name} equity", limit)
    check_dates(
        [date.fromisoformat(f["day"]) for f in run.fills], f"{run_json.parent.name} fills", limit
    )
    check_dates(
        [date.fromisoformat(o["created_day"]) for o in run.orders],
        f"{run_json.parent.name} orders",
        limit,
    )
    return run


def run_index(period: str, runs_dir: Path = RUNS_DIR) -> dict[tuple[str, str, str], Path]:
    """{(strategy label, ticker, setting): run.json} for the records the reports use."""
    out: dict[tuple[str, str, str], Path] = {}
    # Phase 9 records (C1 / C2 / E1 and their re-run twins) come AFTER the Phase 5 / 6 ones, so a twin key keeps the
    # earlier record (identical to the cent — Phase 9 twin consistency check).
    if period == "validation":
        paths = sorted((runs_dir / "validation" / "main").glob("*/run.json"))
        paths += sorted((runs_dir / "phase9" / "validation" / "main").glob("*/run.json"))
    elif period == "development":
        paths = sorted(runs_dir.glob("*/run.json"))
        paths += sorted((runs_dir / "phase9" / "development" / "main").glob("*/run.json"))
    elif period == "final":
        paths = sorted((runs_dir / "final" / "main").glob("*/run.json"))
    elif period == "demo":  # made-up data from scripts/demo.py — safe to show and publish
        paths = sorted(DEMO_RUNS_DIR.glob("*/run.json"))
    else:
        raise ValueError(f"unknown period {period!r}")
    for p in paths:
        r = json.loads(p.read_text(encoding="utf-8"))
        label = LABELS[r["config"]["strategy"]]
        if period == "development" and "phase9" not in p.parts:
            commit = str(r.get("git_commit"))[:7]
            if commit not in DEV_COMMITS or label not in DEV_COMMITS[commit]:
                continue
        key = (label, r["config"]["ticker"], setting_of(r["config"]))
        out.setdefault(
            key, p
        )  # first by run id (S0 dev exists under both commits with identical results)
    return out


def key_results(run: RunRecord, s0: RunRecord | None) -> dict[str, str]:
    """Key results, formatted. CAGR / drawdown / Sharpe via metrics/; everything else from the run summary."""
    s = run.summary
    days, values = run.days, run.values
    dd = max_drawdown(days, values)
    return {
        "Starting capital": f"AUD {float(s['initial_aud']):,.2f} → US${float(s['start_cash_usd']):,.2f} "
        f"(RBA {s['usd_per_aud_start']} USD per AUD, {s['usd_per_aud_start_for_day']})",
        "Test period": f"{days[0]} → {days[-1]} ({len(days)} trading days)",
        "Final value (last close, USD)": f"US${float(s['last_close_value_usd']):,.2f}",
        "Final value (AUD, after selling + FX)": f"AUD {float(s['end_aud_after_liquidation']):,.2f}",
        "Total return (USD)": f"{run.total_return:.2%}",
        "CAGR (USD)": f"{cagr(values[0], values[-1], days[0], days[-1]):.2%}",
        "Max drawdown": f"{dd.max_drawdown:.2%} ({dd.peak_day} → {dd.trough_day})",
        "Sharpe (risk-free 0%)": f"{sharpe(values):.2f}",
        "Excess vs S0 (pp, USD)": NOT_AVAILABLE
        if s0 is None
        else f"{(run.total_return - s0.total_return) * 100:+.1f}",
        "Round trips (sells)": str(round_trips(run.fill_objects)),
        "Fees total (USD)": f"US${float(s['total_fees_usd']):,.2f}",
        "Dividends net (USD, run total)": f"US${float(s['dividends_net_usd']):,.2f}",
    }


def assumptions(run: RunRecord) -> dict[str, str]:
    c, r = run.config, run.record
    files = [r.get("data_provenance"), r.get("warmup_provenance")]
    data = "; ".join(
        f"{p['file_name']} ({p['source']}, downloaded {p['downloaded_at_utc']})" for p in files if p
    )
    return {
        "Broker": str(c["broker"]),
        "Spread level": str(c["spread_level"]),
        "Share mode": str(c["share_mode"]),
        "FX source": f"{c['fx_source']} — files {', '.join(r.get('fx_files') or []) or NOT_AVAILABLE}",
        "Reinvest rule": f"dividends reinvested only when cash ≥ US${c['reinvest_min_cash_usd']}",
        "Minimum order": f"US${c['min_order_usd']}",
        "Data files": data or NOT_AVAILABLE,
        "Code commit": f"{r.get('git_commit')} (dirty: {r.get('git_dirty')})",
        "Run id": str(r["run_id"]),
    }


def equity_table(run: RunRecord, usd_per_aud: Any = None) -> pd.DataFrame:
    """Daily total / cash / invested (USD), drawdown (metrics.drawdown_series) and AUD if an FX series is given."""
    df = pd.DataFrame(
        {
            "day": pd.to_datetime([e["day"] for e in run.equity]),
            "total_usd": run.values,
            "cash_usd": [float(e["cash_usd"]) for e in run.equity],
            "invested_usd": [float(e["market_value_usd"]) for e in run.equity],
        }
    )
    df["drawdown"] = drawdown_series(run.values)
    if usd_per_aud is not None:
        df["total_aud"] = [
            v / float(usd_per_aud.on(d)) for d, v in zip(run.days, run.values, strict=True)
        ]
    return df


def costs_table(run: RunRecord) -> pd.DataFrame:
    """Cumulative fees and spread cost by fill day (from fills.csv). Dividends per day are not saved."""
    rows = [
        (pd.Timestamp(f["day"]), float(f["fee_total_usd"]), float(f["spread_cost_usd"]))
        for f in run.fills
    ]
    df = pd.DataFrame(rows, columns=["day", "fee_usd", "spread_usd"])
    df["cumulative_fees_usd"] = df["fee_usd"].cumsum()
    df["cumulative_spread_usd"] = df["spread_usd"].cumsum()
    return df


NOT_APPLICABLE = "—"  # e.g. realised P&L on a buy (nothing was sold) — different from missing data


def cents(text: str) -> str:
    """Money for DISPLAY: cents, ROUND_HALF_EVEN (portfolio.money.to_display, PROJECT_GUIDE §4)."""
    return f"{to_display(Decimal(text)):,.2f}"


def shares6(text: str) -> str:
    return f"{Decimal(text):.6f}"


def fills_table(run: RunRecord) -> pd.DataFrame:
    """Fills for display: money in cents, shares 6 dp, prices exactly as stored; P&L on buys = "—"."""
    cols = {
        "day": "date",
        "side": "side",
        "quantity": "shares",
        "reference_price_usd": "reference open (USD)",
        "fill_price_usd": "fill (USD)",
        "fee_total_usd": "fee (USD)",
        "spread_cost_usd": "spread cost (USD)",
        "realised_pnl_usd": "realised P&L (USD)",
        "position_after": "position after",
    }
    df = pd.DataFrame(run.fills, columns=list(cols)).rename(columns=cols)
    for c in ("fee (USD)", "spread cost (USD)"):
        df[c] = df[c].map(cents)
    df["realised P&L (USD)"] = df["realised P&L (USD)"].map(
        lambda v: cents(v) if v else NOT_APPLICABLE
    )
    for c in ("shares", "position after"):
        df[c] = df[c].map(shares6)
    return df


def orders_table(run: RunRecord) -> pd.DataFrame:
    df = pd.DataFrame(
        run.orders, columns=["created_day", "intended_day", "side", "size", "status", "reason"]
    )
    return df.replace("", "—")


def trade_effect(run: RunRecord, i: int) -> dict[str, str]:
    """Cash and position before / after fill i — read from the saved files (cash at closes, position_after)."""
    fill = run.fills[i]
    day = date.fromisoformat(fill["day"])
    pos_before = run.fills[i - 1]["position_after"] if i > 0 else "0"
    by_day = {date.fromisoformat(e["day"]): e for e in run.equity}
    prior = [d for d in by_day if d < day]
    return {
        "Trade": f"{fill['side']} {fill['quantity']} shares on {day} at US${float(fill['fill_price_usd']):,.4f}",
        "Position before → after": f"{pos_before} → {fill['position_after']}",
        "Cash at the previous close (USD)": show(
            float(by_day[max(prior)]["cash_usd"]) if prior else None, "US${:,.2f}"
        ),
        "Cash at this day's close (USD)": show(
            float(by_day[day]["cash_usd"]) if day in by_day else None, "US${:,.2f}"
        ),
        "Note": "cash at the close = cash after the fill, unless a dividend arrived that day",
    }


def named_verdict_table() -> str:
    """The saved verdict table for display: each strategy ID with its plain-English name."""
    return labels.name_ids(verdict_table())


def verdict_table(report: Path = REPORTS_DIR / "experiments" / "validation_2017-2020.md") -> str:
    """The pre-registered verdict table, copied as saved in the validation report §1 (not recomputed)."""
    text = report.read_text(encoding="utf-8")
    start = text.index("## 1. Verdicts")
    end = text.index("\n## 2.", start)
    return text[start:end].split("\n", 1)[1].strip()  # without the report's own heading line


# ---------- company research (Step 8.2) — existing screening functions only ----------
SEC_DIR = PROJECT_ROOT / "data" / "raw" / "sec"
COMPANIES = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "T"]
SCREEN_DATES = [date(y, 12, 31) for y in range(2010, 2021)]


@dataclass(frozen=True)
class CompanyYear:
    as_of: date
    ten_k: str  # fiscal-year end / filed, or NOT_AVAILABLE
    quality: float | None
    subscores: dict[str, float]
    why: str
    problems: list[str]  # MISSING / CONFLICT inputs with the reason saved by screening/fundamentals


def screening_rows(sec_dir: Path = SEC_DIR) -> dict[str, list[CompanyYear]]:
    """Per company, per 31 Dec 2010…2020: score, sub-scores, why line and input problems (screening.score)."""
    from quant_research.screening.score import INPUTS, indicators_on, quality_scores

    cfs = {}
    for t in COMPANIES:
        [path] = sorted(sec_dir.glob(f"{t}_CIK*_filed-to-2020-12-31.json"))
        cfs[t] = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[CompanyYear]] = {t: [] for t in COMPANIES}
    for d in SCREEN_DATES:
        got = {t: indicators_on(cfs[t], d) for t in COMPANIES}
        scores = quality_scores({t: ind for t, (_, ind) in got.items()})
        for t in COMPANIES:
            fy, ind = got[t]
            problems = []
            for k, (label, _) in INPUTS.items():
                i = ind.get(k)
                if i is None:
                    problems.append(f"{label}: no 10-K filed before {d}")
                elif i.status in ("MISSING", "CONFLICT"):
                    reason = i.note or "; ".join(
                        f"{c.concept} {c.status}: {c.note}" for c in i.components
                    )
                    problems.append(f"{label}: {i.status} — {reason}")
            sc = scores[t]
            out[t].append(
                CompanyYear(
                    d,
                    NOT_AVAILABLE if fy is None else f"FY end {fy.end}, filed {fy.filed}",
                    sc.quality,
                    sc.subscores,
                    sc.why,
                    problems,
                )
            )
    return out


def trading_profile(ticker: str) -> pd.DataFrame:
    """Step 7.2 indicators per calendar year 2010–2020 (screening.trading on the saved Tiingo files)."""
    from quant_research.data.loader import load_prices, load_prices_with_warmup
    from quant_research.screening.trading import year_indicators

    dev = load_prices_with_warmup(ticker, date(2008, 1, 1), date(2010, 1, 1), date(2016, 12, 31))
    df = pd.concat(
        [dev, load_prices(ticker, date(2017, 1, 1), date(2020, 12, 31))], ignore_index=True
    )
    check_dates(df["date"], f"{ticker} prices")
    rows = [year_indicators(df, y) for y in range(2010, 2021)]
    return pd.DataFrame(
        {
            "year": [r.year for r in rows],
            "volatility": [show(r.volatility_annualised, "{:.2%}") for r in rows],
            "median $ volume (US$ m)": [f"{r.median_dollar_volume_usd / 1e6:,.0f}" for r in rows],
            "median daily range": [f"{r.median_daily_range:.2%}" for r in rows],
            "max drawdown (price)": [f"{r.max_drawdown:.2%}" for r in rows],
            "dividend yield (TTM)": [show(r.dividend_yield_ttm, "{:.2%}") for r in rows],
        }
    )


PHASE9_REPORT = REPORTS_DIR / "experiments" / "phase9_information_2017-2020.md"
FINAL_REPORT = REPORTS_DIR / "experiments" / "FINAL_TEST_2021-2025.md"


def final_verdict_table() -> str:
    """Both verdict tables of the final test, copied as saved (not recomputed)."""
    return verdict_table(FINAL_REPORT)


PHASE9_IDS = ("C1", "C2", "E1")


def phase9_verdict_table() -> str:
    """The Phase 9 verdict table (each information strategy vs its twin), copied as saved (not recomputed)."""
    return verdict_table(PHASE9_REPORT)


def verdict_source(label: str, period: str = "validation") -> str:
    if period == "final":
        return (
            "reports/experiments/FINAL_TEST_2021-2025.md §1 (rules: research/FINAL_TEST_PREREG.md)"
        )
    if label in PHASE9_IDS:
        return "reports/experiments/phase9_information_2017-2020.md §1 (rules: research/PREREGISTRATION_V2.md)"
    return "reports/experiments/validation_2017-2020.md §1 (rules: research/PREREGISTRATION.md)"


def verdict_for(label: str, period: str = "validation") -> str | None:
    """The saved verdict table reduced to its header + this strategy's row (None for S0 — the benchmark).

    Validation — S1–S4: Phase 6 table (vs S0); C1 / C2 / E1: Phase 9 table (vs their twin), row 'Name (ID) (vs …)'.
    Final: the final-test tables (every row 'Name (ID) (vs …)')."""
    if label == "S0":
        return None
    final = period == "final"
    phase9 = final or label in PHASE9_IDS  # rows written as 'Name (ID) (vs …)'
    report = FINAL_REPORT if final else (PHASE9_REPORT if label in PHASE9_IDS else None)
    if report is not None and not report.exists():
        return None
    lines = verdict_table(
        report if report is not None else REPORTS_DIR / "experiments" / "validation_2017-2020.md"
    ).splitlines()
    table = [ln for ln in lines if ln.startswith("|")]
    first = [ln.split("|")[1].strip() for ln in table]
    row = [
        ln
        for ln, cell in zip(table[2:], first[2:], strict=True)
        if (cell.split(" (vs ")[0].endswith(f"({label})") if phase9 else cell == label)
    ]
    return "\n".join([table[0], table[1], *row]) if row else None
