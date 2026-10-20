You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, DATA_SOURCES.md.

STEP 0: docs to main — commit prompts/06_*.md + PROJECT_STATUS.md ("Phase 2: Step 2.2 verified by chat Claude"). Push.
Then delete the merged branch `phase2-tiingo-download` (local, and remote if it exists). Explain in one line.

TASK: Phase 2, Step 2.3 — Validate the downloaded data. Branch: `phase2-data-validation`.
Data in scope: data/raw/tiingo/AAPL_2010-01-01_2016-12-31.csv and XOM_... (already downloaded — do NOT re-download from Tiingo).

PART A — validation module `src/quant_research/data/validation.py`
Return a structured report: list of issues, each with ticker, date, check name, severity (ERROR / WARNING / INFO), message.
ERROR = the run must stop. WARNING = logged, allowed. INFO = noted. Never silently fix data (PROJECT_GUIDE §6).
Checks:
1. Calendar (D4): compare dates with the NYSE calendar (`exchange_calendars`, XNYS; fallback `pandas_market_calendars`
   if it won't install on Python 3.13 — say which you used and why). Missing trading days = ERROR. Extra days = ERROR.
2. Duplicate dates = ERROR. Dates not sorted = ERROR.
3. Missing values in any price/volume column = ERROR.
4. Prices ≤ 0 = ERROR. Volume < 0 = ERROR. Volume = 0 = WARNING.
5. OHLC consistency: low ≤ open, close ≤ high (raw AND adjusted) = ERROR if broken.
6. Split factor: not ≈ 1 → INFO with date + value. Not near a whole/simple ratio (tolerance 1e-4 relative) = WARNING.
7. Dividends: negative = ERROR; record count + dates as INFO.
8. Big moves: |raw close-to-close change| > 25% → if the same date has a split, INFO ("explained by split");
   otherwise WARNING with the move size.
9. Raw vs adjusted consistency (explains the adjusted gap): ratio r = close_adj / close_raw should stay the same
   between event dates and change only on/near dividend or split dates. Flag any day where r changes by more than a
   small tolerance without an event = WARNING. Report how much of the total raw→adj gap is from splits vs dividends,
   and whether the gap also implies splits AFTER 2016 (e.g. a later split) — state it as "implied by the ratio",
   not as a fact.
Tests: synthetic tiny DataFrames for EVERY check (one pass case + one fail case each). No internet.

PART B — cross-check with yfinance (`scripts/crosscheck_yfinance.py`)
- Add yfinance in a separate uv dependency group (e.g. `crosscheck`), not as a main dependency. Say why.
- Download AAPL + XOM 2010-01-01 → 2016-12-31 with `auto_adjust=False` and actions (dividends + splits). Use a cache
  under /data/ (git-ignored). Be gentle: 2 requests, retry on 429.
- WARNING: Yahoo's "Close" may already be SPLIT-adjusted even with auto_adjust=False, and its dividends may be
  split-adjusted too [UNVERIFIED]. Check this from the data itself before comparing, and convert both sources to the
  same basis. Explain what you found.
- Compare: trading-day sets; close prices (report max and median % difference, count over 0.5%);
  dividend dates + amounts; split dates + ratios. Report differences — don't hide or average them away.

PART C — survivorship check (small investigation, report only)
- Find out from Tiingo's OFFICIAL docs whether it publishes a supported-tickers list with start/end dates, and whether it
  includes delisted tickers (endDate in the past). If it's a single small file, download it once to /data/ and report:
  total tickers, how many US stocks have an endDate before 2020. No other API calls. If unclear, report "unclear" + link.

OUTPUT
- `reports/data_validation/2010-2016_AAPL_XOM.md`: counts, issues table, cross-check summary, survivorship finding.
  Counts, dates and % differences only — no price series (licence). This file may be committed.
- Script to run it all: `scripts/validate_initial_dataset.py`. Run it once for real; show the real output.

FINISH
- `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` — real output.
- Key + data safety checks before commit (same as Step 2.2).
- Commit on branch → merge to main when tests pass → push.
- PROJECT_STATUS.md: Step 2.3 result + Findings; update DATA_SOURCES.md §1 "Delisted stocks" and "Timezone of date"
  rows with what you found (with source/evidence). Next action = Step 2.4 (data conventions) + 2.5 (limitations).
- CHANGELOG.md entry.

COMPLETION REPORT: files · library choices + why · validation results per ticker (ERROR/WARNING/INFO counts + notable items) ·
yfinance cross-check results · survivorship finding · tests + real output · open questions.
Do not claim anything is done unless the evidence supports it.
