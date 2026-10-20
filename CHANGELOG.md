# Changelog

## 0.1.0 — 2026-10-20
- Phase 1 (Steps 1.2 + 1.3): project skeleton.
  - uv-managed environment, Python pinned to 3.13 (`.python-version`), `uv.lock` committed.
  - Dev tools: pytest, ruff. No runtime dependencies yet.
  - `src/quant_research` package with version string; one smoke test.
  - `.gitignore` excludes `.env`, `data/`, `.venv/` and caches. `.env.example` template added.
- Style-only fix in `research/calc_feasibility.py` (ruff PLC0206: loop now uses `.items()`).
  Printed output verified identical before/after (diff, 2026-10-20). Approved by Goggy.

## 2026-10-20 — Step 1.4 (docs only, version stays 0.1.0)
- Phase 1 (Step 1.4): added `PROJECT_GUIDE.md` v1 — session start/end, folder map with planned
  modules, naming, units & conventions, testing, error handling, config, Git workflow,
  and open DECISIONS D1–D9 for Goggy. Documentation only; no code changed.
- PROJECT_STATUS.md: Phase 1 check done → "Phase 1: ready for verification".

## 2026-10-20 — Conventions approved (version stays 0.1.0)
- `research/calc_feasibility.py` reformatted with `ruff format` (spacing only; output diffed identical).
- `PROJECT_GUIDE.md` v1.1: D1–D9 recorded as approved by Goggy 2026-10-20. D8 changed: the
  final-test lock (dates ≥ 2021-01-01) sits in the backtest / experiment runner, not data loading;
  unlock only via `final_test_unlocked: true`, set by Goggy.
- PROJECT_STATUS.md: Step 1.4 done; D1–D9 added to IMPORTANT DECISIONS; Phase 1 ready for verification.

## 2026-10-20 — Phase 2, Step 2.2: Tiingo download (version stays 0.1.0)
- Runtime dependencies: pandas, httpx, python-dotenv.
- `quant_research.data.tiingo`: `fetch_daily_prices`, `fetch_meta`, `parse_prices` — columns renamed to
  PROJECT_GUIDE §4 names, plain dates, API key only in the request header, retries on 429/5xx/network errors.
- `quant_research.data.storage`: `save_raw_prices` writes CSV + `.meta.json` (no key), refuses overwrite.
- `scripts/download_initial_dataset.py`: AAPL + XOM, 2010-01-01 → 2016-12-31, prints a summary.
- Offline tests with a made-up fixture (`tests/fixtures/tiingo_prices_sample.json`) and mocked HTTP.
- Fix: `.gitignore` now ignores only the top-level `/data/` (the old `data/` rule also hid `src/quant_research/data/`).

## 2026-10-20 — Phase 2, Step 2.3: data validation (version stays 0.1.0)
- Dependency: `exchange_calendars` (NYSE calendar, D4). New optional group `crosscheck`: `yfinance`.
- `quant_research.data.validation`: calendar, duplicates/order, missing values, positive prices/volume, OHLC,
  split ratios, dividends, big moves, adjusted/raw ratio — structured ERROR/WARNING/INFO report; never fixes data.
- `quant_research.data.crosscheck`: Yahoo download + cache, split-basis detection, comparisons of trading days,
  closes, dividends, splits, and a data-derived explanation test for close differences.
- Scripts: `crosscheck_yfinance.py`, `validate_initial_dataset.py` → `reports/data_validation/2010-2016_AAPL_XOM.md`.
- DATA_SOURCES.md: "Timezone of date", "Delisted stocks" and a new yfinance "Basis" row filled from evidence.

## 2026-10-20 — Phase 2, Steps 2.4–2.5: conventions, loader, limitations (version stays 0.1.0)
- `quant_research.data.loader.load_prices`: reads saved Tiingo files only, requires `.meta.json`, validates,
  stops on any ERROR, returns raw columns (+ adjusted on request) with `Provenance`. 10 offline tests.
- DATA_SOURCES.md v1.1: §7 Data conventions (10 rules), §8 Known limitations; calendar row updated.
- PROJECT_GUIDE.md folder map and README data commands updated.
- PROJECT_STATUS.md: Phase 2 check → ready for verification.
