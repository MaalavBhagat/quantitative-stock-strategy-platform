"""Tests for quant_research.data.tiingo — no live internet (HTTP layer is mocked)."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from quant_research.data.tiingo import (
    TiingoError,
    fetch_daily_prices,
    fetch_meta,
    parse_prices,
    prices_endpoint,
)

FIXTURE = Path(__file__).parent / "fixtures" / "tiingo_prices_sample.json"
FAKE_KEY = "FAKEKEY1234567890"


def load_fixture() -> list[dict]:
    return json.loads(FIXTURE.read_text())


def no_sleep(_seconds: float) -> None:
    pass


def test_parse_prices_renames_columns_to_conventions():
    df = parse_prices(load_fixture(), "TEST")
    assert list(df.columns) == [
        "date",
        "open_raw",
        "high_raw",
        "low_raw",
        "close_raw",
        "volume_raw",
        "open_adj",
        "high_adj",
        "low_adj",
        "close_adj",
        "volume_adj",
        "div_cash_usd",
        "split_factor",
    ]


def test_parse_prices_dates_are_plain_dates_and_raw_format_recorded():
    df = parse_prices(load_fixture(), "TEST")
    assert df["date"].tolist() == [
        date(2014, 6, 4),
        date(2014, 6, 5),
        date(2014, 6, 6),
        date(2014, 6, 9),
    ]
    assert df.attrs["raw_date_example"] == "2014-06-04T00:00:00.000Z"


def test_parse_prices_dtypes():
    df = parse_prices(load_fixture(), "TEST")
    for col in ("open_raw", "close_raw", "close_adj", "div_cash_usd", "split_factor"):
        assert df[col].dtype == "float64", col
    assert df["volume_raw"].dtype == "int64"


def test_parse_prices_keeps_dividend_and_split():
    df = parse_prices(load_fixture(), "TEST")
    assert df["div_cash_usd"].tolist() == [0.0, 3.29, 0.0, 0.0]
    assert df["split_factor"].tolist() == [1.0, 1.0, 1.0, 7.0]


def test_parse_prices_keeps_unknown_extra_fields():
    records = load_fixture()
    for r in records:
        r["newField"] = 1
    df = parse_prices(records, "TEST")
    assert "newField" in df.columns


def test_parse_prices_time_of_day_fails_loudly():
    records = load_fixture()
    records[0]["date"] = "2014-06-04T14:30:00.000Z"
    with pytest.raises(TiingoError, match="time of day"):
        parse_prices(records, "TEST")


def test_parse_prices_missing_field_fails_loudly():
    records = load_fixture()
    for r in records:
        del r["adjClose"]
    with pytest.raises(TiingoError, match="adjClose"):
        parse_prices(records, "TEST")


def test_parse_prices_empty_response_fails_loudly():
    with pytest.raises(TiingoError, match="no price rows"):
        parse_prices([], "TEST")


def test_key_is_sent_in_header_not_url():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=load_fixture())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    df = fetch_daily_prices("AAPL", date(2014, 6, 4), date(2014, 6, 9), FAKE_KEY, client=client)
    assert len(df) == 4
    request = seen[0]
    assert request.headers["Authorization"] == f"Token {FAKE_KEY}"
    assert FAKE_KEY not in str(request.url)
    assert str(request.url) == prices_endpoint("AAPL", date(2014, 6, 4), date(2014, 6, 9))


def test_429_is_retried_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429)
        return httpx.Response(200, json=load_fixture())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    df = fetch_daily_prices(
        "AAPL", date(2014, 6, 4), date(2014, 6, 9), FAKE_KEY, client=client, sleep=no_sleep
    )
    assert calls["n"] == 3
    assert len(df) == 4


def test_429_every_time_gives_clear_error_without_key():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(TiingoError, match="after 4 attempts.*HTTP 429") as excinfo:
        fetch_daily_prices(
            "AAPL", date(2014, 6, 4), date(2014, 6, 9), FAKE_KEY, client=client, sleep=no_sleep
        )
    assert calls["n"] == 4
    assert FAKE_KEY not in str(excinfo.value)


def test_network_error_is_retried_then_fails_clearly():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(TiingoError, match="network error"):
        fetch_daily_prices(
            "AAPL", date(2014, 6, 4), date(2014, 6, 9), FAKE_KEY, client=client, sleep=no_sleep
        )


def test_401_is_not_retried():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(TiingoError, match="HTTP 401"):
        fetch_daily_prices(
            "AAPL", date(2014, 6, 4), date(2014, 6, 9), FAKE_KEY, client=client, sleep=no_sleep
        )
    assert calls["n"] == 1


def test_empty_key_fails_before_any_request():
    with pytest.raises(TiingoError, match="TIINGO_API_KEY"):
        fetch_daily_prices("AAPL", date(2014, 6, 4), date(2014, 6, 9), "")


def test_fetch_meta_uses_header_and_returns_dict():
    meta = {"ticker": "aapl", "name": "Apple Inc", "exchangeCode": "NASDAQ"}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Token {FAKE_KEY}"
        assert FAKE_KEY not in str(request.url)
        return httpx.Response(200, json=meta)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert fetch_meta("AAPL", FAKE_KEY, client=client) == meta
