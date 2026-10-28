# FINAL_TEST_PREREG.md — the ONE-TIME final test 2021–2025, fixed BEFORE any 2021+ data exists

Version: **v1 — 2026-10-28** (git tag `prereg-final`). Decisions by Goggy 2026-10-28 (prompt 26), written and tagged
**before any data dated 2021-01-01 or later has been downloaded**. This file adds to — never replaces —
research/PREREGISTRATION.md (S0–S4, tag `prereg-v1.1`) and research/PREREGISTRATION_V2.md (C1, C2, E1, tag `prereg-v2`).
Any later change is logged in §8 with date and reason, before the results it affects are seen.

The final test is run **ONCE**. Every result is reported, whatever it is. No tuning; no re-runs except to fix a bug
(stop → fix → log here with evidence → re-run ALL runs).

## 1. Period
- **First NYSE trading day of 2021 → 2025-12-31** (EXPERIMENT_PLAN §4: "2021 → latest full year"; 2025 is the latest
  full year on 2026-10-28). Configs use start 2021-01-01 / end 2025-12-31; trading and metrics start at the first
  session (2021-01-04; 1 January is a holiday).
- Indicator warm-up from the 2019–2020 rows of the files already on disk (warm-up start 2019-01-01) — warm-up rows are
  seen by indicators only, never traded or measured.
- AUD 10,000 converted to USD at the RBA rate for the first fill day (latest RBA rate dated ≤ that day; same rule as
  every earlier run); the end value converted back at the last day's rate.

## 2. Stocks — 7
AAPL, MSFT, KO, PG, XOM, INTC, SPY.
- **T (AT&T) is EXCLUDED:** its 2022 WarnerMedia spin-off cannot be modelled by our ledger (unsupported corporate
  action, DATA_SOURCES §8). T is not downloaded for 2021+.
- Any OTHER unsupported corporate action found in the 2021–2025 data of the 7 (spin-off, merger, special distribution,
  a split factor that is not a simple ratio, a reverse split leaving a fraction) → **STOP and ask Goggy BEFORE any run**
  (a data issue, decided without looking at results).

## 3. Strategies and settings — unchanged
- S0, S1, S2, S3, S4-S1, S4-S2 exactly as research/PREREGISTRATION.md §1 (71 settings per stock).
- C1, C2, E1 exactly as research/PREREGISTRATION_V2.md §2 (33 settings per stock; twins S0 and S4-S2 are shared).
- E1 earnings events: SEC 8-K / 8-K/A filings with item 2.02 accepted up to 2025-12-31, same availability rule.
- MAIN settings + the same 6 variants (tight, wide, ibkr, commsec, whole, stress) — research/PREREGISTRATION.md §4.
- Runs: (71 + 33) × 7 stocks = 728 per variant × 7 variants = **5,096 runs**, saved under /data/runs/final/.

## 4. Judgement — rules unchanged, thresholds scaled to 7 stocks
Exactly the operational definitions of research/PREREGISTRATION.md §9 (S1–S4 vs S0) and research/PREREGISTRATION_V2.md
§6 (C1, C2, E1 vs their twins), except the stock-count thresholds:
| Rule | 8 stocks (before) | 7 stocks (final test) |
|---|---|---|
| R1 beats the benchmark (median excess > 0) | ≥ 6 of 8 | **≥ 6 of 7** |
| R3 drawdown within 5 pp (median) | ≥ 6 of 8 | **≥ 6 of 7** |
| R6 median round trips ≥ 10 | ≥ 6 of 8 | **≥ 6 of 7** (else at most INCONCLUSIVE) |
| REJECTED | R1 ≤ 3 of 8 (loses on 5+) | **R1 ≤ 2 of 7** (loses on 5+) |
| R2 settings (mean excess across the stocks > 0) | ≥ 10 of 16 · S3 ≥ 4 of 6 · C1 its one setting | unchanged (mean across the 7) |
| R4 stress (wide + CommSec), R5 best-3 removed | as defined | unchanged |
Verdict per strategy: SUPPORTED = R1–R6 all pass; REJECTED = R1 ≤ 2 of 7; INCONCLUSIVE = anything else.
Regime rule unchanged (each stock-year from that stock's S0 return: ≥ +10% UP, ≤ −10% DOWN, else SIDEWAYS).
H1 is judged on this period as EXPERIMENT_PLAN §6 intended (S1 vs S0); H3 (S4 vs S1/S2), H4 (S3), H7 (C1/C2/E1 vs
twins) from their verdicts; H2, H5, H6 descriptive only (no pre-registered verdict rule).

## 5. Unlock (D8)
- `final_test_unlocked: true` is set ONLY in the final-test run configs, by Goggy's decision 2026-10-28.
- The data downloaders may accept end dates up to 2025-12-31 for this task only — the code change is logged
  (CHANGELOG, DATA_SOURCES). Nothing dated after 2025-12-31 is downloaded or kept.

## 6. After the run, 2021–2025 is USED
Anything later run on 2021–2025 is **not out-of-sample** any more (also written in DATA_SOURCES and
FINAL_TEST_OPTIONS). There is no unseen period left in this project's data after this test.

## 7. Records
Every run saves its full record under /data/runs/final/ (git-ignored). Reports contain summary numbers only (licence).
All runs from one clean commit; the run script lives outside the project folder while runs are saving.

## 8. Change log
- 2026-10-28: v1 written and tagged `prereg-final` before any 2021+ data was downloaded (prompt 26).
