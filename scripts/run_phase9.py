"""Phase 9, Steps 9.5–9.6: the PRE-REGISTERED runs (research/PREREGISTRATION_V2.md, tag prereg-v2).

Run:  uv run python scripts/run_phase9.py
- VALIDATION 2017-01-01 → 2020-12-31 (trading from 2017-01-03), warm-up from 2015-01-01 — same data / FX / warm-up as
  the Phase 6 runs; D8 lock on. Information strategies C1 (8 × 1) + C2 (8 × 16) + E1 (8 × 16) = 264 and their twins
  S0 (8) + S4-S2 (8 × 16) = 136, each at MAIN + tight · wide · ibkr · commsec · whole · stress → 2,800 runs under
  /data/runs/phase9/validation/<variant>/.
- DEVELOPMENT 2010-01-04 → 2016-12-30 (warm-up from 2008-01-01), MAIN only, the same 400 strategy × stock settings →
  /data/runs/phase9/development/main/ (sanity + dev-vs-validation table, not judged).
- Refuses to start from a dirty working tree or if /data/runs/phase9 already holds records.
- Prints progress COUNTS only — no result is printed or summarised here. The report is a separate script.
- During the batch this file lived OUTSIDE the project folder (no repo file may change while records are saved —
  lesson from the aborted Phase 6 batch); it was copied into scripts/ unchanged afterwards.
"""

import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from functools import cache
from pathlib import Path

import quant_research
from quant_research.backtesting.run import (
    DEFAULT_RUNS_DIR,
    XY_GRID,
    RunConfig,
    parse_config,
    run_backtest,
)

PROJECT_ROOT = Path(quant_research.__file__).resolve().parents[2]
OUT_ROOT = DEFAULT_RUNS_DIR / "phase9"
SUBMISSIONS = PROJECT_ROOT / "data" / "raw" / "sec" / "submissions"
TICKERS = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "T", "SPY"]
PERIODS = {  # name: (start, end, warm-up start)
    "validation": (date(2017, 1, 1), date(2020, 12, 31), date(2015, 1, 1)),
    "development": (date(2010, 1, 4), date(2016, 12, 30), date(2008, 1, 1)),
}
VARIANTS = {  # name: (broker, spread_level, share_mode) — PREREGISTRATION §4 (same as scripts/run_validation.py)
    "main": ("stake", "normal", "fractional"),
    "tight": ("stake", "tight", "fractional"),
    "wide": ("stake", "wide", "fractional"),
    "ibkr": ("ibkr_fixed", "normal", "fractional"),
    "commsec": ("commsec_standard", "normal", "fractional"),
    "whole": ("stake", "normal", "whole"),
    "stress": ("commsec_standard", "wide", "fractional"),
}
SHORT = {
    "s0_buy_and_hold": "s0",
    "s4_trend_s2": "s4s2",
    "c1_market_gate": "c1",
    "c2_market_gated_pullback": "c2",
    "e1_earnings_cooloff": "e1",
}


def strategy_grid() -> list[tuple[str, dict]]:
    """Information strategies + twins: S0, C1 (no settings); S4-S2, C2, E1 (16 X/Y settings each) = 50 per stock."""
    grid: list[tuple[str, dict]] = [("s0_buy_and_hold", {}), ("c1_market_gate", {})]
    for strategy in ("s4_trend_s2", "c2_market_gated_pullback", "e1_earnings_cooloff"):
        grid += [
            (strategy, {"profit_target_x": str(x), "rebuy_dip_y": str(y)})
            for x in XY_GRID
            for y in XY_GRID
        ]
    return grid


def jobs() -> list[tuple[str, str, str, str, dict]]:
    out = [
        ("validation", v, t, s, p) for v in VARIANTS for t in TICKERS for s, p in strategy_grid()
    ]
    out += [("development", "main", t, s, p) for t in TICKERS for s, p in strategy_grid()]
    return out


def make_config(period: str, ticker: str, variant: str, strategy: str, params: dict) -> RunConfig:
    start, end, warmup = PERIODS[period]
    broker, spread, shares = VARIANTS[variant]
    tag = "_".join(f"{v}" for v in params.values())
    raw = {
        "run_name": f"p9_{period[:3]}_{variant}_{SHORT[strategy]}_{ticker.lower()}"
        + (f"_{tag}" if tag else ""),
        "strategy": strategy,
        "ticker": ticker,
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
        "final_test_unlocked": False,
        **params,
    }
    return parse_config(
        raw
    )  # same validation as a YAML file, incl. the grid and the D8 lock fields


# ---------- worker process: load FX, prices and events once ----------
_FX = None


@cache
def _prices(ticker: str, warmup_start: date, start: date, end: date):
    from quant_research.data.loader import load_prices_with_warmup

    return load_prices_with_warmup(ticker, warmup_start, start, end)


def _cached_loader(ticker, warmup_start, start, end):
    return _prices(ticker, warmup_start, start, end).copy()


@cache
def _events(ticker: str):
    from quant_research.news.events import load_events

    return tuple(load_events(ticker, SUBMISSIONS))


def run_one(job: tuple[str, str, str, str, dict]) -> tuple[str, str | None]:
    global _FX
    from quant_research.backtesting.run import check_final_test_lock
    from quant_research.data.fx import load_usd_per_aud
    from quant_research.strategies.registry import MARKET_TICKER, make_strategy

    period, variant, ticker, strategy, params = job
    if _FX is None:
        _FX = load_usd_per_aud()
    config = make_config(period, ticker, variant, strategy, params)
    try:
        check_final_test_lock(config)  # before loading SPY or events
        market = _cached_loader(MARKET_TICKER, config.warmup_start, config.start, config.end)
        run_backtest(
            config,
            make_strategy(config, market=market, events=list(_events(ticker))),
            fx_series=_FX,
            runs_dir=OUT_ROOT / period / variant,
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
            f"refused: {OUT_ROOT} already has run records — never mix two batches (move them aside first)"
        )
        return 2
    all_jobs = jobs()
    for job in all_jobs:  # validate every config BEFORE running anything
        make_config(job[0], job[2], job[1], job[3], job[4])
    print(
        f"{len(all_jobs)} runs (validation {len(VARIANTS)} variants × {len(TICKERS)} stocks × "
        f"{len(strategy_grid())} settings + development MAIN {len(TICKERS)} × {len(strategy_grid())})"
    )
    started, done, failures = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(run_one, job) for job in all_jobs]
        for future in as_completed(futures):
            name, error = future.result()
            done += 1
            if error:
                failures.append((name, error))
            if done % 250 == 0 or done == len(all_jobs):
                print(
                    f"  {done}/{len(all_jobs)} done, {len(failures)} failed, {time.time() - started:.0f}s",
                    flush=True,
                )
    print(
        f"finished: {done - len(failures)} ok, {len(failures)} failed, {time.time() - started:.0f}s"
    )
    for name, error in failures[:20]:
        print("  FAILED", name, error)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
