You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, research/EXPERIMENT_PLAN.md (§2 S1 + S2, §3 grid, §4 periods,
§5 metrics, §6 decision rules), research/RESEARCH_QUESTIONS.md (H1 v2, Q4.4–Q4.7), reports/runs/s0_dev_2010-2016.md,
src/quant_research/{backtesting,strategies,metrics}/, and Phase 5 Steps 5.1, 5.2, 5.6, 5.7 in the roadmap.

STEP 0 (docs → main) — chat Claude couldn't reach the files (computer still setting up), so do these edits:
a) Save this prompt as prompts/13_phase5_steps5.1-5.2_s1_s2.md.
b) PROJECT_STATUS.md: mark Phase 4 VERIFIED (2026-10-25) and add:
   "PHASE 4 VERIFIED by chat Claude 2026-10-25: rebuilt S0 independently from the raw Tiingo CSVs with separate code
   (no engine) → AAPL US$37,069.58, XOM US$13,954.00, net dividends 2,239.50 / 2,027.33, fees 51 / 42, no-withholding
   what-if 313.56% / 57.95% — all identical to the engine to the cent. AUD 50,917.02 re-derived from liquidation value.
   All 5 roadmap criteria met."
   CURRENT PHASE = Phase 5 (In progress); CURRENT TASK = Steps 5.1–5.2 (prompt 13).
c) Commit — "Phase 4 verified by chat Claude". Push.

STEP 1 — tighten the S0 sanity check (chat Claude's review of your 5% rule)
The 5% relative limit is too loose: a real bug worth ~4% would pass. The tax drag depends on dividend yield, so
check costs separately from tax. New rule, two parts:
  (1) S0 return must be LOWER than the adjusted-price return (unchanged);
  (2) the no-withholding what-if must be within 1.0% RELATIVE of the adjusted return (it is −0.39% AAPL, −0.52% XOM:
      (1+3.1356)/(1+3.1519)−1 and (1+0.5795)/(1+0.5877)−1). Only costs + entry timing are left in that gap, so 1% is
      plenty while still catching bugs.
Update the script + report wording + PROJECT_STATUS decision ("sanity rule changed 2026-10-25, approved by Goggy").
Re-run S0 — numbers must be identical; only the check text changes. Commit separately.

TASK: Phase 5, Steps 5.1 (S1 fixed profit target) + 5.2 (S2 pullback from peak), configurable (5.6), compared on the
DEVELOPMENT period only (5.7). Branch: `phase5-s1-s2`. FIRST: show Goggy a short plan and WAIT for OK.

EXACT RULES (EXPERIMENT_PLAN §2 — don't change them; any ambiguity → ask Goggy, then log in §10):
S1 — Fixed profit target
- Day 1 close → buy max_affordable at day 2 open. Entry price E = fill price of that ENTRY buy.
  Dividend top-up buys (cash ≥ US$100 while invested) do NOT change E.
- While invested: close ≥ E × (1 + X) → sell ALL at next open. Sale price S = that sell's fill price.
- While in cash: close ≤ S × (1 − Y) → buy max_affordable at next open. New E = that fill price.
- If the price never falls Y below S, stay in cash to the end (honest "missed upside").
- No dividend top-ups while in cash (there's no position).
S2 — Pullback from peak
- Same entry + sell rule as S1.
- After a sale, P = highest CLOSE from the sale-fill day onwards. Rebuy when close ≤ P × (1 − Y). New E = fill price.
Parameters (5.6): X, Y in YAML config, as decimals, from the grid {0.02, 0.03, 0.04, 0.05} only (EXPERIMENT_PLAN §3).
Validate: outside the grid → error unless `grid_override: true` (then logged as exploratory).

TESTS
- Hand-calculated synthetic series for S1 AND S2 (write the day-by-day working in comments): at least one full
  sell → rebuy cycle, one "stranded in cash" case, one case where S2 rebuys HIGHER than it sold and S1 doesn't rebuy.
- Both pass the reusable look-ahead spy check (incl. no same-day fills).
- E unchanged by top-ups; no top-ups in cash; thresholds use close and fills use next open.

METRICS to add (EXPERIMENT_PLAN §5, Q4.4–Q4.7): round trips; stranded episode (sold and never rebought before the end)
yes/no + days; longest cash spell (days); % days in cash; dividends missed vs S0 (S0 net − strategy net); excess return
vs S0 (USD and AUD); "best 3 trades removed" result is Phase 6 — leave a TODO, don't fake it.

REAL RUNS — development period 2010-01-04 → 2016-12-30 ONLY (D8 lock stays off for this)
- S1 and S2 × 16 X/Y combos × AAPL, XOM = 64 runs + the 2 S0 runs. MAIN settings only (Stake, normal spread,
  fractional, RBA FX, reinvest ≥ US$100). Cost/spread sensitivity is Phase 6 — don't do it now.
- Save run records under /data/runs/. Report `reports/experiments/s1_s2_dev_2010-2016.md` with SUMMARY NUMBERS ONLY:
  per ticker, an X×Y table of excess return vs S0 (USD) for S1 and for S2; plus a table per run: final USD, final AUD,
  CAGR, max drawdown, round trips, % days in cash, stranded (y/n), longest cash spell, fees + spread paid, dividends
  missed. Top of report: "SIMULATED, HISTORICAL, DEVELOPMENT PERIOD — exploration only, not evidence (EXPERIMENT_PLAN §4)".
- Do NOT pick a winner, do NOT tune further, do NOT run the validation (2017–2020) or final (2021+) periods.
  Just describe patterns honestly (e.g. "S1 on AAPL was stranded in N of 16 runs") — roadmap 5.7: never prefer a
  setting because it traded more.
- INDEPENDENT CHECK: pick 1 S1 run (AAPL, X=0.05, Y=0.05) and list every trade (date, side, reference open, fill,
  fee, shares, cash after) in the report appendix so chat Claude can re-compute it by hand from the raw CSV.
  (Trade dates + our fill prices only — these are our simulated fills, not a price series.)

FINISH: pytest / ruff check / ruff format --check (real output) · mutation check (make S1 sell at the SAME day's close
once → spy check fails; make S2 use P = sale price instead of the running high → its tests fail; restore) ·
safety checks · commit → merge → push → delete branch · PROJECT_GUIDE · PROJECT_STATUS (Steps 5.1, 5.2, 5.6 done;
next = "chat Claude verifies the S1 trade list, then prompt 14: S3 mean reversion + S4 trend filter") · CHANGELOG.

COMPLETION REPORT: files · rules in plain words · the X×Y excess-return tables · stranded counts · tests + real output ·
mutation check · anything ambiguous you had to ask about · open questions.
SIMULATED, HISTORICAL, DEVELOPMENT PERIOD. Do not claim anything is done unless the evidence supports it.
