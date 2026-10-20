You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, DATA_SOURCES.md, research/EXPERIMENT_PLAN.md.

STEP 0 — save chat Claude's doc updates (docs go straight to main, per D5):
`git status` → commit DATA_SOURCES.md, PROJECT_STATUS.md, research/BROKER_FEES.md,
research/SMALL_ACCOUNT_FEASIBILITY.md, prompts/05_*.md as "Phase 2: add DATA_SOURCES.md (Step 2.1)". Push.

TASK: Phase 2, Step 2.2 — Download a SMALL initial dataset from Tiingo and save it reproducibly.
Branch: `phase2-tiingo-download` (D5). Explain each git step to Goggy in one line.

SCOPE (only this):
- Tickers: AAPL, XOM. Dates: 2010-01-01 → 2016-12-31. Nothing else.
- Downloading + saving only. Full data-quality checks are Step 2.3 (next task) — don't build them now,
  except the basic sanity checks listed below.

BUILD:
1. Dependencies (runtime): pandas, httpx (or requests — pick one, say why), python-dotenv. Add with `uv add`.
2. `src/quant_research/data/tiingo.py`:
   - `fetch_daily_prices(ticker: str, start: date, end: date, api_key: str) -> pandas.DataFrame`
     calling `https://api.tiingo.com/tiingo/daily/<ticker>/prices?startDate=&endDate=`.
   - Also `fetch_meta(ticker, api_key)` → the meta endpoint (startDate, endDate, exchangeCode, name).
   - Keep ALL fields Tiingo returns. Rename to our conventions (PROJECT_GUIDE §4): open_raw, high_raw,
     low_raw, close_raw, volume_raw, open_adj, high_adj, low_adj, close_adj, volume_adj, div_cash_usd,
     split_factor. Keep a `date` column as plain dates (drop any time part; record what the raw value looked like).
   - API key: send it in the request HEADER (`Authorization: Token <key>`), not in the URL, so it never ends up
     in logs or saved metadata. Never print or log the key.
   - HTTP 429 / network errors: retry a few times with backoff, then fail loudly with a clear message.
   - Type hints on every function (D9). logging, not print (§6).
3. `src/quant_research/data/storage.py`: save to `data/raw/tiingo/<TICKER>_<start>_<end>.csv` plus a sidecar
   `<same>.meta.json` with: source, endpoint (no key), tickers, dates, download timestamp (UTC), row count,
   first/last date, package version, git commit. Refuse to overwrite an existing file unless `overwrite=True`.
4. `scripts/download_initial_dataset.py`: loads TIINGO_API_KEY from .env, downloads both tickers, saves, then prints
   a SUMMARY per ticker: rows, first date, last date, count of non-zero dividends, list of split rows
   (date + split_factor), any missing values per column. Report what the data shows — don't assume.
5. Tests (NO live internet in tests — PROJECT_GUIDE §5):
   - Tiny made-up JSON fixture in tests/fixtures/ that looks like Tiingo's response (3–5 days, one dividend,
     one split). Test: column renaming, date parsing, dtypes, divCash/splitFactor kept.
   - Mock the HTTP layer: test that the key goes in the header, not the URL; test 429 → retry → clear error.
   - Test storage: writes CSV + meta.json, refuses overwrite, meta.json contains no key.
6. Run the script ONCE for real (2 API calls). Show the real summary output.

CHECKS BEFORE COMMIT:
- `git status`: nothing under data/ and no .env staged. `grep` the repo for the key's first 6 characters
  read from .env (without printing them) → must find nothing.
- `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` — real output.

FINISH:
- Commit on the branch ("Phase 2: Tiingo download for AAPL + XOM (Step 2.2)"), merge to main when tests pass, push.
- PROJECT_STATUS.md: Step 2.2 result incl. the real summary numbers; anything surprising
  (e.g. split date/ratio, missing values, timezone in raw date) under "Findings". Next action = Step 2.3 (validation).
- CHANGELOG.md entry.

COMPLETION REPORT: files · dependencies added + why · real download summary · tests + real output ·
findings/surprises · known limits.
Do not claim anything is done unless the evidence supports it.
