You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, research/PREREGISTRATION.md, research/FINAL_TEST_OPTIONS.md,
research/RESEARCH_QUESTIONS.md (H7), research/IDEAS_FOR_LATER.md, DATA_SOURCES.md (§10–§11 SEC), and Phase 9 in the roadmap.

STEP 0 (docs → main): PROJECT_STATUS.md — mark Phase 8 VERIFIED (chat Claude's note is already in the file; keep it) and add
"DECISION 2026-10-27 (Goggy): Phase 9 scope = free sources only — market context from existing data + company events from
SEC 8-K filings (item codes + acceptance time). Optional AI labelling of 8-K text = exploratory side test later."
CURRENT PHASE = Phase 9. PHASE 9 PLAN: 23 = data + features + leakage rules (no backtests, no return analysis) ·
24 = pre-registration v2 of the Phase 9 strategies (before any backtest with the new data) · 25 = runs, comparisons
(9.5–9.6), Phase 9 check; then the one-time final test 2021+ for everything (Goggy unlocks).
Commit + push.

TASK: Phase 9 Steps 9.1 (market context features), 9.2 (event source), 9.3 (event classification), 9.4 (no temporal leakage).
Branch: `phase9-context-events`. Show a short plan and WAIT for OK.

HARD RULE FOR THIS PROMPT: build data + features + tests only. Do NOT compute returns around events, do NOT correlate any
feature with future returns, do NOT backtest anything. Looking at "what happened after events" before the Phase 9 rules are
pre-registered (prompt 24) would bias them. Counts and timing statistics only.

PART A — Market context features (9.1), point-in-time as of each close T, from data already on disk (2008–2020):
- Broad market: SPY above its 200-day average (yes/no) and SPY 200-day slope (same split-adjusted-as-of-T method as S4);
  SPY 20-day realised volatility (annualised).
- Stock: 60-day momentum (split-adjusted-as-of-T), 20-day realised volatility, volume vs its 50-day median.
- Each feature at T uses rows ≤ T only. Reuse indicators.py functions; no copies. Missing warm-up → "not available".
- Note in DATA_SOURCES: VIX and other market data not available in our free set → not used.

PART B — SEC 8-K events (9.2)
- Source: `https://data.sec.gov/submissions/CIK##########.json` (same CIKs as Phase 7, incl. the XOM historical CIK
  0000034088). Older filings may sit in extra JSON files listed inside it — follow them. Same User-Agent (.env
  SEC_USER_AGENT) and ≤ 1 request/second.
- VERIFY field names from the real JSON (expected but UNVERIFIED: form, filingDate, acceptanceDateTime, items,
  accessionNumber, primaryDocument). Keep forms 8-K and 8-K/A only.
- D8: drop every filing with filing or acceptance date ≥ 2021-01-01 AT DOWNLOAD; record counts in meta.json.
- TIMEZONE CHECK (critical): EDGAR acceptance times may be labelled "Z" but recorded in US Eastern time [UNVERIFIED].
  Prove which, using a known after-the-close filing: Apple's Q4 FY2019 earnings 8-K filed 2019-10-30 (Apple reports after
  the 4 pm ET close). If its acceptance time reads ~16:3x → stored as Eastern; ~20:3x → UTC. Document the evidence and
  convert everything to US/Eastern accordingly. Test the conversion incl. a daylight-saving date.

PART C — Event classification (9.3), rule-based from official item codes (no AI here):
- Map item codes to categories using the SEC's official Form 8-K item list (cite the SEC page you used):
  earnings (2.02) · deal signed (1.01) · deal completed (2.01) · leadership change (5.02) · shareholder vote (5.07) ·
  impairment (2.06) · restatement / non-reliance (4.02) · bankruptcy (1.03) · delisting notice (3.01) ·
  disclosure / other (7.01, 8.01) · exhibits only (9.01 alone → "exhibits only", not an event on its own) · anything
  else → "other" with the code kept. A filing can have several categories. Before 2004-era codes etc. — report any
  unrecognised codes, never guess.
- Report counts per company × category × year, and how many filings fall before the open / during trading / after the close
  (US/Eastern). Counts only — no prices.

PART D — No temporal leakage (9.4): the availability rule, written into DATA_SOURCES and tested:
- An event becomes usable for the strategy decision at the CLOSE of the first trading day D such that its acceptance time
  (US/Eastern) is before 16:00 ET on D. So: accepted 09:00 ET on D → usable at D's close (trade D+1 open);
  accepted 16:30 ET on D → usable at D+1's close (trade D+2 open); weekends/holidays → next trading day's close.
- 8-K/A amendments are separate events at their own acceptance time (never back-dated to the original).
- Extend the reusable look-ahead spy check: moving every event later by one day must not change any decision before it.
- Tests with synthetic filings: before open / intraday / after close / weekend / holiday / DST switch / amendment.

OUTPUT: `reports/phase9/context_and_events_2010-2020.md` (counts, timing table, item-code map with source, timezone
evidence; NO returns, NO prices). Store raw JSON under /data/raw/sec/submissions/ (git-ignored).

FINISH: pytest / ruff check / ruff format --check (real output) · safety (no data/.env/email; nothing ≥ 2021) · commit →
merge → push → delete branch · DATA_SOURCES (new section: SEC 8-K events + availability rule) · PROJECT_GUIDE (news/
module = events) · PROJECT_STATUS (Steps 9.1–9.4; next = "chat Claude checks the timezone evidence + counts, then
prompt 24: pre-registration v2") · CHANGELOG.

COMPLETION REPORT: verified JSON fields · timezone evidence (the Apple filing's raw time) · dropped-for-D8 counts ·
category counts table · unrecognised codes · timing table · features list with warm-up coverage · tests + output.
Do not claim anything is done unless the evidence supports it.
