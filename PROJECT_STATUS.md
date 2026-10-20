# PROJECT_STATUS.md
Last updated: 2026-10-20

CURRENT PHASE: Phase 2 — Historical Market Data (ready for verification)
CURRENT TASK: Phase 2 verification by chat Claude

PHASE STATES (Not started / In progress / Blocked / Verified):
- Phase 0  Feasibility & research design ........ VERIFIED (2026-10-18)
- Phase 1  Dev environment & repository ......... VERIFIED (2026-10-20)
- Phase 2  Historical market data ............... ready for verification (2026-10-20)
- Phase 3  Portfolio accounting engine .......... Not started
- Phase 4  Backtesting engine ................... Not started
- Phase 5  Strategy laboratory .................. Not started
- Phase 6  Research validation .................. Not started
- Phase 7  Company research & screening ......... Not started
- Phase 8  Interactive dashboard ................ Not started
- Phase 9  Market context & AI news ............. Not started
- Phase 10 Integration, security, reliability ... Not started
- Phase 11 CV & GitHub portfolio ................ Not started

COMPLETED:
- Master roadmap written (Quantitative Stock Strategy Research Platform.txt)
- Roadmap reviewed by Claude; PROJECT_BRIEF.md + this file created
- Open questions Q1–Q6 answered (2026-10-17)
- Step 0.1 research/RESEARCH_QUESTIONS.md v3 — DONE, approved by Goggy 2026-10-17
- Step 0.2 research/MARKET_SELECTION.md v1 — DONE, approved by Goggy 2026-10-17
- Step 0.3 research/INITIAL_UNIVERSE.md v2 — DONE: 8 tickers (AAPL MSFT KO PG XOM INTC T SPY); start with AAPL + XOM
- Step 0.4 research/SMALL_ACCOUNT_FEASIBILITY.md v1 + calc_feasibility.py — DONE, approved by Goggy 2026-10-17
  Result: Stake round trip ≈0.19%; CommSec ≈1.44%. Feasible to test on Stake/IBKR costs.
- Step 0.5 research/EXPERIMENT_PLAN.md v1 — DONE, approved 2026-10-18
- PHASE 0 CHECK (2026-10-18): hypothesis defined ✓ · market selected with reasons ✓ ·
  data providers evaluated ✓ · experiment plan ✓ · limitations documented (EXPERIMENT_PLAN §9) ✓ ·
  no profitability claim ✓  → Phase 0 VERIFIED
- CLAUDE.md created (auto-read rules for Claude Code)
- Step 1.1 Mac inspection — DONE 2026-10-20 (report reviewed by Claude in chat; results under SETUP FACTS)
- Steps 1.2 + 1.3 repo + Python + tests — DONE 2026-10-20 (prompt 02):
  pyproject.toml, .python-version (3.13), uv.lock, .gitignore, .env.example, README.md, CHANGELOG.md,
  src/quant_research/__init__.py (version 0.1.0), tests/test_smoke.py. Dev deps: pytest 9.1.1, ruff 0.17.1.
  Git repo initialised (branch main); pushed to PRIVATE GitHub repo
  https://github.com/MaalavBhagat/quantitative-stock-strategy-platform
  Fresh clone + `uv sync` + `uv run pytest` + `uv run ruff check .` all worked (README steps verified).
  Style-only fix to research/calc_feasibility.py (ruff PLC0206), output diffed identical — approved by Goggy.
- Step 1.4 PROJECT_GUIDE.md v1 (development conventions, 191 lines) — DONE 2026-10-20 (prompt 03),
  pending Goggy's answers to DECISIONS D1–D9 (§9). Documentation only; no code changed.
- PHASE 1 CHECK (2026-10-20, by Claude Code):
  clean environment ✓ (fresh clone: uv sync + pytest + ruff worked) · dependencies documented ✓
  (pyproject.toml + uv.lock + README) · Git configured ✓ (identity set, private GitHub remote, pushes OK) ·
  tests can be executed ✓ (uv run pytest: 1 passed) · project guide explains how to begin ✓ (PROJECT_GUIDE.md §1)
  → Phase 1: ready for verification (NOT marked Verified — Goggy + chat Claude verify after D1–D9)
- Step 1.4 DONE 2026-10-20 (prompt 04): D1–D9 approved by Goggy and recorded in PROJECT_GUIDE.md v1.1 §9
  (D8 changed: lock in backtest/experiment runner, not data loading). ruff format applied
  (research/calc_feasibility.py only; script output diffed identical before/after).
  → Phase 1: ready for verification — all criteria met, decisions applied
- .env created by Goggy 2026-10-20 (TIINGO_API_KEY set, 40 chars, git-ignored — checked without printing it).
- Step 2.1 DATA_SOURCES.md — DONE 2026-10-20 (chat Claude, official Tiingo/Stake pages).
  Findings: Tiingo free = 50 req/h, 1,000/day, 1 GB/mo, "Internal Use Only"; raw + adj OHLCV, divCash on ex-date,
  splitFactor; NO dividend pay date; delisted coverage unknown. Stake withdrawal FX 0.55% VERIFIED.
  yfinance: always pass auto_adjust=False.
- PHASE 1 VERIFIED by chat Claude 2026-10-20: checked commits 6ea91d0..632f381 on disk, clean tree,
  ruff-format commit touches only calc_feasibility.py, PROJECT_GUIDE v1.1 has D1–D9 approved and D8
  (runner-level lock) in §2/§4/§7/§9; Claude Code's fresh-clone test + pytest/ruff output accepted.
- Step 2.2 Tiingo download — DONE 2026-10-20 (prompt 05, branch phase2-tiingo-download, merged to main):
  src/quant_research/data/tiingo.py (fetch_daily_prices, fetch_meta; key in Authorization header; retry 429/5xx/
  network with backoff, then clear error), src/quant_research/data/storage.py (CSV + .meta.json, refuses overwrite),
  scripts/download_initial_dataset.py, 21 new offline tests. Runtime deps: pandas 3.0.6, httpx 0.28.1, python-dotenv 1.2.4.
  Real run (2 API calls, 2026-10-20 05:38 UTC, code commit 454e5d4, git_dirty false):
    AAPL: 1762 rows, 2010-01-04 → 2016-12-30, 18 non-zero dividends, 1 split row (2014-06-09, split_factor 7.000007),
          no missing values in any column.
    XOM:  1762 rows, 2010-01-04 → 2016-12-30, 28 non-zero dividends, no split rows, no missing values.
  Files (git-ignored): data/raw/tiingo/{AAPL,XOM}_2010-01-01_2016-12-31.csv + .meta.json.
  .gitignore fixed: `data/` → `/data/` (old rule also hid src/quant_research/data/ — caught before commit).

FINDINGS (Step 2.2, from the real download — to check in Step 2.3):
- Raw `date` from Tiingo looks like '2010-01-04T00:00:00.000Z' (midnight, labelled UTC). Code drops the time part
  and treats it as the US trading date; any non-midnight time fails loudly. Matches DATA_SOURCES [UNVERIFIED] row.
- AAPL 2014 split factor is 7.000007, NOT exactly 7 → validation must compare with a tolerance and record the
  official ratio (7-for-1 [UNVERIFIED here — confirm from a second source in Step 2.3]).
- Raw prices change 7× across the split (2014-06-06 close_raw 645.57 → 2014-06-09 close_raw 93.70) → raw prices
  can never be used across a split without the split adjustment in the accounting engine (Phase 3).
- Adjusted prices are much lower than raw even after the 2014 split (AAPL 2014-06-09 close_raw 93.70 vs
  close_adj 20.52, ratio ≈ 4.57). Likely cause: later corporate actions (e.g. AAPL's 2020 split) + dividend
  adjustment [UNVERIFIED — explain in Step 2.3]. Means adjusted values depend on download date; we keep raw +
  download date and never trade on adjusted (DATA_SOURCES §4).
- AAPL dividends: 18 non-zero rows in 2010–2016; XOM: 28. Plausibility check (e.g. vs yfinance) is Step 2.3.
- 1762 trading days in both files — check against the NYSE calendar (D4) in Step 2.3.

- Step 2.3 data validation — DONE 2026-10-20 (prompt 06, branch phase2-data-validation, merged to main):
  src/quant_research/data/validation.py (9 checks, ERROR/WARNING/INFO report, never fixes data),
  src/quant_research/data/crosscheck.py (Yahoo basis detection + comparisons), scripts/crosscheck_yfinance.py,
  scripts/validate_initial_dataset.py, report reports/data_validation/2010-2016_AAPL_XOM.md (counts/dates/% only).
  Deps: exchange_calendars 4.13.2 (main; installed fine on 3.13, fallback not needed); yfinance 1.7.0 in separate
  `crosscheck` group (unofficial, personal-use, only for cross-checks — main code must not depend on it).
  Run: `uv run --group crosscheck python scripts/validate_initial_dataset.py` (no Tiingo calls; Yahoo cached).
  RESULTS: AAPL 0 ERROR / 0 WARNING / 5 INFO · XOM 0 ERROR / 0 WARNING / 3 INFO.
    Both: 1,762 rows = 1,762 NYSE sessions; no missing/duplicate/unsorted dates; no missing values; no bad
    prices/volumes; OHLC consistent (raw + adj); adj/raw ratio changes ONLY on dividend/split ex-dates.
    AAPL: split 2014-06-09 factor 7.000007 → 7:1 (rel diff 1e-6); -85.5% raw move that day explained by split;
          18 dividends (first 2012-08-09). Gap inside table ×7.685 = splits ×7.000 × dividends ×1.098.
    XOM: 28 dividends, no splits, no big moves. Gap inside table ×1.221 = dividends only.
  YFINANCE CROSS-CHECK (2 Yahoo requests, cached in /data/cache/yfinance/):
    Trading days identical (1,762 both, 0 only-in-one). Splits identical (AAPL 2014-06-09 7:1).
    Dividends: same dates (18 / 28), amounts match after basis conversion (max diff 0.0004%).
    Closes: AAPL max 0.318% (2015-09-30), 0 days > 0.5%. XOM max 1.085%, 3 days > 0.5%:
      2010-02-05 +0.652% and 2010-05-10 +0.679% = exactly the next day's dividend (day before ex-date);
      2014-07-28 +1.085% unexplained (Yahoo open also differs −0.42%).
  SURVIVORSHIP: Tiingo's official supported_tickers.zip (1 download, 0.8 MB) — 109,085 rows; 16,576 US-exchange
    USD stocks, 3,019 with endDate before 2020 → delisted tickers partly listed. LEH/LEHMQ/ENRNQ/WAMUQ not found by
    symbol → coverage looks partial. Downloadability of delisted price history NOT tested.

FINDINGS (Step 2.3):
- Yahoo `Close`/`Dividends`/`Volume` are split-adjusted for ALL splits (incl. later ones) even with auto_adjust=False
  (AAPL 2010–2014 Yahoo close = Tiingo raw ÷ 28). Confirmed from the data; recorded in DATA_SOURCES §2.
- Tiingo `date` = midnight UTC label, matches NYSE calendar and Yahoo New York dates → US trading date (DATA_SOURCES §1).
- Adj/raw gap explained: in-table = splits × dividends exactly; after 2016 AAPL gap ×4.35 vs ~×1.14 from dividends →
  "implied by the ratio": about a 4:1 later split (rough estimate, matches Yahoo's ÷4 basis). XOM: dividends explain it.
- XOM: on 2 of 28 days before an ex-date, Yahoo's close is higher than Tiingo's by exactly the dividend. Which source
  is right is UNKNOWN — needs a third source if it ever matters (only affects signal-day closes, not fills at next open).
- XOM 2014-07-28: Tiingo vs Yahoo close differ 1.085% — unexplained. Open question.
- 2014-07-28 and the pre-ex-date days are the only cross-source disagreements > 0.5% in 3,524 rows.
- Note: exchange_calendars cannot start a calendar on a holiday (2010-01-01) — handled in nyse_sessions (tested).

- Steps 2.4 + 2.5 — DONE 2026-10-20 (prompt 07, branch phase2-loader, merged to main):
  DATA_SOURCES.md v1.1 §7 "Data conventions" (10 rules: timestamps, NYSE calendar, USD, raw vs adjusted, splits,
  dividends on ex-date + 15% withholding, no filling, caching, versioning/provenance, source disagreements) and
  §8 "Known limitations" (9 rows). src/quant_research/data/loader.py: load_prices() reads saved files only,
  requires .meta.json, validates the slice, raises DataLoadError on any ERROR, logs WARNINGs, returns raw columns
  (+ adj only with include_adjusted=True) and Provenance in df.attrs; does NOT enforce the D8 lock (runner does).
  Real files load: AAPL 1,762 rows, XOM 1,762 rows, provenance = file name + 2026-10-20 download + commit 454e5d4.
  Housekeeping: PROJECT_GUIDE folder map (data/ module created, scripts/, reports/), README data commands,
  DATA_SOURCES calendar row (exchange_calendars runs on 3.13).
- PHASE 2 CHECK (2026-10-20, by Claude Code) — NOT marked Verified:
  retrieved reproducibly ✓ (download script + .meta.json with endpoint/time/commit; refuses overwrite; validation
    report regenerated from saved files and diffed IDENTICAL) ·
  data-quality checks exist ✓ (validation.py 9 checks, 33 tests; Yahoo cross-check, 13 tests) ·
  source limitations documented ✓ (DATA_SOURCES §8, 9 rows; §7 row 10 source disagreements) ·
  pipeline handles missing observations safely ✓ (loader raises on missing day / missing value / missing meta —
    tests test_missing_trading_day_raises, test_missing_value_raises_and_is_not_filled, test_missing_meta…) ·
  initial dataset suitable for basic experiments ✓ (AAPL + XOM 2010–2016, 0 ERROR / 0 WARNING, matches NYSE
    calendar, split + 46 dividends cross-checked) — limited to 2 stocks and the development period by design.
  → Phase 2: ready for verification

IN PROGRESS:
- Phase 2 verification by chat Claude

BLOCKED / OPEN QUESTIONS:
- Stake fractional-share precision UNVERIFIED (D3 assumes 6 dp — check in Phase 3)
- XOM 2014-07-28 Tiingo/Yahoo close differ 1.085% — unexplained (third source?)
- XOM pre-ex-date closes (2010-02-05, 2010-05-10): Tiingo vs Yahoo differ by exactly the dividend — which is right?
- Delisted stocks: can Tiingo price history be downloaded for tickers with endDate in the past? (survivorship; untested)

SETUP FACTS (stated by Goggy, 2026-10-17):
- Computer: Mac. Coding tool: Claude Code in the Claude desktop app (2026-10-20).
- Connectors added 2026-10-20: GitHub, Alpha Vantage, Financial Datasets, alphaXiv, StockPortfolio.pro.
- Broker: Stake = MAIN cost case (Goggy knows it). Also model IBKR (LOW) + CommSec (HIGH).
- Market: start with US (others later).
- Data budget: free preferred; small monthly cost OK.
- Capital: AUD 10,000 (changed from AUD 1,000 on 2026-10-17; overrides master roadmap Step 0.4).
- Rise/dip starting range: 2–5% each.
- Time: 1–2 hours daily, no deadline.
- GitHub: has account; repo can be public later.

Mac environment (checked 2026-10-20 by Claude Code, read-only commands):
- macOS 26.6.2 (build 25G83), MacBook Air, Apple Silicon M2 (arm64).
- Python: main = Homebrew Python 3.14.6 (/opt/homebrew/bin/python3). Also Apple's built-in 3.9.6 (/usr/bin/python3) — don't use.
  No pyenv, no conda.
- Xcode Command Line Tools: installed.
- uv: NOT installed. pip: pip3 26.1.2 (Homebrew). pipx: NOT installed.
- Homebrew: 6.0.17 (/opt/homebrew).
- Git: 2.55.0 (Homebrew). user.name / user.email: NOT set.
- GitHub CLI (gh): NOT installed.
- VS Code: NOT installed (no `code` command, no app in /Applications).
- Free disk: 23 GiB of 228 GiB (data volume 89% used).
- This folder is NOT a git repo yet.
  UPDATE after Step 1.2–1.3 (2026-10-20): installed uv 0.13.2 + gh 2.102.0 (Homebrew; brew auto-cleanup ran);
  uv-managed Python 3.13.16; git user.name = MaalavBhagat, user.email = GitHub noreply address;
  gh logged in as MaalavBhagat (keyring, https). Folder is now a git repo.

KNOWN BUGS:
- None known

IMPORTANT DECISIONS:
- 2026-10-17: Work in small, single tasks. Every task ends by updating this file.
- 2026-10-17: Facts (fees, data prices, provider limits) must have a source link
  or be labelled "UNVERIFIED / ASSUMPTION".
- 2026-10-17: Starting capital AUD 10,000 (was 1,000).
- 2026-10-17: Model 3 cost levels — LOW (IBKR-like), MID (Stake-like), HIGH (CommSec standard).
- 2026-10-17: Stake is the MAIN cost case.
- 2026-10-17: US market first (agreed). Data: Tiingo primary, yfinance cross-check (agreed).
- 2026-10-18: Repo root = this folder (Desktop/Share research). GitHub repo name: quantitative-stock-strategy-platform.
- 2026-10-20: Git identity = MaalavBhagat + GitHub noreply email. GitHub repo created PRIVATE.
- 2026-10-20: Tooling = uv; project Python pinned to 3.13 via uv (Homebrew 3.14 left alone); gh CLI for GitHub. Goggy approved brew install uv + gh.
- 2026-10-18: Q4.11 added — which market/company types suit the strategy (answer after Phase 6/7).
- 2026-10-17: Starting pair AAPL (with momentum) + XOM (without steady momentum) — Goggy's choice. Downloaded data never goes into the public repo (licence).
- 2026-10-17: H1 v2 + H2–H7 approved. H1 v2 is the main hypothesis. H2–H6 tested only after H1 baseline; H7 exploratory.
- 2026-10-20: Coding conventions D1–D9 approved by Goggy (full text: PROJECT_GUIDE.md §9):
  D1 money = Decimal in portfolio/ + execution/ (cash, fees, shares), float for prices/signals/metrics, one tested
     conversion point at the fill · D2 cash rounded to cents at each ledger entry, against us (pay up, receive down) ·
  D3 fractional shares 6 dp, bought round down [ASSUMPTION — check Stake in Phase 3] ·
  D4 NYSE calendar library (Phase 2); date mismatches fail loudly ·
  D5 docs → main; code tasks on phase<N>-<task> branch, merged when tests pass (Claude Code runs + explains) ·
  D6 dirty runs allowed in dev, labelled; validation + final-test runs clean · D7 ruff format adopted ·
  D8 (CHANGED) final-test lock in backtest/experiment runner: data download + quality checks may cover all years,
     but no strategy/backtest/metric/chart/summary stat on dates ≥ 2021-01-01 unless final_test_unlocked: true
     (only Goggy sets it) · D9 type hints required on every function in src/; no type-checker yet.

NEXT ACTION:
- Chat Claude verifies Phase 2, then Phase 3 Step 3.1 (cash accounting)

CHAT CLAUDE CHECK OF STEP 2.3 (2026-10-20): main at 896a53c, no stray branches, no data/.env tracked;
report has counts/dates/% only (no price values found by grep). Results accepted: 0 ERROR/0 WARNING both tickers,
NYSE calendar match 1,762/1,762, Yahoo split-adjusted basis handled, 3 XOM close diffs logged. → Step 2.3 VERIFIED.
Third-source check of the 3 XOM days: Financial Datasets connector has $0 credits → not done; left as known minor issue.
Dividend withholding 15% with W-8BEN VERIFIED on Stake support page (30% without).

TESTS RUN (2026-10-20, Steps 2.4–2.5):
- uv run pytest → "78 passed in 1.09s" (crosscheck 13, loader 10, smoke 1, storage 6, tiingo 15, validation 33)
- uv run ruff check . → "All checks passed!" · uv run ruff format --check . → "38 files already formatted"
- scripts/validate_initial_dataset.py re-run → AAPL 0/0/5, XOM 0/0/3; report diffed IDENTICAL to previous run
- loader on real data: AAPL + XOM 1,762 rows each, June 2014 slice 21 rows

TESTS RUN (2026-10-20, Step 2.3):
- uv run pytest → "68 passed in 0.79s" (smoke 1, storage 6, tiingo 15, validation 33, crosscheck 13)
- uv run ruff check . → first run "Found 17 errors" (15× ISC004 implicit string concat in report script, PERF102, RUF059)
  → fixed (wrapped in parentheses; report regenerated and diffed IDENTICAL) → "All checks passed!"
- uv run ruff format --check . → "35 files already formatted"
- Key check: TIINGO_API_KEY prefix (not printed) NOT found in staged files or in the report; no data/ or .env staged.
- scripts/validate_initial_dataset.py real run → AAPL 0/0/5, XOM 0/0/3 (ERROR/WARNING/INFO), exit 0

TESTS RUN (2026-10-20, Step 2.2):
- uv run pytest → "22 passed in 0.99s" (test_smoke 1, test_storage 6, test_tiingo 15)
- uv run ruff check . → "All checks passed!"
- uv run ruff format --check . → "27 files already formatted"
- Key check: first 6 chars of TIINGO_API_KEY (read from .env, not printed) NOT found in staged files or data/.

TESTS RUN (2026-10-20, prompt 04 — decisions applied):
- uv run ruff format . → "1 file reformatted, 18 files left unchanged" (research/calc_feasibility.py)
- calc_feasibility.py output before vs after format: identical (diff)
- uv run pytest → "1 passed in 0.01s"
- uv run ruff check . → "All checks passed!"
- uv run ruff format --check . → "19 files already formatted"

TESTS RUN (2026-10-20, Step 1.4):
- uv run pytest → "1 passed in 0.01s"
- uv run ruff check . → "All checks passed!"
- uv run ruff format --check . → "1 file would be reformatted, 16 files already formatted"
  (research/calc_feasibility.py, spacing only; NOT applied — waits for D7)

TESTS RUN (2026-10-20, Steps 1.2–1.3):
- uv run pytest  (in project folder AND in a fresh clone)
- uv run ruff check .  (in project folder AND in a fresh clone)

TEST RESULTS (real output):
- pytest: "1 passed in 0.04s" (fresh clone: "1 passed in 0.03s") — tests/test_smoke.py
- ruff: first run "Found 1 error." (PLC0206 in research/calc_feasibility.py) → fixed → "All checks passed!"
- calc_feasibility.py output before vs after fix: identical (diff)
