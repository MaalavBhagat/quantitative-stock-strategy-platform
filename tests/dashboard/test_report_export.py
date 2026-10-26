"""Tests for reporting.run_report and dashboard.export (report sections, licence headers, config round trip)."""

from decimal import Decimal

import pytest
import yaml
from test_data import make_run

from quant_research.backtesting.run import load_config, run_backtest
from quant_research.dashboard import data as dd
from quant_research.dashboard import export as ex
from quant_research.reporting.run_report import build_run_report
from quant_research.strategies.registry import make_strategy

SECTIONS = [
    "## Settings",
    "## Data provenance",
    "## Results vs S0",
    "## Costs",
    "## Trading activity",
    "## Pre-registered verdict for this strategy",
    "## Limitations",
]


def test_report_has_every_section_banner_and_limitations_link(tmp_path):
    run = dd.load_run(make_run(tmp_path), "validation")
    text = build_run_report(run, None, exploratory=True)
    for section in SECTIONS:
        assert section in text
    assert "SIMULATED, HISTORICAL — not financial advice" in text
    assert "EXPLORATORY — NOT PRE-REGISTERED" in text
    assert "DATA_SOURCES.md §8" in text
    assert "| Excess vs S0 (pp, USD) | not available |" in text
    assert "Personal use; do not redistribute." in text


def test_report_marks_stranded_from_the_saved_fills(tmp_path):
    # last fill is a sell to 0 shares and no buy follows → stranded (metrics.performance.stranded)
    run = dd.load_run(make_run(tmp_path), "validation")
    assert run.fills[-1]["side"] == "sell"
    text = build_run_report(run, None)
    assert (
        "Stranded at the end (sold and never bought back): yes — 1 trading days in cash at the end"
        in text
    )


def test_text_exports_carry_the_licence_header(tmp_path):
    run = dd.load_run(make_run(tmp_path), "validation")
    texts = ex.export_texts(run, None)
    assert set(texts) == {
        "trades.csv",
        "orders.csv",
        "equity.csv",
        "config.yaml",
        "report.md",
        "LICENCE.txt",
    }
    for name in ("trades.csv", "orders.csv", "equity.csv", "config.yaml"):
        assert texts[name].startswith(
            "# SIMULATED, HISTORICAL — not financial advice.\n# Source data licences"
        )
    assert (
        "do not redistribute" in texts["LICENCE.txt"]
        and "do not redistribute" in texts["report.md"]
    )
    paths = ex.write_exports(run, None, out_root=tmp_path / "exports", with_chart=False)
    assert paths["trades.csv"].parent == tmp_path / "exports" / "r1"
    assert all(p.exists() for p in paths.values())


# ---------- reproducibility: exported config → run.py → identical result (real local records) ----------
REAL = dd.RUNS_DIR / "validation" / "main"


@pytest.mark.skipif(not REAL.exists(), reason="local run records (data/, git-ignored) not present")
def test_exported_config_reproduces_the_run_exactly(tmp_path):
    original = dd.load_run(
        dd.run_index("validation")[("S4-S2", "AAPL", "X 2% / Y 4%")], "validation"
    )
    exported = ex.write_exports(original, None, out_root=tmp_path / "exports", with_chart=False)[
        "config.yaml"
    ]
    assert exported.read_text().startswith("# ")  # header comments …
    config = load_config(exported)  # … are ignored by the YAML reader
    assert yaml.safe_load(exported.read_text())["run_name"] == original.config["run_name"]
    rerun = run_backtest(config, make_strategy(config), runs_dir=tmp_path / "rerun")
    s, o = rerun.summary, original.summary
    assert str(s["last_close_value_usd"]) == o["last_close_value_usd"] == "22849.41"
    assert str(s["end_aud_after_liquidation"]) == o["end_aud_after_liquidation"]
    assert Decimal(str(s["total_fees_usd"])) == Decimal(o["total_fees_usd"])
    assert len(rerun.result.fills) == len(original.fills) == 23


def test_chart_png_is_a_png(tmp_path):
    pytest.importorskip("vl_convert")
    pytest.importorskip("altair")
    run = dd.load_run(make_run(tmp_path), "validation")
    png = ex.chart_png(run, None)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 1000
