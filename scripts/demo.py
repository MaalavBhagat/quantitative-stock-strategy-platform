"""Demo on MADE-UP prices — runs without any licensed data or API key (Phase 11, Step 11.2).

Run:  uv run python scripts/demo.py            (≈ 10 s; writes demo_output/, git-ignored)
      uv run python scripts/demo.py --update-docs   (also copies the charts to docs/images/ for the README)
Makes a synthetic stock "DEMO" (random walk, fixed seed, quarterly dividends, one 2:1 split) and a synthetic market index
"MKT", then runs Buy-and-hold (S0), Trend filter + pullback (S4-S2, X 2% / Y 4%) and Market-trend gate (C1) through the
REAL engine (backtesting.run: costs, ledger, T close → T+1 open, run records). FX is fixed at 0.70 USD per AUD.
Prints a results table, writes demo_output/demo_report.md (incl. an example trade list) and three charts.
Everything it shows is SIMULATED on MADE-UP data — it says nothing about any real stock.
"""

import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "demo_output"
DOCS_IMAGES = PROJECT_ROOT / "docs" / "images"
SEED = 20261030
WARMUP, START, END = date(2011, 1, 3), date(2012, 1, 2), date(2016, 12, 30)
LABEL = "SIMULATED — made-up prices (scripts/demo.py), not a real stock"
RUNS = [  # (strategy, settings)
    ("s0_buy_and_hold", {}),
    ("s4_trend_s2", {"profit_target_x": "0.02", "rebuy_dip_y": "0.04"}),
    ("c1_market_gate", {}),
]


def weekdays(start: date, end: date) -> list[date]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def synthetic_prices(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(stock, market) tables in the loader's raw format. Same seed → same prices, every time."""
    rng = np.random.default_rng(seed)
    days = weekdays(WARMUP, END)
    n = len(days)
    market_ret = rng.normal(0.0003, 0.010, n)
    stock_ret = 1.1 * market_ret + rng.normal(0.0001, 0.012, n)

    def table(
        returns: np.ndarray, start_price: float, dividends: bool, split_row: int | None
    ) -> pd.DataFrame:
        close = start_price * np.exp(np.cumsum(returns))
        gap = rng.normal(0.0, 0.004, n)
        open_ = np.concatenate([[start_price], close[:-1]]) * np.exp(gap)
        div = np.zeros(n)
        split = np.ones(n)
        if dividends:
            div[np.arange(40, n, 63)] = 0.005 * close[np.arange(40, n, 63)]  # ~0.5% each quarter
        if split_row is not None:  # 2:1 split: every raw price from that day on is halved
            close[split_row:] /= 2
            open_[split_row:] /= 2
            div[split_row:] /= 2
            split[split_row] = 2.0
        return pd.DataFrame(
            {
                "date": days,
                "open_raw": open_.round(4),
                "high_raw": (np.maximum(open_, close) * 1.004).round(4),
                "low_raw": (np.minimum(open_, close) * 0.996).round(4),
                "close_raw": close.round(4),
                "volume_raw": rng.integers(800_000, 1_200_000, n),
                "div_cash_usd": div.round(4),
                "split_factor": split,
            }
        )

    return table(stock_ret, 50.0, True, n // 2), table(market_ret, 200.0, False, None)


def run_demo(out: Path = OUT, update_docs: bool = False) -> list[dict]:
    from quant_research.backtesting.run import parse_config, run_backtest
    from quant_research.dashboard import data as dd
    from quant_research.strategies import labels
    from quant_research.strategies.registry import make_strategy

    if out.exists():
        shutil.rmtree(out)  # demo output only — regenerated every time
    out.mkdir(parents=True)
    stock, market = synthetic_prices()
    records = []
    for strategy, settings in RUNS:
        config = parse_config({
            "run_name": f"demo_{labels.of_config(strategy).lower().replace('-', '')}", "strategy": strategy,
            "ticker": "DEMO", "start": START, "end": END, "warmup_start": WARMUP, "broker": "stake",
            "spread_level": "normal", "share_mode": "fractional", "initial_aud": "10000", "fx_source": "fixed",
            "usd_per_aud_start": "0.70", "usd_per_aud_end": "0.70", **settings,
        })  # fmt: skip
        outcome = run_backtest(
            config,
            make_strategy(config, market=market, events=[]),
            warmup_load_fn=lambda *_: stock.copy(),
            runs_dir=out / "runs" / "demo",
            repo_dir=PROJECT_ROOT,
        )
        records.append(dd.load_run(outcome.run_dir / "run.json", "demo"))
    s0 = records[0]
    rows = []
    for r in records:
        k = dd.key_results(r, s0 if r is not s0 else None)
        rows.append({"Strategy": f"{labels.display(r.label)} {r.setting if r.setting != '—' else ''}".strip(),
                     "Final value (USD)": k["Final value (last close, USD)"], "Total return": k["Total return (USD)"],
                     "CAGR": k["CAGR (USD)"], "Max drawdown": k["Max drawdown"].split(" ")[0],
                     "Round trips": k["Round trips (sells)"], "Fees (USD)": k["Fees total (USD)"],
                     "Excess vs Buy-and-hold (pp)": k["Excess vs S0 (pp, USD)"] if r is not s0 else "—"})  # fmt: skip
    write_report(out, rows, records[1])
    write_charts(out, records, update_docs)
    return rows


def write_report(out: Path, rows: list[dict], example) -> None:
    from quant_research.dashboard import data as dd
    from quant_research.strategies import labels

    head = list(rows[0])
    lines = [
        "# Demo results — SIMULATED on MADE-UP prices",
        "",
        f"> {LABEL}. Real engine, Stake costs, FX fixed at 0.70. Says nothing about any real stock; not financial advice.",
        "",
        "| " + " | ".join(head) + " |",
        "|" + "---|" * len(head),
        *["| " + " | ".join(str(r[h]) for h in head) + " |" for r in rows],
        "",
        f"## Example trade analysis — {labels.display(example.label)} {example.setting} (first 12 fills)",
        "",
        "| Date | Side | Shares | Fill price (USD) | Fee (USD) | Realised P&L (USD) |",
        "|---|---|---|---|---|---|",
    ]
    table = dd.fills_table(example)
    for _, f in table.head(12).iterrows():
        lines.append(f"| {f['date']} | {f['side']} | {f['shares']} | {float(f['fill (USD)']):.2f} | "
                     f"{f['fee (USD)']} | {f['realised P&L (USD)']} |")  # fmt: skip
    lines += [
        "",
        f"{len(table)} fills in total; the split day (2:1) is handled by the ledger — shares double, price halves.",
        "",
    ]
    (out / "demo_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_charts(out: Path, records: list, update_docs: bool) -> None:
    import altair as alt
    import vl_convert as vlc

    from quant_research.dashboard import chart_style as cs
    from quant_research.dashboard import data as dd
    from quant_research.strategies import labels

    bench = labels.display("S0")
    parts = []
    for r in records:
        name = labels.display(r.label) + (f" {r.setting}" if r.setting != "—" else "")
        parts.append(dd.equity_table(r).assign(series=name))
    data = pd.concat(parts)
    names = list(data["series"].unique())
    title = {"text": "", "subtitle": LABEL}
    charts = {
        "demo_equity.png": alt.Chart(data, title={**title, "text": "Total value (USD) — demo"})
        .mark_line()
        .encode(
            x=cs.date_x(), y=alt.Y("total_usd:Q", title="USD"), **cs.series_lines(names, bench)
        ),
        "demo_drawdown.png": alt.Chart(data, title={**title, "text": "Drawdown — demo"})
        .mark_line()
        .encode(
            x=cs.date_x(),
            y=alt.Y("drawdown:Q", title="Drawdown", axis=alt.Axis(format="%")),
            **cs.series_lines(names, bench),
        ),
        "demo_comparison.png": alt.Chart(
            pd.DataFrame({"series": names, "total_return": [r.total_return for r in records]}),
            title={**title, "text": "Total return by strategy — demo"},
        )
        .mark_bar()
        .encode(
            y=alt.Y("series:N", title="", sort=None, axis=alt.Axis(labelLimit=0)),
            x=alt.X("total_return:Q", title="Total return (USD)", axis=alt.Axis(format="%")),
            color=alt.Color(
                "series:N",
                scale=alt.Scale(domain=names, range=[cs.BUY_AND_HOLD, cs.STRATEGY, cs.EXTRA[0]]),
                legend=None,
            ),
        ),
    }
    for file, chart in charts.items():
        png = vlc.vegalite_to_png(
            chart.properties(width=760, height=320).configure(background="#F7EFE4").to_json(),
            scale=2,
        )
        (out / file).write_bytes(png)
        if update_docs:
            DOCS_IMAGES.mkdir(parents=True, exist_ok=True)
            (DOCS_IMAGES / file).write_bytes(png)


def main() -> int:
    import time

    started = time.time()
    rows = run_demo(update_docs="--update-docs" in sys.argv)
    head = list(rows[0])
    widths = [max(len(h), *(len(str(r[h])) for r in rows)) for h in head]
    print(LABEL)
    print("  ".join(h.ljust(w) for h, w in zip(head, widths, strict=True)))
    for r in rows:
        print("  ".join(str(r[h]).ljust(w) for h, w in zip(head, widths, strict=True)))
    print(f"\nwritten: {OUT.relative_to(PROJECT_ROOT)}/demo_report.md + demo_equity.png, demo_drawdown.png, "
          f"demo_comparison.png ({time.time() - started:.1f} s)")  # fmt: skip
    return 0


if __name__ == "__main__":
    from _help import handle_help  # --help: describe and exit, do nothing else

    handle_help(__doc__)
    sys.exit(main())
