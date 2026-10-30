"""Export one saved run (Phase 8, Step 8.7): trade log CSV, equity CSV, config YAML, Markdown report, chart PNG.

Files go to data/exports/<run id>/ (git-ignored). Every text file starts with the licence header; the PNG is
accompanied by LICENCE.txt in the same folder. The CSVs are the SAVED rows at full precision (not display-rounded),
so they can be re-checked. The config YAML is the run's own config.yaml (comments only added) — feeding it back
into backtesting.run gives the identical result (tests/dashboard/test_export.py).
"""

from pathlib import Path

from quant_research.dashboard import data as dd
from quant_research.reporting.run_report import LICENCE_NOTE, build_run_report
from quant_research.strategies import labels

EXPORTS_DIR = dd.PROJECT_ROOT / "data" / "exports"


def header(comment: str = "# ") -> str:
    lines = [
        f"{dd.BANNER}.",
        LICENCE_NOTE,
        "Exported from a saved run record of the Quantitative Stock Strategy Research Platform.",
    ]
    return "".join(f"{comment}{ln}\n" for ln in lines)


def _csv_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def export_texts(
    run: dd.RunRecord, s0: dd.RunRecord | None, exploratory: bool = False
) -> dict[str, str]:
    """File name → content for the text exports (also used by the dashboard download buttons)."""
    folder = run.path.parent
    return {
        "trades.csv": header() + _csv_text(folder / "fills.csv"),
        "orders.csv": header() + _csv_text(folder / "orders.csv"),
        "equity.csv": header() + _csv_text(folder / "equity.csv"),
        "config.yaml": header() + _csv_text(folder / "config.yaml"),
        "report.md": build_run_report(run, s0, exploratory),
        "LICENCE.txt": header(comment=""),
    }


def equity_chart(run: dd.RunRecord, s0: dd.RunRecord | None):
    """Altair chart: total value (USD) of the run and of S0 — the same data as the Performance page."""
    import altair as alt
    import pandas as pd

    parts = [dd.equity_table(run).assign(series=f"{labels.display(run.label)} {run.setting}")]
    if s0 is not None and run.label != "S0":
        parts.append(dd.equity_table(s0).assign(series=labels.display("S0")))
    from quant_research.dashboard import chart_style as cs

    data = pd.concat(parts)[["day", "total_usd", "series"]]
    return (
        alt.Chart(data, title=f"{run.title} — total value (USD). {dd.BANNER}")
        .mark_line()
        .encode(
            x=alt.X("day:T", title="Date"),
            y=alt.Y("total_usd:Q", title="USD"),
            **cs.series_lines(list(data["series"].unique()), labels.display("S0")),
        )
        .properties(width=900, height=400)
    )


def chart_png(run: dd.RunRecord, s0: dd.RunRecord | None) -> bytes:
    import vl_convert as vlc

    return vlc.vegalite_to_png(equity_chart(run, s0).to_json(), scale=2)


def write_exports(
    run: dd.RunRecord,
    s0: dd.RunRecord | None,
    exploratory: bool = False,
    out_root: Path = EXPORTS_DIR,
    with_chart: bool = True,
) -> dict[str, Path]:
    """Write every export of the run into out_root/<run id>/ and return the paths."""
    out = out_root / run.record["run_id"]
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, text in export_texts(run, s0, exploratory).items():
        paths[name] = out / name
        paths[name].write_text(text, encoding="utf-8")
    if with_chart:
        paths["chart.png"] = out / "chart.png"
        paths["chart.png"].write_bytes(chart_png(run, s0))
    return paths
