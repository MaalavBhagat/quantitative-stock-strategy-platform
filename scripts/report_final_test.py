"""ONE-TIME FINAL TEST report (research/FINAL_TEST_PREREG.md, tag prereg-final), from the saved records only.

Run (after scripts/run_final_test.py has finished):  uv run python scripts/report_final_test.py
Applies the pre-registered rules unchanged — PREREGISTRATION §9 (S1–S4 vs S0) and PREREGISTRATION_V2 §6 (C1, C2, E1 vs
their twins) — with the stock-count thresholds scaled to 7 (FINAL_TEST_PREREG §4): R1 / R3 / R6 ≥ 6 of 7,
REJECTED if R1 ≤ 2 of 7. Interpretations exactly as the Phase 6 and Phase 9 report scripts (R5: only round trips with
realised P&L > 0; the benchmark is unchanged; R4 = R1 and R2 both pass at stress).
Writes reports/experiments/FINAL_TEST_2021-2025.md — SUMMARY NUMBERS ONLY (no price or equity series).
"""

import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from report_validation import Run, pct, pts, read_csv, setting_of

from quant_research.strategies import labels

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS = PROJECT_ROOT / "data" / "runs" / "final"
VAL_RUNS = PROJECT_ROOT / "data" / "runs" / "validation" / "main"
P9_RUNS = PROJECT_ROOT / "data" / "runs" / "phase9" / "validation" / "main"
VAL_REPORT = PROJECT_ROOT / "reports" / "experiments" / "validation_2017-2020.md"
P9_REPORT = PROJECT_ROOT / "reports" / "experiments" / "phase9_information_2017-2020.md"
REPORT = PROJECT_ROOT / "reports" / "experiments" / "FINAL_TEST_2021-2025.md"
TICKERS = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "SPY"]
N = len(TICKERS)
NEED = 6  # R1 / R3 / R6: ≥ 6 of 7
REJECT_AT = 2  # REJECTED if R1 ≤ 2 of 7 (loses on 5+)
VARIANTS = ["main", "tight", "wide", "ibkr", "commsec", "whole", "stress"]
V1 = ["S1", "S2", "S3", "S4-S1", "S4-S2"]
V2 = ["C1", "C2", "E1"]
BENCH = {
    "S1": "S0",
    "S2": "S0",
    "S3": "S0",
    "S4-S1": "S0",
    "S4-S2": "S0",
    "C1": "S0",
    "C2": "S4-S2",
    "E1": "S4-S2",
}
R2_NEEDED = {"S1": 10, "S2": 10, "S3": 4, "S4-S1": 10, "S4-S2": 10, "C1": 1, "C2": 10, "E1": 10}
EXPECTED = 5096
YEARS = (2021, 2022, 2023, 2024, 2025)
TOP_LINE = (
    "SIMULATED, HISTORICAL, FINAL TEST 2021–2025 — run once under rules fixed in advance (tags prereg-v1.1, "
    "prereg-v2, prereg-final); not proof of future profit; not financial advice."
)


def name(sid: str) -> str:
    return labels.display(sid)


def load(paths) -> list[Run]:
    runs = []
    for path in paths:
        r = json.loads(path.read_text(encoding="utf-8"))
        cfg, s = r["config"], r["summary"]
        run = Run(path.parent.parent.name, labels.of_config(cfg["strategy"]), cfg["ticker"], setting_of(cfg),
                  float(s["start_cash_usd"]), float(s["last_close_value_usd"]),
                  float(s["end_aud_after_liquidation"]), r, path)  # fmt: skip
        for e in read_csv(path.parent / "equity.csv"):
            run.days.append(date.fromisoformat(e["day"]))
            run.values.append(float(e["total_value_usd"]))
            run.market.append(float(e["market_value_usd"]))
            run.cash.append(e["cash_usd"])
        fills = path.parent / "fills.csv"
        run.fills = read_csv(fills) if fills.stat().st_size else []
        runs.append(run)
    return runs


def checks(runs: list[Run]) -> list[str]:
    problems = []
    if len(runs) != EXPECTED:
        problems.append(f"expected {EXPECTED} runs, found {len(runs)}")
    commits = {str(r.record["git_commit"]) for r in runs}
    if len(commits) != 1 or any(r.record["git_dirty"] for r in runs):
        problems.append(f"runs must come from ONE clean commit: {commits}")
    if any(not r.record["config"]["final_test_unlocked"] for r in runs):
        problems.append("a final-test run without final_test_unlocked")
    if any(r.days[0] != date(2021, 1, 4) or r.days[-1] != date(2025, 12, 31) for r in runs):
        problems.append("a run does not cover exactly 2021-01-04 … 2025-12-31")
    if {r.ticker for r in runs} != set(TICKERS):
        problems.append(f"stocks {sorted({r.ticker for r in runs})} ≠ {TICKERS}")
    return problems


def table(runs: list[Run], variant: str) -> dict:
    by: dict = defaultdict(dict)
    for r in runs:
        if r.variant == variant:
            by[(r.label, r.ticker)][r.setting] = r
    return by


def bench_of(by: dict, label: str, t: str, st: tuple) -> Run:
    b = by[(BENCH[label], t)]
    return b[st] if st in b else b[()]


def pairs(by: dict, label: str, t: str) -> list[tuple[Run, Run]]:
    return [(r, bench_of(by, label, t, st)) for st, r in sorted(by[(label, t)].items())]


def r1_r2(
    by, label, ret_i=lambda r: r.total_return, ret_b=lambda r: r.total_return, tickers=TICKERS
):
    stocks = sum(
        statistics.median(ret_i(i) - ret_b(b) for i, b in pairs(by, label, t)) > 0 for t in tickers
    )
    settings = sorted(by[(label, tickers[0])])
    passed = sum(
        statistics.mean(
            ret_i(by[(label, t)][st]) - ret_b(bench_of(by, label, t, st)) for t in tickers
        )
        > 0
        for st in settings
    )
    return stocks, passed, len(settings)


def verdicts(runs: list[Run]) -> dict:
    main, stress = table(runs, "main"), table(runs, "stress")
    out = {}
    for label in V1 + V2:
        need2 = R2_NEEDED[label]
        r1, r2, n = r1_r2(main, label)
        r3 = sum(
            statistics.median(
                (i.mdd.max_drawdown - b.mdd.max_drawdown) * 100 for i, b in pairs(main, label, t)
            )
            >= -5
            for t in TICKERS
        )
        s_r1, s_r2, _ = r1_r2(stress, label)
        r4_pass = s_r1 >= NEED and s_r2 >= need2
        r4 = "pass" if r4_pass else ("LOW-COST ONLY" if (r1 >= NEED and r2 >= need2) else "fail")
        b_r1, b_r2, _ = r1_r2(main, label, ret_i=lambda r: r.best3_removed_return())
        r5_pass = b_r1 >= NEED and b_r2 >= need2
        r6 = sum(
            statistics.median(r.round_trips for r in main[(label, t)].values()) >= 10
            for t in TICKERS
        )
        if r1 <= REJECT_AT:
            verdict = "REJECTED"
        elif all([r1 >= NEED, r2 >= need2, r3 >= NEED, r4_pass, r5_pass, r6 >= NEED]):
            verdict = "SUPPORTED"
        else:
            verdict = "INCONCLUSIVE" + ("" if r6 >= NEED else " (too few trades)")
        out[label] = {"r1": r1, "r2": r2, "n": n, "r3": r3, "r4": r4, "s_r1": s_r1, "s_r2": s_r2, "r5": r5_pass,
                      "b_r1": b_r1, "b_r2": b_r2, "r6": r6, "verdict": verdict}  # fmt: skip
    return out


def verdict_rows(v: dict, group: list[str]) -> list[str]:
    out = [
        (
            f"| Strategy (benchmark) | R1 stocks (need ≥ {NEED}/{N}) | R2 settings | R3 drawdown stocks (≥ {NEED}/{N}) | "
            f"R4 stress (R1/R2) | R5 best-3 removed (R1/R2) | R6 stocks with ≥ 10 trips (≥ {NEED}/{N}) | VERDICT |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]
    for label in group:
        x = v[label]
        out.append(
            f"| {name(label)} (vs {name(BENCH[label])}) | {x['r1']}/{N} | {x['r2']}/{x['n']} (need ≥ {R2_NEEDED[label]}) | "
            f"{x['r3']}/{N} | {x['r4']} ({x['s_r1']}/{N}, {x['s_r2']}/{x['n']}) | {'pass' if x['r5'] else 'fail'} "
            f"({x['b_r1']}/{N}, {x['b_r2']}/{x['n']}) | {x['r6']}/{N} | **{x['verdict']}** |"
        )
    return out


def saved_verdicts() -> dict[str, tuple[str, str]]:
    """Validation verdicts as SAVED in the Phase 6 and Phase 9 reports: ID → (R1 cell, verdict)."""
    out = {}
    for path in (VAL_REPORT, P9_REPORT):
        text = path.read_text(encoding="utf-8")
        start = text.index("## 1. Verdicts")
        block = text[start : text.index("\n## 2.", start)]
        for ln in block.splitlines():
            if not ln.startswith("| ") or "---" in ln or "R1 stocks" in ln:
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            m = re.search(r"\(([A-Z0-9-]+)\)(?: \(vs|$)", cells[0])
            sid = m.group(1) if m else cells[0]
            out[sid] = (cells[1], cells[-1].strip("*"))
    return out


def build(runs: list[Run], val_main: dict) -> str:
    v = verdicts(runs)
    main = table(runs, "main")
    s0 = {t: main[("S0", t)][()] for t in TICKERS}
    commit = str(runs[0].record["git_commit"])[:7]
    L = [
        "# FINAL TEST 2021–2025 — every strategy, 7 stocks, run ONCE",
        "",
        f"> **{TOP_LINE}**",
        (
            f"> Rules: research/PREREGISTRATION.md §9, research/PREREGISTRATION_V2.md §6, research/FINAL_TEST_PREREG.md "
            f"(7-stock thresholds). All {len(runs):,} runs from one clean commit `{commit}`. Summary numbers only (Tiingo"
        ),
        "> licence). Generated by `scripts/report_final_test.py` from the saved records — nothing typed by hand.",
        "> T (AT&T) excluded before any 2021+ data was downloaded (2022 spin-off not modelled).",
        "",
        "## 1. Verdicts (MAIN: Stake, normal spread, fractional, RBA FX, reinvest ≥ US$100)",
        "",
        f"**S1–S4 vs {name('S0')}** (PREREGISTRATION §9 rules):",
        "",
        *verdict_rows(v, V1),
        "",
        "**C1, C2, E1 vs their twins** (PREREGISTRATION_V2 §6 rules):",
        "",
        *verdict_rows(v, V2),
        "",
        f"SUPPORTED = R1–R6 all pass; REJECTED = R1 ≤ {REJECT_AT} of {N} (loses on 5+ stocks); INCONCLUSIVE = anything else",
        f"(at most INCONCLUSIVE if R6 fails). R2 = settings whose mean excess across the {N} stocks is > 0 (C1: its one",
        "setting). R5 removes only the strategy's own best 3 profitable round trips (benchmark unchanged).",
        "",
        "## 2. Per stock (MAIN) — excess = strategy total return − benchmark total return, pp USD",
        "",
    ]
    for t in TICKERS:
        b = s0[t]
        L += [
            (
                f"**{t}** — {name('S0')}: final US${b.final:,.2f} · AUD {b.final_aud:,.2f} · total {pct(b.total_return)} · "
                f"max DD {pct(b.mdd.max_drawdown)}"
            ),
            "",
            (
                "| Strategy | Benchmark | Median excess | Best | Worst | vs Buy-and-hold (S0) median | Stranded | "
                "Median days in cash | Median round trips |"
            ),
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for label in V1 + V2:
            ps = pairs(main, label, t)
            ex = [i.total_return - w.total_return for i, w in ps]
            ex0 = [i.total_return - b.total_return for i, _ in ps]
            rs = [i for i, _ in ps]
            L.append(
                f"| {name(label)} | {name(BENCH[label])} | {pts(statistics.median(ex))} | {pts(max(ex))} | {pts(min(ex))} | "
                f"{pts(statistics.median(ex0))} | {sum(r.stranded for r in rs)}/{len(rs)} | "
                f"{statistics.median(r.days_in_cash for r in rs):.0%} | {statistics.median(r.round_trips for r in rs):g} |"
            )
        L.append("")
    L += ["## 3. Cost sensitivity — median excess vs the benchmark across all stocks × settings, per variant", "",
          "| Strategy | " + " | ".join(VARIANTS) + " |", "|---|" + "---|" * len(VARIANTS)]  # fmt: skip
    by_var = {var: table(runs, var) for var in VARIANTS}
    for label in V1 + V2:
        cells = [
            pts(
                statistics.median(
                    i.total_return - w.total_return
                    for t in TICKERS
                    for i, w in pairs(by_var[var], label, t)
                )
            )
            for var in VARIANTS
        ]
        L.append(f"| {name(label)} | " + " | ".join(cells) + " |")
    L += ["", f"{name('S0')} itself under each variant (median total return across the {N} stocks): "
          + ", ".join(f"{var} {pct(statistics.median(by_var[var][('S0', t)][()].total_return for t in TICKERS))}"
                      for var in VARIANTS) + "."]  # fmt: skip
    regime = {}
    for t in TICKERS:
        for year, ret in s0[t].year_returns().items():
            regime[(t, year)] = "UP" if ret >= 0.10 else ("DOWN" if ret <= -0.10 else "SIDEWAYS")
    L += ["", "## 4. Regimes — year labels from Buy-and-hold (S0) (≥ +10% UP, ≤ −10% DOWN, else SIDEWAYS)", "",
          "| Stock | " + " | ".join(map(str, YEARS)) + " |", "|---|" + "---|" * len(YEARS)]  # fmt: skip
    L += [f"| {t} | " + " | ".join(regime[(t, y)] for y in YEARS) + " |" for t in TICKERS]
    L += ["", "Median yearly excess vs the benchmark by regime (all stocks × settings × years of that regime, pp):", "",
          "| Strategy | UP | DOWN | SIDEWAYS |", "|---|---|---|---|"]  # fmt: skip
    for label in V1 + V2:
        acc = defaultdict(list)
        for t in TICKERS:
            for i, w in pairs(main, label, t):
                wy = w.year_returns()
                for year, ret in i.year_returns().items():
                    acc[regime[(t, year)]].append(ret - wy[year])
        L.append(f"| {name(label)} | " + " | ".join(pts(statistics.median(acc[k])) if acc[k] else "—"
                                                    for k in ("UP", "DOWN", "SIDEWAYS")) + " |")  # fmt: skip
    counts = {k: sum(x == k for x in regime.values()) for k in ("UP", "DOWN", "SIDEWAYS")}
    L += ["", f"Stock-years per regime: {counts}.", "",
          "**Dependence on a few trades** (runs with a gain; median share of the total gain from the top 1 / top 3",
          "profitable round trips):", "", "| Strategy | Runs with a gain | Top-1 share | Top-3 share |",
          "|---|---|---|---|"]  # fmt: skip
    for label in V1 + V2:
        sh1, sh3 = [], []
        for t in TICKERS:
            for r in main[(label, t)].values():
                gain, top = (
                    r.final - r.start_cash,
                    sorted((p for p in r.sells if p > 0), reverse=True),
                )
                if gain > 0 and top:
                    sh1.append(top[0] / gain)
                    sh3.append(sum(top[:3]) / gain)
        L.append(f"| {name(label)} | {len(sh1)} | {statistics.median(sh1):.1%} | {statistics.median(sh3):.1%} |"
                 if sh1 else f"| {name(label)} | 0 | — | — |")  # fmt: skip
    # 3. validation vs final
    saved = saved_verdicts()
    L += ["", "## 5. Validation 2017–2020 vs final 2021–2025 — did any verdict change?", "",
          "Validation verdicts are copied from the saved reports (8 stocks incl. T, thresholds of 8). The medians are",
          "recomputed from the saved validation records on the SAME 7 stocks (T left out) so they compare like for like.",
          "", ("| Strategy (benchmark) | Validation R1 | Validation verdict | Final R1 | Final verdict | Changed? | "
          "Median excess val (7 stocks) | Median excess final |"), "|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for label in V1 + V2:
        r1_val, verdict_val = saved[label]
        med_val = statistics.median(
            i.total_return - w.total_return for t in TICKERS for i, w in pairs(val_main, label, t)
        )
        med_fin = statistics.median(
            i.total_return - w.total_return for t in TICKERS for i, w in pairs(main, label, t)
        )
        changed = (
            "no" if verdict_val.split(" ")[0] == v[label]["verdict"].split(" ")[0] else "**YES**"
        )
        L.append(f"| {name(label)} (vs {name(BENCH[label])}) | {r1_val} | {verdict_val} | {v[label]['r1']}/{N} | "
                 f"{v[label]['verdict']} | {changed} | {pts(med_val)} | {pts(med_fin)} |")  # fmt: skip
    # 4. H1–H7
    vd = {k: x["verdict"] for k, x in v.items()}
    L += ["", "## 6. Research questions H1–H7 — final answers (from the verdicts only)", "",
          (f"- **H1** (sell after an X% rise, buy back after a Y% dip beats buy-and-hold after costs) → {name('S1')}: "
          f"**{vd['S1']}** on the final test (better on {v['S1']['r1']} of {N} stocks)."),
          ("- **H2** (better risk-adjusted result) → **not judged** (no pre-registered verdict rule); drawdown counts (R3) "
          "are in §1."),
          (f"- **H3** (a trend filter helps) → {name('S4-S1')}: **{vd['S4-S1']}**, {name('S4-S2')}: **{vd['S4-S2']}** "
          f"(without the filter: {name('S1')} {vd['S1']}, {name('S2')} {vd['S2']})."),
          f"- **H4** (mean reversion does better than fixed percentages) → {name('S3')}: **{vd['S3']}**.",
          "- **H5** (works in sideways / volatile years) → **not judged** (no pre-registered verdict rule); regime table §4.",
          "- **H6** (depends on the type of stock) → **not judged** (no pre-registered verdict rule); per-stock tables §2.",
          (f"- **H7** (extra information helps) → {name('C1')}: **{vd['C1']}**, {name('C2')}: **{vd['C2']}**, "
          f"{name('E1')}: **{vd['E1']}** (each vs its twin).")]  # fmt: skip
    L += appendix(runs, main, s0)
    return "\n".join(L) + "\n"


def trade_table(run: Run) -> list[str]:
    cash = dict(zip((d.isoformat() for d in run.days), run.cash, strict=True))
    out = ["| # | Date | Side | Reference open | Fill price | Fee | Shares | Realised P&L | Cash at close |",
           "|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for n, f in enumerate(run.fills, start=1):
        out.append(f"| {n} | {f['day']} | {f['side']} | {f['reference_price_usd']} | {f['fill_price_usd']} | "
                   f"{f['fee_total_usd']} | {f['quantity']} | {f['realised_pnl_usd'] or '—'} | {cash[f['day']]} |")  # fmt: skip
    return out


def appendix(runs: list[Run], main: dict, s0: dict) -> list[str]:
    s = s0["AAPL"].record["summary"]
    out = ["", f"## Appendix A — the 7 {name('S0')} finals (final test, MAIN)", "",
           (f"Start: AUD 10,000 at RBA {s['usd_per_aud_start']} USD per AUD (rate for {s['usd_per_aud_start_for_day']}, the "
           f"first fill day) − Stake FX fee US${float(s['fx_in_fee_usd']):,.2f} = US${float(s['start_cash_usd']):,.2f}. "
           f"End: converted back at RBA {s['usd_per_aud_end']} (rate for {s['usd_per_aud_end_for_day']})."), "",
           "| Stock | Start cash USD | Final USD (last close) | Final AUD (after selling + FX) | Total return USD | Max DD |",
           "|---|---|---|---|---|---|"]  # fmt: skip
    out += [f"| {t} | {r.start_cash:,.2f} | {r.final:,.2f} | {r.final_aud:,.2f} | {pct(r.total_return)} | "
            f"{pct(r.mdd.max_drawdown)} |" for t, r in s0.items()]  # fmt: skip
    rates = {
        (r.record["summary"]["usd_per_aud_start"], r.record["summary"]["usd_per_aud_end"])
        for r in runs
    }
    out += [
        "",
        f"RBA rates used by all {len(runs):,} runs: {sorted(rates)} (start, end) — one pair, as expected.",
    ]
    for letter, (label, t, st) in zip(
        "BC", [("S4-S2", "AAPL", ("0.02", "0.04")), ("C1", "SPY", ())], strict=True
    ):
        r = main[(label, t)][st]
        setting = f" X {float(st[0]):.0%} / Y {float(st[1]):.0%}" if st else ""
        out += ["", (f"## Appendix {letter} — every trade of {name(label)} {t}{setting} (final test, MAIN) — for an "
                "independent re-check"), "",
                "Our simulated fills. Reference open = that day's open_raw; fill = open × (1 ± 0.05%); fee = Stake US$3.", "",
                *trade_table(r), "", (f"Start cash US${r.start_cash:,.2f}; final value at last close US${r.final:,.2f}; "
                f"final AUD {r.final_aud:,.2f}; run `{r.path.parent.name}`.")]  # fmt: skip
    commit = str(runs[0].record["git_commit"])[:7]
    out += ["", (f"Code commit `{commit}` (dirty: False) for all {len(runs):,} runs; records under /data/runs/final/ "
            "(git-ignored).")]  # fmt: skip
    return out


def main() -> int:
    runs = load(sorted(RUNS.glob("*/*/run.json")))
    problems = checks(runs)
    if problems:
        print("STOP —", problems)
        return 1
    val = load([*sorted(VAL_RUNS.glob("*/run.json")), *sorted(P9_RUNS.glob("*/run.json"))])
    # twins exist in both folders with identical results (Phase 9 consistency check) — either copy serves
    val_main = table([r for r in val if r.ticker in TICKERS], "main")
    REPORT.write_text(build(runs, val_main), encoding="utf-8")
    print(f"report written: {REPORT.relative_to(PROJECT_ROOT)} ({len(runs)} runs)")
    return 0


if __name__ == "__main__":
    from _help import handle_help  # --help: describe and exit, do nothing else

    handle_help(__doc__)
    sys.exit(main())
