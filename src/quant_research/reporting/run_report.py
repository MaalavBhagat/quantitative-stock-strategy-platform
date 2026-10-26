"""Markdown research report for one saved run (Phase 8, Step 8.6).

Everything comes from the run record (run.json + CSVs) via dashboard.data and metrics/ — no new maths.
"""

from quant_research.dashboard import data as dd
from quant_research.metrics.performance import stranded

LICENCE_NOTE = (
    "Source data licences: Tiingo price data — internal / personal use only; RBA exchange rates — personal, "
    "non-commercial use with attribution (Reserve Bank of Australia). Personal use; do not redistribute."
)


def build_run_report(run: dd.RunRecord, s0: dd.RunRecord | None, exploratory: bool = False) -> str:
    """Report with: banner, label, settings, data provenance, results vs S0, costs, round trips, stranded,
    the pre-registered verdict for the strategy, limitations, licence note."""
    key = dd.key_results(run, s0)
    s = run.summary
    is_stranded, stranded_days = stranded(run.fill_objects, run.days)
    label = (
        "**EXPLORATORY — NOT PRE-REGISTERED** (strategy-lab run; not part of any pre-registered test)"
        if exploratory
        else "Saved run from the pre-registered experiment set (records under data/runs/)."
    )
    out = [
        f"# Run report — {run.ticker} · {run.label} · {run.setting}",
        "",
        f"> **{dd.banner(run.period)}**",
        "",
        label,
        "",
        "## Settings",
        "",
        "| Item | Value |",
        "|---|---|",
        *[
            f"| {k} | {v} |"
            for k, v in dd.assumptions(run).items()
            if k not in ("Data files", "Code commit")
        ],
        f"| Grid override (outside EXPERIMENT_PLAN grid) | {run.config.get('grid_override')} |",
        "",
        "## Data provenance",
        "",
        f"- Data files: {dd.assumptions(run)['Data files']}",
        f"- Exchange rates: RBA files {', '.join(run.record.get('fx_files') or []) or dd.NOT_AVAILABLE}",
        f"- Code commit: {dd.assumptions(run)['Code commit']}",
        f"- Run started (UTC): {run.record.get('started_utc')}",
        "",
        "## Results vs S0 (buy-and-hold, same stock and period)",
        "",
        "| Measure | This run | S0 |",
        "|---|---|---|",
    ]
    key0 = dd.key_results(s0, None) if s0 is not None else {}
    for name in (
        "Final value (last close, USD)",
        "Final value (AUD, after selling + FX)",
        "Total return (USD)",
        "CAGR (USD)",
        "Max drawdown",
        "Sharpe (risk-free 0%)",
    ):
        out.append(f"| {name} | {key[name]} | {key0.get(name, dd.NOT_AVAILABLE)} |")
    out += [
        f"| Excess vs S0 (pp, USD) | {key['Excess vs S0 (pp, USD)']} | — |",
        "",
        "## Costs",
        "",
        f"- Fees total: US${float(s['total_fees_usd']):,.2f} (run record)",
        f"- Spread cost total: US${sum(float(f['spread_cost_usd']) for f in run.fills):,.2f} (sum of saved fills)",
        f"- Currency conversion fee when funding: US${float(s['fx_in_fee_usd']):,.2f}",
        f"- Currency conversion fee at the end: US${float(s['fx_out_fee_usd']):,.2f}",
        f"- Dividends net (after 15% withholding): US${float(s['dividends_net_usd']):,.2f}",
        "",
        "## Trading activity",
        "",
        f"- Round trips: {key['Round trips (sells)']} · fills: {len(run.fills)} · orders: "
        + ", ".join(f"{k} {v}" for k, v in s["orders"].items()),
        f"- Stranded at the end (sold and never bought back): {'yes' if is_stranded else 'no'}"
        + (f" — {stranded_days} trading days in cash at the end" if is_stranded else ""),
        "",
        "## Pre-registered verdict for this strategy (validation 2017–2020, MAIN settings)",
        "",
    ]
    verdict = dd.verdict_for(run.label)
    out += (
        [
            verdict,
            "",
            "Source: reports/experiments/validation_2017-2020.md §1 (rules: research/PREREGISTRATION.md).",
        ]
        if verdict
        else ["S0 is the benchmark — it has no verdict of its own."]
    )
    out += [
        "",
        "## Limitations",
        "",
        "- Survivors only, chosen with hindsight; daily bars; assumed spreads; no tax; one main data source —",
        "  see DATA_SOURCES.md §8 (Known limitations) and reports/RESULTS_SUMMARY.md §5.",
        "- A single run proves nothing: results depend on the period, the stock and the costs.",
        "",
        "---",
        f"*{dd.BANNER}. {LICENCE_NOTE}*",
        "",
    ]
    return "\n".join(out)
