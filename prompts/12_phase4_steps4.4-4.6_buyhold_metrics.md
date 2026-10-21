You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, research/EXPERIMENT_PLAN.md (§1, §2 S0, §5 metrics, §8),
DATA_SOURCES.md §9 (RBA), src/quant_research/backtesting/*, and Phase 4 Steps 4.4–4.6 + completion criteria in the roadmap.

STEP 0 (docs → main): commit PROJECT_STATUS.md + prompts/12_*.md — "Phase 4: Steps 4.1–4.3 verified by chat Claude". Push.

TASK: Phase 4, Steps 4.4 (buy-and-hold), 4.5 (metrics), 4.6 (edge cases) + RBA exchange rates + Phase 4 check.
Branch: `phase4-buyhold-metrics`. FIRST: show Goggy a short plan and WAIT for OK. (The Part B question is already answered — see below.)

PART A — RBA AUD/USD rates (replace the temporary config fields)
- From the RBA historical-data page (DATA_SOURCES §9), find the daily exchange-rate file(s) covering 2010–2016
  (and later years if in the same file). Report the exact file names, format and column for USD. Download ONCE to
  /data/raw/rba/ with a .meta.json (URL, download time). If the format needs a new package (e.g. xls reader), add the
  smallest one and say why.
- `src/quant_research/data/fx.py`: `load_usd_per_aud()` + `usd_per_aud_on(day)` = latest RBA rate dated ≤ day
  (DATA_SOURCES §9 timing rule). Gap > 5 calendar days → ERROR. Validate: positive, sorted, no duplicates, plausible
  range 0.40–1.20 (else ERROR).
- Config: `fx_source: rba` (default) or `fixed` (keeps the old fields, for tests). Start conversion uses the rate for the
  day of the first trade; end conversion uses the last day's rate.
- Tests with a tiny made-up FX fixture (no real RBA data in tests).

PART B — S0 buy-and-hold (4.4) → `src/quant_research/strategies/buy_and_hold.py` (strategies/ module created now)
- Day 1 close: order "max_affordable" → fills at day 2 open (our T close → T+1 open rule). Document that the
  EXPERIMENT_PLAN wording "buy at the first open" becomes "first possible open after the first close" and log it in
  EXPERIMENT_PLAN §10 change log.
- Dividend reinvestment: after dividend cash arrives, buy max_affordable at the next open — BUT a US$3 fee on a ~US$25
  dividend costs ~12%. GOGGY DECIDED (2026-10-21): option (b) — reinvest only when cash ≥ US$100.
  Make it a config value `reinvest_min_cash_usd: "100"`; this rule applies to EVERY strategy later.
  Record it in EXPERIMENT_PLAN §1 + §10 change log and PROJECT_STATUS decisions.
- Must pass the reusable look-ahead spy check from prompt 11.

PART C — Metrics (4.5) → `src/quant_research/metrics/performance.py` (floats are fine here — D1)
From the daily equity + order/fill logs: final value (USD + AUD), total return, CAGR (calendar days / 365.25),
max drawdown (+ peak and trough dates), annualised volatility (daily returns × √252), Sharpe (rf = 0, EXPERIMENT_PLAN §5),
worst calendar year, total fees, total spread cost, dividends gross / withholding / net, % of days fully in cash,
number of round trips, liquidation value. AUD equity = USD equity ÷ usd_per_aud of that day; final AUD = after the
end FX fee. Tests: tiny hand-calculated equity series for EVERY metric (working in comments, exact or tight tolerance).

PART D — Real runs (development period only — allowed under D8)
- S0 on AAPL and on XOM, 2010-01-04 → 2016-12-30, Stake, normal spread, fractional, AUD 10,000, RBA FX.
- Save full run records under /data/runs/ (git-ignored). Write `reports/runs/s0_dev_2010-2016.md` with SUMMARY
  NUMBERS ONLY (no daily prices or equity series — licence), plus the config used and data provenance.
- INDEPENDENT SANITY CHECK (anti-hallucination): compute separately, without the engine,
  close_adj[last] / close_adj[day of first fill] − 1 from the Tiingo file (adjusted prices are allowed for analysis).
  This is roughly "buy-and-hold with dividends reinvested, no costs, no tax". Our S0 USD return should be close but a
  bit LOWER. Report both numbers and explain the gap in plain words (fees, spread, 15% withholding, reinvestment rule,
  entry at day-2 open). If S0 is HIGHER than the adjusted-price return, or the gap is large (> ~3 percentage points
  over 7 years), STOP and investigate before reporting.

PART E — Edge cases (4.6), synthetic data
- Rising, falling, sideways series; a gap up and a gap down between close and next open; a split + dividend on the
  same day while holding; a day where cash is just short of one share in whole mode.
- Ambiguous bar: `resolve_intrabar(open, high, low, close, buy_level, sell_level)` → when BOTH levels are inside the
  bar, assume the WORSE order for us (CLAUDE.md rule). Tested now; note that S1–S4 currently use the next-open model,
  so this is for later limit-style variants.

PART F — PHASE 4 CHECK (report only; don't mark Verified): buy-and-hold correct · orders follow the documented model ·
accounting integrates · look-ahead controls in place · passes synthetic tests.

FINISH: pytest / ruff check / ruff format --check (real output) · mutation check (remove the withholding from S0's
dividends once → the sanity-check gap must change visibly; break max drawdown once → metric tests fail; restore) ·
safety checks · commit → merge → push → delete branch · PROJECT_GUIDE (strategies/, metrics/ created) ·
PROJECT_STATUS (Steps 4.4–4.6, Phase 4 "ready for verification", next = "chat Claude verifies Phase 4, then Phase 5
Step 5.1 (S1 profit target)") · CHANGELOG.

COMPLETION REPORT: RBA file details · S0 results table (AAPL, XOM: final USD, final AUD,
CAGR, max drawdown + dates, volatility, Sharpe, fees, dividends net, days in cash) · sanity check (both numbers + gap
explanation) · edge cases · tests + real output · mutation check · Phase 4 criteria table · open questions.
These are SIMULATED, HISTORICAL results on the development period — say so at the top of the report.
Do not claim anything is done unless the evidence supports it.
