"""Tests for quant_research.data.loader — temporary folders only, no internet."""

import json
import logging
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from quant_research.data.loader import DataLoadError, Provenance, load_prices
from quant_research.data.storage import save_raw_prices
from quant_research.data.tiingo import parse_prices, prices_endpoint

FIXTURE = Path(__file__).parent / "fixtures" / "tiingo_prices_sample.json"
# Fixture dates 2014-06-04 (Wed) … 2014-06-09 (Mon) are real NYSE sessions.
START, END = date(2014, 6, 4), date(2014, 6, 9)


def write_fixture(data_dir: Path, records: list[dict] | None = None) -> Path:
    if records is None:
        records = json.loads(FIXTURE.read_text())
    csv_path, _ = save_raw_prices(
        parse_prices(records, "TEST"),
        "TEST",
        START,
        END,
        endpoint=prices_endpoint("TEST", START, END),
        out_dir=data_dir,
        repo_dir=data_dir,
    )
    return csv_path


def test_loads_fixture_with_raw_columns_only_by_default(tmp_path):
    write_fixture(tmp_path)
    df = load_prices("TEST", START, END, data_dir=tmp_path)
    assert len(df) == 4
    assert df["date"].tolist()[0] == date(2014, 6, 4)
    assert "close_raw" in df.columns and "split_factor" in df.columns
    assert not any(c.endswith("_adj") for c in df.columns)


def test_include_adjusted_adds_adj_columns(tmp_path):
    write_fixture(tmp_path)
    df = load_prices("TEST", START, END, data_dir=tmp_path, include_adjusted=True)
    assert {"open_adj", "high_adj", "low_adj", "close_adj", "volume_adj"} <= set(df.columns)


def test_provenance_returned(tmp_path):
    write_fixture(tmp_path)
    df = load_prices("TEST", START, END, data_dir=tmp_path)
    prov = df.attrs["provenance"]
    assert isinstance(prov, Provenance)
    assert prov.file_name == "TEST_2014-06-04_2014-06-09.csv"
    assert prov.source == "Tiingo"
    assert prov.downloaded_at_utc.endswith("+00:00")
    assert prov.rows_returned == 4


def test_slice_inside_file(tmp_path):
    write_fixture(tmp_path)
    df = load_prices("TEST", date(2014, 6, 5), date(2014, 6, 6), data_dir=tmp_path)
    assert df["date"].tolist() == [date(2014, 6, 5), date(2014, 6, 6)]


def test_missing_file_gives_clear_error(tmp_path):
    with pytest.raises(DataLoadError, match="download_initial_dataset.py"):
        load_prices("TEST", START, END, data_dir=tmp_path)


def test_missing_meta_gives_clear_error(tmp_path):
    csv_path = write_fixture(tmp_path)
    csv_path.with_suffix(".meta.json").unlink()
    with pytest.raises(DataLoadError, match="meta.json is missing"):
        load_prices("TEST", START, END, data_dir=tmp_path)


def test_missing_trading_day_raises(tmp_path):
    records = json.loads(FIXTURE.read_text())
    del records[2]  # 2014-06-06 (a real NYSE session)
    write_fixture(tmp_path, records)
    with pytest.raises(DataLoadError, match="calendar"):
        load_prices("TEST", START, END, data_dir=tmp_path)


def test_missing_value_raises_and_is_not_filled(tmp_path):
    csv_path = write_fixture(tmp_path)
    df = pd.read_csv(csv_path)
    df.loc[1, "close_raw"] = None
    df.to_csv(csv_path, index=False)
    with pytest.raises(DataLoadError, match="close_raw is missing"):
        load_prices("TEST", START, END, data_dir=tmp_path)


def test_warning_only_data_loads(tmp_path, caplog):
    records = json.loads(FIXTURE.read_text())
    records[0]["volume"] = 0  # zero volume = WARNING, not ERROR
    write_fixture(tmp_path, records)
    with caplog.at_level(logging.WARNING):
        df = load_prices("TEST", START, END, data_dir=tmp_path)
    assert len(df) == 4
    assert any("zero_volume" in r.getMessage() for r in caplog.records)


def test_two_covering_files_is_an_error(tmp_path):
    write_fixture(tmp_path)
    save_raw_prices(
        parse_prices(json.loads(FIXTURE.read_text()), "TEST"),
        "TEST",
        date(2014, 6, 1),
        date(2014, 6, 30),
        endpoint="x",
        out_dir=tmp_path,
        repo_dir=tmp_path,
    )
    with pytest.raises(DataLoadError, match="csv_path="):
        load_prices("TEST", START, END, data_dir=tmp_path)


# ---------- warm-up + main join ----------
def _records(days: list[date], price: float = 100.0) -> list[dict]:
    return [
        {
            "date": f"{d.isoformat()}T00:00:00.000Z",
            "open": price, "high": price + 1, "low": price - 1, "close": price, "volume": 1000,
            "adjOpen": price, "adjHigh": price + 1, "adjLow": price - 1, "adjClose": price, "adjVolume": 1000,
            "divCash": 0.0, "splitFactor": 1.0,
        }
        for d in days
    ]  # fmt: skip


def _save(data_dir: Path, days: list[date], start: date, end: date) -> None:
    save_raw_prices(
        parse_prices(_records(days), "TEST"), "TEST", start, end,
        endpoint="x", out_dir=data_dir, repo_dir=data_dir,
    )  # fmt: skip


def test_warmup_and_main_join_into_one_table(tmp_path):
    from quant_research.data.loader import load_prices_with_warmup

    warm = [date(2014, 6, d) for d in (2, 3, 4, 5, 6)]  # Mon–Fri, real NYSE sessions
    main = [date(2014, 6, d) for d in (9, 10, 11, 12, 13)]
    _save(tmp_path, warm, date(2014, 6, 1), date(2014, 6, 6))
    _save(tmp_path, main, date(2014, 6, 9), date(2014, 6, 13))
    df = load_prices_with_warmup(
        "TEST", date(2014, 6, 1), date(2014, 6, 9), date(2014, 6, 13), data_dir=tmp_path
    )
    assert df["date"].tolist() == warm + main
    assert df.attrs["provenance"].file_name.startswith("TEST_2014-06-09")
    assert df.attrs["warmup_provenance"].file_name.startswith("TEST_2014-06-01")


def test_warmup_gap_at_the_join_is_an_error(tmp_path):
    from quant_research.data.loader import load_prices_with_warmup

    warm = [date(2014, 6, d) for d in (2, 3, 4, 5)]  # 6 June (a trading day) missing
    _save(tmp_path, warm, date(2014, 6, 1), date(2014, 6, 6))
    _save(tmp_path, [date(2014, 6, d) for d in (9, 10)], date(2014, 6, 9), date(2014, 6, 10))
    with pytest.raises(DataLoadError, match="calendar"):
        load_prices_with_warmup(
            "TEST", date(2014, 6, 1), date(2014, 6, 9), date(2014, 6, 10), data_dir=tmp_path
        )


def test_warmup_must_be_before_start(tmp_path):
    from quant_research.data.loader import load_prices_with_warmup

    with pytest.raises(ValueError, match="before start"):
        load_prices_with_warmup(
            "TEST", date(2014, 6, 9), date(2014, 6, 9), date(2014, 6, 10), data_dir=tmp_path
        )
