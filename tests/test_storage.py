"""Tests for quant_research.data.storage — writes to a temporary folder only."""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from quant_research import __version__
from quant_research.data.storage import save_raw_prices
from quant_research.data.tiingo import parse_prices, prices_endpoint

FIXTURE = Path(__file__).parent / "fixtures" / "tiingo_prices_sample.json"
START, END = date(2014, 6, 4), date(2014, 6, 9)


def sample_df() -> pd.DataFrame:
    return parse_prices(json.loads(FIXTURE.read_text()), "TEST")


def save(tmp_path: Path, overwrite: bool = False) -> tuple[Path, Path]:
    return save_raw_prices(
        sample_df(),
        "test",
        START,
        END,
        endpoint=prices_endpoint("TEST", START, END),
        out_dir=tmp_path / "raw" / "tiingo",
        repo_dir=tmp_path,
        overwrite=overwrite,
    )


def test_writes_csv_and_meta_with_expected_names(tmp_path):
    csv_path, meta_path = save(tmp_path)
    assert csv_path.name == "TEST_2014-06-04_2014-06-09.csv"
    assert meta_path.name == "TEST_2014-06-04_2014-06-09.meta.json"
    saved = pd.read_csv(csv_path)
    assert len(saved) == 4
    assert saved["date"].tolist() == ["2014-06-04", "2014-06-05", "2014-06-06", "2014-06-09"]
    assert saved["split_factor"].tolist() == [1.0, 1.0, 1.0, 7.0]


def test_meta_contents(tmp_path):
    _, meta_path = save(tmp_path)
    meta = json.loads(meta_path.read_text())
    assert meta["source"] == "Tiingo"
    assert meta["tickers"] == ["TEST"]
    assert meta["row_count"] == 4
    assert meta["first_date"] == "2014-06-04"
    assert meta["last_date"] == "2014-06-09"
    assert meta["requested_start"] == "2014-06-04"
    assert meta["requested_end"] == "2014-06-09"
    assert meta["raw_date_example"] == "2014-06-04T00:00:00.000Z"
    assert meta["package_version"] == __version__
    assert meta["downloaded_at_utc"].endswith("+00:00")
    assert "git_commit" in meta and "git_dirty" in meta


def test_meta_contains_no_api_key(tmp_path):
    _, meta_path = save(tmp_path)
    text = meta_path.read_text().lower()
    assert "token" not in text
    assert "authorization" not in text
    assert "api_key" not in text and "apikey" not in text


def test_refuses_to_overwrite(tmp_path):
    save(tmp_path)
    with pytest.raises(FileExistsError, match="overwrite=True"):
        save(tmp_path)


def test_overwrite_true_replaces(tmp_path):
    save(tmp_path)
    csv_path, _ = save(tmp_path, overwrite=True)
    assert csv_path.exists()


def test_refuses_empty_table(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        save_raw_prices(
            sample_df().iloc[0:0],
            "TEST",
            START,
            END,
            endpoint="x",
            out_dir=tmp_path,
            repo_dir=tmp_path,
        )
