"""Cost model tests — hand calculations above each assert, exact Decimal equality."""

from datetime import date
from decimal import Decimal

import pytest

from quant_research.execution.costs import (
    COST_TABLE,
    apply_spread,
    aud_to_usd,
    fee_usd,
    fx_fee_settings,
    usd_to_aud,
)
from quant_research.portfolio.ledger import Portfolio

D = Decimal


def test_every_cost_number_has_a_source():
    for key, param in COST_TABLE.items():
        assert param.source.startswith("http") or "[ASSUMPTION]" in param.source, key


def test_stake_flat_fee_up_to_30k():
    # US$6,900 ≤ 30,000 → flat US$3.00
    assert fee_usd("stake", D("6900"), D(30)).total_usd == D("3.00")


def test_stake_percentage_above_30k():
    # US$40,000 > 30,000 → 0.01% × 40,000 = 4.00
    f = fee_usd("stake", D("40000"), D(100))
    assert (f.brokerage_usd, f.fx_usd, f.total_usd) == (D("4.00"), D(0), D("4.00"))


def test_ibkr_minimum_applies():
    # 30 shares × 0.005 = 0.15 → below minimum → 1.00 (cap 1% of 6,900 = 69 doesn't bind)
    assert fee_usd("ibkr_fixed", D("6900"), D(30)).total_usd == D("1.00")


def test_ibkr_one_percent_cap_binds():
    # 1,000 shares × $0.40 = $400 value; per-share 1,000 × 0.005 = 5.00; cap 1% × 400 = 4.00 → 4.00
    assert fee_usd("ibkr_fixed", D("400"), D(1000)).total_usd == D("4.00")


def test_commsec_brokerage_plus_fx_parts():
    # brokerage = max(5.00, 0.12% × 6,900 = 8.28) = 8.28 ; FX = 0.55% × 6,900 = 37.95
    # total = 8.28 + 37.95 = 46.23
    f = fee_usd("commsec_standard", D("6900"), D(30))
    assert (f.brokerage_usd, f.fx_usd, f.total_usd) == (D("8.28"), D("37.95"), D("46.23"))


def test_commsec_minimum_and_fee_rounding_up():
    # value 1,000.01: 0.12% = 1.200012 → below min → 5.00 ; FX 0.55% = 5.500055 → round UP → 5.51
    f = fee_usd("commsec_standard", D("1000.01"), D(1))
    assert (f.brokerage_usd, f.fx_usd, f.total_usd) == (D("5.00"), D("5.51"), D("10.51"))


def test_unknown_broker_is_an_error():
    with pytest.raises(ValueError, match="unknown broker"):
        fee_usd("robinhood", D("100"), D(1))
    with pytest.raises(ValueError, match="unknown broker"):
        fx_fee_settings("robinhood")


def test_spread_buy_and_sell_fill_prices():
    # normal spread 0.05%: buy fill = 230 × 1.0005 = 230.115 ; sell fill = 230 × 0.9995 = 229.885
    # spread cost each side = 0.115 × 30 shares = 3.45
    buy = apply_spread(D("230"), "buy", "normal", D(30))
    sell = apply_spread(D("230"), "sell", "normal", D(30))
    assert (buy.fill_price_usd, buy.spread_cost_usd) == (D("230.115"), D("3.450"))
    assert (sell.fill_price_usd, sell.spread_cost_usd) == (D("229.885"), D("3.450"))


def test_spread_levels_tight_and_wide():
    # tight 0.02%: 100 × 1.0002 = 100.02 ; wide 0.10%: 100 × 0.999 = 99.9
    assert apply_spread(D("100"), "buy", "tight", D(1)).fill_price_usd == D("100.02")
    assert apply_spread(D("100"), "sell", "wide", D(1)).fill_price_usd == D("99.9")
    with pytest.raises(ValueError):
        apply_spread(D("100"), "buy", "huge", D(1))  # type: ignore[arg-type]


def test_aud_to_usd_stake():
    # 10,000 AUD × 0.69 = 6,900.00 USD ; fee 0.55% × 6,900 = 37.95 ; out = 6,862.05
    rate, minimum = fx_fee_settings("stake")
    r = aud_to_usd(D("10000"), D("0.69"), rate, minimum)
    assert (r.fee_usd, r.amount_out) == (D("37.95"), D("6862.05"))


def test_aud_to_usd_rounds_against_us():
    # 1,000.01 AUD × 0.65437 = 654.3765437 USD
    # fee 0.55% × 654.3765437 = 3.59907… → round UP → 3.60
    # out = 654.3765437 − 3.60 = 650.7765437 → round DOWN → 650.77
    r = aud_to_usd(D("1000.01"), D("0.65437"), D("0.0055"))
    assert (r.fee_usd, r.amount_out) == (D("3.60"), D("650.77"))


def test_usd_to_aud_stake_rounds_against_us():
    # fee 0.55% × 6,862.05 = 37.741275 → round UP → 37.75
    # AUD out = (6,862.05 − 37.75) / 0.69 = 6,824.30 / 0.69 = 9,890.289… → round DOWN → 9,890.28
    rate, minimum = fx_fee_settings("stake", "out")
    r = usd_to_aud(D("6862.05"), D("0.69"), rate, minimum)
    assert (r.fee_usd, r.amount_out) == (D("37.75"), D("9890.28"))


def test_ibkr_fx_minimum_fee():
    # 10,000 AUD × 0.69 = 6,900 USD ; 0.002% × 6,900 = 0.138 → minimum US$2.00 ; out 6,898.00
    rate, minimum = fx_fee_settings("ibkr_fixed")
    r = aud_to_usd(D("10000"), D("0.69"), rate, minimum)
    assert (r.fee_usd, r.amount_out) == (D("2.00"), D("6898.00"))


def test_stake_round_trip_matches_feasibility_estimate():
    # One Stake round trip on ~US$6,900, normal spread, through the real ledger:
    # buy 30 @ 230.115 = 6,903.45 + fee 3.00 ; sell 30 @ 229.885 = 6,896.55 − fee 3.00
    # cost = 6,906.45 − 6,893.55 = 12.90 → 12.90 / 6,900 = 0.18696%
    # SMALL_ACCOUNT_FEASIBILITY.md said ≈0.19% — it was a rough estimate, so allow ±0.01 points.
    p = Portfolio("6910.00", share_mode="fractional")
    qty = D(30)
    buy = apply_spread(D("230"), "buy", "normal", qty)
    sell = apply_spread(D("230"), "sell", "normal", qty)
    p.buy(
        date(2014, 6, 2),
        "AAPL",
        qty,
        buy.fill_price_usd,
        fee_usd("stake", D("6900"), qty).total_usd,
    )
    p.sell(
        date(2014, 6, 3),
        "AAPL",
        qty,
        sell.fill_price_usd,
        fee_usd("stake", D("6900"), qty).total_usd,
    )
    round_trip_cost = D("6910.00") - p.cash_usd
    assert round_trip_cost == D("12.90")
    assert abs(round_trip_cost / D(6900) - D("0.0019")) < D("0.0001")
