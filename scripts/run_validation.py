"""Phase 6, Steps 6.1–6.6: the VALIDATION runs, exactly as pre-registered (research/PREREGISTRATION.md, tag prereg-v1.1).

Run:  uv run python scripts/run_validation.py
- Period 2017-01-01 → 2020-12-31 (trading from the first session, 2017-01-03); warm-up rows from 2015-01-01 are used
  ONLY for indicators. AUD 10,000 at the RBA rate. D8 lock stays on (nothing ≥ 2021-01-01).
- 8 stocks × (S0 + 70 settings) = 568 MAIN runs, plus the same 568 for each sensitivity variant:
  tight · wide · ibkr · commsec · whole · stress (wide + CommSec) → 3,976 runs, under /data/runs/validation/<variant>/.
- Refuses to start from a dirty working tree (every record must say dirty: False).
- Prints progress COUNTS only — no result is printed or summarised here (prompt 17). The report is a separate script.
"""

import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from functools import cache
from pathlib import Path

from quant_research.backtesting.run import (
    DEFAULT_RUNS_DIR,
    MR_K_GRID,
    MR_WINDOW_GRID,
    XY_GRID,
    RunConfig,
    parse_config,
    run_backtest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = DEFAULT_RUNS_DIR / "validation"
TICKERS = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "T", "SPY"]
START, END, WARMUP = date(2017, 1, 1), date(2020, 12, 31), date(2015, 1, 1)
VARIANTS = {  # name: (broker, spread_level, share_mode) — PREREGISTRATION §4
    "main": ("stake", "normal", "fractional"),
    "tight": ("stake", "tight", "fractional"),
    "wide": ("stake", "wide", "fractional"),
    "ibkr": ("ibkr_fixed", "normal", "fractional"),
    "commsec": ("commsec_standard", "normal", "fractional"),
    "whole": ("stake", "normal", "whole"),
    "stress": ("commsec_standard", "wide", "fractional"),
}
LABELS = {
    "s0_buy_and_hold": "s0",
    "s1_profit_target": "s1",
    "s2_pullback": "s2",
    "s3_mean_reversion": "s3",
    "s4_trend_s1": "s4s1",
    "s4_trend_s2": "s4s2",
}


def strategy_grid() -> list[tuple[str, dict]]:
    grid: list[tuple[str, dict]] = [("s0_buy_and_hold", {})]
    for strategy in ("s1_profit_target", "s2_pullback", "s4_trend_s1", "s4_trend_s2"):
        grid += [
            (strategy, {"profit_target_x": str(x), "rebuy_dip_y": str(y)})
            for x in XY_GRID
            for y in XY_GRID
        ]
    grid += [
        ("s3_mean_reversion", {"mr_k": str(k), "mr_window": w})
        for k in MR_K_GRID
        for w in MR_WINDOW_GRID
    ]
    return grid


def make_config(ticker: str, variant: str, strategy: str, params: dict) -> RunConfig:
    broker, spread, shares = VARIANTS[variant]
    tag = "_".join(f"{v}" for v in params.values())
    raw = {
        "run_name": f"val_{variant}_{LABELS[strategy]}_{ticker.lower()}"
        + (f"_{tag}" if tag else ""),
        "strategy": strategy,
        "ticker": ticker,
        "start": START,
        "end": END,
        "warmup_start": WARMUP,
        "broker": broker,
        "spread_level": spread,
        "share_mode": shares,
        "initial_aud": "10000",
        "fx_source": "rba",
        "min_order_usd": "10",
        "reinvest_min_cash_usd": "100",
        "final_test_unlocked": False,
        **params,
    }
    return parse_config(
        raw
    )  # same validation as a YAML file, incl. the grid and the D8 lock fields


# ---------- worker process: load FX and each ticker's prices once ----------
_FX = None


@cache
def _prices(ticker: str, warmup_start: date, start: date, end: date):
    from quant_research.data.loader import load_prices_with_warmup

    return load_prices_with_warmup(ticker, warmup_start, start, end)


def _cached_loader(ticker, warmup_start, start, end):
    return _prices(ticker, warmup_start, start, end).copy()


def run_one(job: tuple[str, str, str, dict]) -> tuple[str, str | None]:
    global _FX
    from quant_research.data.fx import load_usd_per_aud
    from quant_research.strategies.registry import make_strategy

    ticker, variant, strategy, params = job
    if _FX is None:
        _FX = load_usd_per_aud()
    config = make_config(ticker, variant, strategy, params)
    try:
        run_backtest(
            config,
            make_strategy(config),
            fx_series=_FX,
            runs_dir=OUT_ROOT / variant,
            warmup_load_fn=_cached_loader,
        )
        return config.run_name, None
    except Exception as exc:  # noqa: BLE001 — every failure is collected and reported, never hidden
        return config.run_name, f"{type(exc).__name__}: {exc}"


def main() -> int:
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        check=False,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    ).stdout
    if dirty.strip():
        print(
            "refused: working tree has uncommitted changes — commit first so every record says dirty: False"
        )
        return 2
    if OUT_ROOT.exists() and any(OUT_ROOT.rglob("run.json")):
        print(
            f"refused: {OUT_ROOT} already has run records — never mix two runs (move them aside first)"
        )
        return 2
    jobs = [(t, v, s, p) for v in VARIANTS for t in TICKERS for s, p in strategy_grid()]
    for t, v, s, p in jobs:  # validate every config BEFORE running anything
        make_config(t, v, s, p)
    print(
        f"{len(jobs)} runs ({len(VARIANTS)} variants × {len(TICKERS)} stocks × {len(strategy_grid())} settings)"
    )
    started, done, failures = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(run_one, job) for job in jobs]
        for future in as_completed(futures):
            name, error = future.result()
            done += 1
            if error:
                failures.append((name, error))
            if done % 250 == 0 or done == len(jobs):
                print(
                    f"  {done}/{len(jobs)} done, {len(failures)} failed, {time.time() - started:.0f}s"
                )
    print(
        f"finished: {done - len(failures)} ok, {len(failures)} failed, {time.time() - started:.0f}s"
    )
    for name, error in failures[:20]:
        print("  FAILED", name, error)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
