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

## 2026-10-20 — Phase 3, Steps 3.1–3.3: ledger core (version stays 0.1.0)
- New module `quant_research.portfolio`: `money` (Decimal helpers, `to_decimal_price`, rounding against us,
  `shares_affordable`) and `ledger` (`Portfolio` with cash, whole/fractional positions, average-cost realised P&L,
  minimum order, immutable audit trail; refused trades change nothing).
- `tests/accounting/`: 29 hand-calculated tests incl. a seeded cash-invariant test.
- PROJECT_GUIDE.md: `portfolio/` marked created; average-cost and fee/minimum-order assumptions in §4.

## 2026-10-20 — Phase 3, Steps 3.4–3.6: costs, dividends, splits (version stays 0.1.0)
- New module `quant_research.execution.costs`: one `COST_TABLE` with sources; brokerage (Stake, IBKR fixed,
  CommSec incl. per-trade FX), spread + slippage, AUD↔USD conversion (rate passed in).
- `quant_research.ratios`: `nearest_simple_ratio` moved here from data validation (shared, not copied).
- Ledger: `apply_dividend` (15% withholding, entitlement at previous close, tiny amounts not credited) and
  `apply_split` (snapped ratio, basis unchanged, reverse-split rules); daily order split → dividend → trades enforced.
- Tests: costs, corporate actions, and the random invariant test extended to dividends + splits (both share modes).
- PROJECT_GUIDE §4 daily event order rule; DATA_SOURCES §8 unsupported corporate actions.

## 2026-10-20 — Phase 3, Steps 3.7–3.8: valuation + independent accounting tests (version stays 0.1.0)
- `Portfolio.valuation` → `Valuation` / `HoldingValuation` (market value rounded down, unrealised P&L, income and
  fees separately); `MissingPriceError`; display helper `money.to_display` (ROUND_HALF_EVEN, display only).
- Changed rule (Goggy, 2026-10-20): dividend withholding is taken from the cents-rounded gross (was: exact gross).
- `tests/accounting/test_golden_scenario.py` (chat Claude's independent answer key + hand-calculated whole-share run),
  `tests/accounting/test_valuation.py`; random invariant test also checks valuation.
- `reports/accounting/golden_scenario.md`; PROJECT_GUIDE §4 display rule; PROJECT_STATUS Phase 3 check.

## 2026-10-21 — Phase 4, Steps 4.1–4.3: engine core (version stays 0.1.0)
- Dependency: `pyyaml` (run configs).
- `quant_research.backtesting`: `engine` (daily timeline: split → dividend → fills at open → valuation → strategy
  at close; expired orders; liquidation value), `lookahead` (reusable no-look-ahead harness), `run` (`RunConfig`
  from YAML, D8 final-test lock before loading, run record under /data/runs/), `synthetic` (made-up price tables).
- `quant_research.execution`: `orders.OrderIntent` (no price field), `fills.fill_order` (next-open fills, exact
  max-affordable sizing, gaps, rejections with reasons).
- `config/s0_buy_and_hold_aapl_dev.yaml` example (FX rates temporary).
- Tests: `tests/backtesting/` (engine, fills, run) — synthetic only.

## 2026-10-21 — Phase 4, Steps 4.4–4.6: buy-and-hold, metrics, edge cases, RBA FX (version stays 0.1.0)
- Dependency: `xlrd` (reads the RBA .xls files).
- `quant_research.data.fx` + `scripts/download_rba_fx.py`: RBA AUD/USD (FXRUSD), latest rate ≤ day, 5-day staleness limit.
- `RunConfig`: `fx_source` (rba | fixed), `reinvest_min_cash_usd` (US$100); engine setting `withholding_rate`.
- `quant_research.strategies` (S0 `BuyAndHold`, registry); `quant_research.metrics.performance`;
  `execution.intrabar.resolve_intrabar` (worse order); fills record `position_after`.
- `scripts/run_s0_dev.py` → `reports/runs/s0_dev_2010-2016.md` (summary numbers only; sanity check + what-if).
- Configs for AAPL + XOM (development period). EXPERIMENT_PLAN §1/§2/§10 updated (S0 wording, reinvest rule).

## 2026-10-25 — Phase 5, Steps 5.1, 5.2, 5.6: S1 + S2 (version stays 0.1.0)
- S0 sanity check tightened: no-withholding what-if within 1% relative of the adjusted return (Goggy).
- `quant_research.strategies.profit_target`: S1 fixed profit target, S2 pullback from peak; remembered prices
  are split-adjusted on split days (bug found by the AAPL trade-list check, fixed before reporting).
- `PortfolioView.fills` (read-only past fills); `RunConfig.profit_target_x` / `rebuy_dip_y` / `grid_override`.
- Metrics: stranded episode, longest cash spell. TODO Phase 6: best-3-trades-removed.
- `scripts/run_s1_s2_dev.py` → `reports/experiments/s1_s2_dev_2010-2016.md` (66 runs, development period only).

## 2026-10-25 — Phase 5, Steps 5.3–5.4: S3 + S4, indicator warm-up (version stays 0.1.0)
- Warm-up data 2008–2009 (download script takes START END); `load_prices_with_warmup`; `RunConfig.warmup_start`;
  `run_engine(trade_start=…)` — strategies see warm-up rows, nothing is traded or measured before the start.
- `quant_research.strategies.indicators` (split-adjusted-as-of-T closes, z-score, SMA, strong uptrend).
- S3 `MeanReversion`; S4 `TrendFilteredProfitTarget` / `TrendFilteredPullback`; config `mr_k` / `mr_window` grid.
- `scripts/run_s3_s4_dev.py` → `reports/experiments/s3_s4_dev_2010-2016.md` (78 runs + warm-up proof, dip caveat).
- EXPERIMENT_PLAN §2 exact S3/S4 choices; §10 S4 on all 16 X/Y.

## 2026-10-25 — Phase 5 close: Steps 5.5 + 5.7, pre-registration (version stays 0.1.0)
- Step 5.5: no hybrid strategy (Goggy's decision) — EXPERIMENT_PLAN §2 + §10.
- `scripts/phase5_comparison.py` → `reports/experiments/phase5_comparison_dev_2010-2016.md` (consistency proof,
  roll-up, multiple-testing note, reproducibility 5/5) — computed from saved run records.
- `research/PREREGISTRATION.md` v1 + git tag `prereg-v1` — Phase 6 tests and judgement fixed before any 2017–2020 data.
- Fix: saved `config.yaml` now reads back unchanged (dates kept as dates); round-trip test.

## 2026-10-25 — Phase 6 data step (prompt 16) (version stays 0.1.0)
- Downloader: optional ticker list; refuses END ≥ 2021-01-01. 20 new Tiingo files (6 new stocks × 3 periods +
  AAPL/XOM 2017–2020); Yahoo cache 2008–2020 for all 8; RBA 2018–2020 kept from 2018-2022.xls (trimmed, original deleted).
- `data.fx`: trimmed RBA CSV support (refuses rows after 2020-12-31). `data.crosscheck`: optional constant non-split
  later factor (prices only, value never reported).
- `scripts/validate_phase6_data.py` → `reports/data_validation/phase6_all_stocks_2008-2020.md` (all 0 ERROR;
  flat-bar scan; same-share-basis special-dividend check).
- PREREGISTRATION §6 + §9: regime rule (before any validation data). DATA_SOURCES §8–§10, INITIAL_UNIVERSE (Stake).
