You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, DATA_SOURCES.md, research/INITIAL_UNIVERSE.md,
research/RESEARCH_QUESTIONS.md (Q4.11, H6), reports/RESULTS_SUMMARY.md, and Phase 7 in the roadmap.

STEP 0 (docs → main): PROJECT_STATUS.md — mark Phase 6 VERIFIED (already written by chat Claude, keep it) and add:
"DECISION 2026-10-26 (Goggy): final test 2021+ stays LOCKED until after Phase 9; then it is run ONCE for S1–S4 and any
Phase 9 model together, under a new pre-registration tag. Until then nothing dated ≥ 2021-01-01 is downloaded, stored or
summarised." Log the same in research/FINAL_TEST_OPTIONS.md and PREREGISTRATION §9. CURRENT PHASE = Phase 7.
Commit "Phase 6 verified; final test deferred to after Phase 9" + push.

TASK: Phase 7, Steps 7.1 (financial indicators) + 7.2 (trading indicators) — data + calculations only, no ranking yet.
Branch: `phase7-fundamentals`. Show a short plan and WAIT for OK. Phase 7 plan: 19 = data + indicators · 20 = screening
method (7.3), selection-bias handling (7.4), comparison (7.5), Phase 7 check.

PART A — Source: SEC EDGAR XBRL API (chosen by chat Claude 2026-10-26)
- Official: https://www.sec.gov/search-filings/edgar-application-programming-interfaces — free, no API key.
  companyfacts: `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (10-digit CIK with leading zeros).
- Fair access (https://www.sec.gov/os/accessing-edgar-data): max 10 requests/second; declare a User-Agent with a name
  + contact email. Put it in .env as SEC_USER_AGENT (Goggy types it himself — never hard-code an email). Stay far
  below the limit (e.g. 1 request/second).
- Look up each company's CIK from SEC's official ticker list (one download) — report the CIK for each.
- Companies: AAPL, MSFT, KO, PG, XOM, INTC, T. SPY is a fund (no company financials) → excluded from 7.1, kept in 7.2.
- Licence/terms: record what SEC says about reuse in DATA_SOURCES (new §10); store under /data/raw/sec/ (git-ignored).
- D8 + point-in-time: each XBRL fact carries a filing date. Keep ONLY facts with filed date ≤ 2020-12-31; drop the rest
  AT DOWNLOAD (like the RBA trim) and record how many were dropped in meta.json. Verify the field names from the real
  JSON (don't assume) and document them.

PART B — Point-in-time rule (Step 7.4 groundwork; critical)
- A financial fact may be used on trading day T only if its filing date < T (strictly before — the filing may come
  after the close). Restatements: use the value as first filed until a later filing replaces it, from that later
  filing's date. Never use a value before it was public. Tests for both rules (synthetic facts).

PART C — Financial indicators (7.1), per company, as of each fiscal year (annual 10-K values), point-in-time:
profitability (net margin, return on assets), cash flow (operating cash flow, free cash flow = OCF − capex, FCF margin),
debt (debt to equity or debt to assets — say which XBRL tags you used), liquidity (current ratio), earnings stability
(std dev of yearly EPS growth over the last 5 available years). For each: the exact XBRL tags, fallbacks if a company
uses a different tag, and "MISSING" when not available — never guess or fill. Report a coverage table (company × indicator
× year: found / fallback / missing).

PART D — Trading indicators (7.2), from the Tiingo raw data we already have (2010–2020 only):
liquidity (median daily dollar volume = close_raw × volume_raw, per year), volatility (annualised, from
split-adjusted-as-of-T closes), typical daily range (high−low)/close, max drawdown per year, dividend yield (trailing
12-month dividends ÷ close). Spreads: not available in free data → state it; use the assumed levels only.

TESTS: synthetic XBRL-like JSON fixtures (no internet): tag mapping + fallbacks, filed-date filter, point-in-time
availability (fact filed on T is NOT usable on T), restatement handling, each ratio's arithmetic, missing → MISSING.
Trading-indicator arithmetic on tiny series.

OUTPUT: `reports/screening/indicators_2010-2020.md` — coverage table, CIKs, tag choices, indicator values per company
per year (these are derived accounting/trading statistics, not price series — OK to commit; no daily prices).
Top: "Descriptive data for Phase 7 screening — not a recommendation."

FINISH: pytest / ruff check / ruff format --check (real output) · safety checks (no data/, .env, User-Agent email in
files) · commit → merge → push → delete branch · DATA_SOURCES §10 · PROJECT_GUIDE (screening/ module) · PROJECT_STATUS
(Steps 7.1–7.2; next = "chat Claude checks a few indicators against the filings, then prompt 20") · CHANGELOG.

COMPLETION REPORT: CIKs · XBRL field names found · facts dropped by the 2020-12-31 trim · coverage table · tag choices ·
a sample (AAPL + KO, one year each) of the raw facts used for every indicator, with filing dates, so chat Claude can
check them against the filings · tests + real output · open questions.
Do not claim anything is done unless the evidence supports it.
