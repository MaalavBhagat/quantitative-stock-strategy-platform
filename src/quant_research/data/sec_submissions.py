"""SEC EDGAR submissions → Form 8-K / 8-K/A filings (Phase 9, Step 9.2). Free, no key; same fair-access rules as data.sec.

Source: https://data.sec.gov/submissions/CIK##########.json — "filings.recent" (newest ~1,000 filings, column lists)
plus older pages listed in "filings.files" (each a JSON with the same column lists). Field names checked in the real
JSON (2026-10-27): form, filingDate, acceptanceDateTime, items, accessionNumber, primaryDocument, reportDate.

Timezone (checked, DATA_SOURCES §12): acceptanceDateTime ends in "Z" and IS UTC — Apple's Q4 FY2019 earnings 8-K
(filed 2019-10-30, released after the 16:00 ET close) reads 20:30:40Z = 16:30:40 US/Eastern (EDT, UTC−4).
D8: filings with filingDate or acceptance date (US/Eastern) ≥ 2021-01-01 are dropped IN MEMORY before saving.
"""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from quant_research import __version__
from quant_research.data.sec import CUTOFF, SecError, Throttle, get_json
from quant_research.data.storage import git_state

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
FILES_URL = "https://data.sec.gov/submissions/{name}"
EASTERN = ZoneInfo("America/New_York")
FINAL_CUTOFF = date(
    2025, 12, 31
)  # one-time final test (research/FINAL_TEST_PREREG.md) — never later
FORMS = ("8-K", "8-K/A")
FIELDS = (
    "form",
    "filingDate",
    "acceptanceDateTime",
    "items",
    "accessionNumber",
    "primaryDocument",
    "reportDate",
)


def acceptance_eastern(raw: str) -> datetime:
    """'2019-10-30T20:30:40.000Z' (UTC) → aware datetime in US/Eastern (DST handled by the tz database)."""
    if not raw.endswith("Z"):
        raise SecError(
            f"acceptanceDateTime without 'Z' (UTC marker): {raw!r} — refusing to guess the timezone"
        )
    return datetime.fromisoformat(raw).astimezone(EASTERN)


def rows_from_columns(block: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """The submissions JSON stores filings as parallel lists; turn them into one dict per filing."""
    missing = [f for f in FIELDS if f not in block]
    if missing:
        raise SecError(f"submissions block is missing fields {missing}")
    n = len(block["form"])
    if any(len(block[f]) != n for f in FIELDS):
        raise SecError("submissions columns have different lengths")
    return [{f: block[f][i] for f in FIELDS} for i in range(n)]


def keep_8k_until_cutoff(
    rows: list[dict[str, Any]], cutoff: date = CUTOFF
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """8-K / 8-K/A filings with filingDate AND acceptance date (US/Eastern) ≤ cutoff; counts of what was dropped."""
    kept, late, other = [], 0, 0
    for r in rows:
        if r["form"] not in FORMS:
            other += 1
            continue
        accepted = acceptance_eastern(r["acceptanceDateTime"])
        if date.fromisoformat(r["filingDate"]) > cutoff or accepted.date() > cutoff:
            late += 1
            continue
        kept.append({**r, "acceptance_eastern": accepted.isoformat()})
    kept.sort(key=lambda r: (r["acceptanceDateTime"], r["accessionNumber"]))
    return kept, {
        "8k_kept": len(kept),
        "8k_dropped_after_cutoff": late,
        "other_forms_not_kept": other,
    }


def fetch_8k(
    cik: int, user_agent: str, throttle: Throttle, cutoff: date = CUTOFF
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """All 8-K / 8-K/A filings ≤ cutoff for one CIK, following the older-filing pages. Nothing is written here."""
    main = get_json(SUBMISSIONS_URL.format(cik=cik), user_agent, throttle)
    rows = rows_from_columns(main["filings"]["recent"])
    pages = []
    for f in main["filings"].get("files", []):
        page = get_json(FILES_URL.format(name=f["name"]), user_agent, throttle)
        rows += rows_from_columns(page)
        pages.append({k: f[k] for k in ("name", "filingCount", "filingFrom", "filingTo")})
    seen = set()
    unique = []
    for r in rows:  # a filing should appear once; refuse silent duplicates
        if r["accessionNumber"] in seen:
            raise SecError(f"CIK {cik}: accession {r['accessionNumber']} appears twice")
        seen.add(r["accessionNumber"])
        unique.append(r)
    kept, counts = keep_8k_until_cutoff(unique, cutoff)
    info = {
        "entity_name": main.get("name"),
        "pages_followed": pages,
        "rows_read": len(unique),
        **counts,
    }
    return kept, info


def save_8k(
    filings: list[dict[str, Any]],
    info: dict[str, Any],
    ticker: str,
    cik: int,
    out_dir: Path,
    repo_dir: Path,
    cutoff: date = CUTOFF,
) -> Path:
    if cutoff > FINAL_CUTOFF:
        raise SecError(f"cutoff {cutoff} is after the final-test limit {FINAL_CUTOFF}")
    late = [
        f
        for f in filings
        if f["filingDate"] > cutoff.isoformat() or f["acceptance_eastern"][:10] > cutoff.isoformat()
    ]
    if late:
        raise SecError(f"{ticker}: refusing to save — {len(late)} filings after {cutoff}")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{ticker.upper()}_CIK{cik:010d}_8k_to-{cutoff.isoformat()}.json"
    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.write_text(
        json.dumps({"ticker": ticker, "cik": cik, "filings": filings}, indent=1), encoding="utf-8"
    )
    meta = {
        "source": "SEC EDGAR submissions API",
        "endpoint": SUBMISSIONS_URL.format(cik=cik),
        "downloaded_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "cutoff_on_or_before": cutoff.isoformat(),
        "forms_kept": list(FORMS),
        **info,
        "timezone_note": "acceptanceDateTime is UTC ('Z'); acceptance_eastern added (America/New_York)",
        "package_version": __version__,
        "licence_note": "SEC: public information, may be copied; cite SEC as the source. data/ is git-ignored.",
        **git_state(repo_dir),
    }
    path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return path
