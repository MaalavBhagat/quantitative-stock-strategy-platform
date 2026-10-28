# PREREGISTRATION_V2.md — Phase 9 information strategies (H7), fixed BEFORE any of them touches real data

Version: **v2 — 2026-10-28** (git tag `prereg-v2`). Proposed by chat Claude 2026-10-28; approved by Goggy by running
prompt 24 (decisions 1–5 below approved 2026-10-28). Written after Phase 9 Steps 9.1–9.4 (data, features and the
availability rule — counts and timing only, no returns) and **before any C1, C2 or E1 run on real data**. Any later
change is logged in §9 **with date and reason, before the results it affects are seen**.

All results stay **SIMULATED, HISTORICAL**. This file does not replace research/PREREGISTRATION.md (v1, S0–S4); it adds
the Phase 9 strategies. Everything not stated here (costs, data, engine, split rule, record keeping) is exactly as in v1
and research/EXPERIMENT_PLAN.md.

## 1. Hypothesis H7 (research/RESEARCH_QUESTIONS.md)
Adding market context or company events (SEC 8-K filings) **improves results compared with the SAME strategy without
that information** — its "twin" — after costs, out of sample.

Few information strategies on purpose: every extra try raises the chance of a fluke.

## 2. The three information strategies (exact rules)
Common to all: decided at day T's close, filled at day T+1's open (engine rule); MAIN settings; dividends reinvested
(buy max affordable at the next open) only while holding and only once cash ≥ US$100. "SPY condition" values use SPY's
split-adjusted-as-of-T closes (strategies/indicators.py — the same method as the S4 trend filter), only SPY rows dated
≤ T. If SPY has no row for a day the stock trades, the run STOPS with an error (decision 5) — nothing is guessed.

| ID | Name | Twin | Settings |
|---|---|---|---|
| C1 | Market-trend gate | S0 Buy-and-hold | none (1 setting) |
| C2 | Market-gated pullback | S4-S2 Trend filter + pullback | the same 16 X × Y ∈ {2,3,4,5}% × {2,3,4,5}% |
| E1 | Earnings cool-off | S4-S2 Trend filter + pullback | the same 16 X/Y settings |

**C1 — Market-trend gate.** SPY condition on day T = SPY close > SPY 200-day average AND that average > its value 20
trading days earlier (the S4 "strong uptrend" test applied to SPY).
- Holding and the condition is false → sell all; wait in cash.
- In cash and the condition is true → buy max affordable.
- Holding and the condition is true → dividend reinvestment only (rule above).
- Day 1: buy only if the condition is true, otherwise start in cash (decision 4). Too little SPY history to compute the
  condition counts as "false" (cannot happen in practice: warm-up from 2015 for validation, 2008 for development).
- No parameters.

**C2 — Market-gated pullback.** S4-S2 exactly, except that a **rebuy** (in cash, close ≤ P × (1 − Y)) is NOT made while
SPY's close is ≤ its 200-day average (no slope test here). The running high P keeps updating while a rebuy is blocked;
when SPY is back above its average the normal rebuy test applies to that day's close. The day-1 entry buy is NOT
blocked (decision 3: the prompt blocks only rebuys, so C2 starts exactly like its twin). Sells are unchanged (S4-S2).

**E1 — Earnings cool-off.** S4-S2 exactly, except for a cool-off after each earnings event:
- Earnings event = an 8-K **or 8-K/A** filing with item 2.02 (an amendment is its own event and starts its own
  cool-off — decision 2). Filings exactly as saved (data/raw/sec/submissions, ≤ 2020-12-31); XOM's extra 2.02 filings
  count as filed (chat Claude ruling 2026-10-28).
- It becomes usable at the close of day U = the first NYSE trading day whose close (16:00 ET, 13:00 on early closes) is
  after the acceptance time (Phase 9 availability rule, DATA_SOURCES §12).
- **Cool-off = the closes of U and of the next trading day** (decision 1: U is cool-off day 1). At those two closes the
  sell signal and the rebuy signal are ignored. Signals resume at the close of the 3rd trading day.
  Example: earnings filed Tuesday after the close → usable Wednesday → Wednesday and Thursday ignored → Friday normal.
- Not blocked (decision 2): the day-1 entry buy and dividend reinvestment. The running high P keeps updating during a
  cool-off. Overlapping cool-offs simply join.

**Declared now, NOT tested:** event-risk exits on items 4.02 (restatement), 2.06 (impairment), 1.03 (bankruptcy) and
3.01 (delisting notice). In 2010–2020 there are 0 · 2 (MSFT 1, XOM 1) · 0 (AT&T's one 1.03 filing is a filer coding
error, reclassified — PROJECT_STATUS 2026-10-28) · 0 such filings (reports/phase9/context_and_events_2010-2020.md §4):
any result would be noise.

**AI labelling of 8-K text:** exploratory only, never part of any verdict.

## 3. Stocks
All 8 from research/INITIAL_UNIVERSE.md: AAPL, MSFT, KO, PG, XOM, INTC, T, SPY. SPY has no 8-K filings: E1 on SPY has
no events, so it trades exactly like its twin (reported, not removed). C1 / C2 on SPY use SPY's own condition.

## 4. Periods
| Period | Dates | Use |
|---|---|---|
| Development | 2010-01-04 → 2016-12-30 (warm-up from 2008) | build + sanity checks only — allowed to look, nothing judged |
| **Validation (judged)** | **2017-01-01 → 2020-12-31** (warm-up from 2015) | the H7 judgement below |
| Final test | 2021-01-01 → | **LOCKED (D8)** — one run for everything after Phase 9, under its own tag |

**Honest note:** the 2017–2020 prices were already seen when the twins were judged in Phase 6 (all REJECTED vs S0).
The information strategies are new, but the period is not fresh — the clean test is the one-time final run 2021+.

## 5. Settings
MAIN (decides the outcome) and sensitivity variants exactly as research/PREREGISTRATION.md §4. Each information strategy
and its twin always run on the same stock, period and settings.

## 6. Judgement — per information strategy, validation period, MAIN settings
R1–R6 exactly as the operational definitions in research/PREREGISTRATION.md §9 (2026-10-25), with the **TWIN as the
benchmark** instead of S0. excess(setting, stock) = information strategy total return − twin total return (same
setting for C2 / E1), USD, percentage points.
- **R1** median excess vs twin across the strategy's settings > 0 on ≥ 6 of 8 stocks.
- **R2** a setting passes if its mean excess vs twin across the 8 stocks is > 0; pass if ≥ 60% of settings pass
  (C2, E1: ≥ 10 of 16). **C1 has one setting, so R2 = "its one setting has mean excess vs twin > 0".**
- **R3** per stock, median across settings of (strategy max drawdown − twin max drawdown) ≥ −5 pp on ≥ 6 of 8 stocks.
- **R4** R1 and R2 re-evaluated at the combined stress setting (wide spread AND CommSec) for BOTH the strategy and its
  twin; pass at MAIN but fail under stress → "low-cost only" (not a pass).
- **R5** the strategy's final value minus the realised P&L (after fees) of its own 3 most profitable round trips (only
  round trips with realised P&L > 0, as in Phase 6); the twin unchanged; R1 + R2 must still pass.
- **R6** per stock, median round trips of the INFORMATION strategy across settings ≥ 10; fewer than 6 of 8 stocks →
  at most INCONCLUSIVE. (Expected: C1 switches rarely, so C1 can probably be INCONCLUSIVE at best — the rule is kept.)
- Verdict: SUPPORTED = R1–R6 all pass; REJECTED = R1 ≤ 3 of 8; INCONCLUSIVE = anything else.
- **H7 is SUPPORTED for a strategy only if it is SUPPORTED vs its twin.** Every result is also reported vs S0
  (descriptive only, no verdict).
- Any bug found during the runs → STOP, report, fix, log in §9, re-run ALL Phase 9 runs (never only the changed ones).

## 7. What is NOT allowed
- Changing any rule, setting, event definition or threshold after seeing any C1 / C2 / E1 result (log in §9 first).
- Adding information strategies or settings because of development results.
- Using event information before its availability close, or any SPY row dated after T.
- Opening the final test period before Goggy unlocks it (D8).

## 8. Records
As v1 §8: every run saves its full record under data/runs/ (git-ignored); reports contain summary numbers only.

## 9. Change log
- 2026-10-28: v2 created (prompt 24) with decisions 1–5 approved by Goggy; tagged `prereg-v2` before any C1, C2 or E1
  run on real data. Code: strategies/information.py (C1, C2, E1) + registry / config support;
  tests on synthetic data only (tests/strategies/test_information.py).
- 2026-10-28: pre-registered runs done (prompt 25) — 3,200 runs from clean commit 3b86c53 (2,800 validation incl. all 7
  variants + 400 development MAIN), 0 failed, 250 s. Twin consistency: all 952 twin runs identical to the Phase 6
  records. No bug found, no rule changed. Verdicts (reports/experiments/phase9_information_2017-2020.md): C1, C2, E1
  REJECTED vs their twins → H7 not supported.

