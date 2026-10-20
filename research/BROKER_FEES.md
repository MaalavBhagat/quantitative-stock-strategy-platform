# BROKER_FEES.md — US share trading costs for an Australian investor
Checked: 2026-10-17. Fees change — re-check before relying on them.
Rule: every number has a source. Anything without one is marked UNVERIFIED.

## 1. Fee table (US shares)
| Broker | Brokerage per US trade | FX conversion | When FX is charged | Fractional | Source |
|---|---|---|---|---|---|
| CommSec (standard) | US$5 or 0.12%, whichever is greater | 0.55% | Every trade (auto-converts AUD↔USD) | Not stated on fee page | [CommSec rates & fees](https://static.commsec.com.au/support/rates-and-fees.html) |
| CommSec (Intl Shares Plus) | US$9.95 or 0.20%, whichever is greater | 0.55% | Avoidable if USD held in Plus wallet | Not stated | same as above |
| Interactive Brokers (Fixed) | US$0.005/share, min US$1, max 1% of trade | 0.03% auto; ~0.002% (min US$2) if converted manually | Once, if you convert manually and hold USD | Yes (UNVERIFIED for AU accounts — check) | [IBKR AU commissions](https://www.interactivebrokers.com.au/en/pricing/commissions-home.php) |
| Stake (Wall St) | US$3 per trade (0.01% above US$30k) | 0.55% | When funding — "no FX fees per trade" (withdrawal FX 0.55% VERIFIED 2026-10-20 — Stake support page) | Yes, min US$10 | VERIFIED 2026-10-17: [Stake AU pricing](https://hellostake.com/au/pricing); also [Finder](https://www.finder.com.au/share-trading/stake) |
| moomoo AU | US$0.99 per trade + pass-through fees | FX spread, rate not published | On conversion | Yes | [moomoo AU pricing](https://moomoo.com/au/pricing) |

Not counted above: bid-ask spread (all brokers), US SEC/FINRA fees (tiny on sells).

## 2. Cost of ONE round trip (buy + sell) on ~AUD 10,000
ASSUMPTION (UNVERIFIED): AUD/USD = 0.65 → AUD 10,000 ≈ US$6,500. Spread ignored here.

| Broker | Brokerage (2 trades) | FX (per round trip) | Total ≈ | As % of US$6,500 |
|---|---|---|---|---|
| CommSec standard | 2 × US$7.80 = US$15.60 | 2 × 0.55% = US$71.50 | ~US$87 | ~1.34% |
| Stake | 2 × US$3 = US$6 | 0 (paid once at deposit) | ~US$6 | ~0.09% |
| IBKR Fixed (e.g. 30 shares) | 2 × US$1 = US$2 | 0 (convert once manually) | ~US$2 | ~0.03% |
| moomoo | 2 × ~US$1.05 = ~US$2.10 | spread unknown | ~US$2 + FX | ~0.03% + FX |

One-off FX cost to get into USD at the start (and back out at the end) applies to ALL strategies incl. buy-and-hold, so it doesn't change the comparison much.

## 3. What this means for the research (Claude's reading)
- CommSec standard costs ~1.3% per round trip, mostly the FX fee charged on every trade.
  A 2% "sell on rise" target would lose about two-thirds of its gain to fees.
- Brokers that let you hold USD (IBKR, Stake, moomoo, CommSec Plus wallet) cut the
  per-trade cost to ~0.03–0.1%. For a frequent-trading strategy this is the single
  biggest factor.
- Plan: model 3 cost scenarios — LOW (IBKR-like), MID (Stake-like), HIGH (CommSec standard).
- DECISION 2026-10-17: Stake = MAIN case (Goggy knows it). Stake fees verified on Stake's own
  site 2026-10-17; withdrawal FX 0.55% confirmed 2026-10-20
  (https://hellostake.com/support/funding-and-withdrawal/withdrawal/26014595952153).
- This is research modelling, not a recommendation to switch brokers.
