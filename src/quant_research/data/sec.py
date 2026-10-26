"""Download company financial facts from SEC EDGAR's XBRL API (Phase 7, Step 7.1). Free, no API key.

Docs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
Fair access (https://www.sec.gov/os/accessing-edgar-data): max 10 requests/second and a declared User-Agent
(name + contact email). The User-Agent comes from .env (SEC_USER_AGENT) and is never printed, logged or saved.
We wait at least 1 second between requests.

D8 + point-in-time: every fact carries the date it was filed. Facts filed after 2020-12-31 are dropped
IN MEMORY, before anything is written to disk (like the RBA trim) — the counts go into meta.json.
"""

import copy
import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from quant_research import __version__
from quant_research.data.storage import git_state

logger = logging.getLogger(__name__)

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
CUTOFF = date(2020, 12, 31)  # D8: nothing filed after this date is kept
MIN_SECONDS_BETWEEN_REQUESTS = 1.0  # SEC allows 10/s; we stay far below
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


class SecError(RuntimeError):
    """SEC request failed or returned data we cannot use."""


class Throttle:
    """Makes sure two requests are at least `seconds` apart."""

    def __init__(
        self,
        seconds: float = MIN_SECONDS_BETWEEN_REQUESTS,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.seconds, self.clock, self.sleep = seconds, clock, sleep
        self.last: float | None = None

    def wait(self) -> None:
        if self.last is not None:
            gap = self.clock() - self.last
            if gap < self.seconds:
                self.sleep(self.seconds - gap)
        self.last = self.clock()


def get_json(
    url: str,
    user_agent: str,
    throttle: Throttle,
    client: httpx.Client | None = None,
    max_attempts: int = 4,
    backoff_seconds: float = 5.0,
) -> Any:
    """GET an SEC URL with the declared User-Agent; retry 429 / 5xx / network errors (slowly)."""
    if not user_agent or "@" not in user_agent:
        raise SecError(
            "SEC_USER_AGENT is empty or has no email — add it to .env (SEC fair-access rule)"
        )
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
    own_client = client is None
    http = client if client is not None else httpx.Client(timeout=60.0)
    try:
        last_problem = ""
        for attempt in range(1, max_attempts + 1):
            throttle.wait()
            try:
                response = http.get(url, headers=headers)
            except httpx.TransportError as exc:
                last_problem = f"network error: {type(exc).__name__}"
            else:
                if response.status_code == 200:
                    return response.json()
                if response.status_code not in RETRY_STATUS_CODES:
                    raise SecError(
                        f"SEC returned HTTP {response.status_code} for {url} (not retried)"
                    )
                last_problem = f"HTTP {response.status_code}"
            if attempt < max_attempts:
                wait = backoff_seconds * 2 ** (attempt - 1)
                logger.warning(
                    "SEC %s (attempt %d/%d) — retrying in %.0fs",
                    last_problem,
                    attempt,
                    max_attempts,
                    wait,
                )
                throttle.sleep(wait)
        raise SecError(
            f"SEC request failed after {max_attempts} attempts ({last_problem}) for {url}"
        )
    finally:
        if own_client:
            http.close()


def ciks_for(tickers_json: Any, tickers: list[str]) -> dict[str, dict[str, Any]]:
    """{TICKER: {"cik": int, "title": str}} from SEC's company_tickers.json; error if a ticker is absent or repeated."""
    if not isinstance(tickers_json, dict):
        raise SecError(
            f"company_tickers.json: expected an object, got {type(tickers_json).__name__}"
        )
    found: dict[str, list[dict[str, Any]]] = {}
    for row in tickers_json.values():
        t = str(row["ticker"]).upper()
        if t in tickers:
            found.setdefault(t, []).append({"cik": int(row["cik_str"]), "title": str(row["title"])})
    missing = [t for t in tickers if t not in found]
    if missing:
        raise SecError(f"tickers not in SEC's list: {missing}")
    repeated = {t: rows for t, rows in found.items() if len({r["cik"] for r in rows}) > 1}
    if repeated:
        raise SecError(f"tickers with more than one CIK: {repeated}")
    return {t: found[t][0] for t in tickers}


def trim_companyfacts(
    data: dict[str, Any], cutoff: date = CUTOFF
) -> tuple[dict[str, Any], dict[str, int]]:
    """Copy of a companyfacts JSON keeping ONLY facts with filed ≤ cutoff; empty units / concepts are removed.

    Returns (trimmed, counts). A fact without a `filed` date is an error (we could not prove it is old enough).
    """
    if "facts" not in data or not isinstance(data["facts"], dict):
        raise SecError("companyfacts JSON has no 'facts' object")
    out = copy.deepcopy(data)
    kept = dropped = concepts_dropped = 0
    for taxonomy, concepts in out["facts"].items():
        for name in list(concepts):
            units = concepts[name].get("units", {})
            for unit in list(units):
                facts = []
                for fact in units[unit]:
                    if "filed" not in fact:
                        raise SecError(
                            f"{taxonomy}:{name} [{unit}] has a fact without 'filed': {fact}"
                        )
                    if date.fromisoformat(fact["filed"]) <= cutoff:
                        facts.append(fact)
                    else:
                        dropped += 1
                kept += len(facts)
                if facts:
                    units[unit] = facts
                else:
                    del units[unit]
            if not units:
                del concepts[name]
                concepts_dropped += 1
    counts = {
        "facts_kept": kept,
        "facts_dropped_after_cutoff": dropped,
        "concepts_dropped_empty": concepts_dropped,
    }
    return out, counts


def latest_filed(data: dict[str, Any]) -> date | None:
    """Latest `filed` date of any fact (used to prove the trim worked)."""
    dates = [
        date.fromisoformat(f["filed"])
        for concepts in data["facts"].values()
        for c in concepts.values()
        for facts in c.get("units", {}).values()
        for f in facts
    ]
    return max(dates) if dates else None


def save_companyfacts(
    trimmed: dict[str, Any],
    counts: dict[str, int],
    ticker: str,
    cik: int,
    out_dir: Path,
    cutoff: date = CUTOFF,
    repo_dir: Path | None = None,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Write `<out_dir>/<TICKER>_CIK##########_filed-to-<cutoff>.json` + `.meta.json` (no User-Agent inside)."""
    newest = latest_filed(trimmed)
    if newest is not None and newest > cutoff:
        raise SecError(f"{ticker}: refusing to save — a fact filed {newest} is after {cutoff}")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{ticker.upper()}_CIK{cik:010d}_filed-to-{cutoff.isoformat()}"
    json_path, meta_path = out_dir / f"{stem}.json", out_dir / f"{stem}.meta.json"
    existing = [p for p in (json_path, meta_path) if p.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            f"{', '.join(map(str, existing))} already exists — pass overwrite=True to replace it"
        )
    meta = {
        "source": "SEC EDGAR XBRL companyfacts API",
        "endpoint": COMPANYFACTS_URL.format(cik=cik),
        "ticker": ticker.upper(),
        "cik": cik,
        "entity_name": trimmed.get("entityName"),
        "downloaded_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "cutoff_filed_on_or_before": cutoff.isoformat(),
        **counts,
        "latest_filed_kept": newest.isoformat() if newest else None,
        "taxonomies": {k: len(v) for k, v in trimmed["facts"].items()},
        "package_version": __version__,
        "licence_note": "SEC: public information, may be copied; cite SEC as the source (sec.gov/privacy). "
        "Stored in data/ (git-ignored) like all downloaded data.",
        **git_state(repo_dir if repo_dir is not None else Path.cwd()),
    }
    json_path.write_text(json.dumps(trimmed), encoding="utf-8")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return json_path, meta_path
