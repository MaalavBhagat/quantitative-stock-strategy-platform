"""Tests for quant_research.data.crosscheck — made-up tables, no internet, no yfinance needed."""

from datetime import date

import pandas as pd
import pytest

from quant_research.data.crosscheck import (
    compare_closes,
    compare_dividends,
    compare_splits,
    compare_trading_days,
    crosscheck,
    detect_split_basis,
    explain_close_differences,
    merge_sources,
)

DATES = [
    date(2014, 6, 4),
    date(2014, 6, 5),
    date(2014, 6, 6),
    date(2014, 6, 9),
    date(2014, 6, 10),
    date(2014, 6, 11),
]


def tiingo_table() -> pd.DataFrame:
    """Raw prices with a 2:1 split on 06-06 and a $1 dividend on 06-05."""
    return pd.DataFrame(
        {
            "date": DATES,
            "close_raw": [100.0, 100.0, 50.0, 50.0, 50.0, 50.0],
            "div_cash_usd": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            "split_factor": [1.0, 1.0, 2.0, 1.0, 1.0, 1.0],
        }
    )


def yahoo_table(later_split: float = 3.0) -> pd.DataFrame:
    """Yahoo-style: everything split-adjusted for the 2:1 split AND a later split."""
    t = tiingo_table()
    in_table = [2.0, 2.0, 1.0, 1.0, 1.0, 1.0]
    return pd.DataFrame(
        {
            "date": DATES,
            "yahoo_close": [c / (s * later_split) for c, s in zip(t["close_raw"], in_table)],
            "yahoo_dividends": [0.0, 1.0 / (2.0 * later_split), 0.0, 0.0, 0.0, 0.0],
            "yahoo_splits": [0.0, 0.0, 2.0, 0.0, 0.0, 0.0],
        }
    )


def test_trading_days_match():
    result = compare_trading_days(tiingo_table(), yahoo_table())
    assert result["only_tiingo"] == [] and result["only_yahoo"] == []


def test_trading_days_mismatch_reported():
    result = compare_trading_days(tiingo_table(), yahoo_table().iloc[:5])
    assert result["only_tiingo"] == [date(2014, 6, 11)]


def test_detect_basis_finds_in_table_and_later_split():
    factor, info = detect_split_basis(merge_sources(tiingo_table(), yahoo_table()))
    assert info["yahoo_close_is_split_adjusted"] is True
    assert info["later_split_ratio_implied"] == "3:1"
    assert factor.tolist() == pytest.approx([1 / 6, 1 / 6, 1 / 3, 1 / 3, 1 / 3, 1 / 3])


def test_detect_basis_unadjusted_source():
    yahoo = yahoo_table(later_split=1.0)
    yahoo["yahoo_close"] = tiingo_table()["close_raw"]
    yahoo["yahoo_splits"] = 0.0
    tiingo = tiingo_table()
    tiingo["split_factor"] = 1.0
    factor, info = detect_split_basis(merge_sources(tiingo, yahoo))
    assert info["yahoo_close_is_split_adjusted"] is False
    assert factor.tolist() == [1.0] * 6


def test_detect_basis_unexplained_ratio_fails_loudly():
    yahoo = yahoo_table()
    yahoo.loc[:1, "yahoo_close"] *= 1.3  # pre-split segment off by 30%
    with pytest.raises(ValueError, match="not explained"):
        detect_split_basis(merge_sources(tiingo_table(), yahoo))


def test_closes_identical_after_basis_conversion():
    merged = merge_sources(tiingo_table(), yahoo_table())
    factor, _ = detect_split_basis(merged)
    result = compare_closes(merged, factor)
    assert result["max_abs_pct"] == pytest.approx(0.0, abs=1e-12)
    assert result["count_over_threshold"] == 0


def test_close_difference_is_reported_not_hidden():
    yahoo = yahoo_table()
    yahoo.loc[3, "yahoo_close"] *= 1.01  # +1% on one day
    merged = merge_sources(tiingo_table(), yahoo)
    factor, _ = detect_split_basis(merged)
    result = compare_closes(merged, factor)
    assert result["count_over_threshold"] == 1
    assert result["worst"][0][0] == date(2014, 6, 9)
    assert result["worst"][0][1] == pytest.approx(0.01)


def test_dividends_match_after_basis_conversion():
    merged = merge_sources(tiingo_table(), yahoo_table())
    factor, _ = detect_split_basis(merged)
    result = compare_dividends(merged, factor)
    assert result["tiingo_count"] == result["yahoo_count"] == 1
    assert result["max_abs_pct"] == pytest.approx(0.0, abs=1e-12)


def test_dividend_only_in_one_source_reported():
    yahoo = yahoo_table()
    yahoo.loc[1, "yahoo_dividends"] = 0.0
    merged = merge_sources(tiingo_table(), yahoo)
    factor, _ = detect_split_basis(merged)
    assert compare_dividends(merged, factor)["only_tiingo"] == [date(2014, 6, 5)]


def test_splits_same_and_different():
    merged = merge_sources(tiingo_table(), yahoo_table())
    assert compare_splits(merged)["same_dates_and_ratios"] is True
    other = yahoo_table()
    other.loc[2, "yahoo_splits"] = 3.0
    assert compare_splits(merge_sources(tiingo_table(), other))["same_dates_and_ratios"] is False


def test_crosscheck_runs_all_parts():
    result = crosscheck(tiingo_table(), yahoo_table())
    assert set(result) == {
        "trading_days",
        "basis",
        "closes",
        "close_differences_explained",
        "dividends",
        "splits",
    }


def test_difference_equal_to_next_day_dividend_is_explained():
    tiingo = tiingo_table()
    tiingo.loc[4, "div_cash_usd"] = 1.0  # ex-date 06-10 (inside the long post-split stretch)
    yahoo = yahoo_table()
    # 06-09 is the day before that ex-date: Yahoo close (raw basis) = Tiingo close + $1.
    yahoo.loc[3, "yahoo_close"] = (50.0 + 1.0) / 3.0
    merged = merge_sources(tiingo, yahoo)
    factor, _ = detect_split_basis(merged)
    notes = explain_close_differences(merged, factor)
    assert [(n["date"], n["note"].startswith("difference equals")) for n in notes] == [
        (date(2014, 6, 9), True)
    ]


def test_other_difference_stays_unexplained():
    yahoo = yahoo_table()
    yahoo.loc[3, "yahoo_close"] *= 1.01
    merged = merge_sources(tiingo_table(), yahoo)
    factor, _ = detect_split_basis(merged)
    assert explain_close_differences(merged, factor)[0]["note"] == "unexplained"
