You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, research/PREREGISTRATION.md (tag prereg-v1),
research/INITIAL_UNIVERSE.md, DATA_SOURCES.md (§1, §7, §8, §9), src/quant_research/data/*, and Phase 6 in the roadmap.

STEP 0 (docs → main, BEFORE any new data):
a) PROJECT_STATUS.md: mark Phase 5 VERIFIED (2026-10-25) with: "Verified by chat Claude: tag prereg-v1 on e8152d8
   (2026-10-25 20:56 +1100), PREREGISTRATION.md unchanged since the tag, no 2017–2020 price files on disk; consistency
   proof over 144 runs + 5/5 reproductions accepted." CURRENT PHASE = Phase 6 (In progress).
b) PREREGISTRATION.md §9 change log — add, dated 2026-10-25, BEFORE any validation data is downloaded:
   "Regime rule (H5, Goggy's decision): each calendar year is labelled per stock from that stock's S0 (buy-and-hold,
   MAIN settings) total return for that year: ≥ +10% = UP, ≤ −10% = DOWN, otherwise SIDEWAYS. Partial first/last
   years use the days available. Decided before any 2017–2020 data exists." Also add it to §6 robustness checks.
c) Commit "Phase 5 verified; pre-registration change: regime rule" and push. (No new tag — the change log records it.)

TASK: Phase 6 data — get every file the pre-registration needs, validate it, run NOTHING else. Branch: `phase6-data`.
FIRST: show a short plan (list of downloads + number of API calls) and WAIT for OK.

PART A — Downloads (Tiingo, existing downloader + validation; stay well under 50 calls/hour)
- New stocks MSFT, KO, PG, INTC, T, SPY: warm-up 2008-01-01→2009-12-31, development 2010-01-01→2016-12-31,
  validation 2017-01-01→2020-12-31 (3 files each = 18 calls).
- AAPL, XOM: validation 2017-01-01→2020-12-31 (2 calls).
- RBA: the historical file(s) covering 2018–2020 (DATA_SOURCES §9), once, with meta.json.
- Do NOT download anything dated 2021 or later.

PART B — Validation (same 9 checks + yfinance cross-check as Step 2.3), for all 24 Tiingo files + joins
(warm-up → dev → validation must join with no gap/overlap on the NYSE calendar).
- Report `reports/data_validation/phase6_all_stocks_2008-2020.md`: per file ERROR/WARNING/INFO counts, splits found
  (date + snapped ratio), dividend counts, Yahoo agreement (days, splits, dividends, close % diffs), anything odd.
  Counts, dates and % only — no price series.
- Expected things to CHECK (from the data, not assumed): any splits in 2008–2020 for these 8 tickers (e.g. AAPL's later
  split implied by the 2.3 ratio check should appear in 2017–2020); SPY is a fund — confirm Tiingo's split/dividend
  fields behave the same; T and INTC corporate actions — anything Tiingo marks that our ledger doesn't support
  (spin-offs, special distributions) → list it, don't silently handle it.
- Any ERROR → stop and report; don't fix data.

PART C — Tradeability check (report only): confirm each of the 8 is offered on Stake Wall St, from Stake's own site
if findable, else mark UNVERIFIED. (SPY was UNVERIFIED in INITIAL_UNIVERSE.md.)

PART D — Lock check: confirm the D8 lock still refuses a config with any date ≥ 2021-01-01 (run the existing test +
one manual attempt, show the refusal message). Confirm no file on disk has data dated ≥ 2021-01-01.

RULES: no strategy, backtest, metric, chart or summary stat of 2017–2020 prices in this task — data quality only.
(Validation results come in prompt 17, against the frozen pre-registration.)

FINISH: pytest / ruff check / ruff format --check (real output) · key + data safety checks · commit → merge → push →
delete branch · DATA_SOURCES.md (new files, any new limitations) · PROJECT_STATUS (data step done; next = "chat Claude
checks the data report, then prompt 17: validation runs per PREREGISTRATION") · CHANGELOG.

COMPLETION REPORT: downloads + API calls used · validation table per stock · splits/dividends found · Yahoo agreement ·
unsupported corporate actions · Stake tradeability · lock check · tests + real output · open questions.
Do not claim anything is done unless the evidence supports it.
