"""Valuation (Step 3.7) — hand calculations above each assert, exact Decimal equality."""

from datetime import date
from decimal import Decimal

import pytest

from quant_research.portfolio.ledger import LedgerError, MissingPriceError, Portfolio
from quant_research.portfolio.money import to_display

D = Decimal
DAY1, DAY2 = date(2014, 6, 2), date(2014, 6, 3)


def test_missing_close_price_is_an_error():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 10, "100", "0")
    with pytest.raises(MissingPriceError, match="AAPL"):
        p.valuation(DAY1, {"XOM": D("80")})


def test_valuation_does_not_change_the_ledger():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 10, "100", "3")
    before = (p.cash_usd, p.position("AAPL"), p.entries, p.realised_pnl_usd)
    p.valuation(DAY1, {"AAPL": D("120")})
    p.valuation(DAY1, {"AAPL": D("80")})
    assert (p.cash_usd, p.position("AAPL"), p.entries, p.realised_pnl_usd) == before


def test_two_tickers():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 10, "100", "3")  # basis 1,003.00
    p.buy(DAY1, "XOM", 20, "50", "3")  # basis 1,003.00
    v = p.valuation(DAY1, {"AAPL": D("110"), "XOM": D("45"), "MSFT": D("40")})
    # cash = 10,000 − 1,003 − 1,003 = 7,994.00
    # AAPL mv 10 × 110 = 1,100.00, unrealised 1,100.00 − 1,003.00 = 97.00
    # XOM  mv 20 × 45  =   900.00, unrealised   900.00 − 1,003.00 = −103.00
    # total mv 2,000.00 ; total value 7,994.00 + 2,000.00 = 9,994.00 ; unrealised −6.00
    assert v.cash_usd == D("7994.00")
    assert (v.holding("AAPL").market_value_usd, v.holding("AAPL").unrealised_pnl_usd) == (
        D("1100.00"),
        D("97.00"),
    )
    assert (v.holding("XOM").market_value_usd, v.holding("XOM").unrealised_pnl_usd) == (
        D("900.00"),
        D("-103.00"),
    )
    assert (v.total_market_value_usd, v.total_value_usd, v.unrealised_pnl_usd) == (
        D("2000.00"),
        D("9994.00"),
        D("-6.00"),
    )
    assert [h.ticker for h in v.holdings] == ["AAPL", "XOM"]  # unheld MSFT price ignored


def test_after_partial_sell():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 10, "100", "0")
    p.buy(DAY1, "AAPL", 10, "110", "0")  # basis 2,100.00 for 20
    p.sell(DAY2, "AAPL", 5, "120", "3")  # realised 72.00 (see test_ledger)
    v = p.valuation(DAY2, {"AAPL": D("115")})
    # cash = 10,000 − 2,100 + 600 − 3 = 8,497.00 ; left 15 shares, basis 1,575.00, avg 105
    # mv 15 × 115 = 1,725.00 ; unrealised 1,725.00 − 1,575.00 = 150.00 ; total 10,222.00
    h = v.holding("AAPL")
    assert (h.quantity, h.average_cost_usd, h.cost_basis_usd) == (D(15), D(105), D("1575.00"))
    assert (h.market_value_usd, h.unrealised_pnl_usd) == (D("1725.00"), D("150.00"))
    assert (v.cash_usd, v.total_value_usd, v.realised_pnl_usd) == (
        D("8497.00"),
        D("10222.00"),
        D("72.00"),
    )


def test_market_value_rounds_down_to_cents():
    p = Portfolio("10000.00", share_mode="fractional")
    p.buy(DAY1, "AAPL", "1.234567", "100", "0")
    v = p.valuation(DAY1, {"AAPL": D("99.99")})
    # mv = 1.234567 × 99.99 = 123.44435433 → round DOWN → 123.44
    assert v.holding("AAPL").market_value_usd == D("123.44")


def test_valuation_reports_income_and_fees_separately():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY1, "AAPL", 10, "100", "3")
    p.apply_dividend(DAY2, "AAPL", "2.65")  # 26.50 − 3.98 = 22.52 (see test_corporate_actions)
    v = p.valuation(DAY2, {"AAPL": D("100")})
    assert (v.dividends_gross_usd, v.withholding_usd, v.dividends_net_usd, v.total_fees_usd) == (
        D("26.50"),
        D("3.98"),
        D("22.52"),
        D("3.00"),
    )


def test_valuation_inputs_checked():
    p = Portfolio("10000.00", share_mode="whole")
    p.buy(DAY2, "AAPL", 1, "100", "0")
    with pytest.raises(LedgerError, match="before the last ledger date"):
        p.valuation(DAY1, {"AAPL": D("100")})
    with pytest.raises(TypeError):
        p.valuation(DAY2, {"AAPL": 100.0})
    with pytest.raises(ValueError):
        p.valuation(DAY2, {"AAPL": D("0")})


def test_empty_portfolio_value_is_cash():
    v = Portfolio("10000.00").valuation(DAY1, {})
    assert (v.total_value_usd, v.total_market_value_usd, v.holdings) == (
        D("10000.00"),
        D("0.00"),
        (),
    )


def test_display_rule_round_half_even():
    # display only: 2.345 → 2.34 (4 is even) ; 2.355 → 2.36 (6 is even) ; −21.125 → −21.12
    assert to_display(D("2.345")) == D("2.34")
    assert to_display(D("2.355")) == D("2.36")
    assert to_display(D("-21.125")) == D("-21.12")
