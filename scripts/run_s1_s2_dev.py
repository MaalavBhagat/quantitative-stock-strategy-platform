"""Phase 5 (Steps 5.1, 5.2, 5.7): S1 + S2 × 16 X/Y × AAPL, XOM on the DEVELOPMENT period, plus S0.

Run:  uv run python scripts/run_s1_s2_dev.py
MAIN settings only (Stake, normal spread, fractional, RBA FX, reinvest ≥ US$100) — sensitivity is Phase 6.
Saves every run record under /data/runs/ (git-ignored) and writes
reports/experiments/s1_s2_dev_2010-2016.md with SUMMARY NUMBERS ONLY. No winner is picked.
SIMULATED, HISTORICAL, DEVELOPMENT PERIOD — exploration only, not evidence (EXPERIMENT_PLAN §4).
"""

import json
import logging
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

import yaml

from quant_research.backtesting.run import (
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
REPORT = PROJECT_ROOT / "reports" / "experiments" / "s1_s2_dev_2010-2016.md"
STRATEGIES = {"s1_profit_target": "S1", "s2_pullback": "S2"}
CHECK_RUN = (
    "AAPL",
    "s1_profit_target",
    Decimal("0.05"),
    Decimal("0.05"),
)  # trade list for chat Claude


@dataclass(frozen=True)
class Run:
    ticker: str
    label: str  # S0 / S1 / S2
    x: Decimal | None
    y: Decimal | None
    config: RunConfig
    out: RunOutcome
    perf: PerformanceSummary


def make_config(base: dict, strategy: str, x: Decimal | None, y: Decimal | None) -> RunConfig:
    raw = dict(base)
    if strategy != "s0_buy_and_hold":
        raw.update(
            strategy=strategy,
            run_name=f"{STRATEGIES[strategy].lower()}_{base['ticker'].lower()}_x{x}_y{y}_dev",
            profit_target_x=str(x),
            rebuy_dip_y=str(y),
        )
    return parse_config(raw)  # same validation as a YAML file (grid check, D8 fields, types)


def run_one(config: RunConfig, label: str, x, y, fx) -> Run:
    out = run_backtest(config, make_strategy(config), fx_series=fx)
    s = out.summary
    perf = summarise(
        out.result, s["start_cash_usd"], config.initial_aud, s["end_aud_after_liquidation"], fx.on
    )
    return Run(config.ticker, label, x, y, config, out, perf)


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    fx = load_usd_per_aud()
    runs: list[Run] = []
    for ticker, path in BASE_CONFIGS.items():
        base = yaml.safe_load((PROJECT_ROOT / path).read_text(encoding="utf-8"))
        runs.append(run_one(make_config(base, "s0_buy_and_hold", None, None), "S0", None, None, fx))
        for strategy, label in STRATEGIES.items():
            for x in XY_GRID:
                for y in XY_GRID:
                    runs.append(run_one(make_config(base, strategy, x, y), label, x, y, fx))
        print(f"{ticker}: {sum(r.ticker == ticker for r in runs)} runs done")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(build_report(runs), encoding="utf-8")
    print(
        f"{len(runs)} runs saved under /data/runs/ ; report written: {REPORT.relative_to(PROJECT_ROOT)}"
    )
    return 0


def pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.2%}"


def pts(x: float) -> str:
    return f"{x * 100:+.1f}"


def build_report(runs: list[Run]) -> str:
    s0 = {r.ticker: r for r in runs if r.label == "S0"}

    def excess_usd(r: Run) -> float:
        return r.perf.total_return_usd - s0[r.ticker].perf.total_return_usd

    def excess_aud(r: Run) -> float:
        return r.perf.total_return_aud - s0[r.ticker].perf.total_return_aud  # type: ignore[operator]

    def missed(r: Run) -> float:
        return s0[r.ticker].perf.dividends_net_usd - r.perf.dividends_net_usd

    lines = [
        "# S1 fixed profit target + S2 pullback — development period 2010–2016 (Phase 5)",
        "",
        "> **SIMULATED, HISTORICAL, DEVELOPMENT PERIOD — exploration only, not evidence (EXPERIMENT_PLAN §4).**",
        "> No winner is picked and nothing is tuned from these numbers. Validation (2017–2020) and the final",
        "> test (2021+) were NOT run. Summary numbers only — no price or equity series (Tiingo licence).",
        "",
        "Settings (MAIN only): Stake fees, normal spread (0.05%/side), fractional shares, AUD 10,000 → USD at",
        "the RBA rate, dividend reinvestment only when cash ≥ US$100, 15% withholding. X = profit target,",
        "Y = dip to rebuy, grid {2, 3, 4, 5}% (EXPERIMENT_PLAN §3). Cost / spread sensitivity is Phase 6.",
        "Excess return = strategy total return − S0 total return, in percentage points (USD).",
        "",
        "## 1. S0 benchmark (same settings)",
        "",
        "| Ticker | Final USD | Final AUD | Total return USD | CAGR USD | Max drawdown | Net dividends |",
        "|---|---|---|---|---|---|---|",
    ]
    for t, r in s0.items():
        p = r.perf
        lines.append(
            f"| {t} | US${p.final_usd:,.2f} | AUD {p.final_aud_after_fx:,.2f} | {pct(p.total_return_usd)} | "
            f"{pct(p.cagr_usd)} | {pct(p.max_drawdown.max_drawdown)} | US${p.dividends_net_usd:,.2f} |"
        )
    lines += ["", "## 2. Excess return vs S0 (USD, percentage points) — rows X, columns Y", ""]
    for t in s0:
        for label in ("S1", "S2"):
            grid = {(r.x, r.y): r for r in runs if r.ticker == t and r.label == label}
            lines += [
                f"**{label} on {t}**",
                "",
                "| X \\ Y | " + " | ".join(f"{y:.0%}" for y in XY_GRID) + " |",
                "|---|" + "---|" * len(XY_GRID),
            ]
            for x in XY_GRID:
                cells = []
                for y in XY_GRID:
                    r = grid[(x, y)]
                    cells.append(pts(excess_usd(r)) + (" (stranded)" if r.perf.stranded else ""))
                lines.append(f"| {x:.0%} | " + " | ".join(cells) + " |")
            lines.append("")
    lines += ["## 3. Patterns (counts only — not a recommendation)", ""]
    for t in s0:
        for label in ("S1", "S2"):
            rs = [r for r in runs if r.ticker == t and r.label == label]
            beat = sum(excess_usd(r) > 0 for r in rs)
            strand = sum(r.perf.stranded for r in rs)
            trips = sorted(r.perf.round_trips for r in rs)
            cash = [r.perf.pct_days_fully_in_cash for r in rs]
            lines.append(
                f"- {label} on {t}: beat S0 (USD) in {beat} of {len(rs)} runs; stranded in cash at the end in "
                f"{strand} of {len(rs)}; round trips {trips[0]}–{trips[-1]} (median {trips[len(trips) // 2]}); "
                f"days fully in cash {min(cash):.0%}–{max(cash):.0%}."
            )
    lines += [
        "",
        "Reminder (roadmap 5.7): a setting is never preferred because it traded more, and development-period",
        "results are exploration only. H1 is judged on the final test period with the EXPERIMENT_PLAN §6 rules.",
        '"Best 3 trades removed" (EXPERIMENT_PLAN §5) is Phase 6 — not computed here.',
        "",
        "## 4. Every run",
        "",
        (
            "| Run | Final USD | Final AUD | CAGR USD | Max DD | Round trips | Days in cash | Stranded (days) |"
            " Longest cash spell (days) | Fees + spread (USD) | Dividends missed vs S0 (USD) | Excess vs S0 USD / AUD (pts) |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in runs:
        p = r.perf
        name = f"{r.label} {r.ticker}" + (f" X{r.x:.0%} Y{r.y:.0%}" if r.x is not None else "")
        strand = f"yes ({p.stranded_days})" if p.stranded else "no"
        ex = "—" if r.label == "S0" else f"{pts(excess_usd(r))} / {pts(excess_aud(r))}"
        lines.append(
            f"| {name} | US${p.final_usd:,.2f} | AUD {p.final_aud_after_fx:,.2f} | {pct(p.cagr_usd)} | "
            f"{pct(p.max_drawdown.max_drawdown)} | {p.round_trips} | {pct(p.pct_days_fully_in_cash)} | {strand} | "
            f"{p.longest_cash_spell_days} | US${p.total_fees_usd + p.total_spread_cost_usd:,.2f} | "
            f"US${missed(r):,.2f} | {ex} |"
        )
    t, strategy, x, y = CHECK_RUN
    check = next(
        r for r in runs if r.ticker == t and r.config.strategy == strategy and r.x == x and r.y == y
    )
    lines += [
        "",
        f"## Appendix A — every trade of {STRATEGIES[strategy]} {t} X={x:.0%} Y={y:.0%} (for an independent re-check)",
        "",
        "Our simulated fills only (dates + fill prices), so chat Claude can recompute them from the raw CSV.",
        "Reference open = that day's open_raw; fill = open × (1 ± 0.05%); fee = Stake US$3.",
        "",
        "| # | Date | Side | Reference open | Fill price | Fee | Shares | Cash after |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, f in enumerate(check.out.result.fills, start=1):
        lines.append(
            f"| {i} | {f.day} | {f.side} | {f.reference_price_usd} | {f.fill_price_usd} | {f.fee.total_usd} | "
            f"{f.quantity} | {f.entry.cash_after_usd} |"
        )
    record = json.loads((check.out.run_dir / "run.json").read_text())
    lines += [
        "",
        (
            f"Start cash US${check.out.summary['start_cash_usd']}; dividends net US${check.perf.dividends_net_usd:,.2f}; "
            f"final value at last close US${check.perf.final_usd:,.2f}."
        ),
        "",
        "## Appendix B — data and code",
        "",
        f"- Code commit `{str(record['git_commit'])[:7]}` (dirty: {record['git_dirty']}); prices "
        f"{', '.join(sorted({json.loads((r.out.run_dir / 'run.json').read_text())['data_provenance']['file_name'] for r in runs[:1] + runs[-1:]}))}"
        " (Tiingo); FX " + ", ".join(record["fx_files"]) + " — Source: Reserve Bank of Australia.",
        f"- {len(runs)} run records under /data/runs/ (git-ignored). Base config: "
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
    sys.exit(main())
