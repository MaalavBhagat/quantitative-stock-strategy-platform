"""Phase 9, Step 9.2: download Form 8-K / 8-K/A filing lists (dates, times, item codes) for the 7 companies.

Run:  uv run python scripts/download_sec_8k.py
- Same CIKs as Phase 7 (data/raw/sec/cik_map.json, XOM = 34088, the 2010–2020 filer). ≥ 1 s between requests.
- Follows the older-filing pages. Keeps 8-K / 8-K/A only; drops anything filed or accepted after 2020-12-31 (D8)
  BEFORE saving. Writes data/raw/sec/submissions/ (git-ignored). Refuses to overwrite.
--final-test (research/FINAL_TEST_PREREG.md): cutoff 2025-12-31, the 6 final-test companies (T excluded), and for
  XOM BOTH filers — 0000034088 (Exxon Mobil Corp) and 0002115436 (the new holding company now on SEC's ticker list) —
  each saved as its own file; news.events.load_events merges them by accession number.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from quant_research.data.sec import CUTOFF, Throttle
from quant_research.data.sec_submissions import FINAL_CUTOFF, fetch_8k, save_8k

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEC_DIR = PROJECT_ROOT / "data" / "raw" / "sec"
OUT = SEC_DIR / "submissions"
COMPANIES = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "T"]
CIK_OVERRIDES = {"XOM": 34088}  # same as scripts/download_sec_companyfacts.py (DATA_SOURCES §11)
FINAL_EXTRA_CIKS = {
    "XOM": [2115436]
}  # new holding company (checked in the final test, not assumed)


def main() -> int:
    final = "--final-test" in sys.argv
    cutoff = FINAL_CUTOFF if final else CUTOFF
    load_dotenv(PROJECT_ROOT / ".env")
    ua = os.environ.get("SEC_USER_AGENT", "")
    ciks = json.loads((SEC_DIR / "cik_map.json").read_text())["ciks"]
    throttle = Throttle()
    for t in COMPANIES:
        if final and t == "T":
            continue  # excluded from the final test (2022 spin-off)
        main_cik = CIK_OVERRIDES.get(t, ciks[t]["cik"])
        for cik in [main_cik, *(FINAL_EXTRA_CIKS.get(t, []) if final else [])]:
            if list(OUT.glob(f"{t}_CIK{cik:010d}_8k_to-{cutoff}.json")):
                print(f"{t} (CIK {cik:010d}): already downloaded — skipped")
                continue
            filings, info = fetch_8k(cik, ua, throttle, cutoff)
            path = save_8k(filings, info, t, cik, OUT, PROJECT_ROOT, cutoff)
            print(
                f"{t} (CIK {cik:010d}, {info['entity_name']}): pages {len(info['pages_followed'])}, rows read "
                f"{info['rows_read']}, 8-K kept {info['8k_kept']}, dropped after {cutoff} "
                f"{info['8k_dropped_after_cutoff']} → {path.name}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
