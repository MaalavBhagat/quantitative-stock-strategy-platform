"""Phase 9, Steps 9.5–9.6: report + H7 verdicts for the pre-registered runs, from the saved records only.

Run (after scripts/run_phase9.py has finished):  uv run python scripts/report_phase9.py
Applies research/PREREGISTRATION_V2.md §6 (tag prereg-v2) — R1–R6 as PREREGISTRATION §9 with the TWIN as benchmark.
Writes reports/experiments/phase9_information_2017-2020.md — SUMMARY NUMBERS ONLY (no price or equity series).

Gate BEFORE anything is built: the twins (S0, S4-S2) re-run in this batch must equal the saved Phase 6 validation
records to the cent (final value USD + AUD, fills) — any difference → STOP.
Interpretations (fixed before any result was looked at, as in Phase 6 / PREREGISTRATION_V2 §6):
- R5: the information strategy's 3 largest round trips with realised P&L > 0 are removed; the twin is unchanged.
- R4 "pass" = R1 and R2 both pass at the stress variant (wide spread + CommSec), strategy and twin both at stress.
- Total return = value at the last close ÷ start cash − 1.
"""

import json
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from report_validation import Run, pct, pts, read_csv, setting_of

from quant_research.strategies import labels

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS = PROJECT_ROOT / "data" / "runs" / "phase9"
PHASE6 = PROJECT_ROOT / "data" / "runs" / "validation"
REPORT = PROJECT_ROOT / "reports" / "experiments" / "phase9_information_2017-2020.md"
TICKERS = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "T", "SPY"]
VARIANTS = ["main", "tight", "wide", "ibkr", "commsec", "whole", "stress"]
INFO = ["C1", "C2", "E1"]
TWIN = {"C1": "S0", "C2": "S4-S2", "E1": "S4-S2"}
R2_NEEDED = {"C1": 1, "C2": 10, "E1": 10}
EXPECTED = {"validation": 2800, "development": 400}
YEARS = (2017, 2018, 2019, 2020)
E1_TRADES = ("KO", ("0.03", "0.03"))


def name(sid: str) -> str:
    return labels.display(sid)


def load(period: str) -> list[Run]:
    runs = []
    for path in sorted((RUNS / period).glob("*/*/run.json")):
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


def checks(val: list[Run], dev: list[Run]) -> list[str]:
    problems = []
    for period, runs in (("validation", val), ("development", dev)):
        if len(runs) != EXPECTED[period]:
            problems.append(f"{period}: expected {EXPECTED[period]} runs, found {len(runs)}")
    commits = {str(r.record["git_commit"]) for r in val + dev}
    if len(commits) != 1 or any(r.record["git_dirty"] for r in val + dev):
        problems.append(f"runs must come from ONE clean commit: {commits}")
    if any(r.days[-1] >= date(2021, 1, 1) or r.days[0] < date(2017, 1, 1) for r in val):
        problems.append("a validation run has days outside 2017-01-01 … 2020-12-31")
    if any(r.days[-1] > date(2016, 12, 30) or r.days[0] < date(2010, 1, 4) for r in dev):
        problems.append("a development run has days outside 2010-01-04 … 2016-12-30")
    return problems


def twin_consistency(val: list[Run]) -> tuple[int, int, int, list[str]]:
    """Every twin run of this batch vs the saved Phase 6 record with the same variant / strategy / stock / setting."""
    phase6 = {}
    for path in PHASE6.glob("*/*/run.json"):
        r = json.loads(path.read_text(encoding="utf-8"))
        cfg = r["config"]
        if cfg["strategy"] in ("s0_buy_and_hold", "s4_trend_s2"):
            phase6[(path.parent.parent.name, cfg["strategy"], cfg["ticker"], setting_of(cfg))] = (
                path
            )
    diffs, checked, main_checked = [], 0, 0
    for run in val:
        if run.label not in ("S0", "S4-S2"):
            continue
        key = (run.variant, run.record["config"]["strategy"], run.ticker, run.setting)
        old_path = phase6.get(key)
        if old_path is None:
            diffs.append(f"{key}: no Phase 6 record")
            continue
        old = json.loads(old_path.read_text(encoding="utf-8"))["summary"]
        new = run.record["summary"]
        same = all(
            old[k] == new[k]
            for k in ("last_close_value_usd", "end_aud_after_liquidation", "start_cash_usd")
        )
        same = (
            same
            and (old_path.parent / "fills.csv").read_text()
            == (run.path.parent / "fills.csv").read_text()
        )
        checked += 1
        main_checked += run.variant == "main"
        if not same:
            diffs.append(
                f"{key}: Phase 6 {old['last_close_value_usd']} vs now {new['last_close_value_usd']}"
            )
    return checked, main_checked, len(phase6), diffs


# ---------- the pre-registered rules (vs the twin) ----------
def table(runs: list[Run], variant: str) -> dict:
    by: dict = defaultdict(dict)
    for r in runs:
        if r.variant == variant:
            by[(r.label, r.ticker)][r.setting] = r
    return by


def pairs(by: dict, label: str, t: str) -> list[tuple[Run, Run]]:
    """(information run, twin run) for the same stock and setting (C1 has one setting, its twin S0 likewise)."""
    twin = by[(TWIN[label], t)]
    return [(r, twin[st] if st in twin else twin[()]) for st, r in sorted(by[(label, t)].items())]


def r1_r2(by, label, ret_i=lambda r: r.total_return, ret_t=lambda r: r.total_return):
    stocks = sum(
        statistics.median(ret_i(i) - ret_t(w) for i, w in pairs(by, label, t)) > 0 for t in TICKERS
    )
    settings = sorted(by[(label, TICKERS[0])])
    passed = 0
    for st in settings:
        diffs = []
        for t in TICKERS:
            i = by[(label, t)][st]
            w = by[(TWIN[label], t)].get(st, by[(TWIN[label], t)].get(()))
            diffs.append(ret_i(i) - ret_t(w))
        passed += statistics.mean(diffs) > 0
    return stocks, passed, len(settings)


def verdicts(val: list[Run]) -> dict:
    main, stress = table(val, "main"), table(val, "stress")
    out = {}
    for label in INFO:
        r1, r2, n = r1_r2(main, label)
        r1_pass, r2_pass = r1 >= 6, r2 >= R2_NEEDED[label]
        r3 = sum(
            statistics.median(
                (i.mdd.max_drawdown - w.mdd.max_drawdown) * 100 for i, w in pairs(main, label, t)
            )
            >= -5
            for t in TICKERS
        )
        s_r1, s_r2, _ = r1_r2(stress, label)
        r4_pass = s_r1 >= 6 and s_r2 >= R2_NEEDED[label]
        r4 = "pass" if r4_pass else ("LOW-COST ONLY" if (r1_pass and r2_pass) else "fail")
        b_r1, b_r2, _ = r1_r2(main, label, ret_i=lambda r: r.best3_removed_return())
        r5_pass = b_r1 >= 6 and b_r2 >= R2_NEEDED[label]
        r6 = sum(
            statistics.median(r.round_trips for r in main[(label, t)].values()) >= 10
            for t in TICKERS
        )
        r6_pass = r6 >= 6
        if r1 <= 3:
            verdict = "REJECTED"
        elif all([r1_pass, r2_pass, r3 >= 6, r4_pass, r5_pass, r6_pass]):
            verdict = "SUPPORTED"
        else:
            verdict = "INCONCLUSIVE" + ("" if r6_pass else " (too few trades)")
        out[label] = {"r1": r1, "r2": r2, "n": n, "r3": r3, "r4": r4, "s_r1": s_r1, "s_r2": s_r2, "r5": r5_pass,
                      "b_r1": b_r1, "b_r2": b_r2, "r6": r6, "verdict": verdict}  # fmt: skip
    return out


def h7_line(label: str, v: dict) -> str:
    x = v[label]
    twin = name(TWIN[label])
    if x["verdict"] == "SUPPORTED":
        return f"- **{name(label)}**: H7 SUPPORTED — the extra information beat {twin} under every pre-registered rule."
    if x["verdict"] == "REJECTED":
        return (
            f"- **{name(label)}**: H7 NOT supported (REJECTED) — the extra information did not beat {twin}: "
            f"better on only {x['r1']} of 8 stocks."
        )
    return (
        f"- **{name(label)}**: H7 NOT supported (INCONCLUSIVE) — better than {twin} on {x['r1']} of 8 stocks, "
        "but not every pre-registered rule passed."
    )


# ---------- report ----------
def build(val: list[Run], dev: list[Run], consistency: tuple) -> str:
    v = verdicts(val)
    main = table(val, "main")
    s0 = {t: main[("S0", t)][()] for t in TICKERS}
    checked, main_checked, _, _ = consistency
    commit = str(val[0].record["git_commit"])[:7]
    L = [
        "# Phase 9 — does extra information help? C1 / C2 / E1 vs their twins, validation 2017–2020 (Steps 9.5–9.6)",
        "",
        "> **SIMULATED, HISTORICAL, VALIDATION 2017–2020 — prices already seen for the twins; the clean test is the final",
        (
            "> 2021+ run.** Rules: research/PREREGISTRATION_V2.md (tag `prereg-v2`). All "
            f"{len(val) + len(dev):,} runs from one clean commit `{commit}`."
        ),
        "> Summary numbers only (Tiingo licence). Generated by `scripts/report_phase9.py` from the saved records — nothing",
        "> typed by hand. Not financial advice.",
        "",
        f"**Twin consistency check (before judging):** all {checked} twin runs of this batch ({main_checked} at MAIN) are",
        "identical to the saved Phase 6 validation records — final value USD and AUD to the cent and every fill.",
        "",
        "## 1. Verdicts vs the TWIN (MAIN: Stake, normal spread, fractional, RBA FX, reinvest ≥ US$100)",
        "",
        (
            "| Strategy (twin) | R1 stocks (need ≥ 6/8) | R2 settings | R3 drawdown stocks (≥ 6/8) | R4 stress (R1/R2) | "
            "R5 best-3 removed (R1/R2) | R6 stocks with ≥ 10 trips (≥ 6/8) | VERDICT |"
        ),
        "|---|---|---|---|---|---|---|---|",
    ]
    for label in INFO:
        x = v[label]
        L.append(
            f"| {name(label)} (vs {name(TWIN[label])}) | {x['r1']}/8 | {x['r2']}/{x['n']} (need ≥ {R2_NEEDED[label]}) | "
            f"{x['r3']}/8 | {x['r4']} ({x['s_r1']}/8, {x['s_r2']}/{x['n']}) | {'pass' if x['r5'] else 'fail'} "
            f"({x['b_r1']}/8, {x['b_r2']}/{x['n']}) | {x['r6']}/8 | **{x['verdict']}** |"
        )
    L += [
        "",
        "Excess = information strategy total return − twin total return (same stock, same X/Y setting), pp USD.",
        "SUPPORTED = R1–R6 all pass; REJECTED = R1 ≤ 3 of 8; INCONCLUSIVE = anything else (at most INCONCLUSIVE if R6",
        "fails). C1 has one setting: R2 = its mean excess over the 8 stocks > 0. R5 removes only the information",
        "strategy's own best 3 profitable round trips (twin unchanged).",
        "",
        "## 2. Compare with simpler models (Step 9.5) — per stock, MAIN",
        "",
        "Excess in pp USD. Medians are across the strategy's settings (C1: one setting).",
        "",
    ]
    for t in TICKERS:
        b = s0[t]
        L += [
            f"**{t}** — {name('S0')}: final US${b.final:,.2f}, total {pct(b.total_return)}, max DD {pct(b.mdd.max_drawdown)}",
            "",
            (
                "| Strategy | vs twin: median | best | worst | vs Buy-and-hold (S0): median | best | worst | "
                "Round trips (median; twin) | Days in cash (median; twin) | Stranded (of settings; twin) |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for label in INFO:
            ps = pairs(main, label, t)
            ex_t = [i.total_return - w.total_return for i, w in ps]
            ex_0 = [i.total_return - b.total_return for i, _ in ps]
            info = [i for i, _ in ps]
            twins = [w for _, w in ps]
            L.append(
                f"| {name(label)} | {pts(statistics.median(ex_t))} | {pts(max(ex_t))} | {pts(min(ex_t))} | "
                f"{pts(statistics.median(ex_0))} | {pts(max(ex_0))} | {pts(min(ex_0))} | "
                f"{statistics.median(r.round_trips for r in info):g}; {statistics.median(r.round_trips for r in twins):g} | "
                f"{statistics.median(r.days_in_cash for r in info):.0%}; {statistics.median(r.days_in_cash for r in twins):.0%} | "
                f"{sum(r.stranded for r in info)}/{len(info)}; {sum(r.stranded for r in twins)}/{len(twins)} |"
            )
        L.append("")
    # 9.6
    L += ["## 3. Incremental value (Step 9.6)", "",
          "**Median (information − twin) per stock and per cost variant** (pp USD, median across settings):", ""]  # fmt: skip
    for label in INFO:
        L += [f"*{name(label)} vs {name(TWIN[label])}*", "", "| Stock | " + " | ".join(VARIANTS) + " |",
              "|---|" + "---|" * len(VARIANTS)]  # fmt: skip
        by_var = {var: table(val, var) for var in VARIANTS}
        for t in TICKERS:
            cells = [
                pts(
                    statistics.median(
                        i.total_return - w.total_return for i, w in pairs(by_var[var], label, t)
                    )
                )
                for var in VARIANTS
            ]
            L.append(f"| {t} | " + " | ".join(cells) + " |")
        allc = [
            pts(
                statistics.median(
                    i.total_return - w.total_return
                    for t in TICKERS
                    for i, w in pairs(by_var[var], label, t)
                )
            )
            for var in VARIANTS
        ]
        L += ["| **all stocks** | " + " | ".join(allc) + " |", ""]
    L += ["**Dependence on a few trades** (MAIN, runs with a gain; median share of the total gain from the top 1 / top 3",
          "profitable round trips):", "", "| Strategy | Runs with a gain | Top-1 share | Top-3 share |", "|---|---|---|---|"]  # fmt: skip
    for label in (*INFO, "S4-S2"):
        sh1, sh3 = [], []
        for t in TICKERS:
            for r in main[(label, t)].values():
                gain = r.final - r.start_cash
                top = sorted((p for p in r.sells if p > 0), reverse=True)
                if gain > 0 and top:
                    sh1.append(top[0] / gain)
                    sh3.append(sum(top[:3]) / gain)
        L.append(f"| {name(label)} | {len(sh1)} | {statistics.median(sh1):.1%} | {statistics.median(sh3):.1%} |"
                 if sh1 else f"| {name(label)} | 0 | — | — |")  # fmt: skip
    regime = {}
    for t in TICKERS:
        for year, ret in s0[t].year_returns().items():
            regime[(t, year)] = "UP" if ret >= 0.10 else ("DOWN" if ret <= -0.10 else "SIDEWAYS")
    L += ["", "**By regime** (Phase 6 labels: each stock-year from Buy-and-hold (S0), ≥ +10% UP, ≤ −10% DOWN, else",
          "SIDEWAYS). Median yearly (information − twin), all stocks × settings × years of that regime, pp:", "",
          "| Strategy | UP | DOWN | SIDEWAYS |", "|---|---|---|---|"]  # fmt: skip
    for label in INFO:
        acc = defaultdict(list)
        for t in TICKERS:
            for i, w in pairs(main, label, t):
                wy = w.year_returns()
                for year, ret in i.year_returns().items():
                    acc[regime[(t, year)]].append(ret - wy[year])
        L.append(f"| {name(label)} | " + " | ".join(pts(statistics.median(acc[k])) if acc[k] else "—"
                                                    for k in ("UP", "DOWN", "SIDEWAYS")) + " |")  # fmt: skip
    counts = {k: sum(x == k for x in regime.values()) for k in ("UP", "DOWN", "SIDEWAYS")}
    L += ["", f"Stock-years per regime: {counts}.", ""]
    dmain = table(dev, "main")
    L += ["**Development 2010–2016 (looked at, not judged) vs validation 2017–2020** — median excess vs twin and",
          "settings beating the twin:", "",
          ("| Strategy | Stock | Dev median | Val median | Dev settings beating twin | Val settings beating twin | "
          "Dev winners still beating twin in val |"), "|---|---|---|---|---|---|---|"]  # fmt: skip
    for label in INFO:
        for t in TICKERS:
            d = {i.setting: i.total_return - w.total_return for i, w in pairs(dmain, label, t)}
            vv = {i.setting: i.total_return - w.total_return for i, w in pairs(main, label, t)}
            winners = [st for st, e in d.items() if e > 0]
            L.append(f"| {name(label)} | {t} | {pts(statistics.median(d.values()))} | {pts(statistics.median(vv.values()))} | "
                     f"{len(winners)}/{len(d)} | {sum(e > 0 for e in vv.values())}/{len(vv)} | "
                     f"{sum(vv[st] > 0 for st in winners)}/{len(winners)} |")  # fmt: skip
    L += ["", "## 4. H7 answer (from the verdicts only)", ""]
    L += [h7_line(label, v) for label in INFO]
    L += ["", "Vs Buy-and-hold (S0) the comparison is descriptive only (§2) — no verdict."]
    L += appendix(val, v)
    return "\n".join(L) + "\n"


def e1_skipped(run: Run) -> list[tuple[date, str, list]]:
    """Re-run E1 KO 3/3 IN MEMORY (nothing saved) with a recording copy, check it reproduces the saved fills, and return
    every signal the cool-off skipped with the earnings event(s) that caused it."""
    from decimal import Decimal

    from quant_research.backtesting.engine import EngineSettings, run_engine
    from quant_research.data.loader import load_prices_with_warmup
    from quant_research.news.events import load_events, usable_close_day
    from quant_research.strategies.information import EARNINGS, EarningsCoolOff
    from quant_research.strategies.profit_target import PullbackFromPeak, TrendFilteredPullback

    class Recording(EarningsCoolOff):
        def on_close(self, day, history, view):
            self.today = day
            return super().on_close(day, history, view)

        def _sell_allowed(self, history):
            if self._cooling and TrendFilteredPullback._sell_allowed(self, history):
                self.skipped.append((self.today, "sell"))
            return super()._sell_allowed(history)

        def _rebuy(self, close):
            hit = PullbackFromPeak._rebuy(
                self, close
            )  # running high P = max(P, close): updating twice changes nothing
            if hit and self._cooling:
                self.skipped.append((self.today, "rebuy"))
            return hit and not self._cooling

    cfg = run.record["config"]
    events = [e for e in load_events(run.ticker, PROJECT_ROOT / "data" / "raw" / "sec" / "submissions")
              if EARNINGS in e.categories]  # fmt: skip
    strat = Recording(run.ticker, Decimal(cfg["profit_target_x"]), Decimal(cfg["rebuy_dip_y"]),
                      Decimal(cfg["reinvest_min_cash_usd"]), events=events)  # fmt: skip
    strat.skipped = []
    prices = load_prices_with_warmup(run.ticker, date.fromisoformat(cfg["warmup_start"]),
                                     date.fromisoformat(cfg["start"]), date.fromisoformat(cfg["end"]))  # fmt: skip
    settings = EngineSettings(
        cfg["broker"], cfg["spread_level"], cfg["share_mode"], Decimal(cfg["min_order_usd"])
    )
    res = run_engine(prices, run.ticker, strat, settings, Decimal(run.record["summary"]["start_cash_usd"]),
                     trade_start=date.fromisoformat(cfg["start"]))  # fmt: skip
    saved = [(f["day"], f["side"], f["quantity"]) for f in run.fills]
    again = [(f.day.isoformat(), f.side, str(f.quantity)) for f in res.fills]
    if saved != again:
        raise SystemExit("STOP — the in-memory E1 re-run does not reproduce the saved fills")
    days = list(prices["date"])
    out = []
    for day, side in strat.skipped:
        k = days.index(day)
        window = set(days[max(0, k - 1) : k + 1])
        out.append((day, side, [e for e in events if usable_close_day(e.accepted_et) in window]))
    return out


def trade_table(run: Run, extra=None) -> list[str]:
    cash = dict(zip((d.isoformat() for d in run.days), run.cash, strict=True))
    head = "| # | Date | Side | Reference open | Fill price | Fee | Shares | Realised P&L | Cash at close |"
    sep = "|---|---|---|---|---|---|---|---|---|"
    if extra:
        head += " Skipped signals before this trade (earnings event → usable day) |"
        sep += "---|"
    out = [head, sep]
    for n, f in enumerate(run.fills, start=1):
        row = (f"| {n} | {f['day']} | {f['side']} | {f['reference_price_usd']} | {f['fill_price_usd']} | "
               f"{f['fee_total_usd']} | {f['quantity']} | {f['realised_pnl_usd'] or '—'} | {cash[f['day']]} |")  # fmt: skip
        if extra:
            row += f" {extra(n - 1)} |"
        out.append(row)
    return out


def appendix(val: list[Run], v: dict) -> list[str]:
    main = table(val, "main")
    c1 = {t: main[("C1", t)][()] for t in TICKERS}
    out = ["", f"## Appendix A — the 8 {name('C1')} finals (validation, MAIN)", "",
           "| Stock | Start cash USD | Final USD (last close) | Final AUD | Round trips | Days in cash |",
           "|---|---|---|---|---|---|"]  # fmt: skip
    out += [f"| {t} | {r.start_cash:,.2f} | {r.final:,.2f} | {r.final_aud:,.2f} | {r.round_trips} | {r.days_in_cash:.0%} |"
            for t, r in c1.items()]  # fmt: skip
    r = c1["AAPL"]
    out += ["", f"## Appendix B — every trade of {name('C1')} AAPL (validation, MAIN) — for an independent re-check", "",
            "Our simulated fills. Reference open = that day's open_raw; fill = open × (1 ± 0.05%); fee = Stake US$3.", "",
            *trade_table(r), "", (f"Start cash US${r.start_cash:,.2f}; final value at last close US${r.final:,.2f}; "
            f"run `{r.path.parent.name}`.")]  # fmt: skip
    t, st = E1_TRADES
    r = main[("E1", t)][st]
    skipped = e1_skipped(r)

    def why(i: int) -> str:
        fill = r.fills[i]
        prev = date.fromisoformat(r.fills[i - 1]["day"]) if i else date.min
        side = "sell" if fill["side"] == "sell" else "rebuy"
        hits = [
            (d, evs)
            for d, s, evs in skipped
            if prev <= d < date.fromisoformat(fill["day"]) and s == side
        ]
        if not hits:
            return "—"
        return "; ".join(
            f"{d} ← "
            + ", ".join(
                f"{e.form} {e.accession} accepted {e.accepted_et:%Y-%m-%d %H:%M} NY" for e in evs
            )
            for d, evs in hits
        )

    out += ["", f"## Appendix C — every trade of {name('E1')} {t} X 3% / Y 3% (validation, MAIN)", "",
            "Skipped signals = days where the twin's rule (trend filter included) would have signalled this side but the",
            "earnings cool-off held it back; recomputed in memory by this script (it first checks that the re-run",
            "reproduces the saved fills exactly).", "", *trade_table(r, why), "",
            f"Start cash US${r.start_cash:,.2f}; final value at last close US${r.final:,.2f}; run `{r.path.parent.name}`.",
            "", f"All skipped signals in this run: {len(skipped)}."]  # fmt: skip
    leftover = [
        (d, s, evs) for d, s, evs in skipped
        if not any(date.fromisoformat(r.fills[i - 1]["day"] if i else "0001-01-01") <= d < date.fromisoformat(f["day"])
                   for i, f in enumerate(r.fills))
    ]  # fmt: skip
    if leftover:
        out += ["", "Skipped signals after the last trade:"]
        out += [f"- {d} {s} ← " + ", ".join(f"{e.form} {e.accession} accepted {e.accepted_et:%Y-%m-%d %H:%M} NY" for e in evs)
                for d, s, evs in leftover]  # fmt: skip
    commit = str(val[0].record["git_commit"])[:7]
    out += [
        "",
        f"Code commit `{commit}` (dirty: False) for all runs; records under /data/runs/phase9/ (git-ignored).",
    ]
    return out


def main() -> int:
    val, dev = load("validation"), load("development")
    problems = checks(val, dev)
    if problems:
        print("STOP —", problems)
        return 1
    consistency = twin_consistency(val)
    checked, main_checked, _, diffs = consistency
    print(
        f"twin consistency: {checked} twin runs compared with Phase 6 ({main_checked} MAIN), {len(diffs)} differences"
    )
    if diffs or checked != 952:
        print("STOP — twins differ from Phase 6 (or are missing); nothing is judged:")
        for d in diffs[:20]:
            print("  ", d)
        return 1
    REPORT.write_text(build(val, dev, consistency), encoding="utf-8")
    print(
        f"report written: {REPORT.relative_to(PROJECT_ROOT)} ({len(val)} validation + {len(dev)} development runs)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
