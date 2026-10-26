"""Tests for quant_research.dashboard.lab — runs go through backtesting.run with synthetic prices (no data/)."""

import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from quant_research.backtesting.run import FinalTestLockedError
from quant_research.backtesting.synthetic import make_prices
from quant_research.dashboard import lab
from quant_research.data.fx import FxSeries

SPEC = lab.LabSpec("AAA", "S1", "validation", "main", x=Decimal("0.02"), y=Decimal("0.04"))


def synthetic_loader(calls: list):
    def load(ticker, warmup_start, start, end):
        calls.append((ticker, warmup_start, start, end))
        # 30 weekdays from 2017-01-02: rise, fall, rise — enough for S1 to trade
        closes = (
            [100 + i for i in range(10)]
            + [109 - i for i in range(10)]
            + [100 + i for i in range(10)]
        )
        return make_prices(closes, closes, start=date(2017, 1, 2))

    return load


def fx_constant() -> FxSeries:
    days = (
        tuple(date(2016, 12, 1 + i) for i in range(31))
        + tuple(date(2017, 1, 1 + i) for i in range(31))
        + tuple(date(2017, 2, 1 + i) for i in range(28))
    )
    return FxSeries(days, tuple(Decimal("0.75") for _ in days), ("synthetic",))


def dirty_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git = ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid"]
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "committed.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-q", "-m", "init"], cwd=repo, check=True)
    (repo / "uncommitted.txt").write_text("x")  # → dirty
    return repo


def test_lab_config_labels_off_grid_and_uses_period_dates():
    on = lab.lab_config(SPEC)
    assert (
        on.grid_override is False
        and on.start == date(2017, 1, 1)
        and on.warmup_start == date(2015, 1, 1)
    )
    off = lab.lab_config(
        lab.LabSpec("AAA", "S1", "development", "commsec", x=Decimal("0.07"), y=Decimal("0.04"))
    )
    assert off.grid_override is True  # outside the grid → run.py's exploratory switch
    assert (off.broker, off.start, off.end) == (
        "commsec_standard",
        date(2010, 1, 4),
        date(2016, 12, 30),
    )
    s0 = lab.lab_config(SPEC, "S0")
    assert (
        s0.strategy == "s0_buy_and_hold" and s0.profit_target_x is None and s0.broker == on.broker
    )


def test_lab_offers_only_development_and_validation():
    assert set(lab.PERIODS) == {"development", "validation"}
    assert all(end < date(2021, 1, 1) for _, end, _ in lab.PERIODS.values())
    with pytest.raises(ValueError, match="D8"):
        lab.lab_config(
            lab.LabSpec("AAA", "S1", "final", "main", x=Decimal("0.02"), y=Decimal("0.04"))
        )


def test_variants_match_the_validation_runs():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from run_validation import VARIANTS

    assert lab.VARIANTS == VARIANTS


def test_run_lab_runs_through_run_py_pairs_s0_and_marks_exploratory(tmp_path):
    calls: list = []
    res = lab.run_lab(
        SPEC,
        runs_dir=tmp_path / "lab",
        repo_dir=dirty_repo(tmp_path),
        warmup_load_fn=synthetic_loader(calls),
        fx_series=fx_constant(),
    )
    assert len(calls) == 2  # the strategy AND its S0, both loaded by run.py
    assert (
        res.run_json.parent.parent == tmp_path / "lab"
        and res.s0_json.parent.parent == tmp_path / "lab"
    )
    rec = json.loads(res.run_json.read_text())
    s0 = json.loads(res.s0_json.read_text())
    assert (
        rec["config"]["strategy"] == "s1_profit_target"
        and s0["config"]["strategy"] == "s0_buy_and_hold"
    )
    marker = json.loads((res.run_json.parent / "lab.json").read_text())
    assert marker["label"] == "EXPLORATORY — NOT PRE-REGISTERED"
    assert marker["paired_s0_run"] == res.s0_json.parent.name
    # dirty tree: the lab says so AND run.py records it in the run record (D6)
    assert res.git_dirty is True and rec["git_dirty"] is True and marker["git_dirty"] is True
    assert [p.name for p, _ in lab.lab_runs(tmp_path / "lab")].count("run.json") == 2


def test_engine_lock_still_applies_through_the_lab(tmp_path, monkeypatch):
    monkeypatch.setitem(
        lab.PERIODS, "validation", (date(2021, 1, 4), date(2021, 6, 30), date(2020, 1, 1))
    )
    calls: list = []
    with pytest.raises(FinalTestLockedError):
        lab.run_lab(
            SPEC,
            runs_dir=tmp_path / "lab",
            warmup_load_fn=synthetic_loader(calls),
            fx_series=fx_constant(),
        )
    assert calls == []  # refused BEFORE any data was loaded
    assert not (tmp_path / "lab").exists()
