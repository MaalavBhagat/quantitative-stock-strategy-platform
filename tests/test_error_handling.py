"""Phase 10, Step 10.2 — every failure gives a CLEAR message (what failed, where, what to do) and never a silent
wrong result. All HTTP is mocked (no internet); files live in tmp_path."""

import json
from datetime import date

import httpx
import pytest

from quant_research.backtesting.run import (
    FinalTestLockedError,
    check_final_test_lock,
    load_config,
    parse_config,
)
from quant_research.data.fx import FxDataError, parse_rba_xls
from quant_research.data.loader import DataLoadError, load_prices
from quant_research.data.sec import SecError, Throttle, get_json
from quant_research.data.tiingo import TiingoError, fetch_daily_prices
from quant_research.data.validation import load_raw_csv

UA = "Research Bot bot@example.com"
GOOD_ROW = {"date": "2020-01-02T00:00:00.000Z", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1,
            "adjOpen": 1, "adjHigh": 1, "adjLow": 1, "adjClose": 1, "adjVolume": 1, "divCash": 0, "splitFactor": 1}  # fmt: skip


def client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def tiingo(handler):
    return fetch_daily_prices("AAPL", date(2020, 1, 2), date(2020, 1, 3), "FAKEKEY", client=client(handler),
                              sleep=lambda s: None)  # fmt: skip


def sec(handler):
    return get_json("https://data.sec.gov/x.json", UA, Throttle(sleep=lambda s: None), client=client(handler),
                    backoff_seconds=0)  # fmt: skip


def raise_(exc):
    def handler(request):
        raise exc

    return handler


# ---------- network / HTTP (Tiingo and SEC) ----------
NETWORK = [
    ("timeout", raise_(httpx.ReadTimeout("slow")), "after 4 attempts (network error: ReadTimeout)"),
    (
        "connection",
        raise_(httpx.ConnectError("down")),
        "after 4 attempts (network error: ConnectError)",
    ),
    ("429", lambda r: httpx.Response(429), "after 4 attempts (HTTP 429)"),
    ("500", lambda r: httpx.Response(500), "after 4 attempts (HTTP 500)"),
    ("401", lambda r: httpx.Response(401), "HTTP 401"),
    ("not json", lambda r: httpx.Response(200, text="<html>maintenance</html>"), "not valid JSON"),
    ("truncated json", lambda r: httpx.Response(200, text='[{"date": "2020'), "not valid JSON"),
]


@pytest.mark.parametrize(("case", "handler", "message"), NETWORK, ids=[c[0] for c in NETWORK])
def test_tiingo_failures_are_clear_and_never_leak_the_key(case, handler, message):
    with pytest.raises(TiingoError, match=message.replace("(", r"\(").replace(")", r"\)")) as err:
        tiingo(handler)
    assert "FAKEKEY" not in str(err.value)


@pytest.mark.parametrize(("case", "handler", "message"), NETWORK, ids=[c[0] for c in NETWORK])
def test_sec_failures_are_clear(case, handler, message):
    with pytest.raises(SecError, match=message.replace("(", r"\(").replace(")", r"\)")):
        sec(handler)


def test_tiingo_malformed_payloads():
    with pytest.raises(TiingoError, match="no price rows"):
        tiingo(lambda r: httpx.Response(200, json={"detail": "Error: ticker not found"}))
    with pytest.raises(TiingoError, match="missing fields"):
        tiingo(
            lambda r: httpx.Response(
                200, json=[{k: v for k, v in GOOD_ROW.items() if k != "close"}]
            )
        )
    with pytest.raises(TiingoError, match="column open_raw has a non-numeric value 'abc'"):
        tiingo(lambda r: httpx.Response(200, json=[{**GOOD_ROW, "open": "abc"}]))


def test_missing_secrets_fail_before_any_request():
    calls = []
    with pytest.raises(TiingoError, match="TIINGO_API_KEY is empty"):
        fetch_daily_prices(
            "AAPL", date(2020, 1, 2), date(2020, 1, 3), "", client=client(calls.append)
        )
    with pytest.raises(SecError, match="SEC_USER_AGENT is empty or has no email"):
        get_json("https://data.sec.gov/x.json", "", Throttle(), client=client(calls.append))
    assert calls == []


# ---------- files on disk ----------
def test_bad_csv_files_name_the_file(tmp_path):
    (tmp_path / "empty.csv").write_text("")
    with pytest.raises(ValueError, match="empty.csv is empty"):
        load_raw_csv(tmp_path / "empty.csv")
    (tmp_path / "nodate.csv").write_text("day,close_raw\n2020-01-02,1\n")
    with pytest.raises(ValueError, match="no 'date' column"):
        load_raw_csv(tmp_path / "nodate.csv")
    (tmp_path / "baddate.csv").write_text("date,close_raw\n02/01/2020,1\n")
    with pytest.raises(ValueError, match="not in YYYY-MM-DD"):
        load_raw_csv(tmp_path / "baddate.csv")


def test_truncated_price_file_is_refused_by_the_loader(tmp_path):
    # a file cut off mid-row: columns missing → validation ERROR → DataLoadError (never returned half-filled)
    (tmp_path / "AAA_2020-01-02_2020-01-03.csv").write_text(
        "date,open_raw,high_raw\n2020-01-02,1.0,"
    )
    (tmp_path / "AAA_2020-01-02_2020-01-03.meta.json").write_text(
        json.dumps(
            {"tickers": ["AAA"], "downloaded_at_utc": "2020-02-01T00:00:00+00:00", "source": "test"}
        )
    )
    with pytest.raises(DataLoadError, match="failed validation"):
        load_prices("AAA", date(2020, 1, 2), date(2020, 1, 3), data_dir=tmp_path)


def test_rba_file_with_unexpected_layout(tmp_path):
    (tmp_path / "2010-2013.xls").write_text("not an excel file")
    with pytest.raises(FxDataError, match="not a readable RBA .xls"):
        parse_rba_xls(tmp_path / "2010-2013.xls")


# ---------- run configs ----------
BASE = {
    "run_name": "x", "strategy": "s0_buy_and_hold", "ticker": "AAPL", "start": date(2017, 1, 1),
    "end": date(2020, 12, 31), "broker": "stake", "spread_level": "normal", "share_mode": "fractional",
    "initial_aud": "10000",
}  # fmt: skip
BAD_CONFIGS = [
    ("float money", {"initial_aud": 10000.5}, TypeError, "write it in quotes"),
    ("unknown key", {"colour": "blue"}, ValueError, "unknown config keys"),
    ("reversed dates", {"start": date(2020, 1, 2), "end": date(2019, 1, 2)}, ValueError, "before start"),
    ("date as text", {"start": "2017-01-01"}, TypeError, "must be a date"),
    ("off grid", {"strategy": "s1_profit_target", "profit_target_x": "0.07", "rebuy_dip_y": "0.02"}, ValueError,
     "outside the grid"),
    ("missing X", {"strategy": "s2_pullback"}, ValueError, "needs profit_target_x"),
    ("unknown strategy", {"strategy": "s9_magic"}, ValueError, "strategy must be one of"),
    ("unknown broker", {"broker": "robinhood"}, ValueError, "broker must be one of"),
    ("unknown spread", {"spread_level": "huge"}, ValueError, "spread_level must be one of"),
    ("unknown share mode", {"share_mode": "half"}, ValueError, "share_mode must be one of"),
    ("negative money", {"initial_aud": "-5"}, ValueError, "must be more than 0"),
    ("money as words", {"initial_aud": "lots"}, ValueError, "not a number"),
    ("unlock not a bool", {"final_test_unlocked": "yes"}, TypeError, "true or false"),
]  # fmt: skip


@pytest.mark.parametrize(
    ("case", "change", "error", "message"), BAD_CONFIGS, ids=[c[0] for c in BAD_CONFIGS]
)
def test_invalid_configs_are_refused_clearly(case, change, error, message):
    with pytest.raises(error, match=message):
        parse_config({**BASE, **change})


def test_2021_plus_without_unlock_is_refused():
    with pytest.raises(FinalTestLockedError, match="locked"):
        check_final_test_lock(parse_config({**BASE, "end": date(2021, 6, 30)}))


def test_bad_yaml_files_name_the_file(tmp_path):
    (tmp_path / "broken.yaml").write_text("run_name: x\nstrategy: [unclosed\n")
    with pytest.raises(ValueError, match="broken.yaml is not valid YAML"):
        load_config(tmp_path / "broken.yaml")
    (tmp_path / "list.yaml").write_text("- a\n- b\n")
    with pytest.raises(TypeError, match="list.yaml must be a list of 'key: value' settings"):
        load_config(tmp_path / "list.yaml")
