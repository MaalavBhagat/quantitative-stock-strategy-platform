You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_STATUS.md, research/PREREGISTRATION.md, research/RESEARCH_QUESTIONS.md,
research/EXPERIMENT_PLAN.md, reports/experiments/{s1_s2_dev_2010-2016,s3_s4_dev_2010-2016,phase5_comparison_dev_2010-2016,
validation_2017-2020}.md, DATA_SOURCES.md §8, and Phase 6 Step 6.7 + completion criteria in the roadmap.

STEP 0 (docs → main): PROJECT_STATUS.md — add:
"VALIDATION VERIFIED by chat Claude 2026-10-26: all 3,976 run records from one clean commit 786e699, all end 2020-12-31.
 prereg-v1.1 tagged 21:36 before the CommSec fix (21:38, logged in §9) and the run script (21:39). Independent
 re-implementation reproduced all 8 S0 finals to the cent (AAPL 34,304.60 · MSFT 26,943.60 · KO 10,492.79 ·
 PG 13,034.01 · XOM 3,865.36 · INTC 10,600.24 · T 5,861.44 · SPY 12,681.98), Appendix B (S4-S2 AAPL 2/4: 23 fills,
 22,849.41) and Appendix C (S1 KO 3/3: 10 fills, 8,688.15) exactly. Verdict: S1, S2, S3, S4-S1, S4-S2 all REJECTED."
Commit "Phase 6 validation verified by chat Claude" + push.

TASK: Phase 6 Step 6.7 (document unsuccessful experiments) + Phase 6 check. Docs only (plus a small script if a number
is needed — never type a number by hand). Branch: `phase6-close`. Show a short outline first and wait for OK.

PART A — `reports/RESULTS_SUMMARY.md` (the project's main findings page; plain English, for a non-expert reader;
1–2 pages; every number copied from a generated report with its section reference):
1. The question (H1 v2, one sentence) and the answer: REJECTED on the 2017–2020 validation period, under rules fixed in
   advance (tags prereg-v1 / v1.1).
2. What was tested: 5 strategies, 70 settings per stock, 8 stocks, 3,976 validation runs, 7 cost/spread variants.
3. Headline table: per strategy — verdict, R1 count, median excess vs S0, % of settings stranded, median days in cash.
4. WHY it failed — evidence-based, one short paragraph each, citing the tables:
   - Sell-and-wait strategies get stranded in uptrends (S1: stranded in X/Y; ~98% days in cash on AAPL/MSFT).
   - Dev winners didn't persist (S4-S2 AAPL 14/16 → 2/16; XOM S1/S4-S1 "wins" were cash during a falling market).
   - Gains depend on a few trades (top-3 share table).
   - Costs: CommSec / stress roughly multiply the shortfall (cost table).
   - Regimes: some help in DOWN years (S3 +13.7 median) but lose in UP years, and most years were UP (18 of 32).
5. What the evidence does NOT show (limits): survivorship (all 8 are survivors), 8 stocks only, US large caps, daily bars,
   no tax, assumed spreads, single-source data, Tiingo bad bar (dev only).
6. What this means for a small Australian investor (factual, no advice): costs + currency facts from BROKER_FEES /
   S0 AUD vs USD results. Include "not financial advice" line.
7. H2, H5, H6 — "not judged (no pre-registered rule)" + the descriptive numbers, clearly labelled as descriptive.

PART B — `research/FAILED_EXPERIMENTS.md` (roadmap 6.7): a log of every experiment that failed or was set aside, with
date, what, result, likely reason, evidence link: S1–S4 validation verdicts; the S0 sanity check that first tripped
(and the rule change); the split-as-dip bug; the CommSec double-FX bug; the aborted 227-dirty-record batch; the
one-cent withholding mismatch; the 5% → 1% sanity-rule change. Mistakes are part of the record — keep them.

PART C — Final-test options for Goggy (write them; DO NOT unlock, DO NOT decide):
In `research/FINAL_TEST_OPTIONS.md`, list neutrally, with pros/cons:
  (a) Run the final test 2021+ once, unchanged, for all strategies — completes the scientific record (a confirmation
      of the rejection, or a surprise to report honestly). Needs first: handling of unsupported 2021+ corporate
      actions (AT&T's 2022 spin-off — e.g. exclude T and report 7 stocks, or model it), RBA 2021+ data, Tiingo 2021+ data.
  (b) Don't run it — validation already rejected everything; the hold-out stays unused for a future, NEW pre-registered
      hypothesis.
  State what must be decided and logged in PREREGISTRATION §9 BEFORE any 2021+ data is downloaded.

PART D — PHASE 6 CHECK (report only; don't mark Verified): out-of-sample results reported · cost sensitivity documented ·
parameter sensitivity documented · limitations explicit · results not presented as proof of future profitability.

FINISH: pytest / ruff check / ruff format --check (real output) · safety checks · commit → merge → push → delete branch ·
README.md: add a 3-line "Findings so far" linking RESULTS_SUMMARY.md · PROJECT_STATUS (Phase 6 "ready for verification";
next = "chat Claude verifies Phase 6; Goggy chooses a final-test option") · CHANGELOG.

COMPLETION REPORT: files · the headline table · the "why it failed" points (one line each) · final-test options summary ·
Phase 6 criteria table · tests + real output.
Do not claim anything is done unless the evidence supports it.
