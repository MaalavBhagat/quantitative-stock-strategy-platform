"""Dividends (3.5) and splits (3.6) — hand calculations above each assert, exact Decimal equality."""

from datetime import date
from decimal import Decimal

import pytest

from quant_research.portfolio.ledger import LedgerError, Portfolio

D = Decimal
DAY1, EX, DAY3 = date(2014, 6, 2), date(2014, 6, 3), date(2014, 6, 4)


def holding(shares: int | str, price: str = "100", mode: str = "whole") -> Portfolio:
    p = Portfolio("10000.00", share_mode=mode)  # type: ignore[arg-type]
    p.buy(DAY1, "AAPL", shares, price, "0")
    return p


# ---------- dividends ----------
def test_dividend_10_shares_withholding_15pct():
    p = holding(10)  # cash 10,000 − 1,000 = 9,000.00, basis 1,000.00
    e = p.apply_dividend(EX, "AAPL", "2.65")
    # gross = 10 × 2.65 = 26.50 ; withholding = 15% × 26.50 = 3.975 → round UP → 3.98
    # net = 26.50 − 3.98 = 22.52 → cash 9,000.00 + 22.52 = 9,022.52
    assert (e.gross_usd, e.withholding_usd) == (D("26.50"), D("3.98"))
    assert p.cash_usd == D("9022.52")
    assert (p.dividends_gross_usd, p.withholding_usd, p.dividends_net_usd) == (
        D("26.50"),
        D("3.98"),
        D("22.52"),
    )
    # dividends never change the cost basis: still 1,000.00
    assert p.position("AAPL").cost_basis_usd == D("1000.00")
    assert e.type == "DIVIDEND" and e.cash_after_usd - e.cash_before_usd == D("22.52")


def test_dividend_on_fractional_holding():
    p = holding("1.234567", mode="fractional")  # cost 123.4567 → 123.46
    p.apply_dividend(EX, "AAPL", "0.57")
    # gross exact = 1.234567 × 0.57 = 0.70370319 → round DOWN → 0.70
    # withholding = 15% × 0.70370319 = 0.1055554785 → round UP → 0.11 ; net = 0.70 − 0.11 = 0.59
    assert (p.dividends_gross_usd, p.withholding_usd, p.dividends_net_usd) == (
        D("0.70"),
        D("0.11"),
        D("0.59"),
    )


def test_buy_on_ex_date_is_not_entitled():
    p = Portfolio("10000.00", share_mode="whole")
    # nothing held at the previous close → no dividend, no entry
    assert p.apply_dividend(EX, "AAPL", "2.65") is None
    p.buy(EX, "AAPL", 10, "100", "0")  # buying on the ex-date afterwards is fine
    assert p.dividends_net_usd == D(0)
    assert [e.type for e in p.entries] == ["BUY"]


def test_dividend_after_a_trade_on_ex_date_is_refused():
    p = holding(10)
    p.buy(EX, "AAPL", 1, "100", "0")
    before = (p.cash_usd, p.entries)
    with pytest.raises(LedgerError, match="BEFORE trades"):
        p.apply_dividend(EX, "AAPL", "2.65")
    assert (p.cash_usd, p.entries) == before


def test_sell_on_ex_date_is_still_entitled():
    p = holding(10)
    p.apply_dividend(EX, "AAPL", "2.65")  # held at previous close → 22.52 (see first test)
    p.sell(EX, "AAPL", 10, "100", "0")
    # cash = 9,000.00 + 22.52 + 1,000.00 = 10,022.52
    assert p.cash_usd == D("10022.52")
    assert p.dividends_net_usd == D("22.52")


def test_same_dividend_twice_is_refused():
    p = holding(10)
    p.apply_dividend(EX, "AAPL", "2.65")
    with pytest.raises(LedgerError, match="already applied"):
        p.apply_dividend(EX, "AAPL", "2.65")
    assert p.dividends_net_usd == D("22.52")


def test_tiny_dividend_under_one_cent_not_credited():
    p = holding("0.1", mode="fractional")  # 0.1 × 100 = 10.00 (exactly the minimum order)
    e = p.apply_dividend(EX, "AAPL", "0.10")
    # gross = 0.1 × 0.10 = 0.01 ; withholding 15% × 0.01 = 0.0015 → UP → 0.01 ; net 0.00 < 0.01
    # → not credited: cash unchanged (10,000 − 10 = 9,990.00), totals stay 0, entry has a note
    assert p.cash_usd == D("9990.00")
    assert p.dividends_net_usd == D(0)
    assert e.note is not None and "not credited" in e.note
    assert e.cash_before_usd == e.cash_after_usd


def test_dividend_bad_inputs():
    p = holding(10)
    with pytest.raises(ValueError):
        p.apply_dividend(EX, "AAPL", "0")
    with pytest.raises(ValueError):
        p.apply_dividend(EX, "AAPL", "1", withholding_rate="1")
    with pytest.raises(TypeError):
        p.apply_dividend(EX, "AAPL", 2.65)


# ---------- splits ----------
def test_aapl_like_7_for_1_split_then_sell():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 10, "600", "3")  # basis 10 × 600 + 3 = 6,003.00 ; cash 3,997.00
    e = p.apply_split(EX, "AAPL", "7.000007")
    # ratio snapped 7.000007 → 7 ; shares 10 × 7 = 70 ; basis unchanged 6,003.00
    # average = 6,003 / 70 = 85.757142857142857… ; cash unchanged
    pos = p.position("AAPL")
    assert (pos.quantity, pos.cost_basis_usd) == (D(70), D("6003.00"))
    assert pos.average_cost_usd == D(6003) / D(70)
    assert str(pos.average_cost_usd).startswith("85.757142857142857")
    assert p.cash_usd == D("3997.00")
    assert (e.type, e.ratio) == ("SPLIT", D(7))
    assert "7.000007" in e.note
    # partial sell 35 @ 90, fee 3: proceeds 3,150.00 − 3.00 = 3,147.00
    # cost of shares sold = 6,003.00 × 35 / 70 = 3,001.50 → P&L = 3,147.00 − 3,001.50 = 145.50
    p.sell(DAY3, "AAPL", 35, "90", "3")
    assert p.realised_pnl_usd == D("145.50")
    # rest 35 @ 90, fee 3: 3,147.00 − remaining basis 3,001.50 = 145.50 → total 291.00
    p.sell(DAY3, "AAPL", 35, "90", "3")
    assert p.realised_pnl_usd == D("291.00")


def test_split_on_ticker_not_held_does_nothing():
    p = Portfolio("10000.00")
    assert p.apply_split(EX, "AAPL", "7") is None
    assert p.entries == ()
    assert p.cash_usd == D("10000.00")


def test_reverse_split_whole_mode_exact():
    p = holding(20)  # basis 2,000.00
    p.apply_split(EX, "AAPL", "0.1")
    # 1-for-10: 20 × 1/10 = 2 shares ; basis 2,000.00 → average 1,000
    pos = p.position("AAPL")
    assert (pos.quantity, pos.cost_basis_usd, pos.average_cost_usd) == (
        D(2),
        D("2000.00"),
        D(1000),
    )


def test_reverse_split_whole_mode_fraction_not_modelled():
    p = holding(15)
    before = (p.position("AAPL"), p.entries)
    # 15 × 1/10 = 1.5 → would need cash-in-lieu → not modelled, nothing changes
    with pytest.raises(NotImplementedError, match="cash-in-lieu"):
        p.apply_split(EX, "AAPL", "0.1")
    assert (p.position("AAPL"), p.entries) == before


def test_reverse_split_fractional_rounds_down_and_notes_fraction():
    p = holding("1.234567", mode="fractional")
    e = p.apply_split(EX, "AAPL", "0.3333333")
    # snapped to 1/3 ; 1.234567 / 3 = 0.411522333… → round DOWN (6 dp) → 0.411522
    # dropped 0.000000333… shares ; cost basis unchanged 123.46
    pos = p.position("AAPL")
    assert pos.quantity == D("0.411522")
    assert pos.cost_basis_usd == D("123.46")
    assert "fraction dropped" in e.note


def test_same_split_twice_is_refused():
    p = holding(10)
    p.apply_split(EX, "AAPL", "2")
    with pytest.raises(LedgerError, match="already applied"):
        p.apply_split(EX, "AAPL", "2")
    assert p.position("AAPL").quantity == D(20)


def test_split_must_come_before_dividend_and_trades():
    p = holding(10)
    p.apply_dividend(EX, "AAPL", "1")
    with pytest.raises(LedgerError, match="split FIRST"):
        p.apply_split(EX, "AAPL", "2")
    q = holding(10)
    q.buy(EX, "AAPL", 1, "100", "0")
    with pytest.raises(LedgerError, match="split FIRST"):
        q.apply_split(EX, "AAPL", "2")


def test_full_day_order_split_dividend_trade():
    p = holding(10)  # basis 1,000.00, cash 9,000.00
    p.apply_split(EX, "AAPL", "2")  # 20 shares
    p.apply_dividend(EX, "AAPL", "0.50")  # per POST-split share (raw price basis that day)
    p.sell(EX, "AAPL", 20, "50", "0")
    # dividend gross 20 × 0.50 = 10.00 ; withholding 1.50 ; net 8.50
    # sale 20 × 50 = 1,000.00 → cash 9,000.00 + 8.50 + 1,000.00 = 10,008.50 ; P&L 1,000 − 1,000 = 0
    assert p.cash_usd == D("10008.50")
    assert p.realised_pnl_usd == D("0.00")
    assert [e.type for e in p.entries] == ["BUY", "SPLIT", "DIVIDEND", "SELL"]
