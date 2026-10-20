You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, src/quant_research/portfolio/*.py,
src/quant_research/execution/costs.py, and Phase 3 Steps 3.7–3.8 + completion criteria in the roadmap.

STEP 0 (docs → main): commit PROJECT_STATUS.md + prompts/10_*.md — "Phase 3: Steps 3.4–3.6 verified by chat Claude". Push.

TASK: Phase 3, Steps 3.7 (portfolio valuation) + 3.8 (independent accounting tests), then the Phase 3 check.
Branch: `phase3-valuation`. FIRST: show Goggy a short plan in plain words and WAIT for OK.

PART A — Valuation (3.7)
`Portfolio.valuation(as_of: date, close_prices_usd: dict[str, Decimal]) -> Valuation` returning SEPARATELY:
cash_usd · per-ticker quantity, average cost, cost basis, close price, market value, unrealised P&L ·
total market value · total portfolio value (= cash + market value; nothing else is modelled) · realised P&L ·
dividends gross / withholding / net · total fees · (spread cost is tracked by execution, not the ledger — note it).
Rules:
- Market value per ticker = quantity × close, rounded DOWN to cents (conservative; it's a value we'd receive).
- Unrealised P&L = market value − cost basis (cost basis exact; result shown to cents — see display rule).
- Missing close price for a held ticker → error (never value at 0 or at an old price silently).
- Close prices come in as Decimal (use to_decimal_price at the edge). Valuation never changes the ledger.
- DISPLAY RULE (closes chat Claude's open note): internal values stay exact Decimal; anything shown or saved in reports
  is rounded to cents with ROUND_HALF_EVEN, and only at the display step. Write this in PROJECT_GUIDE §4.

PART B — Golden scenario (3.8): an INDEPENDENT answer key
Chat Claude computed the numbers below separately (own code, using only the rounding rules in our docs — not your code).
Build `tests/accounting/test_golden_scenario.py` that runs this scenario through YOUR code (costs.py + ledger + valuation)
and asserts every number EXACTLY. If any number differs: DO NOT change the expected value to match the code. Stop, show
both numbers, explain which rule differs, and ask Goggy. Ticker "TEST", made-up prices (no real data in tests).
Settings: fractional mode, broker stake, spread normal (0.05%), withholding 0.15.

| Step | Action | Expected |
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

Also add the same table + a one-paragraph plain-English story to `reports/accounting/golden_scenario.md`
(made-up prices, so safe to commit). Include this observation: the stock gained in USD terms, but AUD out (9,627.14) is
below AUD in (10,000) because AUD/USD moved 0.69 → 0.75 plus two FX fees — currency matters for an Australian investor.

PART C — more independent checks (3.8)
- Whole-share version of the same scenario: compute the expected numbers BY HAND in the test comments first
  (show the working), then assert. Say clearly in the report that chat Claude did NOT pre-compute this one.
- Valuation tests: missing close → error; valuation doesn't change ledger; two tickers; after a partial sell.
- Invariant: total portfolio value at a close == cash + Σ(qty × close rounded down) for the seeded random test.

PART D — PHASE 3 CHECK (report only; don't mark Verified): roadmap criteria met / not met with evidence —
cash balances correct · share quantities correct · dividends consistent · corporate actions don't silently corrupt
holdings · transaction costs included · valuation independently validated. List unsupported items honestly.

FINISH: pytest / ruff check / ruff format --check (real output) · mutation check (break market-value rounding once,
break unrealised P&L once; show tests catch it; restore) · safety checks · commit → merge → push → delete branch ·
PROJECT_STATUS (Steps 3.7–3.8, Phase 3 "ready for verification", next = "chat Claude verifies Phase 3, then Phase 4
Step 4.1 timeline") · CHANGELOG.

COMPLETION REPORT: files · valuation in plain words · golden scenario: every row matched? (show any mismatch) ·
whole-share scenario working · tests + real output · mutation check · Phase 3 criteria table · open questions.
Do not claim anything is done unless the evidence supports it.
