"""Phase 6, Steps 6.1–6.6: report + verdicts for the VALIDATION runs, from the saved records only.

Run (after scripts/run_validation.py has finished):  uv run python scripts/report_validation.py
Applies the PRE-REGISTERED rules R1–R6 (research/PREREGISTRATION.md §5 + §9, tag prereg-v1.1) — nothing tuned.
Writes reports/experiments/validation_2017-2020.md — SUMMARY NUMBERS ONLY (no price or equity series).

Interpretations fixed in this script BEFORE any result was looked at (2026-10-25):
- R5: "3 most profitable round trips" = the 3 largest sells with realised P&L > 0 (a losing round trip is not
  "profitable"; removing one would raise the result). Fewer if a run has fewer profitable round trips.
- R4 "pass" = R1 and R2 both pass at the stress variant (wide spread + CommSec).
- Total return = value at the last close ÷ start cash − 1 (as in all Phase 5 reports).
- H2, H5, H6 have no pre-registered verdict rule → answered "not judged", with descriptive numbers only.
"""

import csv
import json
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from quant_research.metrics.performance import calendar_year_returns, max_drawdown

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS = PROJECT_ROOT / "data" / "runs" / "validation"
DEV_RUNS = PROJECT_ROOT / "data" / "runs"
REPORT = PROJECT_ROOT / "reports" / "experiments" / "validation_2017-2020.md"
TICKERS = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "T", "SPY"]
VARIANTS = ["main", "tight", "wide", "ibkr", "commsec", "whole", "stress"]
STRATEGIES = ["S1", "S2", "S3", "S4-S1", "S4-S2"]
LABELS = {
    "s0_buy_and_hold": "S0",
    "s1_profit_target": "S1",
    "s2_pullback": "S2",
    "s3_mean_reversion": "S3",
    "s4_trend_s1": "S4-S1",
    "s4_trend_s2": "S4-S2",
}
R2_NEEDED = {"S1": 10, "S2": 10, "S3": 4, "S4-S1": 10, "S4-S2": 10}
TRADE_LISTS = [("main", "S4-S2", "AAPL", ("0.02", "0.04")), ("main", "S1", "KO", ("0.03", "0.03"))]
DEV_COMMITS = {"987c81c": ("S0", "S1", "S2"), "8f3cf46": ("S0", "S3", "S4-S1", "S4-S2")}


@dataclass
class Run:
    variant: str
    label: str
    ticker: str
    setting: tuple
    start_cash: float
    final: float
    final_aud: float
    record: dict
    path: Path
    days: list = field(default_factory=list)
    values: list = field(default_factory=list)
    market: list = field(default_factory=list)
    cash: list = field(default_factory=list)
    fills: list = field(default_factory=list)

    @property
    def total_return(self) -> float:
        return self.final / self.start_cash - 1

    @property
    def mdd(self):
        return max_drawdown(self.days, self.values)

    @property
    def sells(self) -> list[float]:
        return [float(f["realised_pnl_usd"]) for f in self.fills if f["side"] == "sell"]

    @property
    def round_trips(self) -> int:
        return len(self.sells)

    @property
    def stranded(self) -> bool:
        return bool(self.fills) and self.fills[-1]["side"] == "sell"

    @property
    def days_in_cash(self) -> float:
        return sum(m == 0 for m in self.market) / len(self.market)

    def best3_removed_return(self) -> float:
        top = sorted((p for p in self.sells if p > 0), reverse=True)[:3]
        return (self.final - sum(top)) / self.start_cash - 1

    def year_returns(self) -> dict[int, float]:
        return calendar_year_returns(self.days, self.values, self.start_cash)


def setting_of(cfg: dict) -> tuple:
    if cfg.get("profit_target_x") not in (None, "None"):
        return (str(cfg["profit_target_x"]), str(cfg["rebuy_dip_y"]))
    if cfg.get("mr_k") not in (None, "None"):
        return (str(cfg["mr_k"]), str(cfg["mr_window"]))
    return ()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_runs() -> list[Run]:
    runs = []
    for path in sorted(RUNS.glob("*/*/run.json")):
        r = json.loads(path.read_text(encoding="utf-8"))
        cfg, s = r["config"], r["summary"]
        run = Run(path.parent.parent.name, LABELS[cfg["strategy"]], cfg["ticker"], setting_of(cfg),
                  float(s["start_cash_usd"]), float(s["last_close_value_usd"]),
                  float(s["end_aud_after_liquidation"]), r, path)  # fmt: skip
        for e in read_csv(path.parent / "equity.csv"):
            run.days.append(date.fromisoformat(e["day"]))
            run.values.append(float(e["total_value_usd"]))
            run.market.append(float(e["market_value_usd"]))
            run.cash.append(e["cash_usd"])
        run.fills = (
            read_csv(path.parent / "fills.csv")
            if (path.parent / "fills.csv").stat().st_size
            else []
        )
        runs.append(run)
    return runs


def checks(runs: list[Run]) -> list[str]:
    problems = []
    if len(runs) != 3976:
        problems.append(f"expected 3976 runs, found {len(runs)}")
    commits = {str(r.record["git_commit"]) for r in runs}
    if len(commits) != 1 or any(r.record["git_dirty"] for r in runs):
        problems.append(f"runs must come from ONE clean commit: {commits}")
    if any(r.days[-1] >= date(2021, 1, 1) or r.days[0] < date(2017, 1, 1) for r in runs):
        problems.append("a run has days outside 2017-01-01 … 2020-12-31")
    return problems


# ---------- the pre-registered rules ----------
def table(runs, variant):
    """(label, ticker) → {setting: run} and S0 per ticker for one variant."""
    by = defaultdict(dict)
    s0 = {}
    for r in runs:
        if r.variant != variant:
            continue
        if r.label == "S0":
            s0[r.ticker] = r
        else:
            by[(r.label, r.ticker)][r.setting] = r
    return by, s0


def r1_r2(by, s0, label, ret=lambda r: r.total_return):
    stocks_pass = sum(
        statistics.median(ret(r) - ret(s0[t]) for r in by[(label, t)].values()) > 0 for t in TICKERS
    )
    settings = sorted(by[(label, TICKERS[0])])
    settings_pass = sum(
        statistics.mean(ret(by[(label, t)][st]) - ret(s0[t]) for t in TICKERS) > 0
        for st in settings
    )
    return stocks_pass, settings_pass, len(settings)


def verdicts(runs):
    main_by, main_s0 = table(runs, "main")
    stress_by, stress_s0 = table(runs, "stress")
    out = {}
    for label in STRATEGIES:
        r1, r2, n_settings = r1_r2(main_by, main_s0, label)
        r1_pass, r2_pass = r1 >= 6, r2 >= R2_NEEDED[label]
        r3 = sum(
            statistics.median(
                (r.mdd.max_drawdown - main_s0[t].mdd.max_drawdown) * 100
                for r in main_by[(label, t)].values()
            )
            >= -5
            for t in TICKERS
        )
        s_r1, s_r2, _ = r1_r2(stress_by, stress_s0, label)
        r4_pass = s_r1 >= 6 and s_r2 >= R2_NEEDED[label]
        r4_note = "pass" if r4_pass else ("LOW-COST ONLY" if (r1_pass and r2_pass) else "fail")
        b_r1, b_r2, _ = r1_r2(main_by, main_s0, label, ret=lambda r: r.best3_removed_return())
        r5_pass = b_r1 >= 6 and b_r2 >= R2_NEEDED[label]
        r6 = sum(
            statistics.median(r.round_trips for r in main_by[(label, t)].values()) >= 10
            for t in TICKERS
        )
        r6_pass = r6 >= 6
        if r1 <= 3:
            verdict = "REJECTED"
        elif all([r1_pass, r2_pass, r3 >= 6, r4_pass, r5_pass, r6_pass]):
            verdict = "SUPPORTED"
        else:
            verdict = "INCONCLUSIVE" + ("" if r6_pass else " (too few trades)")
        out[label] = {"r1": r1, "r2": r2, "n": n_settings, "r3": r3, "r4": r4_note, "s_r1": s_r1, "s_r2": s_r2,
                          "r5": r5_pass, "b_r1": b_r1, "b_r2": b_r2, "r6": r6, "verdict": verdict}  # fmt: skip
    return out


# ---------- report ----------
def pct(x):
    return f"{x:.2%}"


def pts(x):
    return f"{x * 100:+.1f}"


def build(runs: list[Run]) -> str:
    v = verdicts(runs)
    main_by, s0 = table(runs, "main")
    L = [
        "# Validation 2017–2020 — S0 to S4 on 8 stocks (Phase 6, Steps 6.1–6.6)",
        "",
        "> **SIMULATED, HISTORICAL, VALIDATION PERIOD 2017–2020 — dress rehearsal for the final test; not proof of future profit.**",
        "> Rules: research/PREREGISTRATION.md §5 + §9 (tag `prereg-v1.1`, plus the logged CommSec cost correction made",
        "> before any run). All 3,976 runs from one clean commit. Summary numbers only (Tiingo licence). Generated by",
        "> `scripts/report_validation.py` from the saved records — nothing typed by hand.",
        "",
        "## 1. Verdicts (MAIN settings: Stake, normal spread, fractional, RBA FX, reinvest ≥ US$100)",
        "",
        (
            "| Strategy | R1 stocks (need ≥ 6/8) | R2 settings | R3 drawdown stocks (≥ 6/8) | R4 stress (R1/R2) | "
            "R5 best-3 removed (R1/R2) | R6 stocks with ≥ 10 trips (≥ 6/8) | VERDICT |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]
    for label in STRATEGIES:
        x = v[label]
        L.append(
            f"| {label} | {x['r1']}/8 | {x['r2']}/{x['n']} (need ≥ {R2_NEEDED[label]}) | {x['r3']}/8 | "
            f"{x['r4']} ({x['s_r1']}/8, {x['s_r2']}/{x['n']}) | {'pass' if x['r5'] else 'fail'} ({x['b_r1']}/8, "
            f"{x['b_r2']}/{x['n']}) | {x['r6']}/8 | **{x['verdict']}** |"
        )
    L += [
        "",
        "Verdict rule (pre-registered): SUPPORTED = R1–R6 all pass; REJECTED = R1 ≤ 3 of 8; INCONCLUSIVE = anything else",
        "(at most INCONCLUSIVE if R6 fails). R5 counts only round trips with realised P&L > 0 (interpretation fixed in",
        "the report script before results were seen).",
        "",
        "## 2. Per stock (MAIN) — S0 and each strategy vs S0 (excess = total return − S0 total return, pp USD)",
        "",
    ]
    for t in TICKERS:
        b = s0[t]
        L += [
            (
                f"**{t}** — S0: final US${b.final:,.2f} · AUD {b.final_aud:,.2f} · total {pct(b.total_return)} · "
                f"max DD {pct(b.mdd.max_drawdown)}"
            ),
            "",
            "| Strategy | Median excess | Best | Worst | Stranded | Median days in cash | Median round trips |",
            "|---|---|---|---|---|---|---|",
        ]
        for label in STRATEGIES:
            rs = list(main_by[(label, t)].values())
            ex = [r.total_return - b.total_return for r in rs]
            L.append(
                f"| {label} | {pts(statistics.median(ex))} | {pts(max(ex))} | {pts(min(ex))} | "
                f"{sum(r.stranded for r in rs)}/{len(rs)} | {statistics.median(r.days_in_cash for r in rs):.0%} | "
                f"{statistics.median(r.round_trips for r in rs):g} |"
            )
        L.append("")
    L += ["## 3. Parameter sensitivity (6.3) — excess vs S0 per setting (MAIN, pp)", ""]
    for label in STRATEGIES:
        settings = sorted(main_by[(label, TICKERS[0])])
        L += [f"**{label}** (rows = settings {'X/Y' if label != 'S3' else 'k/w'})", "",
              "| Setting | " + " | ".join(TICKERS) + " | Mean |", "|---|" + "---|" * (len(TICKERS) + 1)]  # fmt: skip
        for st in settings:
            ex = [main_by[(label, t)][st].total_return - s0[t].total_return for t in TICKERS]
            L.append(
                f"| {' / '.join(st)} | "
                + " | ".join(pts(e) for e in ex)
                + f" | {pts(statistics.mean(ex))} |"
            )
        L.append("")
    L += ["## 4. Cost sensitivity (6.4) — median excess vs S0 across all stocks × settings, per variant", "",
          "| Strategy | " + " | ".join(VARIANTS) + " |", "|---|" + "---|" * len(VARIANTS)]  # fmt: skip
    for label in STRATEGIES:
        cells = []
        for var in VARIANTS:
            by_v, s0_v = table(runs, var)
            ex = [
                r.total_return - s0_v[t].total_return
                for t in TICKERS
                for r in by_v[(label, t)].values()
            ]
            cells.append(pts(statistics.median(ex)))
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    s0_var = {var: table(runs, var)[1] for var in VARIANTS}
    L += ["", "S0 itself under each variant (median total return across the 8 stocks): "
          + ", ".join(f"{var} {pct(statistics.median(r.total_return for r in s0_var[var].values()))}" for var in VARIANTS) + "."]  # fmt: skip
    # regimes
    labels_by_year = {}
    for t in TICKERS:
        for year, ret in s0[t].year_returns().items():
            labels_by_year[(t, year)] = (
                "UP" if ret >= 0.10 else ("DOWN" if ret <= -0.10 else "SIDEWAYS")
            )
    L += ["", "## 5. Regimes (6.5) — year labels from S0 (≥ +10% UP, ≤ −10% DOWN, else SIDEWAYS; PREREGISTRATION §9)", "",
          "| Stock | " + " | ".join(str(y) for y in (2017, 2018, 2019, 2020)) + " |", "|---|---|---|---|---|"]  # fmt: skip
    for t in TICKERS:
        L.append(
            f"| {t} | "
            + " | ".join(labels_by_year[(t, y)] for y in (2017, 2018, 2019, 2020))
            + " |"
        )
    L += ["", "Median yearly excess vs S0 by regime (all stocks × settings × years of that regime, pp):", "",
          "| Strategy | UP | DOWN | SIDEWAYS |", "|---|---|---|---|"]  # fmt: skip
    for label in STRATEGIES:
        acc = defaultdict(list)
        for t in TICKERS:
            s0y = s0[t].year_returns()
            for r in main_by[(label, t)].values():
                for year, ret in r.year_returns().items():
                    acc[labels_by_year[(t, year)]].append(ret - s0y[year])
        L.append(
            f"| {label} | "
            + " | ".join(
                pts(statistics.median(acc[k])) if acc[k] else "—"
                for k in ("UP", "DOWN", "SIDEWAYS")
            )
            + " |"
        )
    regime_count = {
        k: sum(1 for x in labels_by_year.values() if x == k) for k in ("UP", "DOWN", "SIDEWAYS")
    }
    L += ["", f"Stock-years per regime: {regime_count}."]
    # reliability
    L += ["", "## 6. Reliability (6.6)", "", "**Dependence on a few trades** (runs with a gain; share of the total gain from the top 1 / top 3 profitable round trips, median):", "",
          "| Strategy | Runs with a gain | Top-1 share | Top-3 share |", "|---|---|---|---|"]  # fmt: skip
    for label in STRATEGIES:
        shares1, shares3 = [], []
        for t in TICKERS:
            for r in main_by[(label, t)].values():
                gain = r.final - r.start_cash
                top = sorted((p for p in r.sells if p > 0), reverse=True)
                if gain > 0 and top:
                    shares1.append(top[0] / gain)
                    shares3.append(sum(top[:3]) / gain)
        L.append(
            f"| {label} | {len(shares1)} | {statistics.median(shares1):.0%} | {statistics.median(shares3):.0%} |"
            if shares1
            else f"| {label} | 0 | — | — |"
        )
    L += ["", "**Consistency by year** (stocks, of 8, where the strategy's MEDIAN yearly excess vs S0 is > 0):", "",
          "| Strategy | 2017 | 2018 | 2019 | 2020 |", "|---|---|---|---|---|"]  # fmt: skip
    for label in STRATEGIES:
        cells = []
        for y in (2017, 2018, 2019, 2020):
            n = 0
            for t in TICKERS:
                s0y = s0[t].year_returns()[y]
                n += (
                    statistics.median(
                        r.year_returns()[y] - s0y for r in main_by[(label, t)].values()
                    )
                    > 0
                )
            cells.append(str(n))
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    L += dev_vs_validation(main_by, s0)
    L += [
        "",
        "## 7. Research questions (from the verdicts only)",
        "",
        f"- **H1** (sell after X% rise, rebuy after Y% dip beats buy-and-hold) → S1 verdict: **{v['S1']['verdict']}**.",
        (
            "- **H2** (better risk-adjusted result) → **not judged**: no pre-registered verdict rule for Sharpe/drawdown; R3 "
            f"(drawdown) counts are in §1 (S1 {v['S1']['r3']}/8, S2 {v['S2']['r3']}/8, S3 {v['S3']['r3']}/8, "
            f"S4-S1 {v['S4-S1']['r3']}/8, S4-S2 {v['S4-S2']['r3']}/8 stocks within 5 pp of S0)."
        ),
        (
            f"- **H3** (trend filter helps) → S4-S1: **{v['S4-S1']['verdict']}**, S4-S2: **{v['S4-S2']['verdict']}** "
            f"(plain S1: {v['S1']['verdict']}, S2: {v['S2']['verdict']})."
        ),
        f"- **H4** (mean reversion better than fixed %) → S3 verdict: **{v['S3']['verdict']}**.",
        "- **H5** (works in sideways/volatile regimes) → **not judged** (no pre-registered verdict rule); regime table in §5.",
        "- **H6** (depends on stock type) → **not judged** (no pre-registered verdict rule); per-stock tables in §2–§3.",
    ]
    L += appendix(runs, s0)
    return "\n".join(L) + "\n"


def dev_vs_validation(main_by, s0) -> list[str]:
    dev = defaultdict(dict)
    dev_s0 = {}
    for path in sorted(DEV_RUNS.glob("*/run.json")):
        r = json.loads(path.read_text(encoding="utf-8"))
        commit, label = str(r["git_commit"])[:7], LABELS[r["config"]["strategy"]]
        if commit not in DEV_COMMITS or label not in DEV_COMMITS[commit]:
            continue
        ret = (
            float(r["summary"]["last_close_value_usd"]) / float(r["summary"]["start_cash_usd"]) - 1
        )
        if label == "S0":
            dev_s0[r["config"]["ticker"]] = ret
        else:
            dev[(label, r["config"]["ticker"])][setting_of(r["config"])] = ret
    out = ["", "**Development 2010–2016 vs validation 2017–2020** (AAPL + XOM — the only stocks run in development):", "",
           "| Strategy | Stock | Dev: settings beating S0 | Val: settings beating S0 | Dev winners still beating S0 in val |",
           "|---|---|---|---|---|"]  # fmt: skip
    for label in STRATEGIES:
        for t in ("AAPL", "XOM"):
            d = {st: ret - dev_s0[t] for st, ret in dev[(label, t)].items()}
            val = {st: r.total_return - s0[t].total_return for st, r in main_by[(label, t)].items()}
            winners = [st for st, e in d.items() if e > 0]
            kept = sum(val[st] > 0 for st in winners)
            out.append(
                f"| {label} | {t} | {sum(e > 0 for e in d.values())}/{len(d)} | {sum(e > 0 for e in val.values())}/{len(val)} | "
                f"{kept}/{len(winners)} |"
            )
    return out


def appendix(runs, s0) -> list[str]:
    out = [
        "",
        "## Appendix A — S0 final values (validation, MAIN)",
        "",
        "| Stock | Start cash USD | Final USD (last close) | Final AUD |",
        "|---|---|---|---|",
    ]
    out += [
        f"| {t} | {s0[t].start_cash:,.2f} | {s0[t].final:,.2f} | {s0[t].final_aud:,.2f} |"
        for t in TICKERS
    ]
    for n, (var, label, t, st) in enumerate(TRADE_LISTS, start=1):
        r = next(
            x
            for x in runs
            if x.variant == var and x.label == label and x.ticker == t and x.setting == st
        )
        cash_by_day = dict(zip((d.isoformat() for d in r.days), r.cash, strict=True))
        out += ["", f"## Appendix {'BC'[n - 1]} — every trade of {label} {t} {' / '.join(st)} (validation, MAIN) — for an independent re-check", "",
                ("Our simulated fills. Reference open = that day's open_raw; fill = open × (1 ± 0.05%); fee = Stake US$3. "
                "'Cash at close' = cash at that day's close (= cash after the fill, unless a dividend arrived that day)."), "",
                "| # | Date | Side | Reference open | Fill price | Fee | Shares | Realised P&L | Cash at close |", "|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
        for i, f in enumerate(r.fills, start=1):
            out.append(f"| {i} | {f['day']} | {f['side']} | {f['reference_price_usd']} | {f['fill_price_usd']} | "
                       f"{f['fee_total_usd']} | {f['quantity']} | {f['realised_pnl_usd'] or '—'} | {cash_by_day[f['day']]} |")  # fmt: skip
        out.append(
            f"\nStart cash US${r.start_cash:,.2f}; final value at last close US${r.final:,.2f}; run `{r.path.parent.name}`."
        )
    commit = str(runs[0].record["git_commit"])[:7]
    out += [
        "",
        f"Code commit `{commit}` (dirty: False) for all 3,976 runs; records under /data/runs/validation/ (git-ignored).",
    ]
    return out


def main() -> int:
    runs = load_runs()
    problems = checks(runs)
    if problems:
        print("STOP —", problems)
        return 1
    REPORT.write_text(build(runs), encoding="utf-8")
    print(f"report written: {REPORT.relative_to(PROJECT_ROOT)} ({len(runs)} runs)")
    return 0


if __name__ == "__main__":
    from _help import handle_help  # --help: describe and exit, do nothing else

    handle_help(__doc__)
    sys.exit(main())
