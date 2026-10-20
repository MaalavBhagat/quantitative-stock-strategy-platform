"""Phase 2, Step 2.3 (Part B): cross-check the Tiingo files against Yahoo (yfinance).

Run:  uv run --group crosscheck python scripts/crosscheck_yfinance.py
yfinance is unofficial and personal-use only (DATA_SOURCES §2) — used only to cross-check Tiingo.
Yahoo data is cached under /data/cache/yfinance/ (git-ignored): 1 request per ticker, only when
there is no cache yet.
"""

import logging
import sys
from datetime import date
from pathlib import Path

from quant_research.data.crosscheck import crosscheck, load_or_fetch_yahoo
from quant_research.data.validation import load_raw_csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "tiingo"
CACHE_DIR = PROJECT_ROOT / "data" / "cache" / "yfinance"
TICKERS = ["AAPL", "XOM"]
START = date(2010, 1, 1)
END = date(2016, 12, 31)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for ticker in TICKERS:
        tiingo = load_raw_csv(RAW_DIR / f"{ticker}_{START}_{END}.csv")
        yahoo = load_or_fetch_yahoo(ticker, START, END, CACHE_DIR)
        result = crosscheck(tiingo, yahoo)
        closes, divs = result["closes"], result["dividends"]
        print(f"\n=== {ticker} (Yahoo index timezone: {yahoo.attrs.get('index_timezone')}) ===")
        days = result["trading_days"]
        print(
            f"trading days: Tiingo {days['tiingo_days']}, Yahoo {days['yahoo_days']}, "
            f"only Tiingo {len(days['only_tiingo'])}, only Yahoo {len(days['only_yahoo'])}"
        )
        print(f"basis: {result['basis']}")
        print(
            f"closes: max {closes['max_abs_pct']:.4%}, median {closes['median_abs_pct']:.4%}, "
            f"over 0.5%: {closes['count_over_threshold']}, worst: {closes['worst'][:3]}"
        )
        print(f"dividends: {divs}")
        print(f"splits: {result['splits']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
