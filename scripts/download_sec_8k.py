"""Phase 9, Step 9.2: download Form 8-K / 8-K/A filing lists (dates, times, item codes) for the 7 companies.

Run:  uv run python scripts/download_sec_8k.py
- Same CIKs as Phase 7 (data/raw/sec/cik_map.json, XOM = 34088, the 2010–2020 filer). ≥ 1 s between requests.
- Follows the older-filing pages. Keeps 8-K / 8-K/A only; drops anything filed or accepted after 2020-12-31 (D8)
  BEFORE saving. Writes data/raw/sec/submissions/ (git-ignored). Refuses to overwrite.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from quant_research.data.sec import Throttle
from quant_research.data.sec_submissions import fetch_8k, save_8k

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEC_DIR = PROJECT_ROOT / "data" / "raw" / "sec"
OUT = SEC_DIR / "submissions"
COMPANIES = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "T"]
CIK_OVERRIDES = {"XOM": 34088}  # same as scripts/download_sec_companyfacts.py (DATA_SOURCES §11)


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    ua = os.environ.get("SEC_USER_AGENT", "")
    ciks = json.loads((SEC_DIR / "cik_map.json").read_text())["ciks"]
    throttle = Throttle()
    for t in COMPANIES:
        cik = CIK_OVERRIDES.get(t, ciks[t]["cik"])
        if list(OUT.glob(f"{t}_CIK{cik:010d}_8k_*.json")):
            print(f"{t}: already downloaded — skipped")
            continue
        filings, info = fetch_8k(cik, ua, throttle)
        path = save_8k(filings, info, t, cik, OUT, PROJECT_ROOT)
        print(
            f"{t} (CIK {cik:010d}): pages {len(info['pages_followed'])}, rows read {info['rows_read']}, 8-K kept "
            f"{info['8k_kept']}, 8-K dropped after 2020-12-31 {info['8k_dropped_after_cutoff']} → {path.name}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
