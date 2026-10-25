# FINAL_TEST_OPTIONS.md — what to do with the locked final-test period (2021+)

Roadmap Step 6.7 / end of Phase 6. **Nothing here unlocks anything or makes a decision.** The final-test period
(2021-01-01 → latest full year) stays LOCKED (D8, PROJECT_GUIDE.md) until Goggy decides. This file only lays out the
two options neutrally so the choice can be made — and logged — before any 2021+ data is touched.

Background: all five strategies were REJECTED on the 2017–2020 validation period under the pre-registered rules
(reports/experiments/validation_2017-2020.md §1; reports/RESULTS_SUMMARY.md).

## Option (a) — run the final test once, unchanged
Run all strategies and settings exactly as pre-registered (research/PREREGISTRATION.md, tag `prereg-v1.1`) on
2021-01-01 → latest full year, ONE time, and report whatever comes out.

**Pros**
- Completes the original plan (EXPERIMENT_PLAN §6 judges H1 on the final test period).
- A third, never-seen period is the strongest check available here: it shows whether the "no" holds in a different
  market (2021+ includes years unlike 2017–2020).
- The pipeline, rules and reports already exist; the run is mostly mechanical.

**Cons**
- With every strategy already REJECTED on validation, the outcome adds limited new information about H1; a SUPPORTED
  result on the final test alone would conflict with validation and be hard to interpret.
- Once used, the hold-out is spent: it can never again be an unseen test for any future idea.
- Extra work and data are needed first (below), and each is a chance to make a mistake.

**Must be done first (before any 2021+ data is downloaded)**
1. **AT&T (T) 2022 spin-off** (WarnerMedia, public knowledge; PROJECT_STATUS open item 2). The ledger does not
   support spin-offs (DATA_SOURCES.md §8). Choose ONE and log it: exclude T and report 7 stocks (rules rescaled,
   e.g. "6 of 8" → a stated fraction of 7), or model the spin-off (new code + tests), or another written rule.
   Also check every other stock for unsupported 2021+ corporate actions — with a rule fixed before looking.
2. **RBA AUD/USD 2021+ rates** — not downloaded (PROJECT_STATUS; DATA_SOURCES.md §9).
3. **Tiingo 2021+ prices** for all 8 stocks, plus the same validation checks. The downloader currently refuses END ≥
   2021-01-01, so this needs a deliberate, logged code change.
4. Confirm the period end ("latest full year") as an exact date.

## Option (b) — do not run it; keep the hold-out for a NEW pre-registered hypothesis
Leave 2021+ locked. Report the project's answer from validation alone ("REJECTED on validation, final test not
run"). Keep 2021+ as an unseen test for a future, different idea that gets its own pre-registration first.

**Pros**
- The hold-out stays clean and valuable for a genuinely new question.
- Avoids spending effort and data on a test whose likely contribution to H1 is small.
- No new code for spin-offs and no new downloads are needed now.

**Cons**
- H1 was formally to be judged on the final test (EXPERIMENT_PLAN §6); the answer stays "rejected on validation
  (a dress rehearsal)", not a final-test verdict. That must be stated plainly.
- Validation covers one 4-year period dominated by rising years (18 of 32 stock-years UP; validation report §5).
- A future hypothesis must be truly new and written down before looking; otherwise the hold-out is not clean anyway.

## What must be decided and logged in PREREGISTRATION §9 BEFORE any 2021+ data is downloaded
- Which option, (a) or (b), with date and Goggy's approval.
- If (a): the exact period dates; how T (and any other unsupported corporate action) is handled; whether any rule
  thresholds are rescaled for fewer stocks; that the rules, settings and stock list are otherwise unchanged from
  `prereg-v1.1`; that the test is run ONCE and every result is reported.
- If (b): that 2021+ stays locked, and that any future use requires a new pre-registration (its own tag) first.
- In both cases: a new git tag on the commit with the §9 entry, before any download.

## Decision
DECISION 2026-10-26 (Goggy): final test 2021+ stays LOCKED until after Phase 9; then it is run ONCE for S1–S4 and any Phase 9 model together, under a new pre-registration tag. Until then nothing dated ≥ 2021-01-01 is downloaded, stored or summarised.
(Neither (a) nor (b) as written: the run is deferred, not cancelled.)

## Change log
- 2026-10-26: file created (prompt 18, Step 6.7). Options only — no decision, no unlock.
- 2026-10-26: Goggy's decision recorded (final test deferred to after Phase 9).
