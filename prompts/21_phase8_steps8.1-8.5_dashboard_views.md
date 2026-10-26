You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md (§2 dashboard row: "view saved results; no logic of its own"), PROJECT_STATUS.md,
reports/RESULTS_SUMMARY.md, reports/experiments/validation_2017-2020.md, reports/screening/screening_2010-2020.md,
src/quant_research/{backtesting,metrics,screening}/, and Phase 8 in the roadmap.

STEP 0 (docs → main): PROJECT_STATUS.md — mark Phase 7 VERIFIED (2026-10-26) with:
"Verified by chat Claude: SCREENING_METHOD.md committed alone in f66e267 (16:57) before the scoring code + scores in
3ef65c2 (17:01); the 5 positive strategy–stock pairs of 40 re-computed from the run records (S4-S1 INTC +63.4, S3 T +25.2,
S3 XOM +16.9, S3 INTC +3.6, S4-S2 MSFT +1.9) — identical. All 4 roadmap criteria met." CURRENT PHASE = Phase 8.
Commit "Phase 7 verified by chat Claude" + push.

PHASE 8 PLAN: prompt 21 = read-only views (8.1 overview, 8.2 company research, 8.4 performance, 8.5 trade explorer) ·
prompt 22 = 8.3 strategy lab (runs via the validated engine), 8.6 reports, 8.7 export, Phase 8 check.

TASK: Phase 8 Steps 8.1, 8.2, 8.4, 8.5 — a Streamlit app that VIEWS saved results. Branch: `phase8-dashboard-views`.
Show a short plan (pages + what each shows + new dependencies) and WAIT for OK.

RULES
- Streamlit (roadmap default). Add the smallest set of dependencies (streamlit + one charting library — say which and why)
  in a separate uv group `dashboard`, so the core package doesn't depend on them.
- The app ONLY reads: saved run records (/data/runs/…), the loader (raw prices, never downloads), saved reports, screening
  outputs. All numbers come from existing modules (metrics/, screening/) — the app computes nothing of its own beyond
  formatting. If a number isn't saved or computable by an existing function, show "not available", never estimate.
- D8: nothing dated ≥ 2021-01-01 can be loaded or shown (it doesn't exist on disk — add a guard anyway + a test).
- Licence: runs locally only (`localhost`). Don't deploy it. README must say why (Tiingo + RBA licences).
- Every page shows a banner: "SIMULATED, HISTORICAL — not financial advice" and the period (development / validation).
- Assumptions visible on every results page: broker, spread level, share mode, FX source, reinvest rule, data files +
  download dates, code commit (from the run record).
- Failed experiments are NOT hidden: verdicts with REJECTED shown as prominently as anything else; link
  FAILED_EXPERIMENTS.md.

PAGES
1. Overview (8.1): pick period (dev / validation), stock, strategy, setting → starting capital, test period, key results
   from the run record (final USD + AUD, CAGR, max drawdown, Sharpe, excess vs S0), the pre-registered verdict table, and
   a link to RESULTS_SUMMARY.
2. Company research (8.2): per company: quality score + sub-scores + "why" line per year (from screening outputs);
   trading profile (volatility, dollar volume, range, dividend yield); MISSING / CONFLICT shown with reasons.
3. Performance (8.4): equity curve vs S0 (USD, with AUD toggle), drawdown chart, cash vs invested over time, cumulative
   dividends + fees + spread cost — all from the saved equity/fills/orders files.
4. Trade explorer (8.5): table of fills (date, side, reference open, fill, fee, shares, realised P&L) + orders incl.
   REJECTED / EXPIRED with reasons; click a trade → its effect on cash and position (from the saved files).

TESTS (no Streamlit server needed): put data-shaping logic in plain functions under src/quant_research/dashboard/ and
test them: reading a run record, building the equity/drawdown tables, D8 guard, "not available" behaviour, the banner
text. Plus ONE consistency test: for the S4-S2 AAPL X2% Y4% validation run, the dashboard's final value, max drawdown
and trade count equal the run record + validation report Appendix B (22,849.41; 23 fills).
Smoke check: start the app headless, load each page once, confirm no errors (show the command + output).

FINISH: pytest / ruff check / ruff format --check (real output) · safety checks · commit → merge → push → delete branch ·
README: "How to open the dashboard" (one command) + licence note · PROJECT_GUIDE (dashboard/ module) · PROJECT_STATUS
(Steps 8.1, 8.2, 8.4, 8.5; next = "chat Claude reviews screenshots, then prompt 22") · CHANGELOG.

COMPLETION REPORT: pages + what each shows · dependencies + why · how numbers are sourced (no new maths) · consistency
test result · smoke-check output · 4 screenshots saved to /data/screenshots/ (git-ignored: they show licensed prices)
so Goggy can paste them to chat Claude · tests + output · open questions.
Do not claim anything is done unless the evidence supports it.
