You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, research/EXPERIMENT_PLAN.md (§2 S3 + S4, §3, §10),
research/RESEARCH_QUESTIONS.md (H3, H4), reports/experiments/s1_s2_dev_2010-2016.md, src/quant_research/{data,backtesting,strategies}/,
and Phase 5 Steps 5.3, 5.4, 5.7 in the roadmap.

STEP 0 (docs → main): commit PROJECT_STATUS.md + prompts/14_*.md — "Phase 5: S1/S2 verified by chat Claude". Push.

TASK: Phase 5, Steps 5.3 (S3 mean reversion) + 5.4 (S4 trend filter), development period only. Branch: `phase5-s3-s4`.
FIRST: show Goggy a short plan and WAIT for OK.

PART A — Indicator warm-up data (so indicators exist from day 1 of trading)
- A 200-day average needs ~10 months of history. Download a WARM-UP file for AAPL + XOM: 2008-01-01 → 2009-12-31
  (2 Tiingo calls, same downloader, same validation). Warm-up rows are used ONLY to compute indicators; the engine
  trades and measures performance from the run's start date (2010-01-04) exactly as before. Using earlier data for
  indicators is not look-ahead (it's the past).
- Loader: support loading the warm-up file + main file as one continuous table (dates must join with no gap/overlap
  per the NYSE calendar → else ERROR). Engine: new config `warmup_start`; strategy history includes warm-up rows;
  equity/metrics start at `start`. S0, S1, S2 results must be UNCHANGED (they ignore warm-up) — prove it by re-running
  one S0 and one S1 run and comparing to the saved reports.

PART B — Split-adjusted-as-of-T prices (critical, avoids a hidden look-ahead)
- Indicators can't use Tiingo's close_adj: it already contains splits AND dividends that happen AFTER day T (e.g. AAPL's
  later ~4:1 split). That would be look-ahead.
- Build `split_adjusted_closes(history)`: from close_raw and split_factor in the history up to T only, divide earlier
  closes by every split that happened up to T (snapped ratios). Not dividend-adjusted.
- Tests: a split on day 10 makes day 1–9 values ÷ ratio; a split AFTER T doesn't change anything up to T (spy-style test).

PART C — S3 mean reversion (H4)
- z_T = (P_T − mean of last w values) ÷ std of last w values, P = split-adjusted-as-of-T closes, window includes day T,
  std = sample std (ddof = 1). [state this choice in EXPERIMENT_PLAN §2]
- Starts invested (day-1 close → buy at day-2 open), like S1/S2.
- Invested and z ≥ +k → sell ALL next open. In cash and z ≤ −k → buy max_affordable next open.
- Dividend top-ups while invested, as S1/S2 (≥ US$100).
- Grid: k ∈ {1.5, 2.0, 2.5} × w ∈ {20, 50} = 6 per ticker (EXPERIMENT_PLAN §3).

PART D — S4 trend filter (H3)
- Strong uptrend on day T = P_T > SMA200_T AND SMA200_T > SMA200_(T−20) (P = split-adjusted-as-of-T closes).
- S4 = S1 or S2 rules, but NO SELL signal while in a strong uptrend. Rebuy rules unchanged.
- Run it on ALL 16 X/Y combos for both bases (S4-S1 and S4-S2) — not a hand-picked "best region".
  This is broader than EXPERIMENT_PLAN §3 (≤ 8) and avoids cherry-picking: log it in §10.
- Splits: E, S, P levels handled exactly as in S1/S2 (÷ ratio on split day).

TESTS: hand-worked tiny series for z-score, SMA200 slope (use a shorter window in tests via a parameter, e.g. 5 and 2),
S3 sell/rebuy cycle, S4 blocks a sell in an uptrend and allows it otherwise, warm-up join, split-adjusted-as-of-T.
Every strategy passes the reusable look-ahead spy check. Mutation check: (1) use close_adj instead of split-adjusted-as-of-T
→ a test must fail; (2) compute z with the window ENDING at T+1 → spy check must fail; (3) drop the "SMA rising" part
of the filter → a test must fail. Restore after each.

REAL RUNS (development 2010-01-04 → 2016-12-30, MAIN settings — same as prompt 13):
- S3: 6 × 2 tickers = 12. S4-S1: 16 × 2 = 32. S4-S2: 16 × 2 = 32. Total 76.
- Report `reports/experiments/s3_s4_dev_2010-2016.md`, SUMMARY NUMBERS ONLY, same columns as the S1/S2 report,
  X×Y excess-return tables for S4-S1 and S4-S2, a k×w table for S3, and:
  * a side-by-side "did the filter help?" table: for each X/Y, S4-S1 minus S1 and S4-S2 minus S2 (percentage points).
  * a one-page roll-up across S1–S4 per ticker: how many settings beat S0, stranded counts, typical days in cash.
- Appendix: full trade list for S3 AAPL k=2.0 w=20 and S4-S1 AAPL X=5% Y=5% (dates, side, reference open, fill, fee,
  shares, cash after) so chat Claude can re-compute them independently.
- Top of report: "SIMULATED, HISTORICAL, DEVELOPMENT PERIOD — exploration only, not evidence". No winner picked.
  No validation (2017–2020) or final (2021+) runs.
- Add an honest "caveats" paragraph: results on 2 stocks over 7 years; S1 XOM "wins" were mostly from sitting in cash
  while XOM fell in 2014–2016 (a regime effect, not proof of skill) — check whether the same applies to any S3/S4 "wins"
  by reporting % days in cash next to every positive cell.

FINISH: pytest / ruff check / ruff format --check (real output) · safety checks · commit → merge → push → delete branch ·
EXPERIMENT_PLAN §2 + §10 · PROJECT_GUIDE · PROJECT_STATUS (Steps 5.3, 5.4 done; next = "chat Claude verifies trade lists,
then prompt 15: Step 5.5 hybrid decision + 5.7 comparison + Phase 5 check") · CHANGELOG.

COMPLETION REPORT: files · rules in plain words · warm-up proof (S0/S1 unchanged) · tables · "did the filter help" ·
tests + real output · mutation checks · open questions.
SIMULATED, HISTORICAL, DEVELOPMENT PERIOD. Do not claim anything is done unless the evidence supports it.
