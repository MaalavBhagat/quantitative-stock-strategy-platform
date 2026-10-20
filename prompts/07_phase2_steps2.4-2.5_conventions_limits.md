You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, DATA_SOURCES.md, research/EXPERIMENT_PLAN.md,
reports/data_validation/2010-2016_AAPL_XOM.md, and Phase 2 Steps 2.4–2.5 + completion criteria in the roadmap .txt.

STEP 0 (docs → main): commit research/EXPERIMENT_PLAN.md (withholding 15% verified), PROJECT_STATUS.md,
prompts/07_*.md — "Phase 2: Step 2.3 verified by chat Claude; withholding rate verified". Push.

TASK: Phase 2, Steps 2.4 (data conventions) + 2.5 (limitations), then the Phase 2 completion check.
Branch for code: `phase2-loader`.

PART A — DATA_CONVENTIONS section (add as §7 "Data conventions" in DATA_SOURCES.md — don't create a new file).
Short tables, plain language. Must cover (roadmap 2.4):
1. Timestamps: Tiingo gives midnight UTC → stored as plain US trading date. Any other time → ERROR.
2. Calendar: NYSE (XNYS, exchange_calendars 4.13.2). Data must match it exactly.
3. Currency: all Tiingo prices + dividends in USD [state evidence: US listings]; AUD only at portfolio start/end via FX.
4. Raw vs adjusted: trading + accounting use *_raw only. *_adj only for analysis/validation. Adjusted values change
   with download date → never compare adjusted values across downloads.
5. Splits: split_factor snapped to the nearest realistic ratio (as validation does); on the split date, share count
   × ratio and raw prices already reflect it. Exact rule to be built + tested in Phase 3.
6. Dividends: div_cash_usd is on the ex-date. Entitlement = holding shares at the close of the day BEFORE the ex-date.
   Cash credited on the ex-date [ASSUMPTION — Tiingo has no pay date; documented limitation]. Withholding 15% (W-8BEN,
   VERIFIED, link in EXPERIMENT_PLAN). Same rule for every strategy.
7. Missing data: never filled, interpolated or forward-filled. Validation ERROR → load stops.
8. Caching: a saved file is reused, never silently re-downloaded; re-download needs overwrite=True and creates a new
   download timestamp in meta.json.
9. Versioning: file name = ticker + requested dates; meta.json = download time, endpoint (no key), git commit.
   A run records which data files it used (filename + downloaded_at_utc).
10. Source disagreements: Tiingo is the source of truth; known Tiingo-vs-Yahoo differences are listed, not "fixed".
    List: XOM 2010-02-05, 2010-05-10 (Yahoo higher by next-day dividend), 2014-07-28 (+1.085%, unexplained).
    Note: chat Claude tried a 3rd source (Financial Datasets) — no credits; left unresolved, impact judged tiny.

PART B — the safe loader (code)
`src/quant_research/data/loader.py`: `load_prices(ticker, start, end) -> DataFrame`
- reads the saved CSV(s) under data/raw/tiingo/, checks meta.json exists, runs validation.py on the slice,
  raises a clear error if ANY ERROR issue, logs WARNINGs, returns only *_raw + div/split columns by default
  (`include_adjusted=True` to get adj columns for analysis).
- Never downloads. If the file is missing → clear error telling the user which script to run.
- Returns data provenance (file name, downloaded_at_utc, git commit) alongside the table (e.g. in df.attrs or a small dataclass).
- Does NOT enforce the D8 lock (that lives in the future runner, per D8) — but add a one-line docstring note saying so.
Tests (no internet): loads a fixture CSV + meta; missing file → clear error; missing trading day → raises;
WARNING-only data loads fine; adjusted columns excluded by default; provenance returned.

PART C — limitations (roadmap 2.5): add §8 "Known limitations" to DATA_SOURCES.md. Table: limitation · effect on results ·
what we do about it. Include at least: daily bars (intraday order unknown), no pay dates, no spread history,
partial delisted coverage (3,019 pre-2020 US enddates; Lehman/Enron/WaMu absent under checked symbols), adjusted
prices drift with download date, single-source primary data (Yahoo only as cross-check, 3 XOM close differences),
licence (internal use only), split factor not exact (7.000007).

PART D — housekeeping found in Step 2.3:
- PROJECT_GUIDE.md: mark `data/` module as created (list tiingo, storage, validation, crosscheck, loader).
- README.md: add the `uv run --group crosscheck ...` command and the download/validate scripts, one line each.

PART E — PHASE 2 CHECK (report only; do NOT mark Verified — chat Claude verifies):
Roadmap criteria, each met/not met with evidence:
retrieved reproducibly · data-quality checks exist · source limitations documented · pipeline handles missing
observations safely · initial dataset suitable for basic experiments.

FINISH: pytest / ruff check / ruff format --check (real output) · key + data safety checks · commit on branch →
merge → push → delete branch · PROJECT_STATUS.md (Steps 2.4 + 2.5, Phase 2 "ready for verification", next action =
"chat Claude verifies Phase 2, then Phase 3 Step 3.1 (cash accounting)") · CHANGELOG.md.

COMPLETION REPORT: files · conventions summary (10 lines max) · loader behaviour · limitations table ·
Phase 2 criteria table · tests + real output · open questions.
Do not claim anything is done unless the evidence supports it.
