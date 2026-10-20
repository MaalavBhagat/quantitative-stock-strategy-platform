"""Save downloaded raw data reproducibly: a CSV plus a `.meta.json` sidecar.

data/ is git-ignored (personal-use licence) — files written here are never committed.
"""

import json
import logging
import subprocess
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_research import __version__

logger = logging.getLogger(__name__)


def raw_file_stem(ticker: str, start: date, end: date) -> str:
    """File name without extension, e.g. `AAPL_2010-01-01_2016-12-31`."""
    return f"{ticker.upper()}_{start.isoformat()}_{end.isoformat()}"


def git_state(repo_dir: Path) -> dict[str, Any]:
    """Current git commit and whether there are uncommitted changes ("dirty", D6)."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        logger.warning("Could not read git state (%s) — recorded as unknown", exc)
        return {"git_commit": None, "git_dirty": None}
    return {"git_commit": commit, "git_dirty": bool(status.strip())}


def save_raw_prices(
    df: pd.DataFrame,
    ticker: str,
    start: date,
    end: date,
    endpoint: str,
    out_dir: Path,
    source: str = "Tiingo",
    repo_dir: Path | None = None,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Write `<out_dir>/<TICKER>_<start>_<end>.csv` and `.meta.json`; return both paths.

    Refuses to overwrite existing files unless `overwrite=True`. The metadata never contains
    an API key (the endpoint passed in must be the key-free URL).
    """
    if df.empty:
        raise ValueError(f"{ticker}: refusing to save an empty table")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = raw_file_stem(ticker, start, end)
    csv_path = out_dir / f"{stem}.csv"
    meta_path = out_dir / f"{stem}.meta.json"
    existing = [p for p in (csv_path, meta_path) if p.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            f"{', '.join(str(p) for p in existing)} already exists — "
            "pass overwrite=True to replace it"
        )

    meta: dict[str, Any] = {
        "source": source,
        "endpoint": endpoint,
        "tickers": [ticker.upper()],
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "downloaded_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "row_count": len(df),
        "first_date": str(min(df["date"])),
        "last_date": str(max(df["date"])),
        "columns": list(df.columns),
        "raw_date_example": df.attrs.get("raw_date_example"),
        "package_version": __version__,
        "licence_note": "Personal / internal use only — never commit or share this data",
        **git_state(repo_dir if repo_dir is not None else Path.cwd()),
    }
    df.to_csv(csv_path, index=False)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    logger.info("Saved %d rows to %s", len(df), csv_path)
    return csv_path, meta_path
