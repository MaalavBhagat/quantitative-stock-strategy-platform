"""Financial indicators from SEC XBRL companyfacts, POINT-IN-TIME (Phase 7, Step 7.1; Step 7.4 groundwork).

Floats are fine here (D1: Decimal only in the ledger). Nothing is guessed or filled: a value that is not in the
filings is MISSING.

Point-in-time rule (PROJECT_STATUS decision, prompt 19):
- A fact may be used on trading day T only if its filed date is STRICTLY BEFORE T (a filing can arrive after
  the close of its filing day).
- Restatements: for one period, the value is the one in the LATEST filing filed before T — i.e. the value as
  first filed until a later filing replaces it, from that later filing's date. Never a value before it was public.
- Two different values for the same period in filings with the same filed date → CONFLICT (never pick one).

Annual values only: forms 10-K / 10-K/A; durations 350–380 days (52/53-week years); instants at the fiscal-year end.
"""

import itertools
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

FOUND, FALLBACK, MISSING, CONFLICT = "found", "fallback", "MISSING", "CONFLICT"
ANNUAL_DAYS = (350, 380)
MAX_REPORT_LAG_DAYS = 180  # a 10-K is filed within months of its year end
MIN_FACTS_FOR_YEAR_END = 5


@dataclass(frozen=True)
class Fact:
    tag: str
    unit: str
    start: date | None  # None for an instant (balance-sheet) fact
    end: date
    val: float
    filed: date
    form: str
    accn: str
    fy: int | None
    fp: str | None


@dataclass(frozen=True)
class Concept:
    """One accounting item: XBRL tags in priority order (first = preferred, the rest = fallbacks)."""

    name: str
    tags: tuple[str, ...]
    unit: str
    instant: bool
    must_agree: int = (
        0  # the first n tags mean the same thing: if 2+ have values that differ > 0.5% → CONFLICT
    )


AGREE_TOLERANCE = 0.005
REVENUE = Concept(
    "revenue",
    (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueGoodsNet",  # goods only — last resort, not cross-checked (KO tags its revenue this way)
    ),
    "USD",
    False,
    must_agree=4,  # PG FY2014 `Revenues` 29.4bn vs `SalesRevenueNet` 83.1bn → must not silently pick one
)
NET_INCOME = Concept(
    "net income",
    ("NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic", "ProfitLoss"),
    "USD",
    False,
)
ASSETS = Concept("total assets", ("Assets",), "USD", True)
OCF = Concept(
    "operating cash flow",
    (
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ),
    "USD",
    False,
)
CAPEX = Concept(
    "capex",
    ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"),
    "USD",
    False,
)
LIABILITIES = Concept("total liabilities", ("Liabilities",), "USD", True)
LIAB_AND_EQUITY = Concept(
    "liabilities and equity", ("LiabilitiesAndStockholdersEquity",), "USD", True
)
EQUITY_INCL_NCI = Concept(
    "equity incl. non-controlling",
    ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",),
    "USD",
    True,
)
EQUITY_PARENT = Concept("equity (parent only)", ("StockholdersEquity",), "USD", True)
NCI_TAGS = (
    "MinorityInterest",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
)
CURRENT_ASSETS = Concept("current assets", ("AssetsCurrent",), "USD", True)
CURRENT_LIABILITIES = Concept("current liabilities", ("LiabilitiesCurrent",), "USD", True)
EPS = Concept("EPS", ("EarningsPerShareDiluted", "EarningsPerShareBasic"), "USD/shares", False)

CONCEPTS = [REVENUE, NET_INCOME, ASSETS, OCF, CAPEX, LIABILITIES, LIAB_AND_EQUITY, EQUITY_INCL_NCI]
CONCEPTS += [CURRENT_ASSETS, CURRENT_LIABILITIES, EPS]
INDICATORS = [
    "net_margin",
    "return_on_assets",
    "operating_cash_flow",
    "free_cash_flow",
    "fcf_margin",
    "liabilities_to_assets",
    "current_ratio",
    "eps_growth_stdev_5y",
]


# ---------- reading the JSON ----------
def facts_for(companyfacts: dict[str, Any], tag: str, unit: str) -> list[Fact]:
    """All us-gaap facts for one tag + unit (empty list if the company never used the tag)."""
    concept = companyfacts.get("facts", {}).get("us-gaap", {}).get(tag)
    if concept is None:
        return []
    out = []
    for f in concept.get("units", {}).get(unit, []):
        out.append(
            Fact(
                tag=tag,
                unit=unit,
                start=date.fromisoformat(f["start"]) if f.get("start") else None,
                end=date.fromisoformat(f["end"]),
                val=float(f["val"]),
                filed=date.fromisoformat(f["filed"]),
                form=str(f.get("form", "")),
                accn=str(f.get("accn", "")),
                fy=f.get("fy"),
                fp=f.get("fp"),
            )
        )
    return out


def is_annual(f: Fact, instant: bool) -> bool:
    if not f.form.startswith("10-K"):
        return False
    if instant:
        return f.start is None
    return f.start is not None and ANNUAL_DAYS[0] <= (f.end - f.start).days <= ANNUAL_DAYS[1]


def usable_on(f: Fact, day: date) -> bool:
    """The point-in-time rule: filed strictly before the trading day."""
    return f.filed < day


# ---------- point-in-time value of one tag for one period ----------
@dataclass(frozen=True)
class PitValue:
    status: str  # FOUND / MISSING / CONFLICT
    fact: Fact | None = None
    note: str = ""


def value_as_of(facts: list[Fact], period_end: date, day: date, instant: bool) -> PitValue:
    """Value for the annual period ending `period_end`, as known on trading day `day` (latest filing before it)."""
    candidates = [
        f for f in facts if f.end == period_end and is_annual(f, instant) and usable_on(f, day)
    ]
    if not candidates:
        return PitValue(MISSING)
    newest = max(f.filed for f in candidates)
    latest = [f for f in candidates if f.filed == newest]
    if len({f.val for f in latest}) > 1:
        return PitValue(CONFLICT, None, f"{len(latest)} different values filed {newest}")
    return PitValue(FOUND, latest[0])


@dataclass(frozen=True)
class Component:
    concept: str
    status: str  # FOUND (first tag) / FALLBACK (a later tag or derived) / MISSING / CONFLICT
    value: float | None
    facts: tuple[Fact, ...] = ()
    note: str = ""


def concept_as_of(
    companyfacts: dict[str, Any], concept: Concept, period_end: date, day: date
) -> Component:
    """First tag in priority order that has a point-in-time value; a conflict stops the search (never skipped).

    If `concept.must_agree` = n, the first n tags are compared first: two values more than 0.5% apart → CONFLICT.
    """
    if concept.must_agree:
        seen = {}
        for tag in concept.tags[: concept.must_agree]:
            pv = value_as_of(
                facts_for(companyfacts, tag, concept.unit), period_end, day, concept.instant
            )
            if pv.fact is not None:
                seen[tag] = pv.fact.val
        if len(seen) > 1:
            lo, hi = min(seen.values()), max(seen.values())
            if lo <= 0 or (hi - lo) / lo > AGREE_TOLERANCE:
                listing = ", ".join(f"{t} {v:,.0f}" for t, v in seen.items())
                return Component(concept.name, CONFLICT, None, (), f"tags disagree: {listing}")
    for i, tag in enumerate(concept.tags):
        pv = value_as_of(
            facts_for(companyfacts, tag, concept.unit), period_end, day, concept.instant
        )
        if pv.status == CONFLICT:
            return Component(concept.name, CONFLICT, None, (), f"{tag}: {pv.note}")
        if pv.status == FOUND and pv.fact is not None:
            return Component(
                concept.name, FOUND if i == 0 else FALLBACK, pv.fact.val, (pv.fact,), tag
            )
    return Component(concept.name, MISSING, None, (), "none of: " + ", ".join(concept.tags))


def _nci_tagged(companyfacts: dict[str, Any], period_end: date, day: date) -> bool:
    """True if ANY non-controlling-interest fact for this date was public before `day`."""
    return any(
        value_as_of(facts_for(companyfacts, tag, "USD"), period_end, day, True).status != MISSING
        for tag in NCI_TAGS
    )


def liabilities_as_of(companyfacts: dict[str, Any], period_end: date, day: date) -> Component:
    """Total liabilities, in this order:

    1. tag Liabilities (FOUND);
    2. FALLBACK (derived) LiabilitiesAndStockholdersEquity − StockholdersEquityIncludingPortionAttributableTo…;
    3. FALLBACK (derived, ASSUMPTION) LiabilitiesAndStockholdersEquity − StockholdersEquity — ONLY when the company
       tagged no non-controlling interest at all for that date (assumes it has none; else MISSING, never guessed).
    """
    direct = concept_as_of(companyfacts, LIABILITIES, period_end, day)
    if direct.status in (FOUND, CONFLICT):
        return direct
    total = concept_as_of(companyfacts, LIAB_AND_EQUITY, period_end, day)
    if total.value is None:
        return Component(
            "total liabilities",
            MISSING,
            None,
            (),
            "no Liabilities and no LiabilitiesAndStockholdersEquity",
        )
    with_nci = concept_as_of(companyfacts, EQUITY_INCL_NCI, period_end, day)
    if with_nci.value is not None:
        return Component(
            "total liabilities",
            FALLBACK,
            total.value - with_nci.value,
            total.facts + with_nci.facts,
            "derived: LiabilitiesAndStockholdersEquity − StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        )
    parent = concept_as_of(companyfacts, EQUITY_PARENT, period_end, day)
    if parent.value is None or _nci_tagged(companyfacts, period_end, day):
        return Component(
            "total liabilities",
            MISSING,
            None,
            (),
            "no Liabilities; derived fallbacks incomplete or NCI present",
        )
    return Component(
        "total liabilities",
        FALLBACK,
        total.value - parent.value,
        total.facts + parent.facts,
        "derived: LiabilitiesAndStockholdersEquity − StockholdersEquity (ASSUMPTION: no non-controlling interest tagged)",
    )


# ---------- fiscal years ----------
@dataclass(frozen=True)
class FiscalYear:
    end: date
    filed: date  # filed date of the ORIGINAL 10-K for this year
    accn: str

    @property
    def usable_from(self) -> date:
        """First calendar day on which this 10-K's facts may be used (strictly after the filed date)."""
        return self.filed + timedelta(days=1)


def fiscal_years(
    companyfacts: dict[str, Any], min_facts: int = MIN_FACTS_FOR_YEAR_END
) -> list[FiscalYear]:
    """One entry per original 10-K (form exactly "10-K"; amendments only replace values later).

    Its fiscal-year end = the LATEST end date among its ~1-year duration facts that (a) is before the filing date
    by at most MAX_REPORT_LAG_DAYS and (b) is backed by at least `min_facts` facts. Real filings contain
    a few stray facts dated after the filing (e.g. INTC's 10-K filed 2011-02-18 has one ending 2011-12-31) — those
    can never be the year just reported.
    """
    counts: dict[str, dict[date, int]] = {}
    filed_of: dict[str, date] = {}
    for c in companyfacts.get("facts", {}).get("us-gaap", {}).values():
        for facts in c.get("units", {}).values():
            for f in facts:
                if f.get("form") != "10-K" or not f.get("start"):
                    continue
                start, end = date.fromisoformat(f["start"]), date.fromisoformat(f["end"])
                if not ANNUAL_DAYS[0] <= (end - start).days <= ANNUAL_DAYS[1]:
                    continue
                filed = date.fromisoformat(f["filed"])
                filed_of[f["accn"]] = min(filed, filed_of.get(f["accn"], filed))
                ends = counts.setdefault(f["accn"], {})
                ends[end] = ends.get(end, 0) + 1
    first: dict[date, FiscalYear] = {}
    for accn, ends in counts.items():
        filed = filed_of[accn]
        ok = [
            e
            for e, n in ends.items()
            if n >= min_facts and 0 < (filed - e).days <= MAX_REPORT_LAG_DAYS
        ]
        if not ok:
            continue
        end = max(ok)
        if end not in first or filed < first[end].filed:
            first[end] = FiscalYear(end, filed, accn)
    return sorted(first.values(), key=lambda fy: fy.end)


# ---------- indicators ----------
@dataclass(frozen=True)
class Indicator:
    name: str
    status: str  # FOUND / FALLBACK / MISSING / CONFLICT
    value: float | None
    components: tuple[Component, ...] = field(default_factory=tuple)
    note: str = ""


def _combine(name: str, parts: list[Component], compute: Any, note: str = "") -> Indicator:
    for bad in (CONFLICT, MISSING):
        if any(p.status == bad for p in parts):
            return Indicator(name, bad, None, tuple(parts), note)
    try:
        value = compute(*[p.value for p in parts])
    except ZeroDivisionError:
        return Indicator(name, MISSING, None, tuple(parts), "division by zero")
    status = FALLBACK if any(p.status == FALLBACK for p in parts) else FOUND
    return Indicator(name, status, value, tuple(parts), note)


def eps_growth_stdev(
    companyfacts: dict[str, Any], period_end: date, day: date, years: int = 5
) -> Indicator:
    """Sample std dev (n − 1) of the last `years` yearly EPS growth rates ending at `period_end`, as known on `day`.

    Growth_t = (EPS_t − EPS_(t−1)) ÷ |EPS_(t−1)|. Both EPS values of a pair come from the SAME filing (the latest
    filed before `day` that reports both), so a stock split never mixes share bases. Diluted EPS preferred,
    basic EPS as fallback (same tag within a pair). Any missing pair or EPS_(t−1) = 0 → MISSING.
    """
    name = "eps_growth_stdev_5y"
    for i, tag in enumerate(EPS.tags):
        annual = [
            f
            for f in facts_for(companyfacts, tag, EPS.unit)
            if is_annual(f, False) and usable_on(f, day)
        ]
        ends = sorted({f.end for f in annual if f.end <= period_end}, reverse=True)
        if not ends or ends[0] != period_end:
            continue
        chain = [period_end]
        for e in ends[1:]:  # consecutive fiscal years only (gap of one ~year)
            if len(chain) == years + 1:
                break
            if 350 <= (chain[-1] - e).days <= 380:
                chain.append(e)
        if len(chain) < years + 1:
            return Indicator(
                name,
                MISSING,
                None,
                (),
                f"{tag}: only {len(chain)} consecutive years known on {day}",
            )
        growths, used = [], []
        for cur, prev in itertools.pairwise(chain):
            by_accn: dict[str, dict[date, Fact]] = {}
            for f in annual:
                if f.end in (cur, prev):
                    by_accn.setdefault(f.accn, {})[f.end] = f
            pairs = [p for p in by_accn.values() if cur in p and prev in p]
            if not pairs:
                return Indicator(
                    name,
                    MISSING,
                    None,
                    (),
                    f"{tag}: no single filing reports both {prev} and {cur}",
                )
            newest = max(p[cur].filed for p in pairs)
            same_day = [p for p in pairs if p[cur].filed == newest]
            if len({(p[cur].val, p[prev].val) for p in same_day}) > 1:
                return Indicator(
                    name, CONFLICT, None, (), f"{tag}: different EPS pairs filed {newest}"
                )
            pair = same_day[0]
            if pair[prev].val == 0:
                return Indicator(
                    name, MISSING, None, (), f"{tag}: EPS {prev} is 0 (growth undefined)"
                )
            growths.append((pair[cur].val - pair[prev].val) / abs(pair[prev].val))
            used += [pair[cur], pair[prev]]
        comp = Component("EPS pairs", FOUND if i == 0 else FALLBACK, None, tuple(used), tag)
        return Indicator(
            name,
            comp.status,
            statistics.stdev(growths),
            (comp,),
            "growths " + ", ".join(f"{g:+.4f}" for g in growths),
        )
    return Indicator(
        name, MISSING, None, (), f"no EPS ({' / '.join(EPS.tags)}) for {period_end} known on {day}"
    )


def indicators_as_of(
    companyfacts: dict[str, Any], period_end: date, day: date
) -> dict[str, Indicator]:
    """Every Step 7.1 indicator for the fiscal year ending `period_end`, using only facts filed before `day`."""
    c = {k.name: concept_as_of(companyfacts, k, period_end, day) for k in CONCEPTS}
    liabilities = liabilities_as_of(companyfacts, period_end, day)
    rev, ni, assets = c["revenue"], c["net income"], c["total assets"]
    ocf, capex = c["operating cash flow"], c["capex"]
    out = [
        _combine("net_margin", [ni, rev], lambda n, r: n / r, "net income ÷ revenue"),
        _combine(
            "return_on_assets",
            [ni, assets],
            lambda n, a: n / a,
            "net income ÷ year-end total assets",
        ),
        _combine("operating_cash_flow", [ocf], lambda o: o, "USD"),
        _combine("free_cash_flow", [ocf, capex], lambda o, k: o - k, "OCF − capex, USD"),
        _combine(
            "fcf_margin", [ocf, capex, rev], lambda o, k, r: (o - k) / r, "(OCF − capex) ÷ revenue"
        ),
        _combine(
            "liabilities_to_assets",
            [liabilities, assets],
            lambda li, a: li / a,
            "total liabilities ÷ total assets (a debt proxy: includes non-debt liabilities)",
        ),
        _combine(
            "current_ratio",
            [c["current assets"], c["current liabilities"]],
            lambda ca, cl: ca / cl,
            "current assets ÷ current liabilities",
        ),
        eps_growth_stdev(companyfacts, period_end, day),
    ]
    return {i.name: i for i in out}
