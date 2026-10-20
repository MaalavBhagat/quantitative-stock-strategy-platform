"""Ledger tests — every expected number is worked out by hand in the comment above its assert.

All amounts are exact Decimal comparisons (no "approximately equal").
"""

import dataclasses
import random
from datetime import date, datetime
from decimal import ROUND_FLOOR, Decimal

import pytest

from quant_research.portfolio.ledger import (
    InsufficientCashError,
    InsufficientSharesError,
    LedgerError,
    Portfolio,
)
from quant_research.portfolio.money import round_shares_down, shares_affordable

D = Decimal
DAY1, DAY2, DAY3 = date(2014, 6, 2), date(2014, 6, 3), date(2014, 6, 4)


def snapshot(p: Portfolio) -> tuple:
    """Everything a refused trade must leave unchanged."""
    return (
        p.cash_usd,
        p.total_spent_usd,
        p.total_received_usd,
        p.total_fees_usd,
        p.realised_pnl_usd,
        p.position("AAPL"),
        p.entries,
    )


# ---------- 3.1 cash ----------
def test_start_cash():
    p = Portfolio(D("10000.00"))
    # nothing has happened yet: cash = 10,000.00, all totals 0
    assert p.cash_usd == D("10000.00")
    assert p.initial_cash_usd == D("10000.00")
    assert (p.total_spent_usd, p.total_received_usd, p.total_fees_usd) == (D(0), D(0), D(0))
    assert p.entries == ()


def test_start_entry_when_start_date_given():
    p = Portfolio("10000.00", start_date=DAY1)
    # one START line: cash 0 → 10,000.00
    (entry,) = p.entries
    assert (entry.type, entry.cash_before_usd, entry.cash_after_usd) == (
        "START",
        D(0),
        D("10000.00"),
    )


def test_initial_cash_must_be_whole_cents():
    with pytest.raises(ValueError, match="whole cents"):
        Portfolio("100.005")


# ---------- 3.2 whole shares ----------
def test_buy_whole_shares():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 10, "150.25", "3")
    # cost = 10 × 150.25 = 1,502.50 ; fee 3.00
    # cash = 10,000.00 − 1,502.50 − 3.00 = 8,494.50
    assert p.cash_usd == D("8494.50")
    assert p.total_spent_usd == D("1502.50")
    assert p.total_fees_usd == D("3.00")
    # position 10 shares, cost basis incl. fee = 1,502.50 + 3.00 = 1,505.50
    assert p.position("AAPL").quantity == D(10)
    assert p.position("AAPL").cost_basis_usd == D("1505.50")


def test_buy_then_sell_realised_pnl():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 10, "100", "3")
    p.sell(DAY2, "AAPL", 10, "110", "3")
    # buy: cost 1,000.00 + fee 3.00 → basis 1,003.00, cash 8,997.00
    # sell: proceeds 1,100.00 − fee 3.00 = 1,097.00 → cash 8,997.00 + 1,097.00 = 10,094.00
    # realised P&L = 1,097.00 − 1,003.00 = 94.00
    assert p.cash_usd == D("10094.00")
    assert p.realised_pnl_usd == D("94.00")
    assert p.entries[-1].realised_pnl_usd == D("94.00")
    assert p.position("AAPL").quantity == D(0)
    assert p.position("AAPL").cost_basis_usd == D(0)


def test_two_buys_average_cost():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 10, "100", "0")
    p.buy(DAY2, "AAPL", 10, "110", "0")
    # basis = 10 × 100 + 10 × 110 = 2,100.00 for 20 shares → average 2,100 / 20 = 105
    pos = p.position("AAPL")
    assert pos.quantity == D(20)
    assert pos.cost_basis_usd == D("2100.00")
    assert pos.average_cost_usd == D(105)


def test_partial_sell_uses_average_cost():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 10, "100", "0")
    p.buy(DAY2, "AAPL", 10, "110", "0")
    p.sell(DAY3, "AAPL", 5, "120", "3")
    # cash after buys = 10,000 − 1,000 − 1,100 = 7,900.00
    # sell: proceeds 5 × 120 = 600.00, fee 3.00 → net 597.00 → cash 8,497.00
    # cost of shares sold = 2,100 × 5 / 20 = 525.00 → P&L = 597.00 − 525.00 = 72.00
    # left: 15 shares, basis 2,100 − 525 = 1,575.00, average 1,575 / 15 = 105
    assert p.cash_usd == D("8497.00")
    assert p.realised_pnl_usd == D("72.00")
    pos = p.position("AAPL")
    assert pos.quantity == D(15)
    assert pos.cost_basis_usd == D("1575.00")
    assert pos.average_cost_usd == D(105)


def test_too_little_cash_raises_and_changes_nothing():
    p = Portfolio("1000.00", share_mode="whole")
    before = snapshot(p)
    # needs 10 × 100 = 1,000.00 + fee 3.00 = 1,003.00 > cash 1,000.00 → short by 3.00
    with pytest.raises(InsufficientCashError, match=r"1003\.00.*1000\.00.*3\.00"):
        p.buy(DAY1, "AAPL", 10, "100", "3")
    assert snapshot(p) == before


def test_selling_more_than_held_raises_and_changes_nothing():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 5, "100", "0")
    before = snapshot(p)
    # hold 5, try to sell 6 → short by 1
    with pytest.raises(InsufficientSharesError, match="only 5 held"):
        p.sell(DAY2, "AAPL", 6, "100", "0")
    assert snapshot(p) == before


def test_selling_unknown_ticker_raises():
    p = Portfolio("10000.00")
    with pytest.raises(InsufficientSharesError):
        p.sell(DAY1, "MSFT", 1, "100", "0")


def test_whole_mode_rejects_fractional_quantity():
    p = Portfolio("10000.00", share_mode="whole")
    with pytest.raises(ValueError, match="whole number"):
        p.buy(DAY1, "AAPL", "1.5", "100", "0")


def test_bad_inputs_rejected():
    p = Portfolio("10000.00")
    with pytest.raises(ValueError, match="quantity"):
        p.buy(DAY1, "AAPL", 0, "100", "0")
    with pytest.raises(ValueError, match="price_usd"):
        p.buy(DAY1, "AAPL", 1, "0", "0")
    with pytest.raises(ValueError, match="fee_usd"):
        p.buy(DAY1, "AAPL", 1, "100", "-1")
    with pytest.raises(ValueError, match="ticker"):
        p.buy(DAY1, " ", 1, "100", "0")
    assert p.entries == ()


# ---------- 3.3 fractional shares ----------
def test_fractional_buy_rounds_shares_down_to_6dp():
    p = Portfolio("10000.00", share_mode="fractional")
    entry = p.buy(DAY1, "AAPL", "1.23456789", "100", "0")
    # shares 1.23456789 → round DOWN to 6 dp → 1.234567
    # cost = 1.234567 × 100 = 123.4567 → we pay, round UP → 123.46
    # cash = 10,000.00 − 123.46 = 9,876.54
    assert entry.quantity == D("1.234567")
    assert p.position("AAPL").quantity == D("1.234567")
    assert entry.gross_usd == D("123.46")
    assert p.cash_usd == D("9876.54")


def test_cash_rounding_against_us_on_buy_and_sell():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 3, "10.333", "0")
    # buy cost 3 × 10.333 = 30.999 → pay → round UP → 31.00 → cash 9,969.00
    assert p.cash_usd == D("9969.00")
    p.sell(DAY2, "AAPL", 3, "10.333", "0")
    # sell proceeds 30.999 → receive → round DOWN → 30.99 → cash 9,999.99
    # same price in and out still loses 1 cent to rounding: P&L = 30.99 − 31.00 = −0.01
    assert p.cash_usd == D("9999.99")
    assert p.realised_pnl_usd == D("-0.01")


def test_fee_with_fractions_of_a_cent_rounds_up():
    p = Portfolio("10000.00")
    entry = p.buy(DAY1, "AAPL", 1, "100", "0.001")
    # fee 0.001 → pay → round UP → 0.01 ; cash = 10,000 − 100.00 − 0.01 = 9,899.99
    assert entry.fee_usd == D("0.01")
    assert p.cash_usd == D("9899.99")


def test_shares_affordable_buy_succeeds_and_leaves_no_negative_cash():
    p = Portfolio("1000.00", share_mode="fractional")
    qty = shares_affordable(p.cash_usd, D("300"), D("3"), "fractional")
    p.buy(DAY1, "AAPL", qty, "300", "3")
    # qty 3.323333 → cost 996.9999 → 997.00 ; + fee 3.00 = 1,000.00 → cash 0.00 (never negative)
    assert p.cash_usd == D("0.00")


def test_min_order_10_usd():
    p = Portfolio("10000.00", share_mode="fractional")
    # 0.05 × 150 = 7.50 < 10 → refused
    with pytest.raises(LedgerError, match="minimum order"):
        p.buy(DAY1, "AAPL", "0.05", "150", "0")
    # 0.1 × 100 = 10.00 → exactly the minimum → allowed
    p.buy(DAY1, "AAPL", "0.1", "100", "0")
    p.buy(DAY1, "AAPL", "0.1", "100", "0")
    # partial sell 0.05 × 100 = 5.00 < 10 → refused
    with pytest.raises(LedgerError, match="minimum order"):
        p.sell(DAY2, "AAPL", "0.05", "100", "0")
    # selling the WHOLE position (0.2 × 40 = 8.00) is allowed below the minimum [ASSUMPTION]
    p.sell(DAY2, "AAPL", "0.2", "40", "0")
    assert p.position("AAPL").quantity == D(0)


def test_float_inputs_rejected():
    p = Portfolio("10000.00")
    with pytest.raises(TypeError, match="to_decimal_price"):
        p.buy(DAY1, "AAPL", 1, 100.5, "0")
    with pytest.raises(TypeError):
        p.buy(DAY1, "AAPL", 1.0, "100", "0")
    with pytest.raises(TypeError):
        Portfolio(10000.0)


def test_dates_cannot_go_backwards_or_have_a_time():
    p = Portfolio("10000.00")
    p.buy(DAY2, "AAPL", 1, "100", "0")
    with pytest.raises(LedgerError, match="before the last ledger date"):
        p.buy(DAY1, "AAPL", 1, "100", "0")
    with pytest.raises(TypeError, match="no time"):
        p.buy(datetime(2014, 6, 5, 9, 30), "AAPL", 1, "100", "0")
    # same day is fine (several trades per day)
    p.buy(DAY2, "AAPL", 1, "100", "0")


def test_ledger_entries_complete_and_immutable():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "aapl", 2, "100", "3")
    p.sell(DAY2, "AAPL", 2, "101", "3")
    buy, sell = p.entries
    # buy: cash 10,000.00 → 10,000 − 200.00 − 3.00 = 9,797.00
    assert (buy.date, buy.type, buy.ticker, buy.quantity, buy.price_usd, buy.fee_usd) == (
        DAY1,
        "BUY",
        "AAPL",
        D(2),
        D(100),
        D("3.00"),
    )
    assert (buy.gross_usd, buy.cash_before_usd, buy.cash_after_usd) == (
        D("200.00"),
        D("10000.00"),
        D("9797.00"),
    )
    # sell: proceeds 202.00 − 3.00 = 199.00 → cash 9,996.00 ; P&L 199.00 − 203.00 = −4.00
    assert (sell.cash_before_usd, sell.cash_after_usd, sell.realised_pnl_usd) == (
        D("9797.00"),
        D("9996.00"),
        D("-4.00"),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        buy.cash_after_usd = D("999999")  # type: ignore[misc]
    assert isinstance(p.entries, tuple)  # no append/remove from outside


def replay_shares(p: Portfolio) -> dict[str, Decimal]:
    """Shares implied by the audit trail alone: buys − sells, × split ratios (rounded down)."""
    shares: dict[str, Decimal] = {}
    for e in p.entries:
        if e.type == "BUY":
            shares[e.ticker] = shares.get(e.ticker, D(0)) + e.quantity
        elif e.type == "SELL":
            shares[e.ticker] -= e.quantity
        elif e.type == "SPLIT":
            shares[e.ticker] = round_shares_down(shares[e.ticker] * e.ratio, p.share_mode)
    return shares


@pytest.mark.parametrize(
    ("mode", "split_ratios"),
    [("fractional", ["2", "3", "7", "0.5", "0.25"]), ("whole", ["2", "3", "7"])],
)
def test_invariants_hold_after_random_trades_dividends_and_splits(mode, split_ratios):
    # For ANY sequence of valid events, after EVERY step (exactly, no tolerance):
    #   initial − spent − fees + received + dividends_net == cash
    #   shares held per ticker == shares implied by the log (buys − sells, × split ratios)
    #   total value at a close == cash + Σ(qty × close rounded down)  (once per day)
    rng = random.Random(20261020)
    p = Portfolio("10000.00", share_mode=mode)
    tickers = ["AAPL", "XOM"]
    day = date(2014, 1, 1)
    counts = {"trade": 0, "dividend": 0, "split": 0}
    for _ in range(400):
        day = date.fromordinal(day.toordinal() + 1)
        t = rng.choice(tickers)
        # daily order: split → dividend → trades
        if rng.random() < 0.05 and p.position(t).quantity > 0:
            p.apply_split(day, t, rng.choice(split_ratios))  # held > 0 → always logs an entry
            counts["split"] += 1
        if rng.random() < 0.15 and p.position(t).quantity > 0:
            amount = D(rng.randint(1, 300)) / 100  # 0.01 … 3.00 per share
            e = p.apply_dividend(day, t, amount)
            if e is not None and e.note is None:
                counts["dividend"] += 1
        for _ in range(rng.choice([1, 2])):
            price = D(rng.randint(500, 50000)) / 100  # 5.00 … 500.00
            fee = D(rng.choice([0, 1, 3, 300])) / 100  # 0.00, 0.01, 0.03, 3.00
            held = p.position(t).quantity
            try:
                if held > 0 and rng.random() < 0.5:
                    share = D(rng.randint(1, 99)) / 100
                    qty = held if rng.random() < 0.3 else round_shares_down(held * share, mode)
                    if qty > 0:
                        p.sell(day, t, qty, price, fee)
                        counts["trade"] += 1
                else:
                    qty = round_shares_down(
                        shares_affordable(p.cash_usd, price, fee, mode)
                        * D(rng.randint(1, 60))
                        / 100,
                        mode,
                    )
                    if qty > 0:
                        p.buy(day, t, qty, price, fee)
                        counts["trade"] += 1
            except LedgerError:
                pass  # e.g. below the minimum order — refused trades change nothing
            assert (
                p.initial_cash_usd
                - p.total_spent_usd
                - p.total_fees_usd
                + p.total_received_usd
                + p.dividends_net_usd
                == p.cash_usd
            )
            assert p.cash_usd >= 0
            implied = replay_shares(p)
            for ticker in tickers:
                assert p.position(ticker).quantity == implied.get(ticker, D(0))
        # valuation at a random close: total == cash + Σ(qty × close rounded DOWN to cents)
        closes = {ticker: D(rng.randint(500, 50000)) / 100 for ticker in tickers}
        v = p.valuation(day, closes)
        expected_mv = sum(
            (
                (p.position(ticker).quantity * closes[ticker]).quantize(D("0.01"), ROUND_FLOOR)
                for ticker in tickers
            ),
            D(0),
        )
        assert v.total_value_usd == p.cash_usd + expected_mv
    # the sequence really exercised every kind of event
    assert counts["trade"] > 100 and counts["dividend"] > 10 and counts["split"] > 3, counts
