"""Tests for quant_research.data.validation — tiny made-up tables, no internet."""

from datetime import date

import pandas as pd
import pytest

from quant_research.data.validation import (
    Severity,
    check_adjustment_ratio,
    check_big_moves,
    check_calendar,
    check_dividends,
    check_missing_values,
    check_ohlc,
    check_order_and_duplicates,
    check_positive,
    check_splits,
    nearest_simple_ratio,
    nyse_sessions,
    validate_prices,
)

DATES = [date(2014, 6, 2), date(2014, 6, 3), date(2014, 6, 4), date(2014, 6, 5), date(2014, 6, 6)]


def make_df(n: int = 5) -> pd.DataFrame:
    """Clean table: price 10 (raw), adjusted = raw × 0.5, no events."""
    return pd.DataFrame(
        {
            "date": DATES[:n],
            "open_raw": [10.0] * n,
            "high_raw": [11.0] * n,
            "low_raw": [9.0] * n,
            "close_raw": [10.0] * n,
            "volume_raw": [100] * n,
            "open_adj": [5.0] * n,
            "high_adj": [5.5] * n,
            "low_adj": [4.5] * n,
            "close_adj": [5.0] * n,
            "volume_adj": [200.0] * n,
            "div_cash_usd": [0.0] * n,
            "split_factor": [1.0] * n,
        }
    )


def severities(issues, check=None):
    return [i.severity for i in issues if check is None or i.check == check]


# 1. calendar
def test_calendar_pass():
    assert check_calendar(make_df(), "T", DATES) == []


def test_calendar_missing_day_is_error():
    issues = check_calendar(make_df().drop(index=2), "T", DATES)
    assert [(i.date, i.severity) for i in issues] == [(date(2014, 6, 4), Severity.ERROR)]


def test_calendar_extra_day_is_error():
    issues = check_calendar(make_df(), "T", DATES[:4])
    assert [(i.date, i.severity) for i in issues] == [(date(2014, 6, 6), Severity.ERROR)]


def test_nyse_sessions_skip_weekend_and_holiday():
    # 2014-07-04 (Fri) Independence Day; 5-6 July weekend.
    assert nyse_sessions(date(2014, 7, 3), date(2014, 7, 7)) == [date(2014, 7, 3), date(2014, 7, 7)]


def test_nyse_sessions_can_start_on_a_holiday():
    # 2010-01-01 was New Year's Day; first session 2010-01-04.
    assert nyse_sessions(date(2010, 1, 1), date(2010, 1, 5)) == [date(2010, 1, 4), date(2010, 1, 5)]


# 2. duplicates / sorted
def test_order_pass():
    assert check_order_and_duplicates(make_df(), "T") == []


def test_duplicate_date_is_error():
    df = make_df()
    df.loc[3, "date"] = df.loc[2, "date"]
    assert severities(check_order_and_duplicates(df, "T"), "duplicates") == [Severity.ERROR]


def test_unsorted_is_error():
    df = make_df().iloc[[0, 2, 1, 3, 4]].reset_index(drop=True)
    assert severities(check_order_and_duplicates(df, "T"), "sorted") == [Severity.ERROR]


# 3. missing values
def test_missing_pass():
    assert check_missing_values(make_df(), "T") == []


def test_missing_value_is_error():
    df = make_df()
    df.loc[1, "close_raw"] = None
    issues = check_missing_values(df, "T")
    assert [(i.date, i.severity) for i in issues] == [(date(2014, 6, 3), Severity.ERROR)]


def test_missing_column_is_error():
    issues = check_missing_values(make_df().drop(columns="close_adj"), "T")
    assert severities(issues) == [Severity.ERROR]


# 4. positive prices / volume
def test_positive_pass():
    assert check_positive(make_df(), "T") == []


def test_zero_price_is_error():
    df = make_df()
    df.loc[0, "low_raw"] = 0.0
    assert severities(check_positive(df, "T")) == [Severity.ERROR]


def test_negative_volume_is_error():
    df = make_df()
    df.loc[0, "volume_raw"] = -1
    assert severities(check_positive(df, "T")) == [Severity.ERROR]


def test_zero_volume_is_warning():
    df = make_df()
    df.loc[0, "volume_raw"] = 0
    assert severities(check_positive(df, "T")) == [Severity.WARNING]


# 5. OHLC
def test_ohlc_pass():
    assert check_ohlc(make_df(), "T") == []


def test_close_above_high_raw_is_error():
    df = make_df()
    df.loc[2, "close_raw"] = 11.5
    assert severities(check_ohlc(df, "T")) == [Severity.ERROR]


def test_open_below_low_adj_is_error():
    df = make_df()
    df.loc[2, "open_adj"] = 4.0
    assert severities(check_ohlc(df, "T")) == [Severity.ERROR]


# 6. splits
def test_no_split_pass():
    assert check_splits(make_df(), "T") == []


def test_near_whole_split_is_info_only():
    df = make_df()
    df.loc[2, "split_factor"] = 7.000007
    issues = check_splits(df, "T")
    assert severities(issues) == [Severity.INFO]
    assert "7:1" in issues[0].message


def test_odd_split_factor_is_warning():
    df = make_df()
    df.loc[2, "split_factor"] = 7.3
    assert severities(check_splits(df, "T")) == [Severity.INFO, Severity.WARNING]


def test_nearest_simple_ratio():
    assert str(nearest_simple_ratio(1.5)) == "3/2"
    assert str(nearest_simple_ratio(0.25)) == "1/4"
    assert str(nearest_simple_ratio(7.000007)) == "7"
    assert str(nearest_simple_ratio(1 / 35)) == "1/35"


# 7. dividends
def test_dividends_pass_records_info():
    df = make_df()
    df.loc[3, "div_cash_usd"] = 0.5
    issues = check_dividends(df, "T")
    assert severities(issues) == [Severity.INFO]
    assert "1 dividend ex-dates: 2014-06-05" in issues[0].message


def test_negative_dividend_is_error():
    df = make_df()
    df.loc[3, "div_cash_usd"] = -0.5
    assert Severity.ERROR in severities(check_dividends(df, "T"))


# 8. big moves
def test_small_moves_pass():
    assert check_big_moves(make_df(), "T") == []


def test_big_move_without_split_is_warning():
    df = make_df()
    df.loc[3:, "close_raw"] = 13.0  # +30%
    issues = check_big_moves(df, "T")
    assert [(i.date, i.severity) for i in issues] == [(date(2014, 6, 5), Severity.WARNING)]
    assert "+30.0%" in issues[0].message


def test_big_move_with_split_is_info():
    df = make_df()
    df.loc[3:, "close_raw"] = 5.0  # -50% on a 2:1 split day
    df.loc[3, "split_factor"] = 2.0
    assert severities(check_big_moves(df, "T")) == [Severity.INFO]


# 9. adjusted / raw ratio
def test_ratio_constant_pass_and_gap_split():
    df = make_df()
    # Event on 06-05: dividend steps ratio from 0.5 to 0.55 (step ×1.1).
    df.loc[3, "div_cash_usd"] = 0.5
    df.loc[3:, "close_adj"] = 5.5
    issues, stats = check_adjustment_ratio(df, "T", downloaded=date(2014, 6, 6))
    assert Severity.WARNING not in severities(issues)
    assert stats["gap_from_dividends_in_table"] == pytest.approx(1.1)
    assert stats["gap_from_splits_in_table"] == pytest.approx(1.0)
    assert stats["gap_after_table_end"] == pytest.approx(1 / 0.55)


def test_ratio_change_without_event_is_warning():
    df = make_df()
    df.loc[3:, "close_adj"] = 5.5
    issues, _ = check_adjustment_ratio(df, "T")
    warnings = [i for i in issues if i.severity == Severity.WARNING]
    assert [i.date for i in warnings if i.date is not None] == [date(2014, 6, 5)]
    # The unexplained step also means splits × dividends no longer equal the total change.
    assert any("do not multiply" in i.message for i in warnings)


def test_ratio_implies_later_split():
    df = make_df()  # ratio 0.5 everywhere, no dividends in the table
    _issues, stats = check_adjustment_ratio(df, "T", downloaded=date(2015, 6, 6))
    assert "about a 2:1 split" in stats["implied_later_split"]


def test_ratio_no_later_split_when_close_to_one():
    df = make_df()
    df["close_adj"] = 9.9  # ratio 0.99
    _, stats = check_adjustment_ratio(df, "T", downloaded=date(2015, 6, 6))
    assert "no split" in stats["implied_later_split"]


# whole run
def test_validate_prices_clean_table_has_no_errors_or_warnings():
    report = validate_prices(make_df(), "T", DATES[0], DATES[-1], sessions=DATES)
    assert report.count(Severity.ERROR) == 0
    assert report.count(Severity.WARNING) == 0
    assert report.stats["rows"] == 5


def test_validate_prices_reports_errors():
    df = make_df()
    df.loc[1, "open_raw"] = -1.0
    report = validate_prices(df, "T", DATES[0], DATES[-1], sessions=DATES)
    assert report.has_errors
