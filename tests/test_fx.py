"""AUD/USD exchange-rate series — tiny made-up rates (no real RBA data in tests)."""

from datetime import date
from decimal import Decimal

import pytest

from quant_research.data.fx import FxDataError, build_series, load_usd_per_aud

D = Decimal
ROWS = [
    (date(2014, 6, 2), D("0.9200")),  # Mon
    (date(2014, 6, 3), D("0.9250")),
    (date(2014, 6, 4), D("0.9180")),
    (date(2014, 6, 6), D("0.9300")),  # Thu 5th missing (e.g. Sydney holiday)
    (date(2014, 6, 13), D("0.9400")),  # next row a week later
]


def test_rate_on_a_day_with_a_rate():
    assert build_series(ROWS).on(date(2014, 6, 3)) == D("0.9250")


def test_missing_day_uses_latest_earlier_rate():
    # 5 June has no rate → latest dated ≤ 5 June is 4 June (0.9180)
    assert build_series(ROWS).on(date(2014, 6, 5)) == D("0.9180")


def test_stale_rate_more_than_5_days_is_an_error():
    s = build_series(ROWS)
    # 11 June: latest is 6 June = 5 days old → allowed ; 12 June: 6 days old → error
    assert s.on(date(2014, 6, 11)) == D("0.9300")
    with pytest.raises(FxDataError, match="more than 5 days old"):
        s.on(date(2014, 6, 12))


def test_before_first_rate_is_an_error():
    with pytest.raises(FxDataError, match="no AUD/USD rate"):
        build_series(ROWS).on(date(2014, 6, 1))


def test_validation_errors():
    with pytest.raises(FxDataError, match="not sorted"):
        build_series([ROWS[1], ROWS[0]])
    with pytest.raises(FxDataError, match="duplicate"):
        build_series([ROWS[0], ROWS[0]])
    with pytest.raises(FxDataError, match="plausible"):
        build_series([(date(2014, 6, 2), D("1.50"))])
    with pytest.raises(FxDataError, match="plausible"):
        build_series([(date(2014, 6, 2), D("0.30"))])
    with pytest.raises(FxDataError, match="no exchange-rate rows"):
        build_series([])


def test_row_gaps_are_allowed_only_lookups_are_limited():
    # a 7-day gap between rows is accepted at build time (Sydney holidays) …
    s = build_series(ROWS)
    # … but a lookup inside it more than 5 days after the last rate fails (tested above)
    assert len(s.dates) == 5


def test_load_without_files_or_meta_is_a_clear_error(tmp_path):
    with pytest.raises(FxDataError, match="download_rba_fx.py"):
        load_usd_per_aud(tmp_path)
    (tmp_path / "2010-2013.xls").write_bytes(b"not used")
    with pytest.raises(FxDataError, match="meta.json"):
        load_usd_per_aud(tmp_path)


def test_trimmed_csv_loads_and_refuses_post_2020_rows(tmp_path):
    import json

    from quant_research.data.fx import parse_trimmed_csv

    good = tmp_path / "2018-2020_from_2018-2022.csv"
    good.write_text("date,usd_per_aud\n2020-12-30,0.7650\n2020-12-31,0.7700\n")
    assert parse_trimmed_csv(good) == [
        (date(2020, 12, 30), D("0.7650")),
        (date(2020, 12, 31), D("0.7700")),
    ]
    (tmp_path / "2018-2020_from_2018-2022.meta.json").write_text(json.dumps({"note": "made up"}))
    assert load_usd_per_aud(tmp_path).on(date(2020, 12, 31)) == D(
        "0.7700"
    )  # lookup only; no 2021 row exists
    bad = tmp_path / "bad.csv"
    bad.write_text("date,usd_per_aud\n2020-12-31,0.7700\n2021-01-04,0.7800\n")
    with pytest.raises(FxDataError, match="after 2020-12-31"):
        parse_trimmed_csv(bad)


def test_final_test_extracts_follow_their_own_trim_date(tmp_path):
    import json

    from quant_research.data.fx import parse_trimmed_csv

    ok = tmp_path / "2023-2025_from_2023-current.csv"
    ok.write_text("date,usd_per_aud\n2025-12-30,0.6650\n2025-12-31,0.6700\n")
    ok.with_suffix(".meta.json").write_text(json.dumps({"trimmed_to": "2025-12-31"}))
    assert parse_trimmed_csv(ok)[-1] == (date(2025, 12, 31), D("0.6700"))
    late = tmp_path / "late.csv"
    late.write_text("date,usd_per_aud\n2025-12-31,0.6700\n2026-01-02,0.6710\n")
    late.with_suffix(".meta.json").write_text(json.dumps({"trimmed_to": "2025-12-31"}))
    with pytest.raises(FxDataError, match="after 2025-12-31"):
        parse_trimmed_csv(late)
    beyond = tmp_path / "beyond.csv"
    beyond.write_text("date,usd_per_aud\n2026-01-02,0.6710\n")
    beyond.with_suffix(".meta.json").write_text(json.dumps({"trimmed_to": "2026-06-30"}))
    with pytest.raises(FxDataError, match="is after 2025-12-31"):
        parse_trimmed_csv(beyond)
