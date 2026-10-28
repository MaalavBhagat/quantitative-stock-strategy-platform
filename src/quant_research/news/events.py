"""Company events from SEC Form 8-K filings (Phase 9, Steps 9.3–9.4). Rule-based — no AI, no prices, no returns.

Categories come only from the OFFICIAL item codes (SEC Form 8-K, form SEC 873 (02-25), https://www.sec.gov/files/form8-k.pdf).
AVAILABILITY RULE (DATA_SOURCES §12): an event becomes usable for a decision at the CLOSE of the first NYSE trading day D
whose close (16:00 ET, 13:00 ET on early-close days) is AFTER the acceptance time (US/Eastern) → trade at D+1's open.
8-K/A amendments are separate events at their own acceptance time (never back-dated to the original).
"""

import bisect
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
OPEN_ET = time(9, 30)

# official Form 8-K items (all current codes) — titles abbreviated
OFFICIAL_ITEMS = {
    "1.01", "1.02", "1.03", "1.04", "1.05", "2.01", "2.02", "2.03", "2.04", "2.05", "2.06", "3.01", "3.02", "3.03",
    "4.01", "4.02", "5.01", "5.02", "5.03", "5.04", "5.05", "5.06", "5.07", "5.08", "6.01", "6.02", "6.03", "6.04",
    "6.05", "6.06", "7.01", "8.01", "9.01",
}  # fmt: skip
CATEGORY = {
    "2.02": "earnings",
    "1.01": "deal signed",
    "2.01": "deal completed",
    "5.02": "leadership change",
    "5.07": "shareholder vote",
    "2.06": "impairment",
    "4.02": "restatement / non-reliance",
    "1.03": "bankruptcy",
    "3.01": "delisting notice",
    "7.01": "disclosure / other",
    "8.01": "disclosure / other",
}
EXHIBITS_ONLY = "exhibits only"
# Logged per-filing overrides (accession → categories, reason, source). Only for proven filer coding errors.
OVERRIDES: dict[str, tuple[tuple[str, ...], str, str]] = {
    "0000732717-12-000006": (
        ("deal signed (1.01-type), reclassified",),
        (
            "AT&T 8-K 2012-01-13 is tagged item 1.03 (bankruptcy), but its own heading reads 'Item 1.03 Entry into "
            "a Material Definitive Agreement' and it concerns reducing a US$5bn credit facility to US$3bn — a filer "
            "coding error (chat Claude ruling 2026-10-28, PROJECT_STATUS)."
        ),
        "https://www.sec.gov/Archives/edgar/data/732717/000073271712000006/creditfacility_8k.htm",
    ),
}


def categories(items: str) -> list[str]:
    """Categories of one filing from its item codes ('2.02,9.01'). Several categories possible.

    9.01 alone → 'exhibits only' (not an event on its own); 9.01 next to other items adds nothing. An official code
    without a category → 'other (x.xx)'. A code NOT in the official list (e.g. pre-2004 single numbers) →
    'UNRECOGNISED (x)' — never guessed.
    """
    codes = [c.strip() for c in items.split(",") if c.strip()]
    if codes == ["9.01"]:
        return [EXHIBITS_ONLY]
    out = []
    for c in codes:
        if c == "9.01":
            continue
        if c not in OFFICIAL_ITEMS:
            label = f"UNRECOGNISED ({c})"
        else:
            label = CATEGORY.get(c, f"other ({c})")
        if label not in out:
            out.append(label)
    return out or ["UNRECOGNISED (no item codes)"]


def filing_categories(filing: dict) -> list[str]:
    """Categories of a saved filing: the logged override if its accession has one, else categories(items)."""
    override = OVERRIDES.get(filing["accessionNumber"])
    return list(override[0]) if override else categories(filing["items"])


@cache
def _schedule() -> dict[date, datetime]:
    """NYSE session date → its close time (US/Eastern), 1994–2021, from exchange_calendars (early closes included)."""
    import exchange_calendars as xcals

    cal = xcals.get_calendar("XNYS", start="1994-01-01", end="2021-12-31")
    sched = cal.schedule
    return {
        d.date(): c.to_pydatetime().astimezone(EASTERN)
        for d, c in zip(sched.index, sched["close"], strict=True)
    }


def close_on(day: date, schedule: dict[date, datetime] | None = None) -> datetime | None:
    """NYSE close (US/Eastern) of `day`, or None if it is not a trading day."""
    return (schedule if schedule is not None else _schedule()).get(day)


@cache
def _default_days() -> tuple[date, ...]:
    return tuple(sorted(_schedule()))


def usable_close_day(accepted_et: datetime, schedule: dict[date, datetime] | None = None) -> date:
    """First trading day D whose close is after the acceptance time: the event is usable at D's close."""
    if accepted_et.tzinfo is None:
        raise ValueError("acceptance time must be timezone-aware (US/Eastern)")
    sched = schedule if schedule is not None else _schedule()
    days = tuple(sorted(sched)) if schedule is not None else _default_days()
    i = bisect.bisect_left(days, accepted_et.date())
    for d in days[i : i + 10]:  # the next trading day is never more than a few calendar days away
        if accepted_et < sched[d]:
            return d
    raise ValueError(f"no trading day after {accepted_et} in the calendar")


def timing(accepted_et: datetime, schedule: dict[date, datetime] | None = None) -> str:
    """'before open' / 'during trading' / 'after close' on a trading day, else 'non-trading day' (US/Eastern)."""
    close = close_on(accepted_et.date(), schedule)
    if close is None:
        return "non-trading day"
    t = accepted_et.timetz().replace(tzinfo=None)
    if t < OPEN_ET:
        return "before open"
    return "during trading" if accepted_et < close else "after close"


@dataclass(frozen=True)
class Event:
    accession: str
    form: str  # 8-K or 8-K/A (an amendment is its own event)
    accepted_et: datetime
    categories: tuple[str, ...]


def load_events(ticker: str, sub_dir: Path) -> list[Event]:
    """8-K / 8-K/A events of one company from the saved submissions file (≤ 2020-12-31). No file (e.g. SPY) → []."""
    paths = sorted(sub_dir.glob(f"{ticker.upper()}_CIK*_8k_to-2020-12-31.json"))
    if not paths:
        return []
    [path] = paths
    filings = json.loads(path.read_text(encoding="utf-8"))["filings"]
    return [
        Event(
            f["accessionNumber"],
            f["form"],
            datetime.fromisoformat(f["acceptance_eastern"]),
            tuple(filing_categories(f)),
        )
        for f in filings
    ]


def usable_by(
    day: date, events: Sequence[Event], schedule: dict[date, datetime] | None = None
) -> list[Event]:
    """Events a decision at the CLOSE of `day` may use (availability rule)."""
    return [e for e in events if usable_close_day(e.accepted_et, schedule) <= day]
