"""Phase 7, Step 7.1: download SEC EDGAR companyfacts for the 7 companies (SPY is a fund — no company financials).

Run from the project folder:  uv run python scripts/download_sec_companyfacts.py
- 1 request for SEC's official ticker → CIK list (only our 8 rows are kept), then 1 request per company.
- ≥ 1 second between requests (SEC allows 10/s). Needs SEC_USER_AGENT in .env (never printed or saved).
- Facts filed after 2020-12-31 are dropped BEFORE saving (D8); counts go into each .meta.json.
- Skips companies already downloaded; refuses to overwrite. Writes only under data/raw/sec/ (git-ignored).
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from quant_research.data.sec import (
    COMPANYFACTS_URL,
    CUTOFF,
    TICKERS_URL,
    Throttle,
    ciks_for,
    get_json,
    save_companyfacts,
    trim_companyfacts,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "raw" / "sec"
COMPANIES = ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "T"]
ALL_TICKERS = [*COMPANIES, "SPY"]  # SPY looked up only to report that it is a fund
# Point-in-time entity fixes (checked on SEC's submissions API, 2026-10-26). SEC's ticker list is TODAY's:
# "XOM" now points to ExxonMobil Holdings Corp (CIK 2115436, nothing filed before 2021). The company that filed
# Exxon's 10-Ks in 2010–2020 is EXXON MOBIL CORP (formerly EXXON CORP), CIK 34088, which has no ticker today.
CIK_OVERRIDES = {"XOM": 34088}


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    user_agent = os.environ.get("SEC_USER_AGENT", "")
    throttle = Throttle()
    cik_path = OUT_DIR / "cik_map.json"
    if cik_path.exists():
        ciks = json.loads(cik_path.read_text(encoding="utf-8"))["ciks"]
        print(f"CIK map: reusing {cik_path.relative_to(PROJECT_ROOT)}")
    else:
        tickers_json = get_json(TICKERS_URL, user_agent, throttle)
        try:
            ciks = ciks_for(tickers_json, ALL_TICKERS)
        except Exception as exc:  # noqa: BLE001 — SPY may be absent from the company list; report it
            print(f"note: {exc}")
            ciks = ciks_for(tickers_json, COMPANIES)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        cik_path.write_text(
            json.dumps(
                {
                    "source": TICKERS_URL,
                    "downloaded_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                    "rows_in_sec_file": len(tickers_json),
                    "note": "Only our tickers kept. SEC's list is a CURRENT snapshot (ticker ↔ CIK).",
                    "ciks": ciks,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    for t, row in ciks.items():
        print(f"  {t}: CIK {row['cik']:010d}  {row['title']}")
    for t, cik in CIK_OVERRIDES.items():
        print(
            f"  override {t}: SEC list says CIK {ciks[t]['cik']:010d}; using {cik:010d} for 2010-2020 filings"
        )
    for t in COMPANIES:
        cik = CIK_OVERRIDES.get(t, ciks[t]["cik"])
        if list(OUT_DIR.glob(f"{t}_CIK{cik:010d}_*.json")):
            print(f"{t}: already downloaded (CIK {cik:010d}) — skipped")
            continue
        raw = get_json(COMPANYFACTS_URL.format(cik=cik), user_agent, throttle)
        trimmed, counts = trim_companyfacts(raw, CUTOFF)
        del raw  # the untrimmed JSON is never written anywhere
        json_path, _ = save_companyfacts(trimmed, counts, t, cik, OUT_DIR, repo_dir=PROJECT_ROOT)
        print(
            f"{t}: kept {counts['facts_kept']} facts, dropped {counts['facts_dropped_after_cutoff']} filed after "
            f"{CUTOFF} ({counts['concepts_dropped_empty']} concepts left empty) → {json_path.name}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
