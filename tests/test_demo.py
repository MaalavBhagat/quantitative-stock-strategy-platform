"""scripts/demo.py — the made-up-data demo runs without licensed data and is repeatable (Phase 11.2)."""

import importlib.util
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(
    0, str(SCRIPTS)
)  # demo.py imports the scripts' --help helper only when run directly
SPEC = importlib.util.spec_from_file_location("demo", SCRIPTS / "demo.py")
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


def test_synthetic_prices_are_repeatable_and_include_a_split_and_dividends():
    a, market = demo.synthetic_prices()
    b, _ = demo.synthetic_prices()
    assert a.equals(b) and len(a) == len(market)
    assert (a["split_factor"] == 2.0).sum() == 1 and (a["div_cash_usd"] > 0).sum() > 10


def test_demo_runs_through_the_real_engine_quickly_and_writes_its_outputs(tmp_path):
    started = time.time()
    rows = demo.run_demo(tmp_path)
    assert time.time() - started < 120
    assert [r["Strategy"].split(" (")[0] for r in rows] == [
        "Buy-and-hold",
        "Trend filter + pullback",
        "Market-trend gate",
    ]
    assert rows[0]["Final value (USD)"] == "US$24,423.22"  # same seed → same result, every time
    for name in ("demo_report.md", "demo_equity.png", "demo_drawdown.png", "demo_comparison.png"):
        assert (tmp_path / name).stat().st_size > 0
    assert "SIMULATED" in (tmp_path / "demo_report.md").read_text()
    assert len(list((tmp_path / "runs" / "demo").glob("*/run.json"))) == 3
