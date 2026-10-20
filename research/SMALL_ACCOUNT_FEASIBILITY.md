# SMALL_ACCOUNT_FEASIBILITY.md — Step 0.4
Status: Draft v1 (2026-10-17) — awaiting Goggy's review
Capital: AUD 10,000 (roadmap said 1,000; changed by Goggy 2026-10-17)
Numbers are produced by `research/calc_feasibility.py` — re-run it to check. Nothing typed by hand.

## 1. Inputs and where they come from
| Input | Value | Label | Source |
|---|---|---|---|
| Stake brokerage | US$3/trade; 0.01% above US$30k | VERIFIED (Stake site) | [Stake AU pricing](https://hellostake.com/au/pricing) |
| Stake FX | 0.55%, only when funding — "no FX fees per trade" | VERIFIED (Stake site) | same |
| Stake FX on withdrawal | 0.55% | VERIFIED 2026-10-20 (Stake support) | [Stake withdrawals](https://hellostake.com/support/funding-and-withdrawal/withdrawal/26014595952153) |
| Stake fractional | Yes, from US$10 | VERIFIED (Stake site) | [Stake AU pricing](https://hellostake.com/au/pricing) |
| IBKR fixed | US$0.005/share, min US$1, max 1%; FX ~0.002% manual | SOURCED | [IBKR AU](https://www.interactivebrokers.com.au/en/pricing/commissions-home.php) |
| CommSec standard | US$5 or 0.12% (greater); FX 0.55% each trade | SOURCED | [CommSec fees](https://static.commsec.com.au/support/rates-and-fees.html) |
| AUD/USD | 0.69 | ASSUMPTION (rate in Stake's own example, not live) | — |
| Spread + slippage per side | tight 0.02% / normal 0.05% / wide 0.10% | ASSUMPTION (no free spread history) | — |
| Share price for per-share maths | US$250 | ASSUMPTION (illustrative) | — |

## 2. Results (from calc_feasibility.py)

**A. Cost of one round trip (sell + rebuy), % of position**
| Broker | Brokerage | FX | Tight spread | Normal | Wide |
|---|---|---|---|---|---|
| IBKR (LOW) | 0.03% | 0% | 0.07% | 0.13% | 0.23% |
| **Stake (MID, main)** | 0.09% | 0% | 0.13% | **0.19%** | 0.29% |
| CommSec (HIGH) | 0.24% | 1.10% | 1.38% | 1.44% | 1.54% |

**B. What's left of each dip after costs** (normal spread; net ≈ Y − cost)
| Broker | Y = 2% | Y = 3% | Y = 5% |
|---|---|---|---|
| IBKR | +1.87% | +2.87% | +4.87% |
| **Stake** | **+1.81%** | **+2.81%** | **+4.81%** |
| CommSec | +0.56% | +1.56% | +3.56% |

**C. Yearly cost drag by number of round trips** (normal spread)
| Broker | 5/yr | 10/yr | 20/yr | 50/yr |
|---|---|---|---|---|
| IBKR | 0.6% | 1.3% | 2.6% | 6.5% |
| **Stake** | **0.9%** | **1.9%** | **3.8%** | **9.4%** |
| CommSec | 7.2% | 14.4% | 28.8% | 72.0% |

**D. One-off FX (in + out):** Stake ~1.1% total, IBKR ~0%. Hits buy-and-hold equally.

**E. Whole shares only:** at US$250/share, up to 3.6% of cash sits idle (avg ~1.8%).
Not an issue on Stake (fractional). Matters for CommSec (assume no fractional) and IBKR [UNVERIFIED for AU].

## 3. What this means (plain words)
- **On Stake, costs do NOT kill the idea.** A 2% dip still leaves ~1.8% after costs.
- **On CommSec, costs nearly kill it.** A 2% dip leaves only ~0.6%; 20 trades/year = ~29% lost to fees.
- **Trade count is the danger.** Even on Stake, 50 round trips/year costs ~9% — more than a typical
  year of stock market return. So the strategy must trade *rarely and well*, not often.
- **The bigger risk is not fees, it's missed upside.** Costs are now small; the real question for
  H1 is how often we sell and the stock never comes back down (Q4.4). Only the backtest can answer that.
- **Spread is a guess.** For large US stocks it's probably small, but we test tight/normal/wide.

## 4. Verdict for Phase 0
- **Feasible to test** at AUD 10,000 with Stake (MID) and IBKR (LOW) costs.
- CommSec (HIGH) is kept as a stress test — expected to fail most settings.
- No profitability claim is made. This only shows costs are not an automatic deal-breaker.

## 5. Limits
- Fixed trade size (US$6,900); real size changes as the portfolio grows/shrinks.
- AUD/USD fixed at 0.69; real rate moves and adds currency gain/loss (affects buy-and-hold too).
- Tax (CGT) ignored — frequent selling creates taxable gains; buy-and-hold defers them. This
  favours buy-and-hold in real life. Noted as a known limit.

## 6. Open items
- Check Stake AU_Pricing.pdf for withdrawal FX + any other US fees (Phase 2).
