"""Download daily prices and ticker metadata from Tiingo's end-of-day API.

The API key is sent only in the request header, never in the URL, so it cannot end up in
logs or saved metadata. This module never prints or logs the key.
Docs: https://www.tiingo.com/documentation/end-of-day
"""

import logging
import time
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

BASE_URL = "https://api.tiingo.com/tiingo/daily"

# Tiingo field -> our name (PROJECT_GUIDE §4: raw vs adjusted and currency always explicit).
COLUMN_MAP: dict[str, str] = {
    "date": "date",
    "open": "open_raw",
    "high": "high_raw",
    "low": "low_raw",
    "close": "close_raw",
    "volume": "volume_raw",
    "adjOpen": "open_adj",
    "adjHigh": "high_adj",
    "adjLow": "low_adj",
    "adjClose": "close_adj",
    "adjVolume": "volume_adj",
    "divCash": "div_cash_usd",
    "splitFactor": "split_factor",
}

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


class TiingoError(RuntimeError):
    """Tiingo request failed or returned data we cannot use."""


def prices_endpoint(ticker: str, start: date, end: date) -> str:
    """Full prices URL for a ticker and date range (contains no API key)."""
    return (
        f"{BASE_URL}/{ticker.lower()}/prices"
        f"?startDate={start.isoformat()}&endDate={end.isoformat()}"
    )


def meta_endpoint(ticker: str) -> str:
    """Metadata URL for a ticker (contains no API key)."""
    return f"{BASE_URL}/{ticker.lower()}"


def _get_json(
    url: str,
    api_key: str,
    client: httpx.Client | None = None,
    max_attempts: int = 4,
    backoff_seconds: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """GET a Tiingo URL with the key in the header; retry 429 / 5xx / network errors."""
    if not api_key:
        raise TiingoError("TIINGO_API_KEY is empty — put your key in .env (see .env.example)")
    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
    own_client = client is None
    http = client if client is not None else httpx.Client(timeout=30.0)
    try:
        last_problem = ""
        for attempt in range(1, max_attempts + 1):
            try:
                response = http.get(url, headers=headers)
            except httpx.TransportError as exc:
                last_problem = f"network error: {type(exc).__name__}"
            else:
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError:  # Phase 10 fix: was a bare JSONDecodeError traceback
                        raise TiingoError(
                            f"Tiingo returned HTTP 200 but the body is not valid JSON for {url} "
                            f"(starts {response.text[:60]!r}) — try again later; nothing was saved"
                        ) from None
                if response.status_code not in RETRY_STATUS_CODES:
                    raise TiingoError(
                        f"Tiingo returned HTTP {response.status_code} for {url} — "
                        "check the ticker and your API key (not retried)"
                    )
                last_problem = f"HTTP {response.status_code}"
            if attempt < max_attempts:
                wait = backoff_seconds * 2 ** (attempt - 1)
                logger.warning(
                    "Tiingo %s (attempt %d/%d) — retrying in %.0fs",
                    last_problem,
                    attempt,
                    max_attempts,
                    wait,
                )
                sleep(wait)
        raise TiingoError(
            f"Tiingo request failed after {max_attempts} attempts ({last_problem}) for {url}. "
            "If HTTP 429: free plan limit is 50 requests/hour — wait and try again later."
        )
    finally:
        if own_client:
            http.close()


def parse_prices(records: list[dict[str, Any]], ticker: str) -> pd.DataFrame:
    """Turn Tiingo's JSON list into a DataFrame with our column names.

    Keeps every field Tiingo returns (unknown fields keep their original name, with a warning).
    `date` becomes a plain calendar date; any non-midnight time part fails loudly.
    The first raw date string is kept in `df.attrs["raw_date_example"]`.
    """
    if not isinstance(records, list) or not records:
        raise TiingoError(f"{ticker}: Tiingo returned no price rows (got {type(records).__name__})")
    df = pd.DataFrame.from_records(records)
    missing = [field for field in COLUMN_MAP if field not in df.columns]
    if missing:
        raise TiingoError(f"{ticker}: Tiingo response is missing fields {missing}")
    extra = [c for c in df.columns if c not in COLUMN_MAP]
    if extra:
        logger.warning("%s: Tiingo returned extra fields %s — kept unchanged", ticker, extra)
    df = df.rename(columns=COLUMN_MAP)

    timestamps = pd.to_datetime(df["date"], utc=True)
    not_midnight = timestamps[timestamps != timestamps.dt.normalize()]
    if not not_midnight.empty:
        raise TiingoError(
            f"{ticker}: {len(not_midnight)} date values have a time of day (first: "
            f"{df.loc[not_midnight.index[0], 'date']!r}) — cannot treat them as trading dates"
        )
    df["date"] = timestamps.dt.date

    numeric = [v for v in COLUMN_MAP.values() if v != "date"]
    for (
        col
    ) in numeric:  # Phase 10 fix: a non-number used to fail with a bare "could not convert" error
        bad = pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna()
        if bad.any():
            first = bad.idxmax()
            raise TiingoError(
                f"{ticker}: column {col} has a non-numeric value {df.loc[first, col]!r} on {df.loc[first, 'date']} "
                "— the response is malformed; nothing was saved"
            )
    for col in ("volume_raw", "volume_adj"):
        df[col] = pd.to_numeric(df[col])
    float_cols = [v for v in COLUMN_MAP.values() if v not in ("date", "volume_raw", "volume_adj")]
    df[float_cols] = df[float_cols].astype("float64")
    ordered = list(COLUMN_MAP.values()) + extra
    result = df[ordered]
    # Record the raw date exactly as Tiingo sent it, so its format/timezone is documented.
    result.attrs["raw_date_example"] = str(records[0]["date"])
    return result


def fetch_daily_prices(
    ticker: str,
    start: date,
    end: date,
    api_key: str,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> pd.DataFrame:
    """Download daily raw + adjusted prices, dividends and split factors for one ticker."""
    if end < start:
        raise ValueError(f"end {end} is before start {start}")
    url = prices_endpoint(ticker, start, end)
    logger.info("Downloading %s prices %s → %s from Tiingo", ticker, start, end)
    records = _get_json(url, api_key, client=client, sleep=sleep)
    return parse_prices(records, ticker)


def fetch_meta(
    ticker: str,
    api_key: str,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Ticker metadata: ticker, name, exchangeCode, startDate, endDate (+ any other fields)."""
    meta = _get_json(meta_endpoint(ticker), api_key, client=client, sleep=sleep)
    if not isinstance(meta, dict):
        raise TiingoError(f"{ticker}: unexpected metadata response type {type(meta).__name__}")
    return meta
