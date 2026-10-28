"""Phase 5 (Steps 5.3, 5.4, 5.7): S3 mean reversion + S4 trend filter on the DEVELOPMENT period.

Run:  uv run python scripts/run_s3_s4_dev.py
- 76 runs (S3 6 × 2, S4-S1 16 × 2, S4-S2 16 × 2) + 2 S0 baselines, MAIN settings, warm-up 2008–2009
  for indicators only (trading + metrics from 2010-01-04). Records under /data/runs/.
- Warm-up proof: S0 + all 64 S1/S2 settings re-run WITH warm-up rows (records under
  /data/runs/_reproductions/) and compared to the saved S1/S2 report — must match to the cent.
- Report reports/experiments/s3_s4_dev_2010-2016.md — SUMMARY NUMBERS ONLY, no winner picked.
SIMULATED, HISTORICAL, DEVELOPMENT PERIOD — exploration only, not evidence (EXPERIMENT_PLAN §4).
"""

import itertools
import json
import logging
import re
import statistics
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import yaml

from quant_research.backtesting.run import (
    DEFAULT_RUNS_DIR,
    MR_K_GRID,
    MR_WINDOW_GRID,
    XY_GRID,
    RunConfig,
    RunOutcome,
    parse_config,
    run_backtest,
)
from quant_research.data.fx import load_usd_per_aud
from quant_research.metrics.performance import PerformanceSummary, summarise
from quant_research.strategies.registry import make_strategy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIGS = {
    "AAPL": "config/s0_buy_and_hold_aapl_dev.yaml",
    "XOM": "config/s0_buy_and_hold_xom_dev.yaml",
}
S1S2_REPORT = PROJECT_ROOT / "reports" / "experiments" / "s1_s2_dev_2010-2016.md"
REPORT = PROJECT_ROOT / "reports" / "experiments" / "s3_s4_dev_2010-2016.md"
WARMUP_START = date(2008, 1, 1)
LABELS = {
    "s0_buy_and_hold": "S0",
    "s1_profit_target": "S1",
    "s2_pullback": "S2",
    "s3_mean_reversion": "S3",
    "s4_trend_s1": "S4-S1",
    "s4_trend_s2": "S4-S2",
}
TRADE_LISTS = [
    ("AAPL", "s3_mean_reversion", {"mr_k": Decimal("2.0"), "mr_window": 20}),
    ("AAPL", "s4_trend_s1", {"profit_target_x": Decimal("0.05"), "rebuy_dip_y": Decimal("0.05")}),
]


@dataclass(frozen=True)
class Run:
    ticker: str
    label: str
    params: dict
    config: RunConfig
    out: RunOutcome
    perf: PerformanceSummary

    @property
    def name(self) -> str:
        if "mr_k" in self.params:
            return f"{self.label} {self.ticker} k{self.params['mr_k']} w{self.params['mr_window']}"
        if "profit_target_x" in self.params:
            return f"{self.label} {self.ticker} X{self.params['profit_target_x']:.0%} Y{self.params['rebuy_dip_y']:.0%}"
        return f"{self.label} {self.ticker}"


def make_config(base: dict, strategy: str, params: dict) -> RunConfig:
    raw = {**base, "strategy": strategy, "warmup_start": WARMUP_START}
    tag = "_".join(f"{k}{v}" for k, v in params.items())
    raw["run_name"] = (
        f"{LABELS[strategy].lower().replace('-', '')}_{base['ticker'].lower()}_{tag}_dev".rstrip(
            "_"
        )
    )
    for key, value in params.items():
        raw[key] = value if isinstance(value, int) else str(value)
    return parse_config(raw)


def run_one(base: dict, strategy: str, params: dict, fx, runs_dir: Path) -> Run:
    config = make_config(base, strategy, params)
    out = run_backtest(config, make_strategy(config), fx_series=fx, runs_dir=runs_dir)
    s = out.summary
    perf = summarise(
        out.result, s["start_cash_usd"], config.initial_aud, s["end_aud_after_liquidation"], fx.on
    )
    return Run(config.ticker, LABELS[strategy], params, config, out, perf)


def saved_final_values() -> dict[str, str]:
    """Final USD per run name from the saved S1/S2 report (§1 S0 table and §4 every-run table)."""
    text = S1S2_REPORT.read_text(encoding="utf-8")
    found = {
        f"S0 {t}": v
        for t, v in re.findall(r"^\| (AAPL|XOM) \| US\$([\d,]+\.\d\d) \|", text, re.MULTILINE)
    }
    found.update(
        dict(
            re.findall(r"^\| (S[12] \w+ X\d+% Y\d+%) \| US\$([\d,]+\.\d\d) \|", text, re.MULTILINE)
        )
    )
    return found


def xy_grid() -> list[dict]:
    return [{"profit_target_x": x, "rebuy_dip_y": y} for x in XY_GRID for y in XY_GRID]


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    fx = load_usd_per_aud()
    repro_dir = DEFAULT_RUNS_DIR / "_reproductions" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    runs: list[Run] = []
    repro: list[Run] = []
    for ticker, path in BASE_CONFIGS.items():
        base = yaml.safe_load((PROJECT_ROOT / path).read_text(encoding="utf-8"))
        runs.append(run_one(base, "s0_buy_and_hold", {}, fx, DEFAULT_RUNS_DIR))
        for strategy in ("s1_profit_target", "s2_pullback"):
            for params in xy_grid():
                repro.append(run_one(base, strategy, params, fx, repro_dir))
        for k in MR_K_GRID:
            for w in MR_WINDOW_GRID:
                runs.append(
                    run_one(
                        base, "s3_mean_reversion", {"mr_k": k, "mr_window": w}, fx, DEFAULT_RUNS_DIR
                    )
                )
        for strategy in ("s4_trend_s1", "s4_trend_s2"):
            for params in xy_grid():
                runs.append(run_one(base, strategy, params, fx, DEFAULT_RUNS_DIR))
        print(f"{ticker}: done")
    saved = saved_final_values()
    baselines = [r for r in runs if r.label == "S0"]
    checks = [(r.name, saved.get(r.name), f"{r.perf.final_usd:,.2f}") for r in [*baselines, *repro]]
    mismatches = [c for c in checks if c[1] != c[2]]
    print(f"warm-up proof: {len(checks) - len(mismatches)} of {len(checks)} reproduced exactly")
    if mismatches:
        print("STOP — warm-up changed S0/S1/S2 results, report NOT written:", mismatches[:5])
        return 1
    REPORT.write_text(build_report(runs, repro, checks), encoding="utf-8")
    print(
        f"{len(runs)} runs (+{len(repro)} reproductions) ; report written: {REPORT.relative_to(PROJECT_ROOT)}"
    )
    return 0


def pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.2%}"


def pts(x: float) -> str:
    return f"{x * 100:+.1f}"


def dip_dependence(winners: list[Run]) -> list[str]:
    """For the largest win: how much it rests on a few cheap rebuys (split-adjusted to the last day's units)."""
    if not winners:
        return []
    top = max(winners, key=lambda r: r.perf.total_return_usd)
    fills = top.out.result.fills
    splits = [(e.date, e.ratio) for e in top.out.result.portfolio.entries if e.type == "SPLIT"]

    def in_last_units(day, price):
        for split_day, ratio in splits:
            if day < split_day:
                price = price / ratio
        return price

    cycles = [
        (
            f.day,
            in_last_units(f.day, f.fill_price_usd),
            g.day,
            in_last_units(g.day, g.fill_price_usd),
        )
        for f, g in itertools.pairwise(fills)
        if f.side == "sell" and g.side == "buy"
    ]
    cheaper = sum(1 for _, sold, _, bought in cycles if bought < sold)
    best = sorted(cycles, key=lambda c: c[3] / c[1])[:3]
    return [
        f"- The largest S3/S4 result ({top.name}) rests on {len(cycles)} sell → rebuy cycles, {cheaper} of them",
        "  rebought cheaper (split-adjusted). The three cheapest rebuys: "
        + "; ".join(f"sold {a} → rebought {c} {(d / b - 1):+.1%}" for a, b, c, d in best)
        + ".",
        "  A few large dips (e.g. a crash-day open) can carry the whole result — Phase 6's \"best 3 trades",
        '  removed" check is needed before reading anything into it.',
    ]


def build_report(runs: list[Run], repro: list[Run], checks: list) -> str:
    s0 = {r.ticker: r for r in runs if r.label == "S0"}
    every = [*runs, *repro]

    def excess(r: Run) -> float:
        return r.perf.total_return_usd - s0[r.ticker].perf.total_return_usd

    def cell(r: Run) -> str:
        text = pts(excess(r))
        if excess(r) > 0:
            text += f" ({r.perf.pct_days_fully_in_cash:.0%} in cash)"
        if r.perf.stranded:
            text += " (stranded)"
        return text

    def find(label: str, ticker: str, params: dict) -> Run:
        return next(
            r for r in every if r.label == label and r.ticker == ticker and r.params == params
        )

    lines = [
        "# S3 mean reversion + S4 trend filter — development period 2010–2016 (Phase 5)",
        "",
        "> **SIMULATED, HISTORICAL, DEVELOPMENT PERIOD — exploration only, not evidence (EXPERIMENT_PLAN §4).**",
        "> No winner is picked and nothing is tuned from these numbers. Validation (2017–2020) and the final",
        "> test (2021+) were NOT run. Summary numbers only — no price or equity series (Tiingo licence).",
        "",
        "Settings (MAIN only, same as the S1/S2 report): Stake fees, normal spread, fractional shares, AUD 10,000",
        "→ USD at the RBA rate, reinvest dividends only when cash ≥ US$100, 15% withholding. Indicators use",
        "2008–2009 warm-up rows and split-adjusted-as-of-T closes (never close_adj — it contains later splits",
        "and dividends). Excess return = strategy total return − S0 total return, percentage points (USD).",
        "Positive cells also show the % of days fully in cash (see caveats).",
        "",
        "## 1. Warm-up proof — S0/S1/S2 unchanged with warm-up rows present",
        "",
        f"{len(checks)} of {len(checks)} runs (2 S0 + 64 S1/S2) reproduced the saved final USD value **exactly**",
        "(to the cent) with 2008–2009 warm-up rows in the table. The 64 S1/S2 reproductions are kept under",
        '/data/runs/_reproductions/ and were used only for this check and the "did the filter help?" table.',
        "",
        "| Run | Saved report | With warm-up |",
        "|---|---|---|",
        *[
            f"| {n} | US${a} | US${b} |"
            for n, a, b in checks
            if n.startswith("S0") or n.endswith("X5% Y5%")
        ],
        "",
        "## 2. S3 mean reversion — excess return vs S0 (rows k, columns w)",
        "",
    ]
    for t in s0:
        lines += [
            f"**S3 on {t}**",
            "",
            "| k \\ w | " + " | ".join(str(w) for w in MR_WINDOW_GRID) + " |",
            "|---|---|---|",
        ]
        for k in MR_K_GRID:
            lines.append(
                f"| {k} | "
                + " | ".join(
                    cell(find("S3", t, {"mr_k": k, "mr_window": w})) for w in MR_WINDOW_GRID
                )
                + " |"
            )
        lines.append("")
    lines += ["## 3. S4 trend filter — excess return vs S0 (rows X, columns Y)", ""]
    for t in s0:
        for label in ("S4-S1", "S4-S2"):
            lines += [f"**{label} on {t}**", "", "| X \\ Y | " + " | ".join(f"{y:.0%}" for y in XY_GRID) + " |",
                      "|---|" + "---|" * len(XY_GRID)]  # fmt: skip
            for x in XY_GRID:
                lines.append(
                    f"| {x:.0%} | "
                    + " | ".join(
                        cell(find(label, t, {"profit_target_x": x, "rebuy_dip_y": y}))
                        for y in XY_GRID
                    )
                    + " |"
                )
            lines.append("")
    lines += [
        "## 4. Did the filter help? (S4 − base, percentage points of total return; + = filter helped)",
        "",
    ]
    for t in s0:
        for label, base in (("S4-S1", "S1"), ("S4-S2", "S2")):
            lines += [f"**{label} − {base} on {t}**", "", "| X \\ Y | " + " | ".join(f"{y:.0%}" for y in XY_GRID) + " |",
                      "|---|" + "---|" * len(XY_GRID)]  # fmt: skip
            helped = 0
            for x in XY_GRID:
                row = []
                for y in XY_GRID:
                    p = {"profit_target_x": x, "rebuy_dip_y": y}
                    diff = (
                        find(label, t, p).perf.total_return_usd
                        - find(base, t, p).perf.total_return_usd
                    )
                    helped += diff > 0
                    row.append(pts(diff))
                lines.append(f"| {x:.0%} | " + " | ".join(row) + " |")
            lines += ["", f"Filter helped in {helped} of 16 settings.", ""]
    lines += ["## 5. Roll-up across S1–S4 (per ticker; counts only — not a recommendation)", "",
              "| Ticker | Strategy | Settings | Beat S0 | Stranded at end | Median days fully in cash |",
              "|---|---|---|---|---|---|"]  # fmt: skip
    for t in s0:
        for label in ("S1", "S2", "S3", "S4-S1", "S4-S2"):
            rs = [r for r in every if r.ticker == t and r.label == label]
            lines.append(
                f"| {t} | {label} | {len(rs)} | {sum(excess(r) > 0 for r in rs)} | {sum(r.perf.stranded for r in rs)} | "
                f"{statistics.median(r.perf.pct_days_fully_in_cash for r in rs):.0%} |"
            )
    winners = [r for r in runs if r.label != "S0" and excess(r) > 0]
    lines += [
        "",
        "## 6. Caveats (honest reading)",
        "",
        "- Two stocks, seven years, one cost level: far too little to judge any hypothesis. This is exploration.",
        "- S1's XOM \"wins\" (S1/S2 report) came while 73–88% of days were in cash during XOM's 2014–2016 fall —",
        "  a regime effect, not evidence of skill. The same check for S3/S4: "
        + (
            f"{len(winners)} S3/S4 runs beat S0; their % of days fully in cash: "
            + ", ".join(f"{r.name} {r.perf.pct_days_fully_in_cash:.0%}" for r in winners)
            + "."
            if winners
            else "no S3/S4 run beat S0."
        ),
        *dip_dependence(winners),
        '- Roadmap 5.7: a setting is never preferred because it traded more. "Best 3 trades removed" and cost /',
        "  spread sensitivity are Phase 6. H1 is judged only on the final test period (EXPERIMENT_PLAN §6).",
        "- S4 was run on all 16 X/Y combinations (broader than EXPERIMENT_PLAN §3's ≤ 8) to avoid choosing a",
        '  "best region" from development results — logged in EXPERIMENT_PLAN §10.',
        "",
        "## 7. Every run",
        "",
        (
            "| Run | Final USD | Final AUD | CAGR USD | Max DD | Round trips | Days in cash | Stranded (days) |"
            " Longest cash spell (days) | Fees + spread (USD) | Dividends missed vs S0 (USD) | Excess vs S0 USD / AUD (pts) |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in runs:
        p = r.perf
        ex = "—" if r.label == "S0" else (
            f"{pts(excess(r))} / {pts(p.total_return_aud - s0[r.ticker].perf.total_return_aud)}"
        )  # fmt: skip
        lines.append(
            f"| {r.name} | US${p.final_usd:,.2f} | AUD {p.final_aud_after_fx:,.2f} | {pct(p.cagr_usd)} | "
            f"{pct(p.max_drawdown.max_drawdown)} | {p.round_trips} | {pct(p.pct_days_fully_in_cash)} | "
            f"{f'yes ({p.stranded_days})' if p.stranded else 'no'} | {p.longest_cash_spell_days} | "
            f"US${p.total_fees_usd + p.total_spread_cost_usd:,.2f} | "
            f"US${s0[r.ticker].perf.dividends_net_usd - p.dividends_net_usd:,.2f} | {ex} |"
        )
    for i, (t, strategy, params) in enumerate(TRADE_LISTS):
        r = find(LABELS[strategy], t, params)
        lines += [
            "",
            f"## Appendix {'AB'[i]} — every trade of {r.name} (for an independent re-check)",
            "",
            "Our simulated fills only. Reference open = that day's open_raw; fill = open × (1 ± 0.05%); fee = Stake US$3.",
            "",
            "| # | Date | Side | Reference open | Fill price | Fee | Shares | Cash after |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for n, f in enumerate(r.out.result.fills, start=1):
            lines.append(
                f"| {n} | {f.day} | {f.side} | {f.reference_price_usd} | {f.fill_price_usd} | {f.fee.total_usd} | "
                f"{f.quantity} | {f.entry.cash_after_usd} |"
            )
        lines += ["", (f"Start cash US${r.out.summary['start_cash_usd']}; dividends net US${r.perf.dividends_net_usd:,.2f}; "
                  f"final value at last close US${r.perf.final_usd:,.2f}.")]  # fmt: skip
    record = json.loads((runs[0].out.run_dir / "run.json").read_text())
    lines += [
        "",
        "## Appendix C — data and code",
        "",
        f"- Code commit `{str(record['git_commit'])[:7]}` (dirty: {record['git_dirty']}). Prices: "
        f"{record['warmup_provenance']['file_name']} (warm-up) + {record['data_provenance']['file_name']} and the XOM "
        "equivalents (Tiingo). FX: "
        + ", ".join(record["fx_files"])
        + " — Source: Reserve Bank of Australia.",
        f"- {len(runs)} run records under /data/runs/ + {len(repro)} reproductions under /data/runs/_reproductions/.",
        "- Base config: "
        + json.dumps(
            {
                k: str(v)
                for k, v in asdict(s0["AAPL"].config).items()
                if k not in ("run_name", "ticker")
            }
        ),
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    from _help import handle_help  # --help: describe and exit, do nothing else

    handle_help(__doc__)
    sys.exit(main())
