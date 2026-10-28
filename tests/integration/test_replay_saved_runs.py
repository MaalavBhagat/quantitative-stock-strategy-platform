"""Phase 10, Step 10.1 — re-run 20 randomly chosen SAVED runs from their own config.yaml and get identical results.

Picks (seed 20261028) from data/runs/{validation,phase9,final}/ — the pre-registered batches. Each config is fed back
through backtesting.run with the registry (C1 / C2 load SPY, E1 loads the 8-K files covering the run's end date) and the
new record must match the saved one: last-close value, liquidation value, AUD at the end, and every fill.
This reproduces saved runs only; nothing is judged. Skipped automatically when data/ is absent (e.g. a fresh clone).
"""

import json
import random
from pathlib import Path

import pytest

from quant_research.backtesting.run import load_config, run_backtest
from quant_research.strategies.registry import make_strategy

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "data" / "runs"
BATCHES = ("validation", "phase9", "final")
SEED, N = 20261028, 20


def saved_runs() -> list[Path]:
    return sorted(p for b in BATCHES for p in (RUNS / b).rglob("run.json"))


AVAILABLE = saved_runs() if RUNS.exists() else []
REASON = "saved run records not present (data/ is git-ignored — licensed data; e.g. a fresh clone): replay test skipped"


@pytest.mark.skipif(len(AVAILABLE) < N, reason=REASON)
@pytest.mark.parametrize("index", range(N))
def test_saved_run_replays_identically(index, tmp_path):
    picked = random.Random(SEED).sample(AVAILABLE, N)[index]
    folder = picked.parent
    saved = json.loads(picked.read_text())
    config = load_config(folder / "config.yaml")
    again = run_backtest(config, make_strategy(config), runs_dir=tmp_path, repo_dir=tmp_path)
    for key in (
        "last_close_value_usd",
        "liquidation_value_usd",
        "end_aud_after_liquidation",
        "start_cash_usd",
    ):
        assert str(again.summary[key]) == saved["summary"][key], f"{folder.name}: {key}"
    assert (again.run_dir / "fills.csv").read_text() == (folder / "fills.csv").read_text(), (
        folder.name
    )
