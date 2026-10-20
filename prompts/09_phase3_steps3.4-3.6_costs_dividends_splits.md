You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, research/BROKER_FEES.md, research/SMALL_ACCOUNT_FEASIBILITY.md,
research/EXPERIMENT_PLAN.md §1, DATA_SOURCES.md §7, src/quant_research/portfolio/*.py, and Phase 3 Steps 3.4–3.6 in the roadmap.

STEP 0 (docs → main): commit PROJECT_STATUS.md + prompts/09_*.md — "Phase 3: Steps 3.1–3.3 verified by chat Claude". Push.

TASK: Phase 3, Steps 3.4 (transaction costs), 3.5 (dividends), 3.6 (splits). Branch: `phase3-costs-dividends-splits`.
FIRST: show Goggy a short plan in plain words and WAIT for OK.

PART A — Cost model (3.4) → `src/quant_research/execution/costs.py` (the execution/ module is created now)
Pure functions, Decimal only, no ledger changes. Every number below must appear in ONE config table in code with its
source link copied from BROKER_FEES.md, or the label [ASSUMPTION].
1. Brokerage fee per trade, `fee_usd(broker, trade_value_usd, quantity)`:
   - stake: US$3.00 if value ≤ US$30,000 else 0.01% of value.
   - ibkr_fixed: US$0.005 × shares, min US$1.00, max 1% of trade value.
   - commsec_standard: max(US$5.00, 0.12% of value) PLUS per-trade FX 0.55% of value (CommSec converts every trade).
     Return the parts separately (brokerage, fx) AND the total, so reports can show where costs come from.
2. Spread + slippage per side: tight 0.02% / normal 0.05% / wide 0.10% [ASSUMPTION]. Applied to the PRICE:
   buy fill = reference × (1 + s), sell fill = reference × (1 − s). Return both the fill price and the spread cost in USD
   (= |fill − reference| × qty) so it can be reported separately from fees.
3. FX at start/end: `aud_to_usd(amount_aud, usd_per_aud, fee_rate)` and `usd_to_aud(...)`. Fee 0.55% for Stake + CommSec,
   ~0.002% (min US$2) for IBKR manual conversion (BROKER_FEES). The RATE is always passed in explicitly — no hard-coded rate.
   Rounding against us (D2). Note in PROJECT_STATUS: historical AUD/USD rate source still to choose (Phase 4 question).
Tests (hand-calculated, exact): Stake on US$6,900 → 3.00; on US$40,000 → 4.00 · IBKR 30 shares → 1.00 (minimum);
IBKR case where the 1% cap binds · CommSec on US$6,900 → brokerage 8.28 + FX 37.95 = 46.23 · spread buy/sell fill prices
and spread cost · FX both directions with rounding against us · unknown broker → error.
Consistency test: one Stake round trip (buy then sell same reference price, normal spread) on ~US$6,900 costs ≈0.19% of
value (SMALL_ACCOUNT_FEASIBILITY.md) — assert within a small tolerance and say in a comment that the doc was a rough estimate.

PART B — Dividends (3.5) → add to the ledger
`apply_dividend(ex_date, ticker, amount_per_share_usd, withholding_rate=Decimal("0.15"))`:
- Entitlement = shares held at the close BEFORE ex_date → must be called BEFORE any trade on ex_date (enforce: refuse if
  a trade for that ticker is already logged on ex_date, with a clear error).
- gross = shares × amount (amount is per RAW share as of that date — DATA_SOURCES §7); withholding rounds UP (against us);
  net = gross − withholding, rounded DOWN; net < US$0.01 → not credited, logged as such (BROKER_FEES §4).
- Track separately: dividends_gross_usd, withholding_usd, dividends_net_usd. Log a DIVIDEND ledger entry.
- Dividends never change cost basis (income, tracked separately from price returns — roadmap 3.5).
- Double-counting guard: the same (ticker, ex_date) dividend can't be applied twice → error.
- No holding on ex_date → no entry, no error (log at debug).
Tests: 10 shares × $2.65 → gross 26.50, withholding 3.975→3.98, net 22.52 · fractional holding · buy on ex-date not entitled
(order rule) · sell on ex-date still entitled · double-apply refused · tiny dividend under 1 cent not credited · zero holding.

PART C — Splits (3.6) → add to the ledger
`apply_split(date, ticker, ratio)` — called at the START of the day, before dividends and trades (order: split → dividend → trades).
- ratio snapped with the SAME function validation.py uses (7.000007 → 7). Reuse it, don't copy it.
- quantity × ratio; cost basis unchanged; average cost ÷ ratio. Cash unchanged. Log a SPLIT entry.
- Forward splits: always fine. Reverse splits (ratio < 1) that would create a fraction in WHOLE mode → raise
  NotImplementedError("cash-in-lieu not modelled") and list it in DATA_SOURCES §8 as unsupported. In fractional mode,
  round down to 6 dp and log the dropped fraction.
- Same split twice → error.
Tests: AAPL-like 7:1 — hold 10 shares, cost basis US$6,003.00 → 70 shares, cost basis 6,003.00, avg 85.757142857…;
then a sell after the split gives the right realised P&L · split on a ticker not held → nothing happens · reverse split cases.

PART D — Invariants (extend the existing seeded random test)
After every step: initial − spent − fees + received + dividends_net == cash (exactly), and
sum over tickers of shares == shares implied by the log (buys − sells, × split ratios).

PART E — Daily event order: write it in PROJECT_GUIDE §4 as a rule: split → dividend → trades (at open). One line why.

FINISH: pytest / ruff check / ruff format --check (real output) · mutation check (break the withholding rounding once and
the split cost basis once; show tests catch it; restore) · safety checks · commit → merge → push → delete branch ·
PROJECT_GUIDE (`execution/` created) · PROJECT_STATUS (Steps 3.4–3.6, next = prompt 10) · CHANGELOG.

COMPLETION REPORT: files · cost config table (with sources) · how dividends + splits work in plain words · tests + real output ·
mutation-check result · assumptions · open questions.
Do not claim anything is done unless the evidence supports it.
