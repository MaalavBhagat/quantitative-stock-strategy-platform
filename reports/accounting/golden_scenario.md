# Golden accounting scenario (Phase 3, Step 3.8)

Made-up prices for a made-up ticker "TEST" — not market data, safe to share. Every number below is
asserted **exactly** by `tests/accounting/test_golden_scenario.py` against our real code
(`execution/costs.py` + `portfolio/ledger.py` + valuation). Simulated, illustrative only.

## 1. Fractional shares — independent answer key (computed by chat Claude, not by our code)
Settings: fractional mode · broker Stake (US$3 per trade) · spread normal (0.05% per side) · withholding 15%.

| Step | Action | Expected (all matched exactly) |
|---|---|---|
| Start | aud_to_usd(10000 AUD, usd_per_aud 0.69, fee 0.55%) | gross 6900.00 · FX fee 37.95 · cash 6862.05 |
| 2014-06-02 | buy max affordable at reference open 630.00 (fee 3.00) | fill 630.315 · qty 10.881939 · cost 6859.05 · cash 0.00 · cost basis 6862.05 · spread cost ≈3.4278 |
| 2014-06-02 close 628.65 | valuation | market value 6840.93 · total 6840.93 · unrealised −21.12 |
| 2014-06-09 | split 7 (start of day) | qty 76.173573 · cost basis 6862.05 · avg ≈90.0843919 |
| 2014-06-09 close 93.70 | valuation | market value 7137.46 · total 7137.46 · unrealised 275.41 |
| 2014-08-07 | dividend 0.47/share (before trades) | gross 35.80 · withholding 5.37 · net 30.43 · cash 30.43 |
| 2014-08-07 close 94.48 | valuation | market value 7196.87 · total 7227.30 · unrealised 334.82 |
| 2014-08-08 | sell ALL at reference open 95.00 (fee 3.00) | fill 94.9525 · proceeds 7232.87 · cash 7260.30 · realised P&L 367.82 |
| End | usd_to_aud(7260.30, 0.75, 0.55%) | FX fee 39.94 · AUD out 9627.14 |
| Check | initial − spent − fees + received + net dividends | 6862.05 − 6859.05 − 6.00 + 7232.87 + 30.43 = 7260.30 = cash |

**One rule had to be decided (2026-10-20).** Our first code took the 15% withholding from the
*exact* dividend (35.80157931 → 5.3702 → rounded up 5.38). The answer key took it from the dividend
*in cents* (35.80 → 5.37). The expected value was not changed; Goggy chose the answer key's rule
(tax is withheld on the dividend actually paid, in cents). The code was changed, and all earlier
tests kept their values.

**The story in plain English.** Goggy converts AUD 10,000 into US$6,862.05 (Stake keeps 0.55%) and
buys as many TEST shares as the money allows at the open, paying a small spread and US$3 brokerage —
cash is now zero. The price dips at the close (a paper loss of US$21.12), then a 7-for-1 split turns
10.88 shares into 76.17 shares without changing what they cost in total. A dividend of US$0.47 a share
arrives on the ex-date; 15% US tax is withheld and US$30.43 lands in cash. The next morning everything
is sold for US$7,232.87, for a realised profit of US$367.82 after all fees. Converting the US$7,260.30
back gives AUD 9,627.14.

**Currency matters.** The stock gained in USD terms (+US$367.82 realised, plus US$30.43 of dividends),
yet the account returns **less AUD (9,627.14) than went in (10,000)**. That's because AUD/USD moved from
0.69 to 0.75 (each US dollar buys fewer Australian dollars on the way back) and two 0.55% FX fees were
paid. For an Australian investor, results must be reported in AUD as well as USD.

## 2. Whole shares — hand-calculated by Claude Code (NOT pre-computed by chat Claude)
Same steps and prices, whole-share mode. Working is written in the test comments.

| Step | Result |
|---|---|
| Start | cash 6862.05 |
| Buy | 10 shares at 630.315 · cost 6303.15 · cash 555.90 · cost basis 6306.15 · spread cost 3.15 |
| Close 628.65 | market value 6286.50 · total 6842.40 · unrealised −19.65 |
| Split 7 | 70 shares · cost basis 6306.15 |
| Close 93.70 | market value 6559.00 · total 7114.90 · unrealised 252.85 |
| Dividend 0.47 | gross 32.90 · withholding 4.94 · net 27.96 · cash 583.86 |
| Close 94.48 | market value 6613.60 · total 7197.46 · unrealised 307.45 |
| Sell 70 at 94.9525 | proceeds 6646.67 · cash 7227.53 · realised P&L 337.52 |
| End | FX fee 39.76 · AUD out 9583.69 |
| Check | 6862.05 − 6303.15 − 6.00 + 6646.67 + 27.96 = 7227.53 = cash |

Whole shares leave US$555.90 uninvested, so this run ends US$32.77 lower than the fractional one.
