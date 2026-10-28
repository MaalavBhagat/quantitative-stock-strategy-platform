You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_STATUS.md, research/PREREGISTRATION_V2.md (tag prereg-v2), research/PREREGISTRATION.md §9,
reports/experiments/validation_2017-2020.md, reports/phase9/context_and_events_2010-2020.md, and Phase 9 Steps 9.5–9.6 +
completion criteria in the roadmap.

STEP 0 (docs → main): PROJECT_STATUS.md — add "Prompt 24 verified by chat Claude 2026-10-28: prereg-v2 tag on 4497870
(16:27:46 +1100); no C1/C2/E1 run records exist before it; labels shipped (display only)." Commit + push.

TASK: Phase 9 Steps 9.5 (compare with simpler models) + 9.6 (incremental value) — the pre-registered runs. Branch:
`phase9-runs`. Show a short plan with run counts + estimated time and WAIT for OK.
RULES: exactly PREREGISTRATION_V2. Start from a clean commit; do not look at, print or summarise any result until ALL
runs have finished (keep scripts OUTSIDE the project folder while runs are going — lesson from the aborted batch).
Any bug → stop, fix, log in PREREGISTRATION_V2 change log, re-run ALL.

RUNS (validation 2017-01-03 → 2020-12-31, same data/FX/warm-up as the Phase 6 runs; D8 lock on):
- Information strategies: C1 (8 stocks × 1) + C2 (8 × 16) + E1 (8 × 16) = 264, at MAIN + the same 6 variants
  (tight, wide, ibkr, commsec, whole, stress) = 1,848.
- Twins in the SAME batch and commit: S0 (8) + S4-S2 (8 × 16) = 136 × 7 = 952. CONSISTENCY CHECK: their MAIN results must
  equal the saved Phase 6 validation values to the cent (e.g. S0 AAPL 34,304.60; S4-S2 AAPL 2/4 22,849.41). Any
  difference → STOP and report before judging anything.
- Development 2010-01-04 → 2016-12-30, MAIN only, for C1/C2/E1 + twins on all 8 stocks (sanity + dev-vs-validation table;
  not judged).
Save under /data/runs/phase9/ (git-ignored).

REPORT → `reports/experiments/phase9_information_2017-2020.md` (script-generated, summary numbers only, labels with names):
1. Verdict table per information strategy vs its TWIN: R1–R6 counts + VERDICT (SUPPORTED / REJECTED / INCONCLUSIVE).
   Top line: "SIMULATED, HISTORICAL, VALIDATION 2017–2020 — prices already seen for the twins; the clean test is the final
   2021+ run."
2. 9.5 compare with simpler models: each information strategy vs twin AND vs S0 per stock (median excess, best/worst,
   round trips, days in cash, stranded).
3. 9.6 incremental value: median (information − twin) per stock and per cost variant; top-3-trades dependence; by regime
   (Phase 6 labels); dev vs validation.
4. H7 answer in one plain line per strategy, from the verdicts only.
5. Appendix: full trade lists for C1 AAPL and E1 KO X3%/Y3% (validation, MAIN) + the 8 C1 finals, for chat Claude's
   independent re-check; and for every E1 trade, the earnings event (accession, acceptance time NY) that caused any
   skipped signal days.

PART D — AI labelling side test (EXPLORATORY, never part of any verdict, optional — ask Goggy first):
- Download the primary documents of 40 randomly chosen (fixed seed) 2010–2020 8-Ks from our 7 companies (≤1 req/s,
  SEC_USER_AGENT). Have Claude Code classify each into our categories from the TEXT ONLY (item codes hidden), store the
  labels + the exact instruction used + model name/date in reports/phase9/ai_labels_sample.md, then compare with the
  official item codes: agreement rate + every disagreement listed for Goggy to spot-check 5 by hand.
- Purpose: shows how reliable AI reading of filings is. No trading use.

PHASE 9 CHECK (report only; don't mark Verified): news sources + limitations documented · historical decisions use only
available information (events spy check, SPY spy check, availability rule tests) · AI interpretations distinguished from
verified facts · added complexity justified by evidence or labelled exploratory.

FINISH: pytest / ruff check / ruff format --check (real output) · safety · commit → merge → push → delete branch ·
RESULTS_SUMMARY.md: add a short "Phase 9: does extra information help?" section from the verdicts · dashboard shows the
new runs with names · PROJECT_STATUS (Phase 9 "ready for verification"; next = "chat Claude verifies; then Goggy decides
on the one-time final test 2021+") · CHANGELOG.
COMPLETION REPORT: run counts + time · twin consistency check result · verdict table · H7 lines · incremental-value
highlights · appendix pointers · AI side test result (if run) · Phase 9 criteria · tests + output.
Do not claim anything is done unless the evidence supports it. Report results whatever they are.
