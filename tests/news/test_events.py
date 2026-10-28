"""Tests for 8-K download shaping, classification, timing and the availability rule (synthetic filings, no internet)."""

from datetime import date, datetime

import pytest

from quant_research.backtesting.lookahead import check_events_no_lookahead
from quant_research.data.sec import SecError
from quant_research.data.sec_submissions import (
    acceptance_eastern,
    keep_8k_until_cutoff,
    rows_from_columns,
)
from quant_research.news.events import (
    EXHIBITS_ONLY,
    Event,
    categories,
    timing,
    usable_by,
    usable_close_day,
)


def et(text: str) -> datetime:
    """A raw EDGAR acceptance time (UTC, 'Z') → US/Eastern, exactly as the download does it."""
    return acceptance_eastern(text)


# ---------- timezone ----------
def test_acceptance_time_is_utc_and_converted_with_dst():
    # Apple's earnings 8-Ks, both released at 16:30 New York time: summer (EDT, UTC−4) and winter (EST, UTC−5)
    assert et("2019-10-30T20:30:40.000Z").isoformat() == "2019-10-30T16:30:40-04:00"
    assert et("2020-01-28T21:30:40.000Z").isoformat() == "2020-01-28T16:30:40-05:00"


def test_acceptance_time_without_utc_marker_is_refused():
    with pytest.raises(SecError, match="refusing to guess"):
        acceptance_eastern("2019-10-30T16:30:40")


# ---------- download shaping ----------
def row(form: str, filed: str, accepted: str, items: str = "2.02,9.01", accn: str = "A") -> dict:
    return {"form": form, "filingDate": filed, "acceptanceDateTime": accepted, "items": items,
            "accessionNumber": accn, "primaryDocument": "x.htm", "reportDate": filed}  # fmt: skip


def test_keep_only_8k_until_the_cutoff():
    rows = [
        row("8-K", "2020-12-30", "2020-12-30T21:23:04.000Z", accn="1"),
        row("8-K/A", "2020-06-01", "2020-06-01T13:00:00.000Z", accn="2"),
        row("10-Q", "2020-05-01", "2020-05-01T20:00:00.000Z", accn="3"),
        row("8-K", "2021-01-04", "2021-01-04T14:00:00.000Z", accn="4"),
        # filed 2020-12-31 but accepted 2021-01-01 00:30 ET (05:30 UTC) → after the cutoff in US/Eastern
        row("8-K", "2020-12-31", "2021-01-01T05:30:00.000Z", accn="5"),
    ]
    kept, counts = keep_8k_until_cutoff(rows)
    assert [r["accessionNumber"] for r in kept] == ["2", "1"]  # sorted by acceptance time
    assert counts == {"8k_kept": 2, "8k_dropped_after_cutoff": 2, "other_forms_not_kept": 1}
    assert kept[1]["acceptance_eastern"] == "2020-12-30T16:23:04-05:00"


def test_rows_from_columns_checks_fields_and_lengths():
    cols = {k: [v] for k, v in row("8-K", "2020-01-02", "2020-01-02T12:00:00.000Z").items()}
    assert rows_from_columns(cols)[0]["form"] == "8-K"
    with pytest.raises(SecError, match="missing"):
        rows_from_columns({k: v for k, v in cols.items() if k != "items"})
    cols["items"] = []
    with pytest.raises(SecError, match="lengths"):
        rows_from_columns(cols)


# ---------- classification ----------
def test_categories_from_official_item_codes():
    assert categories("2.02,9.01") == ["earnings"]
    assert categories("9.01") == [EXHIBITS_ONLY]
    assert categories("5.02,7.01,9.01") == ["leadership change", "disclosure / other"]
    assert categories("7.01,8.01") == ["disclosure / other"]  # one category, listed once
    assert categories("1.01,2.03") == ["deal signed", "other (2.03)"]
    assert categories("1.03") == ["bankruptcy"] and categories("4.02") == [
        "restatement / non-reliance"
    ]


def test_unrecognised_codes_are_reported_never_guessed():
    assert categories("5,7") == [
        "UNRECOGNISED (5)",
        "UNRECOGNISED (7)",
    ]  # pre-2004 single-number codes
    assert categories("") == ["UNRECOGNISED (no item codes)"]


# ---------- availability rule + timing (real NYSE calendar) ----------
@pytest.mark.parametrize(
    ("accepted_utc", "usable", "when"),
    [
        (
            "2019-10-30T13:00:00.000Z",
            date(2019, 10, 30),
            "before open",
        ),  # 09:00 ET → that day's close
        ("2019-10-30T17:00:00.000Z", date(2019, 10, 30), "during trading"),  # 13:00 ET
        (
            "2019-10-30T20:30:40.000Z",
            date(2019, 10, 31),
            "after close",
        ),  # 16:30 ET → next day's close
        ("2020-01-25T15:00:00.000Z", date(2020, 1, 27), "non-trading day"),  # Saturday → Monday
        (
            "2019-07-04T14:00:00.000Z",
            date(2019, 7, 5),
            "non-trading day",
        ),  # Independence Day holiday
        (
            "2019-11-29T19:00:00.000Z",
            date(2019, 12, 2),
            "after close",
        ),  # 14:00 ET on a 13:00 early-close day
        (
            "2019-11-29T17:00:00.000Z",
            date(2019, 11, 29),
            "during trading",
        ),  # 12:00 ET, before the early close
        # DST starts Sun 2020-03-08: the same UTC hour is 15:30 ET on Friday (EST) but 16:30 ET on Monday (EDT)
        ("2020-03-06T20:30:00.000Z", date(2020, 3, 6), "during trading"),
        ("2020-03-09T20:30:00.000Z", date(2020, 3, 10), "after close"),
    ],
)
def test_availability_rule(accepted_utc, usable, when):
    t = et(accepted_utc)
    assert usable_close_day(t) == usable
    assert timing(t) == when


def test_naive_time_is_refused():
    with pytest.raises(ValueError, match="timezone-aware"):
        usable_close_day(datetime(2020, 1, 2, 10, 0))


def test_amendment_is_its_own_event_never_back_dated():
    original = Event(
        "A1", "8-K", et("2020-02-03T21:00:00.000Z"), ("earnings",)
    )  # Mon 16:00 ET → Tue
    amendment = Event(
        "A2", "8-K/A", et("2020-02-07T21:30:00.000Z"), ("earnings",)
    )  # Fri 16:30 ET → Mon
    assert usable_close_day(original.accepted_et) == date(2020, 2, 4)
    assert usable_close_day(amendment.accepted_et) == date(2020, 2, 10)
    assert usable_by(date(2020, 2, 7), [original, amendment]) == [original]
    assert usable_by(date(2020, 2, 10), [original, amendment]) == [original, amendment]


# ---------- the events spy check ----------
DAYS = [date(2020, 2, d) for d in (3, 4, 5, 6, 7, 10, 11)]
EVENTS = [
    Event(
        "E1", "8-K", et("2020-02-04T21:30:00.000Z"), ("earnings",)
    ),  # Tue after close → usable Wed
    Event("E2", "8-K", et("2020-02-06T14:00:00.000Z"), ("earnings",)),  # Thu 09:00 → usable Thu
]


def test_spy_check_passes_a_decision_that_uses_the_rule():
    def decide(day, events):
        return len([e for e in usable_by(day, events) if "earnings" in e.categories])

    check_events_no_lookahead(decide, DAYS, EVENTS)


def test_spy_check_catches_a_decision_that_peeks_after_the_close():
    def leaky(
        day, events
    ):  # counts a filing on its calendar day, even when it came after the close
        return len([e for e in events if e.accepted_et.date() <= day])

    with pytest.raises(AssertionError, match="look-ahead"):
        check_events_no_lookahead(leaky, DAYS, EVENTS)


# ---------- logged override + loading saved events ----------
def test_att_override_reclassifies_only_that_filing():
    from quant_research.news.events import OVERRIDES, filing_categories

    att = {"accessionNumber": "0000732717-12-000006", "items": "1.03,9.01"}
    other = {"accessionNumber": "0000732717-12-000007", "items": "1.03,9.01"}
    assert filing_categories(att) == ["deal signed (1.01-type), reclassified"]
    assert filing_categories(other) == ["bankruptcy"]  # the rule itself is unchanged
    assert OVERRIDES["0000732717-12-000006"][2].startswith(
        "https://www.sec.gov/Archives/edgar/data/732717/"
    )


def test_load_events_from_a_saved_file(tmp_path):
    import json

    from quant_research.news.events import load_events

    kept, _ = keep_8k_until_cutoff([row("8-K", "2019-10-30", "2019-10-30T20:30:40.000Z", accn="X")])
    (tmp_path / "AAA_CIK0000000001_8k_to-2020-12-31.json").write_text(json.dumps({"filings": kept}))
    [e] = load_events("aaa", tmp_path)
    assert (e.accession, e.form, e.categories) == ("X", "8-K", ("earnings",))
    assert e.accepted_et.isoformat() == "2019-10-30T16:30:40-04:00"
    assert load_events("SPY", tmp_path) == []  # a fund files no 8-Ks
