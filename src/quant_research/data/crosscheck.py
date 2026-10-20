"""Cross-check Tiingo raw data against Yahoo Finance (via yfinance) — Phase 2, Step 2.3.

Yahoo's "Close", dividends and volume come split-adjusted (also for splits after the table
ends), even with auto_adjust=False. We find that basis from the data, as whole split ratios,
convert Yahoo back to Tiingo's raw basis, and report every remaining difference.
yfinance is optional (dependency group `crosscheck`) and imported only when downloading.
"""

import json
import logging
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quant_research.ratios import nearest_simple_ratio

logger = logging.getLogger(__name__)

DIFF_THRESHOLD = 0.005  # 0.5%: differences above this are counted and listed
BASIS_REL_TOL = 1e-3  # how closely the found split basis must match the data


# ---------- download + cache (needs: uv run --group crosscheck ...) ----------


def yahoo_cache_path(cache_dir: Path, ticker: str, start: date, end: date) -> Path:
    return cache_dir / f"{ticker.upper()}_{start.isoformat()}_{end.isoformat()}.csv"


def fetch_yahoo(
    ticker: str, start: date, end: date, max_attempts: int = 4, backoff_seconds: float = 5.0
) -> pd.DataFrame:
    """One yfinance history request (auto_adjust=False, with actions); retried on rate limits."""
    import yfinance as yf

    yf.config.debug.hide_exceptions = False  # fail loudly instead of returning empty data
    end_exclusive = (pd.Timestamp(end) + pd.Timedelta(days=1)).date().isoformat()
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        try:
            hist = yf.Ticker(ticker).history(
                start=start.isoformat(), end=end_exclusive, auto_adjust=False, actions=True
            )
        except Exception as exc:  # yfinance has several error types; non-rate-limit re-raised
            last_error = f"{type(exc).__name__}: {exc}"
            if "rate" not in last_error.lower() and "429" not in last_error:
                raise
        else:
            if hist.empty:
                raise RuntimeError(f"{ticker}: Yahoo returned no rows")
            return hist
        if attempt < max_attempts:
            wait = backoff_seconds * 2 ** (attempt - 1)
            logger.warning("%s rate-limited (attempt %d) — waiting %.0fs", ticker, attempt, wait)
            time.sleep(wait)
    raise RuntimeError(f"{ticker}: Yahoo rate-limited after {max_attempts} attempts: {last_error}")


def yahoo_history_to_table(hist: pd.DataFrame) -> pd.DataFrame:
    """yfinance history → plain table with `date` as plain dates."""
    table = pd.DataFrame(
        {
            "date": [ts.date() for ts in hist.index],
            "yahoo_open": hist["Open"].to_numpy(),
            "yahoo_high": hist["High"].to_numpy(),
            "yahoo_low": hist["Low"].to_numpy(),
            "yahoo_close": hist["Close"].to_numpy(),
            "yahoo_adj_close": hist["Adj Close"].to_numpy(),
            "yahoo_volume": hist["Volume"].to_numpy(),
            "yahoo_dividends": hist["Dividends"].to_numpy(),
            "yahoo_splits": hist["Stock Splits"].to_numpy(),
        }
    )
    table.attrs["index_timezone"] = str(hist.index.tz)
    return table


def load_or_fetch_yahoo(ticker: str, start: date, end: date, cache_dir: Path) -> pd.DataFrame:
    """Read the cached Yahoo table, or download it once and cache it (CSV + .meta.json)."""
    path = yahoo_cache_path(cache_dir, ticker, start, end)
    meta_path = path.with_suffix(".meta.json")
    if path.exists():
        logger.info("%s: using cached Yahoo data %s", ticker, path.name)
        table = pd.read_csv(path)
        table["date"] = pd.to_datetime(table["date"], format="%Y-%m-%d").dt.date
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        table.attrs["index_timezone"] = meta.get("index_timezone")
        return table
    import yfinance as yf

    table = yahoo_history_to_table(fetch_yahoo(ticker, start, end))
    cache_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    meta = {
        "source": "Yahoo Finance via yfinance (unofficial, personal use only)",
        "yfinance_version": yf.__version__,
        "ticker": ticker.upper(),
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "auto_adjust": False,
        "actions": True,
        "downloaded_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "index_timezone": table.attrs["index_timezone"],
        "row_count": len(table),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    logger.info("%s: cached %d Yahoo rows to %s", ticker, len(table), path.name)
    return table


# ---------- comparison (pure functions, tested offline) ----------


def compare_trading_days(tiingo: pd.DataFrame, yahoo: pd.DataFrame) -> dict[str, Any]:
    a, b = set(tiingo["date"]), set(yahoo["date"])
    return {
        "tiingo_days": len(a),
        "yahoo_days": len(b),
        "only_tiingo": sorted(a - b),
        "only_yahoo": sorted(b - a),
    }


def merge_sources(tiingo: pd.DataFrame, yahoo: pd.DataFrame) -> pd.DataFrame:
    return tiingo.merge(yahoo, on="date", how="inner").sort_values("date").reset_index(drop=True)


def detect_split_basis(merged: pd.DataFrame) -> tuple[pd.Series, dict[str, Any]]:
    """Find the factor that turns Yahoo's split-adjusted values back into Tiingo raw values.

    factor[t] = 1 / (later_split_ratio × product of Tiingo split factors after t), where
    later_split_ratio (splits after the table ends) is read from the data as a whole ratio.
    Raises ValueError if the data does not fit this explanation.
    """
    q = merged["yahoo_close"] / merged["close_raw"]
    is_split = (merged["split_factor"] - 1.0).abs() > 1e-12
    ratios = [float(nearest_simple_ratio(f)) for f in merged["split_factor"]]
    split_ratio = pd.Series([r if s else 1.0 for r, s in zip(ratios, is_split)])
    # product of split ratios strictly after each row
    after = split_ratio[::-1].cumprod()[::-1].shift(-1, fill_value=1.0)
    segment = is_split.cumsum()
    last_median = float(q[segment == segment.max()].median())
    later_ratio = nearest_simple_ratio(1.0 / last_median)
    factor = 1.0 / (float(later_ratio) * after)
    segments = []
    for idx in merged.groupby(segment).groups.values():
        median_q = float(q[idx].median())
        expected = float(factor[idx].iloc[0])
        rel = abs(median_q - expected) / expected
        segments.append(
            {
                "from": merged.at[idx[0], "date"],
                "to": merged.at[idx[-1], "date"],
                "yahoo_over_tiingo_median": median_q,
                "explained_as": f"1/{1 / expected:g}",
                "rel_diff": rel,
            }
        )
        if rel > BASIS_REL_TOL:
            raise ValueError(
                f"Yahoo/Tiingo close ratio {median_q:.6f} from {segments[-1]['from']} is not "
                f"explained by split basis {expected:.6f} — cannot compare safely"
            )
    info = {
        "yahoo_close_is_split_adjusted": bool((factor != 1.0).any()),
        "later_split_ratio_implied": f"{later_ratio.numerator}:{later_ratio.denominator}",
        "segments": segments,
    }
    return factor, info


def _diff_stats(
    pct: pd.Series, dates: pd.Series, threshold: float = DIFF_THRESHOLD
) -> dict[str, Any]:
    abs_pct = pct.abs()
    worst = abs_pct.sort_values(ascending=False).head(5).index
    return {
        "compared": int(abs_pct.notna().sum()),
        "max_abs_pct": float(abs_pct.max()),
        "median_abs_pct": float(abs_pct.median()),
        "count_over_threshold": int((abs_pct > threshold).sum()),
        "worst": [(dates[i], float(pct[i])) for i in worst],
    }


def compare_closes(merged: pd.DataFrame, factor: pd.Series) -> dict[str, Any]:
    """% difference between Yahoo close (converted to raw basis) and Tiingo close_raw."""
    pct = (merged["yahoo_close"] / factor) / merged["close_raw"] - 1
    return _diff_stats(pct, merged["date"])


def explain_close_differences(merged: pd.DataFrame, factor: pd.Series) -> list[dict[str, Any]]:
    """For each close difference over the threshold, test simple explanations from the data.

    Only one is tested so far: "Yahoo close − Tiingo close equals the dividend whose ex-date is
    the next trading day" (within 1% of the dividend). Anything else stays "unexplained".
    """
    yahoo_raw = merged["yahoo_close"] / factor
    pct = yahoo_raw / merged["close_raw"] - 1
    next_div = merged["div_cash_usd"].shift(-1, fill_value=0.0)
    out = []
    for i in merged.index[pct.abs() > DIFF_THRESHOLD]:
        gap = float(yahoo_raw[i] - merged.at[i, "close_raw"])
        if next_div[i] > 0 and abs(gap - next_div[i]) <= 0.01 * next_div[i]:
            note = "difference equals the next day's dividend (day before ex-date)"
        else:
            note = "unexplained"
        out.append({"date": merged.at[i, "date"], "pct": float(pct[i]), "note": note})
    return out


def compare_dividends(merged: pd.DataFrame, factor: pd.Series) -> dict[str, Any]:
    """Dividend ex-dates in each source, and % difference of amounts on common dates."""
    t = merged["div_cash_usd"] > 0
    y = merged["yahoo_dividends"] > 0
    both = t & y
    pct = (merged.loc[both, "yahoo_dividends"] / factor[both]) / merged.loc[
        both, "div_cash_usd"
    ] - 1
    result = {
        "tiingo_count": int(t.sum()),
        "yahoo_count": int(y.sum()),
        "only_tiingo": list(merged.loc[t & ~y, "date"]),
        "only_yahoo": list(merged.loc[y & ~t, "date"]),
    }
    if both.any():
        result.update(_diff_stats(pct, merged["date"]))
    return result


def compare_splits(merged: pd.DataFrame) -> dict[str, Any]:
    tiingo = [
        (d, float(f))
        for d, f in zip(merged["date"], merged["split_factor"])
        if abs(f - 1.0) > 1e-12
    ]
    yahoo = [(d, float(f)) for d, f in zip(merged["date"], merged["yahoo_splits"]) if f != 0]
    tiingo_ratios = {d: float(nearest_simple_ratio(f)) for d, f in tiingo}
    yahoo_ratios = {d: float(nearest_simple_ratio(f)) for d, f in yahoo}
    return {
        "tiingo": tiingo,
        "yahoo": yahoo,
        "same_dates_and_ratios": tiingo_ratios == yahoo_ratios,
    }


def crosscheck(tiingo: pd.DataFrame, yahoo: pd.DataFrame) -> dict[str, Any]:
    """Run every comparison and return one result dictionary."""
    merged = merge_sources(tiingo, yahoo)
    factor, basis = detect_split_basis(merged)
    return {
        "trading_days": compare_trading_days(tiingo, yahoo),
        "basis": basis,
        "closes": compare_closes(merged, factor),
        "close_differences_explained": explain_close_differences(merged, factor),
        "dividends": compare_dividends(merged, factor),
        "splits": compare_splits(merged),
    }
