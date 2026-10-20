"""Phase 2, Step 2.2: download the small initial dataset (AAPL + XOM, 2010-2016) from Tiingo.

Run from the project folder:  uv run python scripts/download_initial_dataset.py
Needs TIINGO_API_KEY in .env. Uses 2 API calls. Refuses to overwrite existing files.
"""

import logging
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from quant_research.data.storage import save_raw_prices
from quant_research.data.tiingo import fetch_daily_prices, prices_endpoint

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "raw" / "tiingo"
TICKERS = ["AAPL", "XOM"]
START = date(2010, 1, 1)
END = date(2016, 12, 31)


def summarise(ticker: str, df: pd.DataFrame) -> None:
    """Print what the data actually shows (no assumptions)."""
    dividends = df[df["div_cash_usd"] != 0]
    splits = df[df["split_factor"] != 1.0]
    missing = df.isna().sum()
    print(f"\n=== {ticker} ===")
    print(f"rows: {len(df)}")
    print(f"first date: {min(df['date'])}   last date: {max(df['date'])}")
    print(f"raw date value from Tiingo (first row): {df.attrs.get('raw_date_example')!r}")
    print(f"non-zero dividends: {len(dividends)}")
    if splits.empty:
        print("split rows: none")
    else:
        print("split rows (date, split_factor):")
        for row in splits.itertuples():
            print(f"  {row.date}  {row.split_factor}")
    if missing.sum() == 0:
        print("missing values: none in any column")
    else:
        print("missing values per column:")
        for col, count in missing[missing > 0].items():
            print(f"  {col}: {count}")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.environ.get("TIINGO_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        print("ERROR: TIINGO_API_KEY not set in .env (copy .env.example to .env).", file=sys.stderr)
        return 1

    for ticker in TICKERS:
        df = fetch_daily_prices(ticker, START, END, api_key)
        csv_path, meta_path = save_raw_prices(
            df,
            ticker,
            START,
            END,
            endpoint=prices_endpoint(ticker, START, END),
            out_dir=OUT_DIR,
            repo_dir=PROJECT_ROOT,
        )
        print(f"saved {csv_path.relative_to(PROJECT_ROOT)} + {meta_path.name}")
        summarise(ticker, df)
    return 0


if __name__ == "__main__":
    sys.exit(main())
