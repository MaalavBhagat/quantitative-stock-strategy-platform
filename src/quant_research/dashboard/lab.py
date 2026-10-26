"""Strategy lab (Phase 8, Step 8.3): START runs only through backtesting.run — no strategy or accounting logic here.

Every lab run is EXPLORATORY — NOT PRE-REGISTERED: saved under data/runs/lab/ (never data/runs/validation/), with a
`lab.json` marker, and always paired with an S0 run on the same stock, period and cost variant. Periods offered:
development and validation only (D8 — the run.py lock refuses anything ≥ 2021-01-01 in any case). Settings outside
the EXPERIMENT_PLAN grid use run.py's `grid_override` (logged as exploratory by run.py itself).
"""

import json
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from quant_research.backtesting.run import (
    DEFAULT_RUNS_DIR,
    MR_K_GRID,
    MR_WINDOW_GRID,
    PROJECT_ROOT,
    XY_GRID,
    RunConfig,
    parse_config,
    run_backtest,
)
from quant_research.data.storage import git_state

LAB_DIR = DEFAULT_RUNS_DIR / "lab"
LABEL = "EXPLORATORY — NOT PRE-REGISTERED"
# (start, end, warm-up start) — the same dates the development and validation runs used
PERIODS: dict[str, tuple[date, date, date]] = {
    "development": (date(2010, 1, 4), date(2016, 12, 30), date(2008, 1, 1)),
    "validation": (date(2017, 1, 1), date(2020, 12, 31), date(2015, 1, 1)),
}
# name: (broker, spread level, share mode) — same as scripts/run_validation.py VARIANTS (a test checks they match)
VARIANTS: dict[str, tuple[str, str, str]] = {
    "main": ("stake", "normal", "fractional"),
    "tight": ("stake", "tight", "fractional"),
    "wide": ("stake", "wide", "fractional"),
    "ibkr": ("ibkr_fixed", "normal", "fractional"),
    "commsec": ("commsec_standard", "normal", "fractional"),
    "whole": ("stake", "normal", "whole"),
    "stress": ("commsec_standard", "wide", "fractional"),
}
STRATEGIES = {
    "S0": "s0_buy_and_hold",
    "S1": "s1_profit_target",
    "S2": "s2_pullback",
    "S3": "s3_mean_reversion",
    "S4-S1": "s4_trend_s1",
    "S4-S2": "s4_trend_s2",
}


@dataclass(frozen=True)
class LabSpec:
    ticker: str
    strategy: str  # label, e.g. "S4-S2"
    period: str  # "development" | "validation"
    variant: str  # key of VARIANTS
    x: Decimal | None = None  # S1/S2/S4: profit target X
    y: Decimal | None = None  # S1/S2/S4: dip Y
    k: Decimal | None = None  # S3
    w: int | None = None  # S3


@dataclass(frozen=True)
class LabResult:
    run_json: Path
    s0_json: Path
    git_dirty: bool | None
    on_grid: bool


def _params(spec: LabSpec) -> tuple[dict[str, Any], bool]:
    """Strategy parameters for run.py and whether they lie on the pre-registered grid."""
    if spec.strategy in ("S1", "S2", "S4-S1", "S4-S2"):
        if spec.x is None or spec.y is None:
            raise ValueError(f"{spec.strategy} needs X and Y")
        return {"profit_target_x": str(spec.x), "rebuy_dip_y": str(spec.y)}, (
            spec.x in XY_GRID and spec.y in XY_GRID
        )
    if spec.strategy == "S3":
        if spec.k is None or spec.w is None:
            raise ValueError("S3 needs k and w")
        return {"mr_k": str(spec.k), "mr_window": spec.w}, (
            spec.k in MR_K_GRID and spec.w in MR_WINDOW_GRID
        )
    if spec.strategy == "S0":
        return {}, True
    raise ValueError(f"unknown strategy {spec.strategy!r}")


def lab_config(spec: LabSpec, strategy_label: str | None = None) -> RunConfig:
    """RunConfig for the spec (or for S0 with the same stock / period / variant). Validated by run.parse_config."""
    if spec.period not in PERIODS:
        raise ValueError(f"lab periods are {list(PERIODS)} only (D8), got {spec.period!r}")
    if spec.variant not in VARIANTS:
        raise ValueError(f"unknown cost variant {spec.variant!r}")
    label = strategy_label or spec.strategy
    params, on_grid = _params(spec) if label == spec.strategy else ({}, True)
    start, end, warmup = PERIODS[spec.period]
    broker, spread, shares = VARIANTS[spec.variant]
    tag = "_".join(str(v) for v in params.values())
    raw = {
        "run_name": f"lab_{spec.period[:3]}_{spec.variant}_{label.lower().replace('-', '')}_{spec.ticker.lower()}"
        + (f"_{tag}" if tag else ""),
        "strategy": STRATEGIES[label],
        "ticker": spec.ticker,
        "start": start,
        "end": end,
        "warmup_start": warmup,
        "broker": broker,
        "spread_level": spread,
        "share_mode": shares,
        "initial_aud": "10000",
        "fx_source": "rba",
        "min_order_usd": "10",
        "reinvest_min_cash_usd": "100",
        "grid_override": not on_grid,
        "final_test_unlocked": False,
        **params,
    }
    return parse_config(raw)


def run_lab(
    spec: LabSpec, runs_dir: Path = LAB_DIR, repo_dir: Path = PROJECT_ROOT, **run_kwargs: Any
) -> LabResult:
    """Run the spec AND its S0 through backtesting.run.run_backtest; mark both folders EXPLORATORY.

    The git dirty flag is recorded by run_backtest (D6); it is also returned so the page can say so.
    `run_kwargs` pass through to run_backtest (tests: loaders / FX series).
    """
    from quant_research.strategies.registry import make_strategy  # local: registry imports run.py

    _, on_grid = _params(spec)
    dirty = git_state(repo_dir)["git_dirty"]
    outcomes = []
    for label in (spec.strategy, "S0") if spec.strategy != "S0" else ("S0",):
        config = lab_config(spec, label)
        outcomes.append(
            run_backtest(
                config, make_strategy(config), runs_dir=runs_dir, repo_dir=repo_dir, **run_kwargs
            )
        )
    s0_dir = outcomes[-1].run_dir
    for o in outcomes:
        marker = {
            "label": LABEL,
            "spec": {k: (str(v) if v is not None else None) for k, v in asdict(spec).items()},
            "on_pre_registered_grid": on_grid,
            "git_dirty": dirty,
            "paired_s0_run": s0_dir.name,
            "note": "Lab run started from the dashboard through backtesting.run; not part of any pre-registered test.",
        }
        (o.run_dir / "lab.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    return LabResult(outcomes[0].run_dir / "run.json", s0_dir / "run.json", dirty, on_grid)


def lab_runs(runs_dir: Path = LAB_DIR) -> list[tuple[Path, dict[str, Any]]]:
    """Saved lab runs (newest first) with their marker — S0 partner runs are listed with their pair."""
    out = []
    for marker in sorted(runs_dir.glob("*/lab.json"), reverse=True):
        out.append((marker.parent / "run.json", json.loads(marker.read_text(encoding="utf-8"))))
    return out
