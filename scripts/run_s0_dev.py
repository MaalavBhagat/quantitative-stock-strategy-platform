"""Phase 4: run S0 buy-and-hold on AAPL + XOM, development period 2010-01-04 → 2016-12-30.

Run:  uv run python scripts/run_s0_dev.py [--report]
Saves full run records under /data/runs/ (git-ignored). With --report, writes
reports/runs/s0_dev_2010-2016.md with SUMMARY NUMBERS ONLY (no price or equity series — licence).
Includes an independent sanity check from adjusted prices (no engine involved) and a
no-withholding what-if (same engine, withholding_rate = 0; not a saved run).
SIMULATED, HISTORICAL results — not a prediction and not advice.
"""

import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from quant_research.backtesting.engine import EngineSettings, run_engine
from quant_research.backtesting.run import RunConfig, RunOutcome, load_config, run_backtest
from quant_research.data.fx import load_usd_per_aud
from quant_research.data.loader import load_prices
from quant_research.metrics.performance import PerformanceSummary, summarise
from quant_research.strategies.registry import make_strategy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ["config/s0_buy_and_hold_aapl_dev.yaml", "config/s0_buy_and_hold_xom_dev.yaml"]
REPORT = PROJECT_ROOT / "reports" / "runs" / "s0_dev_2010-2016.md"
# STOP rule (changed 2026-10-25, approved by Goggy — chat Claude found the 5% limit too loose: a ~4% bug
# would pass). Two parts, so tax drag (depends on dividend yield) is checked separately from costs:
#   (1) S0 return must be LOWER than the adjusted-price return;
#   (2) the no-withholding what-if must be within 1.0% RELATIVE of the adjusted return (only costs +
#       entry timing remain in that gap).
WHAT_IF_MAX_RELATIVE = 0.01


@dataclass(frozen=True)
class Row:
    config: RunConfig
    out: RunOutcome
    perf: PerformanceSummary
    adjusted_return: float
    first_fill: date
    no_withholding_return: float

    @property
    def gap_points(self) -> float:
        return (self.adjusted_return - self.perf.total_return_usd) * 100

    @property
    def relative(self) -> float:
        """(1 + S0 return) / (1 + adjusted return) − 1."""
        return (1 + self.perf.total_return_usd) / (1 + self.adjusted_return) - 1

    @property
    def what_if_relative(self) -> float:
        """(1 + no-withholding what-if) / (1 + adjusted return) − 1."""
        return (1 + self.no_withholding_return) / (1 + self.adjusted_return) - 1


def adjusted_price_return(ticker: str, start: date, end: date, first_fill_day: date) -> float:
    """close_adj[last] / close_adj[day of first fill] − 1, straight from the Tiingo file."""
    df = load_prices(ticker, start, end, include_adjusted=True)
    first = df.loc[df["date"] == first_fill_day, "close_adj"].iloc[0]
    return float(df["close_adj"].iloc[-1] / first - 1)


def no_withholding_return(config: RunConfig, start_cash_usd: Decimal) -> float:
    """What-if: same prices, strategy and start cash, but no dividend withholding."""
    settings = EngineSettings(
        config.broker, config.spread_level, config.share_mode, config.min_order_usd, Decimal(0)
    )
    prices = load_prices(config.ticker, config.start, config.end)
    result = run_engine(prices, config.ticker, make_strategy(config), settings, start_cash_usd)
    return float(result.last_close_value_usd) / float(start_cash_usd) - 1


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    fx = load_usd_per_aud()
    rows: list[Row] = []
    for path in CONFIGS:
        config = load_config(PROJECT_ROOT / path)
        out = run_backtest(config, make_strategy(config), fx_series=fx)
        s = out.summary
        perf = summarise(
            out.result,
            s["start_cash_usd"],
            config.initial_aud,
            s["end_aud_after_liquidation"],
            fx.on,
        )
        first_fill = out.result.fills[0].day
        row = Row(
            config,
            out,
            perf,
            adjusted_price_return(config.ticker, config.start, config.end, first_fill),
            first_fill,
            no_withholding_return(config, s["start_cash_usd"]),
        )
        rows.append(row)
        print(
            f"{config.ticker}: run {out.run_id} | S0 {perf.total_return_usd:.4%} | adjusted "
            f"{row.adjusted_return:.4%} | gap {row.gap_points:.2f} pts | relative {row.relative:+.3%} | "
            f"no-withholding what-if {row.no_withholding_return:.4%} (relative {row.what_if_relative:+.3%}) | "
            f"fills {len(out.result.fills)}"
        )
    problems = [
        f"{r.config.ticker}: S0 {r.perf.total_return_usd:.4%} vs adjusted {r.adjusted_return:.4%}; "
        f"no-withholding what-if relative {r.what_if_relative:+.2%}"
        for r in rows
        if r.perf.total_return_usd >= r.adjusted_return
        or abs(r.what_if_relative) > WHAT_IF_MAX_RELATIVE
    ]
    if problems:
        print("STOP — sanity check failed, report NOT written:\n  " + "\n  ".join(problems))
        return 1
    if "--report" in sys.argv:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(build_report(rows), encoding="utf-8")
        print(f"report written: {REPORT.relative_to(PROJECT_ROOT)}")
    return 0


def pct(x: float | None) -> str:
    return "—" if x is None else f"{x:.2%}"


def build_report(rows: list[Row]) -> str:
    lines = [
        "# S0 buy-and-hold — development period 2010–2016 (Phase 4)",
        "",
        "> **SIMULATED, HISTORICAL results on the development period only.** Not a prediction, not",
        "> advice. Benchmark for later strategies. Summary numbers only — no price or equity series",
        "> (Tiingo licence: internal use; RBA data attributed below). Full run records are in /data/runs/.",
        "",
        "## 1. Results",
        "",
        "| | " + " | ".join(r.config.ticker for r in rows) + " |",
        "|---|" + "---|" * len(rows),
    ]

    def add(label: str, values: list[str]) -> None:
        lines.append(f"| {label} | " + " | ".join(values) + " |")

    def each(fn) -> list[str]:
        return [fn(r) for r in rows]

    add(
        "Start: AUD → USD (RBA rate, day, FX fee)",
        each(
            lambda r: (
                f"AUD {r.out.summary['initial_aud']} → US${r.out.summary['start_cash_usd']} "
                f"({r.out.summary['usd_per_aud_start']} on {r.out.summary['usd_per_aud_start_for_day']}, "
                f"fee US${r.out.summary['fx_in_fee_usd']})"
            )
        ),
    )
    add("First fill (day-2 open)", each(lambda r: str(r.first_fill)))
    add("Final value at last close (USD)", each(lambda r: f"US${r.perf.final_usd:,.2f}"))
    add(
        "Liquidation value (USD, after spread + fee)",
        each(lambda r: f"US${r.perf.liquidation_usd:,.2f}"),
    )
    add(
        "Final AUD (after end FX fee; RBA rate, day)",
        each(
            lambda r: (
                f"AUD {r.perf.final_aud_after_fx:,.2f} ({r.out.summary['usd_per_aud_end']} on "
                f"{r.out.summary['usd_per_aud_end_for_day']})"
            )
        ),
    )
    add(
        "Total return USD / AUD",
        each(lambda r: f"{pct(r.perf.total_return_usd)} / {pct(r.perf.total_return_aud)}"),
    )
    add("CAGR USD / AUD", each(lambda r: f"{pct(r.perf.cagr_usd)} / {pct(r.perf.cagr_aud)}"))
    add(
        "Max drawdown USD (peak → trough)",
        each(
            lambda r: (
                f"{pct(r.perf.max_drawdown.max_drawdown)} ({r.perf.max_drawdown.peak_day} → "
                f"{r.perf.max_drawdown.trough_day})"
            )
        ),
    )
    add(
        "Max drawdown AUD (peak → trough)",
        each(
            lambda r: (
                f"{pct(r.perf.max_drawdown_aud.max_drawdown)} ({r.perf.max_drawdown_aud.peak_day} → "
                f"{r.perf.max_drawdown_aud.trough_day})"
            )
        ),
    )
    add("Annual volatility (USD)", each(lambda r: pct(r.perf.annual_volatility)))
    add("Sharpe (rf = 0, USD)", each(lambda r: f"{r.perf.sharpe:.2f}"))
    add(
        "Worst calendar year (USD)",
        each(lambda r: f"{r.perf.worst_year[0]}: {pct(r.perf.worst_year[1])}"),
    )
    add(
        "Fees / spread cost (USD)",
        each(lambda r: f"US${r.perf.total_fees_usd:,.2f} / US${r.perf.total_spread_cost_usd:,.2f}"),
    )
    add(
        "Dividends gross / withheld / net (USD)",
        each(
            lambda r: (
                f"US${r.perf.dividends_gross_usd:,.2f} / US${r.perf.withholding_usd:,.2f} / "
                f"US${r.perf.dividends_net_usd:,.2f}"
            )
        ),
    )
    add(
        "Buys (first + reinvestments when cash ≥ US$100)",
        each(lambda r: str(len(r.out.result.fills))),
    )
    add("Days fully in cash", each(lambda r: pct(r.perf.pct_days_fully_in_cash)))
    add("Round trips", each(lambda r: str(r.perf.round_trips)))
    lines += [
        "",
        "## 2. Independent sanity check (no engine)",
        "",
        'close_adj[last] ÷ close_adj[first-fill day] − 1 from the Tiingo file ≈ "buy-and-hold with dividends',
        'reinvested, no costs, no tax". S0 should be close but a bit LOWER.',
        "",
        (
            "| | S0 USD return | Adjusted-price return | Gap (points) | Relative | S0 with NO withholding "
            "(what-if) | What-if relative (limit ±1%) | Explained by withholding (points) | Rest (points) |"
        ),
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.config.ticker} | {pct(r.perf.total_return_usd)} | {pct(r.adjusted_return)} | "
            f"{r.gap_points:.2f} | {r.relative:+.2%} | {pct(r.no_withholding_return)} | "
            f"{r.what_if_relative:+.2%} | "
            f"{(r.no_withholding_return - r.perf.total_return_usd) * 100:.2f} | "
            f"{(r.adjusted_return - r.no_withholding_return) * 100:.2f} |"
        )
    lines += [
        "",
        "**Why S0 is lower.** The biggest part is the 15% US tax withheld on every dividend — the adjusted",
        "price assumes dividends are reinvested tax-free. The rest: a US$3 fee and 0.05% spread on each buy,",
        "reinvesting only once cash reaches US$100, and entering at the day-2 open while the adjusted return",
        "is measured from the day-2 close (this last part can be + or −).",
        "",
        "**Check rule (changed 2026-10-25, approved by Goggy).** (1) S0 must be LOWER than the adjusted-price",
        "return. (2) The no-withholding what-if must be within 1.0% RELATIVE of the adjusted return — tax drag",
        "depends on the dividend yield, so it is checked separately; only costs + entry timing remain in that",
        'gap, so 1% still catches real bugs. History: prompt 12\'s "~3 points" rule was exceeded (AAPL, XOM),',
        "investigated and accepted (2026-10-21); a 5% relative limit was then judged too loose by chat Claude",
        "(a ~4% bug would pass). The what-if is computed by this script with the engine setting",
        "withholding_rate = 0; it is not a saved run.",
        "",
        "## 3. Config and data used",
        "",
    ]
    for r in rows:
        record = json.loads((r.out.run_dir / "run.json").read_text())
        prov = record["data_provenance"]
        lines += [
            (
                f"**{r.config.ticker}** — run `{r.out.run_id}`, code commit `{str(record['git_commit'])[:7]}` "
                f"(dirty: {record['git_dirty']})"
            ),
            f"- Config: {json.dumps({k: str(v) for k, v in asdict(r.config).items()})}",
            f"- Prices: {prov['file_name']} (Tiingo, downloaded {prov['downloaded_at_utc']})",
            (
                f"- FX: {', '.join(record['fx_files'])} — Source: Reserve Bank of Australia (FXRUSD, latest "
                "rate dated ≤ day)"
            ),
            "",
        ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    from _help import handle_help  # --help: describe and exit, do nothing else

    handle_help(__doc__)
    sys.exit(main())
