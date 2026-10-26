"""Tests for quant_research.data.sec — no live internet (HTTP layer is mocked)."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from quant_research.data.sec import (
    SecError,
    Throttle,
    ciks_for,
    get_json,
    latest_filed,
    save_companyfacts,
    trim_companyfacts,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sec_companyfacts_sample.json"
FAKE_UA = "Test Person test@example.com"


def load() -> dict:
    return json.loads(FIXTURE.read_text())


def test_trim_drops_facts_filed_after_cutoff_and_counts_them():
    data = load()
    trimmed, counts = trim_companyfacts(data, date(2020, 12, 31))
    # fixture: 2 facts filed 2021-02-12 (NetIncomeLoss FY2020, Goodwill) → dropped; Goodwill concept becomes empty
    assert counts["facts_dropped_after_cutoff"] == 2
    assert counts["concepts_dropped_empty"] == 1
    assert "Goodwill" not in trimmed["facts"]["us-gaap"]
    assert latest_filed(trimmed) == date(2020, 5, 1)
    total = sum(
        len(f) for c in data["facts"].values() for k in c.values() for f in k["units"].values()
    )
    assert counts["facts_kept"] == total - 2
    assert latest_filed(data) == date(2021, 2, 12)  # the input is not changed


def test_trim_keeps_a_fact_filed_exactly_on_the_cutoff():
    data = load()
    data["facts"]["us-gaap"]["Assets"]["units"]["USD"][0]["filed"] = "2020-12-31"
    trimmed, _ = trim_companyfacts(data, date(2020, 12, 31))
    assert trimmed["facts"]["us-gaap"]["Assets"]["units"]["USD"][0]["filed"] == "2020-12-31"


def test_trim_refuses_a_fact_without_filed_date():
    data = load()
    del data["facts"]["us-gaap"]["Assets"]["units"]["USD"][0]["filed"]
    with pytest.raises(SecError, match="without 'filed'"):
        trim_companyfacts(data)


def test_save_refuses_untrimmed_data_and_never_overwrites(tmp_path):
    with pytest.raises(SecError, match="after 2020-12-31"):
        save_companyfacts(load(), {}, "SYN", 1, tmp_path)
    trimmed, counts = trim_companyfacts(load())
    json_path, meta_path = save_companyfacts(trimmed, counts, "SYN", 1, tmp_path, repo_dir=tmp_path)
    assert json_path.name == "SYN_CIK0000000001_filed-to-2020-12-31.json"
    meta = json.loads(meta_path.read_text())
    assert meta["facts_dropped_after_cutoff"] == 2 and meta["latest_filed_kept"] == "2020-05-01"
    assert "@" not in meta_path.read_text()  # no User-Agent / email saved
    with pytest.raises(FileExistsError):
        save_companyfacts(trimmed, counts, "SYN", 1, tmp_path)


def test_ciks_for_reads_sec_ticker_list_and_fails_loudly():
    sec_list = {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 21344, "ticker": "KO", "title": "COCA COLA CO"},
    }
    assert ciks_for(sec_list, ["AAPL", "KO"]) == {
        "AAPL": {"cik": 320193, "title": "Apple Inc."},
        "KO": {"cik": 21344, "title": "COCA COLA CO"},
    }
    with pytest.raises(SecError, match="not in SEC's list"):
        ciks_for(sec_list, ["AAPL", "SPY"])
    sec_list["2"] = {"cik_str": 999, "ticker": "KO", "title": "other"}
    with pytest.raises(SecError, match="more than one CIK"):
        ciks_for(sec_list, ["KO"])


def test_get_json_sends_user_agent_retries_and_throttles():
    seen, calls = [], {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["User-Agent"])
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] == 1 else httpx.Response(200, json={"ok": True})

    sleeps: list[float] = []
    clock = iter(
        [0.0, 0.2, 1.0]
    ).__next__  # 1st request at 0 s; 2nd wait sees 0.2 s, then stamps 1.0
    throttle = Throttle(1.0, clock=clock, sleep=sleeps.append)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert get_json("https://data.sec.gov/x", FAKE_UA, throttle, client, backoff_seconds=5) == {
            "ok": True
        }
    assert seen == [FAKE_UA, FAKE_UA]
    assert sleeps == [5.0, 0.8]  # back-off after the 503, then the throttle tops the gap up to 1 s


def test_get_json_requires_user_agent_with_email():
    with pytest.raises(SecError, match="SEC_USER_AGENT"):
        get_json("https://data.sec.gov/x", "", Throttle(sleep=lambda s: None))
    with pytest.raises(SecError, match="no email"):
        get_json("https://data.sec.gov/x", "Just A Name", Throttle(sleep=lambda s: None))


def test_get_json_does_not_retry_404():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(SecError, match="HTTP 404"),
    ):
        get_json("https://data.sec.gov/x", FAKE_UA, Throttle(sleep=lambda s: None), client)
