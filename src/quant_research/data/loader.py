"""Load saved price data safely for research (Phase 2, Step 2.4).

`load_prices` reads files already saved under data/raw/tiingo/, validates them, and refuses to
return data with any ERROR. It never downloads, never fills or fixes data (DATA_SOURCES §7).
Note: it does NOT enforce the final-test lock (dates ≥ 2021-01-01) — per D8 that lock lives in
the backtest / experiment runner.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from quant_research.data.validation import (
    ADJ_PRICE_COLS,
    RAW_PRICE_COLS,
    Severity,
    load_raw_csv,
    validate_prices,
)

logger = logging.getLogger(__name__)

# src/quant_research/data/loader.py → project root is three folders up from this file's folder.
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "tiingo"
DOWNLOAD_HINT = (
    "run `uv run python scripts/download_initial_dataset.py` (needs TIINGO_API_KEY in .env)"
)
FILE_PATTERN = re.compile(
    r"^(?P<ticker>[A-Z0-9.\-]+)_(?P<start>\d{4}-\d{2}-\d{2})_(?P<end>\d{4}-\d{2}-\d{2})\.csv$"
)

BASE_COLUMNS = ["date", *RAW_PRICE_COLS, "volume_raw", "div_cash_usd", "split_factor"]
ADJ_COLUMNS = [*ADJ_PRICE_COLS, "volume_adj"]


class DataLoadError(RuntimeError):
    """Saved data is missing, ambiguous or failed validation."""


@dataclass(frozen=True)
class Provenance:
    """Where the returned data came from — recorded by every run (EXPERIMENT_PLAN §8)."""

    file_name: str
    source: str
    downloaded_at_utc: str
    git_commit: str | None
    rows_returned: int


def find_data_file(ticker: str, start: date, end: date, data_dir: Path) -> Path:
    """The one saved CSV for `ticker` whose requested dates cover start..end."""
    if not data_dir.exists():
        raise DataLoadError(f"data folder {data_dir} does not exist — {DOWNLOAD_HINT}")
    covering = []
    for path in sorted(data_dir.glob(f"{ticker.upper()}_*.csv")):
        match = FILE_PATTERN.match(path.name)
        if match is None or match["ticker"] != ticker.upper():
            continue
        file_start = date.fromisoformat(match["start"])
        file_end = date.fromisoformat(match["end"])
        if file_start <= start and file_end >= end:
            covering.append(path)
    if not covering:
        raise DataLoadError(
            f"no saved file for {ticker.upper()} covering {start} → {end} in {data_dir} — {DOWNLOAD_HINT}"
        )
    if len(covering) > 1:
        names = ", ".join(p.name for p in covering)
        raise DataLoadError(
            f"{len(covering)} saved files cover {ticker.upper()} {start} → {end} ({names}) — "
            "pass csv_path= to choose one"
        )
    return covering[0]


def load_prices(
    ticker: str,
    start: date,
    end: date,
    include_adjusted: bool = False,
    data_dir: Path = DEFAULT_DATA_DIR,
    csv_path: Path | None = None,
    sessions: list[date] | None = None,
) -> pd.DataFrame:
    """Validated daily data for one ticker, start..end inclusive.

    Returns date, *_raw prices, volume_raw, div_cash_usd, split_factor (plus *_adj columns when
    include_adjusted=True — for analysis only, never for trading). Provenance is in
    `df.attrs["provenance"]`. Raises DataLoadError if the file or its .meta.json is missing, or if
    validation finds any ERROR. WARNINGs are logged and the data is returned.
    `sessions` overrides the NYSE calendar (tests only).
    """
    if end < start:
        raise ValueError(f"end {end} is before start {start}")
    path = csv_path if csv_path is not None else find_data_file(ticker, start, end, data_dir)
    if not path.exists():
        raise DataLoadError(f"{path} does not exist — {DOWNLOAD_HINT}")
    meta_path = path.with_suffix(".meta.json")
    if not meta_path.exists():
        raise DataLoadError(
            f"{meta_path.name} is missing — data without a download record is not used. {DOWNLOAD_HINT}"
        )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if ticker.upper() not in meta.get("tickers", []):
        raise DataLoadError(f"{meta_path.name} is for {meta.get('tickers')}, not {ticker.upper()}")

    full = load_raw_csv(path)
    table = full[(full["date"] >= start) & (full["date"] <= end)].reset_index(drop=True)
    if table.empty:
        raise DataLoadError(f"{path.name} has no rows between {start} and {end}")

    downloaded = pd.Timestamp(meta["downloaded_at_utc"]).date()
    report = validate_prices(
        table, ticker.upper(), start, end, downloaded=downloaded, sessions=sessions
    )
    errors = [i for i in report.issues if i.severity == Severity.ERROR]
    if errors:
        shown = "; ".join(f"{i.date} {i.check}: {i.message}" for i in errors[:5])
        more = f" (+{len(errors) - 5} more)" if len(errors) > 5 else ""
        raise DataLoadError(
            f"{ticker.upper()} {start} → {end} failed validation with {len(errors)} ERROR(s): "
            f"{shown}{more}. Data is not filled or fixed — check the source file."
        )
    for issue in report.issues:
        if issue.severity == Severity.WARNING:
            logger.warning("%s %s %s: %s", issue.ticker, issue.date, issue.check, issue.message)

    columns = BASE_COLUMNS + (ADJ_COLUMNS if include_adjusted else [])
    result = table[columns].copy()
    result.attrs["provenance"] = Provenance(
        file_name=path.name,
        source=str(meta.get("source")),
        downloaded_at_utc=str(meta["downloaded_at_utc"]),
        git_commit=meta.get("git_commit"),
        rows_returned=len(result),
    )
    logger.info("Loaded %d rows of %s from %s", len(result), ticker.upper(), path.name)
    return result


def load_prices_with_warmup(
    ticker: str,
    warmup_start: date,
    start: date,
    end: date,
    include_adjusted: bool = False,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> pd.DataFrame:
    """Warm-up rows (warmup_start … last session before start) + main rows (start … end) as ONE table.

    Warm-up rows are only for computing indicators (they are the past, not look-ahead); the engine
    trades from `start`. Both slices are validated, then the joined table is validated again over
    warmup_start … end, so a gap or overlap at the join is an ERROR (NYSE calendar).
    Provenance: df.attrs["provenance"] = main file, df.attrs["warmup_provenance"] = warm-up file.
    """
    from quant_research.data.validation import nyse_sessions  # local: keeps the import graph simple

    if warmup_start >= start:
        raise ValueError(f"warmup_start {warmup_start} must be before start {start}")
    before = [d for d in nyse_sessions(warmup_start, start) if d < start]
    if not before:
        raise DataLoadError(f"no NYSE sessions between {warmup_start} and {start}")
    # load with adjusted columns so the joined table gets the FULL validation, then drop them if not wanted
    warm = load_prices(ticker, warmup_start, before[-1], True, data_dir)
    main = load_prices(ticker, start, end, True, data_dir)
    full = pd.concat([warm, main], ignore_index=True)
    report = validate_prices(full, ticker.upper(), warmup_start, end)
    errors = [i for i in report.issues if i.severity == Severity.ERROR]
    if errors:
        shown = "; ".join(f"{i.date} {i.check}: {i.message}" for i in errors[:5])
        raise DataLoadError(f"{ticker.upper()} warm-up join {warmup_start} → {end} failed: {shown}")
    for issue in report.issues:
        if issue.severity == Severity.WARNING:
            logger.warning("%s %s %s: %s", issue.ticker, issue.date, issue.check, issue.message)
    columns = BASE_COLUMNS + (ADJ_COLUMNS if include_adjusted else [])
    joined = full[columns].copy()
    joined.attrs["provenance"] = main.attrs["provenance"]
    joined.attrs["warmup_provenance"] = warm.attrs["provenance"]
    return joined
