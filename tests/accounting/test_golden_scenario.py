"""Golden scenario (Phase 3, Step 3.8) — an INDEPENDENT answer key.

FRACTIONAL scenario: every expected number was computed separately by chat Claude (own code, using
only the rounding rules in our docs). Do NOT edit an expected value to match the code — a mismatch
means a rule differs and Goggy decides (see PROJECT_STATUS: withholding base, 2026-10-20).
WHOLE-SHARE scenario: computed BY HAND here (working in comments) — NOT pre-computed by chat Claude.
Ticker "TEST" with made-up prices (no real market data in tests).
"""

from datetime import date
from decimal import Decimal

from quant_research.execution.costs import (
    apply_spread,
    aud_to_usd,
    fee_usd,
    fx_fee_settings,
    usd_to_aud,
)
from quant_research.portfolio.ledger import Portfolio
from quant_research.portfolio.money import shares_affordable

D = Decimal
T = "TEST"
BUY_DAY, SPLIT_DAY, DIV_DAY, SELL_DAY = (
    date(2014, 6, 2),
    date(2014, 6, 9),
    date(2014, 8, 7),
    date(2014, 8, 8),
)


def start(mode: str) -> tuple[Portfolio, object]:
    rate, minimum = fx_fee_settings("stake", "in")
    fx = aud_to_usd(D(10000), D("0.69"), rate, minimum)
    return Portfolio(fx.amount_out, share_mode=mode), fx  # type: ignore[arg-type]


def buy_max(p: Portfolio, reference: Decimal):
    fill = apply_spread(reference, "buy", "normal", D(1)).fill_price_usd
    qty = shares_affordable(p.cash_usd, fill, D("3.00"), p.share_mode)
    spread = apply_spread(reference, "buy", "normal", qty)
    fee = fee_usd("stake", qty * fill, qty).total_usd
    return p.buy(BUY_DAY, T, qty, fill, fee), spread


def sell_all(p: Portfolio, reference: Decimal):
    qty = p.position(T).quantity
    fill = apply_spread(reference, "sell", "normal", qty).fill_price_usd
    return p.sell(SELL_DAY, T, qty, fill, fee_usd("stake", qty * fill, qty).total_usd)


def test_golden_scenario_fractional_matches_independent_answer_key():
    # Start: aud_to_usd(10000 AUD, 0.69, 0.55%) → gross 6900.00 · FX fee 37.95 · cash 6862.05
    p, fx = start("fractional")
    assert (fx.amount_in * fx.usd_per_aud, fx.fee_usd, p.cash_usd) == (
        D("6900.00"),
        D("37.95"),
        D("6862.05"),
    )

    # 2014-06-02 buy max at reference open 630.00 (fee 3.00)
    # → fill 630.315 · qty 10.881939 · cost 6859.05 · cash 0.00 · cost basis 6862.05 · spread ≈3.4278
    buy, spread = buy_max(p, D("630.00"))
    assert (buy.price_usd, buy.quantity, buy.gross_usd, p.cash_usd) == (
        D("630.315"),
        D("10.881939"),
        D("6859.05"),
        D("0.00"),
    )
    assert p.position(T).cost_basis_usd == D("6862.05")
    assert spread.spread_cost_usd.quantize(D("0.0001")) == D("3.4278")  # key gives ≈3.4278

    # 2014-06-02 close 628.65 → market value 6840.93 · total 6840.93 · unrealised −21.12
    v = p.valuation(BUY_DAY, {T: D("628.65")})
    assert (v.total_market_value_usd, v.total_value_usd, v.unrealised_pnl_usd) == (
        D("6840.93"),
        D("6840.93"),
        D("-21.12"),
    )

    # 2014-06-09 split 7 → qty 76.173573 · cost basis 6862.05 · avg ≈90.0843919
    p.apply_split(SPLIT_DAY, T, "7")
    pos = p.position(T)
    assert (pos.quantity, pos.cost_basis_usd) == (D("76.173573"), D("6862.05"))
    assert pos.average_cost_usd.quantize(D("0.0000001")) == D("90.0843919")  # key gives ≈

    # 2014-06-09 close 93.70 → market value 7137.46 · total 7137.46 · unrealised 275.41
    v = p.valuation(SPLIT_DAY, {T: D("93.70")})
    assert (v.total_market_value_usd, v.total_value_usd, v.unrealised_pnl_usd) == (
        D("7137.46"),
        D("7137.46"),
        D("275.41"),
    )

    # 2014-08-07 dividend 0.47/share → gross 35.80 · withholding 5.37 · net 30.43 · cash 30.43
    p.apply_dividend(DIV_DAY, T, "0.47")
    assert (p.dividends_gross_usd, p.withholding_usd, p.dividends_net_usd, p.cash_usd) == (
        D("35.80"),
        D("5.37"),
        D("30.43"),
        D("30.43"),
    )

    # 2014-08-07 close 94.48 → market value 7196.87 · total 7227.30 · unrealised 334.82
    v = p.valuation(DIV_DAY, {T: D("94.48")})
    assert (v.total_market_value_usd, v.total_value_usd, v.unrealised_pnl_usd) == (
        D("7196.87"),
        D("7227.30"),
        D("334.82"),
    )

    # 2014-08-08 sell ALL at reference open 95.00 (fee 3.00)
    # → fill 94.9525 · proceeds 7232.87 · cash 7260.30 · realised P&L 367.82
    sell = sell_all(p, D("95.00"))
    assert (sell.price_usd, sell.gross_usd, p.cash_usd, p.realised_pnl_usd) == (
        D("94.9525"),
        D("7232.87"),
        D("7260.30"),
        D("367.82"),
    )

    # End: usd_to_aud(7260.30, 0.75, 0.55%) → FX fee 39.94 · AUD out 9627.14
    rate, minimum = fx_fee_settings("stake", "out")
    out = usd_to_aud(p.cash_usd, D("0.75"), rate, minimum)
    assert (out.fee_usd, out.amount_out) == (D("39.94"), D("9627.14"))

    # Check: 6862.05 − 6859.05 − 6.00 + 7232.87 + 30.43 = 7260.30 = cash
    assert (p.total_spent_usd, p.total_fees_usd, p.total_received_usd) == (
        D("6859.05"),
        D("6.00"),
        D("7232.87"),
    )
    assert (
        p.initial_cash_usd
        - p.total_spent_usd
        - p.total_fees_usd
        + p.total_received_usd
        + p.dividends_net_usd
        == p.cash_usd
        == D("7260.30")
    )


def test_whole_share_scenario_hand_calculated():
    # NOT pre-computed by chat Claude — working shown here, then asserted.
    # Start: same as fractional → cash 6862.05
    p, _ = start("whole")
    assert p.cash_usd == D("6862.05")

    # Buy: fill 630.00 × 1.0005 = 630.315 ; available for shares 6862.05 − 3.00 = 6859.05
    # 6859.05 / 630.315 = 10.88… → whole shares → 10
    # cost 10 × 630.315 = 6303.15 (exact cents) ; cash 6862.05 − 6303.15 − 3.00 = 555.90
    # basis 6303.15 + 3.00 = 6306.15 ; spread cost 0.315 × 10 = 3.15
    buy, spread = buy_max(p, D("630.00"))
    assert (buy.quantity, buy.gross_usd, p.cash_usd) == (D(10), D("6303.15"), D("555.90"))
    assert (p.position(T).cost_basis_usd, spread.spread_cost_usd) == (D("6306.15"), D("3.15"))

    # Close 628.65: market value 10 × 628.65 = 6286.50 ; total 555.90 + 6286.50 = 6842.40
    # unrealised 6286.50 − 6306.15 = −19.65
    v = p.valuation(BUY_DAY, {T: D("628.65")})
    assert (v.total_market_value_usd, v.total_value_usd, v.unrealised_pnl_usd) == (
        D("6286.50"),
        D("6842.40"),
        D("-19.65"),
    )

    # Split 7: 10 × 7 = 70 shares ; basis 6306.15 ; avg 6306.15 / 70 = 90.0878571428…
    p.apply_split(SPLIT_DAY, T, "7")
    assert (p.position(T).quantity, p.position(T).cost_basis_usd) == (D(70), D("6306.15"))

    # Close 93.70: market value 70 × 93.70 = 6559.00 ; total 555.90 + 6559.00 = 7114.90
    # unrealised 6559.00 − 6306.15 = 252.85
    v = p.valuation(SPLIT_DAY, {T: D("93.70")})
    assert (v.total_market_value_usd, v.total_value_usd, v.unrealised_pnl_usd) == (
        D("6559.00"),
        D("7114.90"),
        D("252.85"),
    )

    # Dividend 0.47: gross 70 × 0.47 = 32.90 ; withholding 15% × 32.90 = 4.935 → UP → 4.94
    # net 32.90 − 4.94 = 27.96 ; cash 555.90 + 27.96 = 583.86
    p.apply_dividend(DIV_DAY, T, "0.47")
    assert (p.dividends_gross_usd, p.withholding_usd, p.dividends_net_usd, p.cash_usd) == (
        D("32.90"),
        D("4.94"),
        D("27.96"),
        D("583.86"),
    )

    # Close 94.48: market value 70 × 94.48 = 6613.60 ; total 583.86 + 6613.60 = 7197.46
    # unrealised 6613.60 − 6306.15 = 307.45
    v = p.valuation(DIV_DAY, {T: D("94.48")})
    assert (v.total_market_value_usd, v.total_value_usd, v.unrealised_pnl_usd) == (
        D("6613.60"),
        D("7197.46"),
        D("307.45"),
    )

    # Sell 70: fill 95.00 × 0.9995 = 94.9525 ; proceeds 70 × 94.9525 = 6646.675 → DOWN → 6646.67
    # fee 3.00 → net 6643.67 ; cash 583.86 + 6643.67 = 7227.53 ; realised 6643.67 − 6306.15 = 337.52
    sell = sell_all(p, D("95.00"))
    assert (sell.gross_usd, p.cash_usd, p.realised_pnl_usd) == (
        D("6646.67"),
        D("7227.53"),
        D("337.52"),
    )

    # End: fee 0.55% × 7227.53 = 39.751415 → UP → 39.76
    # AUD out (7227.53 − 39.76) / 0.75 = 7187.77 / 0.75 = 9583.6933… → DOWN → 9583.69
    rate, minimum = fx_fee_settings("stake", "out")
    out = usd_to_aud(p.cash_usd, D("0.75"), rate, minimum)
    assert (out.fee_usd, out.amount_out) == (D("39.76"), D("9583.69"))

    # Check: 6862.05 − 6303.15 − 6.00 + 6646.67 + 27.96 = 7227.53 = cash
    assert (
        p.initial_cash_usd
        - p.total_spent_usd
        - p.total_fees_usd
        + p.total_received_usd
        + p.dividends_net_usd
        == p.cash_usd
        == D("7227.53")
    )
