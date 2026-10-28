# FAILED_EXPERIMENTS.md — what did not work, and our own mistakes (kept on purpose)

Roadmap Step 6.7. Every entry: **what** · **result** · **likely reason** · **evidence**. Nothing here is deleted or
softened later; a mistake that was fixed stays in the record. Results are SIMULATED, HISTORICAL. Numbers are copied
from the linked reports / status entries, not typed from memory.

## A. Strategy results (validation 2017–2020, pre-registered rules `prereg-v1.1`)

| Date | What | Result | Likely reason | Evidence |
|---|---|---|---|---|
| 2026-10-25 | S1 fixed profit target, 16 X/Y settings × 8 stocks | **REJECTED** — beat S0 on 0/8 stocks (R1), 0/16 settings (R2); median −43.9 pp | Sells early, then waits for a dip that often never comes: stranded in cash at the end in 96/128 runs, median 89% of days in cash | reports/experiments/validation_2017-2020.md §1, §2; validation_headline_2017-2020.md |
| 2026-10-25 | S2 pullback from peak | **REJECTED** — 0/8 stocks, 0/16 settings; median −12.1 pp | Same stranding in rising markets (47/128 runs); costs bite (−29.0 pp with CommSec) | same, §1, §4 |
| 2026-10-28 | C1 Market-trend gate (SPY above its rising 200-day average) vs Buy-and-hold (S0) | **REJECTED** — better on 1/8 stocks; median −43.4 pp vs twin | Steps out of the stock 12 times in 2017–2020 and misses rebounds (16% of days in cash); helped only in DOWN years (+3.5 pp median) | reports/experiments/phase9_information_2017-2020.md §1–§3 |
| 2026-10-28 | C2 Market-gated pullback vs Trend filter + pullback (S4-S2) | **REJECTED** — better on 1/8 stocks (KO +39.5 pp); median −0.5 pp | Blocking buy-backs while SPY is weak kept it in cash during the 2020 rebound (AAPL −100 pp, MSFT −89 pp) | same, §2 |
| 2026-10-28 | E1 Earnings cool-off vs Trend filter + pullback (S4-S2) | **REJECTED** — better on 3/8 stocks; median +0.0 pp | Rarely changes anything (78/128 runs trade exactly like the twin); the AAPL gain (+22.6 pp) did not generalise | same, §2–§3 |
| 2026-10-28 | **FINAL TEST 2021–2025** (one-time, prereg-final): S1, S2, S3, S4-S1, S4-S2 vs S0 and C1, C2, E1 vs twins, 7 stocks | **All 8 REJECTED** — R1 2/7, 2/7, 2/7, 2/7, 0/7 (S1–S4) and 2/7, 1/7, 2/7 (C1, C2, E1); no verdict changed from validation | Same pattern as validation: selling early misses strong rises (XOM, AAPL, MSFT); rules only helped on falling / flat stocks (INTC, PG) and in DOWN years | reports/experiments/FINAL_TEST_2021-2025.md §1–§6 |
| 2026-10-25 | S3 mean reversion (6 k/w settings) | **REJECTED** — 3/8 stocks, 0/6 settings; median −19.4 pp | Helps in DOWN years (+13.7 pp median) but loses in UP years (−16.6); 18 of 32 stock-years were UP | same, §1, §5 |
| 2026-10-25 | S4-S1 trend filter + S1 | **REJECTED** — 1/8 stocks, 0/16 settings; median −32.2 pp | Filter does not stop S1's stranding (93/128 runs) | same, §1, §2 |
| 2026-10-25 | S4-S2 trend filter + S2 (incl. the AAPL development "winner") | **REJECTED** — 1/8 stocks, 1/16 settings; median −2.3 pp | Development wins did not persist: AAPL 14/16 settings → 2/16 (1 of 14 kept); depended on a few large dips | same, §1, §6; reports/experiments/s3_s4_dev_2010-2016.md |

## B. Checks that tripped, and rule changes

| Date | What | Result | Likely reason | Evidence |
|---|---|---|---|---|
| 2026-10-21 | S0 sanity check vs the adjusted-price return, rule "gap about 3 points" | **Tripped** — AAPL gap 7.06 pts, XOM 5.14 pts | Not a bug: the adjusted series assumes no tax; 15% dividend withholding explains 5.43 / 4.32 pts, fees + spread the rest. Goggy accepted after investigation; rule changed to a **5% relative** limit | PROJECT_STATUS.md decisions 2026-10-21; reports/runs/s0_dev_2010-2016.md |
| 2026-10-25 | 5% relative sanity rule judged too loose (chat Claude review) | **Rule tightened** to: S0 below the adjusted return, AND the no-withholding what-if within **1% relative** — AAPL −0.39%, XOM −0.52% (pass); numbers unchanged | A 5% limit could hide a real bug | commits f82f146, f6f6ba6; reports/runs/s0_dev_2010-2016.md (sanity section); CHANGELOG.md |

## C. Our own bugs and process mistakes

| Date | What | Result | Likely reason | Evidence |
|---|---|---|---|---|
| 2026-10-20 | One-cent withholding mismatch in the independent golden scenario | Code gave withholding 5.38 (15% of exact gross 35.80157931), answer key 5.37 (15% of cents gross 35.80) | Rounding order not specified. Goggy chose the key's rule (cents first); the **code** was changed, the expected values were never edited | reports/accounting/golden_scenario.md; PROJECT_STATUS.md Phase 3; commit f162ea5 |
| 2026-10-25 | Split treated as a dip (S1, development runs) | AAPL 7:1 split on 2014-06-09 caused a fake rebuy on 2014-06-10 (pre-split lowest close 222.25 vs level 215.89) | Remembered entry/sell/peak prices stayed in pre-split units. Fix (Goggy): divide E, S, P by the snapped split ratio; all 64 development runs re-run | research/EXPERIMENT_PLAN.md §10; PROJECT_STATUS.md Phase 5; commit 987c81c |
| 2026-10-25 | CommSec currency fee counted twice | Found **before** any validation run; fixed and tested | CommSec converts inside every trade (0.55%), yet a separate start/end conversion fee was also charged. Now 0 for CommSec | research/PREREGISTRATION.md §9; commit 6ccc0dd |
| 2026-10-25 | Validation batch aborted: 227 records marked dirty | Batch stopped; 1,836 records set aside (not deleted) in data/runs/validation_ABORTED_20261025_227-dirty-records; ALL 3,976 runs re-run clean (0 failed) | I (Claude) created a script file inside the repo while runs were saving, so the git-dirty flag turned on for 227 of the 1,671 records checked (1,836 had been saved by the time the batch stopped). Lesson: create no repo files during a run | PROJECT_STATUS.md Steps 6.1–6.6; commit 786e699 |

## Change log
- 2026-10-26: file created (prompt 18, Step 6.7).
