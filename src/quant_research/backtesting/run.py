"""Run configuration, the final-test lock (D8) and the run record (EXPERIMENT_PLAN §8).

A run = RunConfig (YAML in config/) → lock check → load validated data → engine → run record
saved under /data/runs/<run_id>/ (git-ignored: equity curves come from licensed prices).
"""

import csv
import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from quant_research.backtesting.engine import EngineResult, EngineSettings, Strategy, run_engine
from quant_research.data.fx import FxSeries, load_usd_per_aud
from quant_research.data.loader import load_prices
from quant_research.data.storage import git_state
from quant_research.execution.costs import aud_to_usd, fx_fee_settings, usd_to_aud
from quant_research.portfolio.money import require_decimal

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNS_DIR = PROJECT_ROOT / "data" / "runs"
FINAL_TEST_START = date(2021, 1, 1)  # EXPERIMENT_PLAN §4 hold-out period


class FinalTestLockedError(PermissionError):
    """The run touches the final test period and Goggy has not unlocked it (D8)."""


@dataclass(frozen=True)
class RunConfig:
    run_name: str
    strategy: str
    ticker: str
    start: date
    end: date
    broker: str
    spread_level: str
    share_mode: str
    initial_aud: Decimal
    fx_source: str = "rba"  # "rba" (DATA_SOURCES §9) or "fixed" (uses the two rates below; tests)
    usd_per_aud_start: Decimal | None = None  # only for fx_source: fixed
    usd_per_aud_end: Decimal | None = None  # only for fx_source: fixed
    min_order_usd: Decimal | None = Decimal(10)
    reinvest_min_cash_usd: Decimal = Decimal(100)  # Goggy 2026-10-21 — applies to every strategy
    final_test_unlocked: bool = False


DECIMAL_FIELDS = {
    "initial_aud",
    "usd_per_aud_start",
    "usd_per_aud_end",
    "min_order_usd",
    "reinvest_min_cash_usd",
}


def parse_config(raw: dict[str, Any]) -> RunConfig:
    """Validate a config dict. Money/rates must be quoted strings or ints (no floats)."""
    known = {f.name for f in fields(RunConfig)}
    unknown = set(raw) - known
    if unknown:
        raise ValueError(f"unknown config keys: {sorted(unknown)}")
    values = dict(raw)
    for key in DECIMAL_FIELDS & set(values):
        if values[key] is None and key in ("min_order_usd", "usd_per_aud_start", "usd_per_aud_end"):
            continue
        if isinstance(values[key], float):
            raise TypeError(
                f"config {key} is a float ({values[key]!r}) — write it in quotes, e.g. '0.69'"
            )
        values[key] = require_decimal(values[key], key)
    for key in ("start", "end"):
        if key in values and not isinstance(values[key], date):
            raise TypeError(f"config {key} must be a date like 2010-01-04, got {values[key]!r}")
    if "final_test_unlocked" in values and not isinstance(values["final_test_unlocked"], bool):
        raise TypeError("final_test_unlocked must be true or false")
    try:
        config = RunConfig(**values)
    except TypeError as exc:
        raise ValueError(f"config is missing required keys: {exc}") from None
    if config.end < config.start:
        raise ValueError(f"end {config.end} is before start {config.start}")
    if config.fx_source not in ("rba", "fixed"):
        raise ValueError(f"fx_source must be 'rba' or 'fixed', got {config.fx_source!r}")
    if config.fx_source == "fixed" and (
        config.usd_per_aud_start is None or config.usd_per_aud_end is None
    ):
        raise ValueError("fx_source 'fixed' needs usd_per_aud_start and usd_per_aud_end")
    return config


def load_config(path: Path) -> RunConfig:
    return parse_config(yaml.safe_load(path.read_text(encoding="utf-8")))


def check_final_test_lock(config: RunConfig) -> None:
    """D8: refuse any run touching dates ≥ 2021-01-01 unless final_test_unlocked is true."""
    if (
        config.end >= FINAL_TEST_START or config.start >= FINAL_TEST_START
    ) and not config.final_test_unlocked:
        raise FinalTestLockedError(
            f"run {config.run_name!r} reaches {config.end} — the final test period "
            f"(≥ {FINAL_TEST_START}) is locked. Only Goggy may set final_test_unlocked: true."
        )


@dataclass(frozen=True)
class RunOutcome:
    run_id: str
    run_dir: Path
    result: EngineResult
    summary: dict[str, Any]
    fx: FxSeries | None  # the RBA series used (None for fx_source: fixed)


def _jsonable(value: Any) -> Any:
    if isinstance(value, (Decimal, date, Path)):
        return str(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        if not rows:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _jsonable(v) for k, v in row.items()})


def run_backtest(
    config: RunConfig,
    strategy: Strategy,
    load_fn: Callable[..., pd.DataFrame] = load_prices,
    runs_dir: Path = DEFAULT_RUNS_DIR,
    repo_dir: Path = PROJECT_ROOT,
    fx_series: FxSeries | None = None,
) -> RunOutcome:
    """Lock check → load → AUD→USD → engine → USD→AUD → save the run record.

    FX (rba): start conversion at the rate for the first possible trade day (day 2 = the first
    open after the first close); end conversion at the last day's rate. Latest RBA rate ≤ day.
    """
    check_final_test_lock(config)  # before loading anything
    started = datetime.now(UTC)
    prices = load_fn(config.ticker, config.start, config.end)
    provenance = prices.attrs.get("provenance")

    first_trade_day = prices["date"].iloc[1] if len(prices) > 1 else prices["date"].iloc[0]
    last_day = prices["date"].iloc[-1]
    if config.fx_source == "rba":
        fx_series = fx_series if fx_series is not None else load_usd_per_aud()
        usd_per_aud_start = fx_series.on(first_trade_day)
        usd_per_aud_end = fx_series.on(last_day)
    else:
        fx_series = None
        usd_per_aud_start, usd_per_aud_end = config.usd_per_aud_start, config.usd_per_aud_end
    rate_in, min_in = fx_fee_settings(config.broker, "in")
    fx_in = aud_to_usd(config.initial_aud, usd_per_aud_start, rate_in, min_in)
    settings = EngineSettings(
        config.broker, config.spread_level, config.share_mode, config.min_order_usd
    )
    result = run_engine(prices, config.ticker, strategy, settings, fx_in.amount_out)
    rate_out, min_out = fx_fee_settings(config.broker, "out")
    fx_out = usd_to_aud(result.liquidation_value_usd, usd_per_aud_end, rate_out, min_out)
    finished = datetime.now(UTC)

    run_id = f"{started:%Y%m%dT%H%M%SZ}_{config.run_name}"
    run_dir = runs_dir / run_id
    if run_dir.exists():
        raise FileExistsError(f"run folder {run_dir} already exists")
    run_dir.mkdir(parents=True)
    p = result.portfolio
    summary = {
        "initial_aud": config.initial_aud,
        "fx_source": config.fx_source,
        "usd_per_aud_start": usd_per_aud_start,
        "usd_per_aud_start_for_day": first_trade_day,
        "usd_per_aud_end": usd_per_aud_end,
        "usd_per_aud_end_for_day": last_day,
        "fx_in_fee_usd": fx_in.fee_usd,
        "start_cash_usd": fx_in.amount_out,
        "last_close_value_usd": result.last_close_value_usd,
        "liquidation_value_usd": result.liquidation_value_usd,
        "fx_out_fee_usd": fx_out.fee_usd,
        "end_aud_after_liquidation": fx_out.amount_out,
        "realised_pnl_usd": p.realised_pnl_usd,
        "dividends_net_usd": p.dividends_net_usd,
        "total_fees_usd": p.total_fees_usd,
        "orders": {
            s: sum(o.status == s for o in result.orders) for s in ("FILLED", "REJECTED", "EXPIRED")
        },
        "trading_days": len(result.equity),
    }
    record = {
        "run_id": run_id,
        "started_utc": started.isoformat(timespec="seconds"),
        "finished_utc": finished.isoformat(timespec="seconds"),
        "config": asdict(config),
        "data_provenance": asdict(provenance) if provenance is not None else None,
        **git_state(repo_dir),
        "fx_files": list(fx_series.source_files) if fx_series is not None else None,
        "fx_note": "RBA daily AUD/USD (FXRUSD), latest rate dated <= day; source: Reserve Bank of Australia",
        "summary": summary,
    }
    (run_dir / "run.json").write_text(
        json.dumps(_jsonable(record), indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "config.yaml").write_text(
        yaml.safe_dump(_jsonable(asdict(config)), sort_keys=False), encoding="utf-8"
    )
    _write_csv(
        run_dir / "orders.csv",
        [
            {
                "created_day": o.created_day,
                "intended_day": o.intended_day,
                "side": o.intent.side,
                "ticker": o.intent.ticker,
                "size": o.intent.size,
                "status": o.status,
                "reason": o.reason,
            }
            for o in result.orders
        ],
    )
    _write_csv(
        run_dir / "fills.csv",
        [
            {
                "day": f.day,
                "side": f.side,
                "quantity": f.quantity,
                "reference_price_usd": f.reference_price_usd,
                "fill_price_usd": f.fill_price_usd,
                "spread_cost_usd": f.spread_cost_usd,
                "brokerage_usd": f.fee.brokerage_usd,
                "fx_usd": f.fee.fx_usd,
                "fee_total_usd": f.fee.total_usd,
                "gap_pct": f.gap_pct,
            }
            for f in result.fills
        ],
    )
    _write_csv(run_dir / "equity.csv", [asdict(e) for e in result.equity])
    logger.info("run %s saved to %s", run_id, run_dir)
    return RunOutcome(run_id, run_dir, result, summary, fx_series)
