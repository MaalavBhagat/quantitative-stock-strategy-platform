You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, research/EXPERIMENT_PLAN.md (all, esp. §3, §4, §6, §7, §10),
research/RESEARCH_QUESTIONS.md, research/INITIAL_UNIVERSE.md, reports/experiments/s1_s2_dev_2010-2016.md,
reports/experiments/s3_s4_dev_2010-2016.md, and Phase 5 Steps 5.5, 5.7 + completion criteria in the roadmap.

STEP 0 (docs → main): commit PROJECT_STATUS.md + prompts/15_*.md — "Phase 5: S3/S4 verified by chat Claude". Push.

TASK: close Phase 5 — Step 5.5 decision, Step 5.7 comparison, a PRE-REGISTRATION of the validation tests, Phase 5 check.
Docs + one small script only; no new strategies. Branch: `phase5-close`. Show a short plan, wait for OK.

PART A — Step 5.5 (hybrid): DECISION by Goggy 2026-10-25: NO new hybrid strategy. Reason: S4 already combines a trend
filter with the profit-target rules, and every extra variant tried on the same 2010–2016 data raises the chance of a
lucky fluke. Record in EXPERIMENT_PLAN §2 (S5: "not built — decision 2026-10-25") + §10 + PROJECT_STATUS decisions.

PART B — Step 5.7 comparison → `reports/experiments/phase5_comparison_dev_2010-2016.md` (SUMMARY NUMBERS ONLY)
1. Consistency proof (computed by a script from the saved run records, not typed): for EVERY run used in the two
   reports, show that initial capital, data files + download dates, period, broker, spread level, share mode, FX source,
   reinvest rule, min order and benchmark (S0 of the same ticker) are identical. Any difference → STOP and report it.
2. One roll-up table per ticker: strategy · settings tried · # beat S0 · median excess vs S0 · best and worst excess ·
   # stranded · median % days in cash · median round trips.
3. "Settings tried" total and an honest multiple-testing note in plain words: we tried 70 settings per stock
   (S1 16, S2 16, S3 6, S4-S1 16, S4-S2 16); with that many tries some will beat S0 by luck alone, so a dev-period win
   is a hypothesis, not evidence. That's why validation + robustness come next.
4. NO winner, NO ranking by return, NO ranking by number of trades (roadmap 5.7).

PART C — PRE-REGISTRATION → `research/PREREGISTRATION.md` (freeze BEFORE any 2017–2020 data is run)
Write down, now, exactly what Phase 6 will test and how it will be judged, so results can't move the goalposts:
- Strategies: S0, S1, S2, S3, S4-S1, S4-S2 — ALL grid settings (no pruning based on dev results).
- Stocks: all 8 from INITIAL_UNIVERSE.md (AAPL MSFT KO PG XOM INTC T SPY). Note: 6 still need data (Phase 6 task).
- Periods: validation 2017-01-01 → 2020-12-31; final test 2021+ stays locked (D8) until Goggy unlocks it after Phase 6.
- Settings: MAIN (Stake, normal spread, fractional, RBA FX, reinvest ≥ US$100) + sensitivity: tight/wide spread,
  IBKR + CommSec costs, whole shares.
- Judgement: EXPERIMENT_PLAN §6 rules, copied word for word (6 of 8 stocks; ≥ 60% of settings; drawdown ≤ 5 pp worse;
  wide spread + HIGH costs; best-3-trades removed; ≥ 10 round trips) — applied per strategy on the VALIDATION period,
  as a dress rehearsal for the final test. Outcomes: SUPPORTED / REJECTED / INCONCLUSIVE.
- Robustness checks to run (roadmap 6.3–6.6): parameter sensitivity heatmaps, cost sensitivity, best-3-removed,
  regime split (up / down / sideways years), consistency across stocks and years, dependence on a few trades.
- Explicit statement: the S4-S2 AAPL dev result (+217 pts best) gets NO special treatment.
- Any later change to this file → logged in its own change log with date + reason, before results are seen.
After committing, create a git tag `prereg-v1` on that commit and push the tag. Explain the tag to Goggy in one line.

PART D — PHASE 5 CHECK (report only; don't mark Verified): each strategy has explicit rules · strategies pass
independent tests (point to chat Claude's independent re-implementations: S1/S2 64 cells, S3/S4 76 cells + trade lists) ·
results reproducible (re-run 5 random saved configs from the records → identical final values; show them) ·
no winner chosen by trade count · all compared against S0.

FINISH: pytest / ruff check / ruff format --check (real output) · safety checks · commit → merge → push tag + main →
delete branch · PROJECT_STATUS (Phase 5 "ready for verification"; next = "chat Claude verifies Phase 5, then Phase 6
prompt 16: data for the other 6 stocks + validation-period data") · CHANGELOG.

COMPLETION REPORT: files · consistency proof result · roll-up tables · PREREGISTRATION summary + tag · reproducibility
check · Phase 5 criteria table · open questions.
SIMULATED, HISTORICAL, DEVELOPMENT PERIOD. Do not claim anything is done unless the evidence supports it.
