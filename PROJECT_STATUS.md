# PROJECT_STATUS.md
Last updated: 2026-10-28

CURRENT PHASE: Phase 10 — Integration, security, reliability (In progress)
CURRENT TASK: Phase 10 ready for verification (chat Claude); then Phase 11

PHASE STATES (Not started / In progress / Blocked / Verified):
- Phase 0  Feasibility & research design ........ VERIFIED (2026-10-18)
- Phase 1  Dev environment & repository ......... VERIFIED (2026-10-20)
- Phase 2  Historical market data ............... VERIFIED (2026-10-20)
- Phase 3  Portfolio accounting engine .......... VERIFIED (2026-10-20)
- Phase 4  Backtesting engine ................... VERIFIED (2026-10-25)
- Phase 5  Strategy laboratory .................. VERIFIED (2026-10-25)
- Phase 6  Research validation .................. VERIFIED (2026-10-26)
- Phase 7  Company research & screening ......... VERIFIED (2026-10-26)
- Phase 8  Interactive dashboard ................ VERIFIED (2026-10-27)
- Phase 9  Market context & AI news ............. VERIFIED (2026-10-28)
- Phase 10 Integration, security, reliability ... In progress (ready for verification 2026-10-28)
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

- Steps 3.1–3.3 ledger core — DONE 2026-10-20 (prompt 08, plan approved by Goggy incl. 3 choices; branch
  phase3-ledger-core, merged to main): src/quant_research/portfolio/money.py (to_decimal_price = the ONE float→Decimal
  point; require_decimal rejects floats; round_pay up / round_receive down to cents; round_shares_down 6 dp;
  shares_affordable) and portfolio/ledger.py (Portfolio: cash, totals spent/received/fees, positions with cost basis,
  average-cost realised P&L, immutable LedgerEntry audit trail; InsufficientCashError / InsufficientSharesError;
  refused trades change nothing; whole/fractional modes; min order US$10; dates never backwards).
  Tests: tests/accounting/ — 29 tests with hand calculations, exact Decimal equality, incl. a seeded 500-step
  invariant test (initial − spent − fees + received == cash). Mutation check: breaking pay-rounding → 5 tests fail;
  dropping fees from cost basis → 3 tests fail; restored code passes.
  Choices approved 2026-10-20: (1) buy fees in cost basis, sell fees off proceeds → P&L after all costs;
  (2) min order US$10 on buys + partial sells, whole-position sell allowed below it [ASSUMPTION];
  (3) fees rounded up to the cent.

- Steps 3.4–3.6 costs, dividends, splits — DONE 2026-10-20 (prompt 09, plan + 3 design choices approved by Goggy;
  branch phase3-costs-dividends-splits, merged to main):
  src/quant_research/execution/costs.py — ONE config table COST_TABLE (every row: source link or [ASSUMPTION]);
  fee_usd (stake / ibkr_fixed / commsec_standard, brokerage + per-trade FX + total), apply_spread (fill price +
  spread cost), aud_to_usd / usd_to_aud (rate passed in, fee in USD rounded up, amount out rounded down),
  fx_fee_settings. src/quant_research/ratios.py — nearest_simple_ratio moved here (shared by validation + ledger).
  Ledger: apply_dividend (entitled at previous close; refused after a trade that day; gross down / withholding up;
  net < US$0.01 not credited with a note; gross/withholding/net totals; basis unchanged; double-apply refused) and
  apply_split (snapped ratio; shares × ratio; basis + cash unchanged; whole-mode fractional reverse split →
  NotImplementedError; fractional rounds down + notes dropped fraction; double-apply refused). Daily order
  split → dividend → trades enforced.
  Tests: test_costs 15, test_corporate_actions 16, invariant test now covers dividends + splits in both share modes
  (cash equation incl. dividends_net, and shares == replay of the log). Stake round trip on US$6,900 normal spread
  = US$12.90 = 0.187% (feasibility doc ≈0.19% — consistent).
  Mutation check: withholding rounded DOWN → 5 tests fail; split changing cost basis → 4 fail; restored → all pass.
- Design choices approved 2026-10-20: (1) ratio function moved to quant_research/ratios.py (no copy);
  (2) FX fees counted in USD, rounded up, converted amount rounded down; (3) fractional reverse split keeps cost
  basis unchanged when a tiny fraction is dropped (conservative).

- Steps 3.7–3.8 valuation + independent tests — DONE 2026-10-20 (prompt 10, plan approved; branch phase3-valuation,
  merged to main): Portfolio.valuation(as_of, close_prices_usd) → Valuation (cash, per-ticker qty / avg cost /
  basis / close / market value rounded DOWN / unrealised, totals, realised, dividends gross/withholding/net, fees;
  spread is inside fill prices, tracked by execution). MissingPriceError for a held ticker without a close.
  Display rule: exact Decimal inside, ROUND_HALF_EVEN to cents only at display (money.to_display; PROJECT_GUIDE §4).
  GOLDEN SCENARIO (chat Claude's independent answer key): dry run found ONE mismatch — dividend withholding 5.38
  (15% of exact gross 35.80157931) vs key 5.37 (15% of cents gross 35.80), carrying 1 cent into net, cash, total
  and AUD out. Expected values NOT changed; Goggy decided 2026-10-20: withholding = 15% of the cents-rounded gross.
  Code changed; earlier tests kept their values. Now EVERY row of the key matches exactly
  (tests/accounting/test_golden_scenario.py). Whole-share version hand-calculated by Claude Code (not pre-computed
  by chat Claude) also passes. Report: reports/accounting/golden_scenario.md (made-up prices).
  Finding: TEST gained in USD (+367.82 realised, +30.43 dividends) but AUD out 9,627.14 < AUD in 10,000 because
  AUD/USD 0.69 → 0.75 plus two 0.55% FX fees → results must be shown in AUD too.
  Mutation check: market value rounded UP → 3 tests fail; unrealised sign flipped → 4 fail; restored → all pass.
- PHASE 3 CHECK (2026-10-20, by Claude Code) — NOT marked Verified:
  cash balances correct ✓ (hand-calculated tests; random invariant initial − spent − fees + received + div_net ==
    cash after every step, both share modes; golden scenario) ·
  share quantities correct ✓ (shares == replay of the log incl. splits; fractional 6 dp round-down tests) ·
  dividends consistent ✓ (entitlement at previous close, order enforced, double-apply refused, gross/withholding/net
    tracked, basis unchanged, golden row matches) ·
  corporate actions don't silently corrupt holdings ✓ (snapped ratio, basis unchanged, double-apply refused,
    whole-mode fractional reverse split raises, dropped fractions noted) ·
  transaction costs included ✓ (COST_TABLE with sources; Stake round trip 0.187%; spread in fill prices; FX in/out) ·
  valuation independently validated ✓ (golden scenario from chat Claude's own code + hand-calculated whole-share run).
  Unsupported (documented): cash-in-lieu on reverse splits (whole mode), spin-offs/mergers/special distributions,
  tax (CGT), interest on cash (0%), dividend pay-date lag (credited on ex-date), mid-run deposits/withdrawals,
  multi-currency cash (account is USD; AUD only at start/end), short selling / margin.
  → Phase 3: ready for verification

- Steps 4.1–4.3 engine core — DONE 2026-10-21 (prompt 11, plan approved incl. pyyaml; branch phase4-engine-core,
  merged to main). Synthetic data only.
  backtesting/engine.py — run_engine: per day OPEN split → dividend → fill yesterday's orders at open_raw;
  CLOSE valuation → equity row; strategy.on_close(day, history ending at T (a copy), read-only PortfolioView) →
  OrderIntents queued for T+1; leftovers EXPIRED; end: last-close value AND liquidation value (spread + fee).
  execution/orders.py — OrderIntent (side, ticker, size = shares | "all" | "max_affordable"; NO price field).
  execution/fills.py — fill_order at T's open via costs.apply_spread + costs.fee_usd; max_affordable = exact
  binary search (fees that grow with size: IBKR per-share + 1% cap, CommSec %); gap % recorded; cash / shares /
  minimum / nothing-affordable → Rejection with reason (run continues); bad inputs / missing open → error.
  backtesting/lookahead.py — reusable check_no_lookahead (scramble all data after T → decisions, orders, equity up
  to T identical; strategy never sees a row after its day; no order handled on the day it was created).
  backtesting/run.py — RunConfig from YAML (config/s0_buy_and_hold_aapl_dev.yaml), D8 lock checked BEFORE loading,
  run record in /data/runs/<run_id>/ (run.json with config, provenance, git commit + dirty, times, summary;
  orders.csv, fills.csv, equity.csv). FX rates usd_per_aud_start/end in config are TEMPORARY (RBA in prompt 12).
  Mutation check: fills at T's close → 9 tests fail (timing tests + the look-ahead harness after adding the
  same-day-fill rule — the first version of the harness did NOT catch it, because it only compared post-T data).
  Bug found + fixed while testing: first max_affordable could stop below the true maximum when the fee grows
  with size (CommSec / IBKR cap) — never overspent, but under-invested; replaced with exact binary search.

- Steps 4.4–4.6 + RBA FX — DONE 2026-10-21 (prompt 12, plan approved incl. xlrd + 2 RBA downloads; branch
  phase4-buyhold-metrics, merged to main).
  RBA: 2010-2013.xls + 2014-2017.xls (sheet Data, Series ID FXRUSD), downloaded once to /data/raw/rba/ + .meta.json;
  data/fx.py (latest rate ≤ day, > 5 days stale → error, range 0.40–1.20, sorted, no duplicates). Real-data findings:
  one "N/A" cell (2015-05-25, US holiday) → skipped, not filled; a 6-day gap between RBA rows (Easter + Anzac Day 2011)
  → my own extra row-gap check was stricter than the prompt and was changed to a log; the prompt's 5-day LOOKUP
  limit holds for every NYSE session 2010–2016 (max age 5 days; 50 sessions use an earlier day's rate).
  Config: fx_source rba (default) | fixed; reinvest_min_cash_usd "100". Engine setting withholding_rate (default 15%).
  strategies/buy_and_hold.py (S0: day-1 close max_affordable → day-2 open; reinvest when cash ≥ US$100; passes the
  look-ahead spy check). metrics/performance.py (total return, CAGR, max drawdown + dates, volatility, Sharpe rf 0,
  worst year, fees, spread, dividends, days in cash, round trips, AUD via daily RBA rate). execution/intrabar.py
  resolve_intrabar (both levels in a bar → assume the worse order: flat → buy only, holding → sell only).
  REAL RUNS (development period, SIMULATED/HISTORICAL; report reports/runs/s0_dev_2010-2016.md, records /data/runs/):
    AAPL: US$9,082.76 → US$37,069.58 at last close (liquidation 37,047.33) · AUD 10,000 → AUD 50,917.02 ·
          CAGR 22.30% USD / 26.23% AUD · max DD −43.79% (2012-09-19 → 2013-04-19) · vol 26.19% · Sharpe 0.90 ·
          fees US$51.00 · spread US$5.63 · dividends net US$2,239.50 · 17 buys · days in cash 0.06%.
    XOM:  US$9,082.76 → US$13,954.00 (liquidation 13,944.02) · AUD 19,164.34 · CAGR 6.34% USD / 9.76% AUD ·
          max DD −31.87% (2014-06-23 → 2015-08-25) · vol 18.82% · Sharpe 0.42 · fees US$42.00 · spread US$5.53 ·
          dividends net US$2,027.33 · 14 buys · days in cash 0.06%.
  SANITY CHECK: S0 vs adjusted-price return — AAPL 308.13% vs 315.19% (gap 7.06 pts, relative −1.70%);
    XOM 53.63% vs 58.77% (gap 5.14 pts, relative −3.24%). Prompt's "~3 points" STOP rule TRIGGERED → investigated:
    withholding explains 5.43 / 4.32 pts (no-withholding what-if 313.56% / 57.95%); fees + spread ≈ 1.2 pts; the rest
    matches day-2 open vs close entry. Direction correct (S0 lower). Goggy accepted 2026-10-21; check now relative.
  Mutation check: withholding removed → gap shrinks by 5.43 / 4.32 pts (visible); max drawdown measured from the
  first value instead of the running peak → test_max_drawdown_with_dates fails; restored → all pass.
- PHASE 4 CHECK (2026-10-21, by Claude Code) — NOT marked Verified:
  buy-and-hold correct ✓ (S0 tests incl. reinvest rule; real runs; independent adjusted-price sanity check explained) ·
  orders follow the documented model ✓ (T close → T+1 open tests; gaps fill at open; rejections logged; EXPIRED) ·
  accounting integrates ✓ (engine drives the ledger; cash identity exact in multi-day + edge runs; golden scenario) ·
  look-ahead controls in place ✓ (truncated copy, read-only view, no price field, reusable spy check incl. same-day
  rule; same-close mutation → 9 failures) ·
  passes synthetic tests ✓ (rising, falling, sideways, gaps, split + dividend same day, cash just short, intrabar).
  → Phase 4: ready for verification

- PHASE 4 VERIFIED by chat Claude 2026-10-25: rebuilt S0 independently from the raw Tiingo CSVs with separate code
  (no engine) → AAPL US$37,069.58, XOM US$13,954.00, net dividends 2,239.50 / 2,027.33, fees 51 / 42, no-withholding
  what-if 313.56% / 57.95% — all identical to the engine to the cent. AUD 50,917.02 re-derived from liquidation value.
  All 5 roadmap criteria met.

- Steps 5.1 (S1), 5.2 (S2), 5.6 (configurable) — DONE 2026-10-25 (prompt 13, plan approved incl. read-only fill
  history; branch phase5-s1-s2, merged to main). strategies/profit_target.py: FixedProfitTarget (S1), PullbackFromPeak
  (S2) — E from the strategy's own entry fill (top-ups don't change it), sell all at close ≥ E(1+X), rebuy at
  close ≤ S(1−Y) (S1) or P(1−Y), P = running high close since the sale-fill day (S2); no top-ups in cash.
  PortfolioView.fills (read-only past fills). RunConfig profit_target_x / rebuy_dip_y on the §3 grid
  (grid_override for exploratory). Metrics: stranded (+ days), longest cash spell.
  BUG FOUND by the trade-list check + FIXED (Goggy decision 2026-10-25): AAPL's 7:1 split (2014-06-09) made the
  remembered raw prices wrong → a fake "dip" rebuy on 2014-06-10 (lowest pre-split close 222.25 never reached the
  215.89 level). E, S, P are now divided by the snapped split ratio on split days (EXPERIMENT_PLAN §2 + §10).
  The pre-fix run records stay in /data/runs/ (never deleted) but are NOT used; the report is from commit 987c81c.
  DEVELOPMENT-PERIOD RESULTS (SIMULATED, HISTORICAL, exploration only — reports/experiments/s1_s2_dev_2010-2016.md):
    S1 AAPL: beat S0 in 0/16, stranded 16/16 (sold early 2010, never rebought), excess −294.8 … −306.6 pts.
    S2 AAPL: beat S0 in 0/16, stranded 0/16, round trips 13–33, excess −62.7 … −224.5 pts.
    S1 XOM: beat S0 in 4/16 (all Y = 2%), stranded 16/16, excess −48.8 … +23.5 pts.
    S2 XOM: beat S0 in 3/16, stranded 0/16, excess −23.6 … +7.2 pts.
  No winner picked; validation/final periods not run; cost/spread sensitivity and "best 3 trades removed" = Phase 6.
  Mutation checks: S1 sells at the same day's close → 9 tests fail (incl. 6 look-ahead checks); S2 P = sale price →
  2 fail; no split adjustment → 2 fail; all restored.

- Steps 5.3 (S3) + 5.4 (S4) — DONE 2026-10-25 (prompt 14, plan approved incl. 2 Tiingo warm-up calls; branch
  phase5-s3-s4, merged to main). Warm-up data AAPL + XOM 2008-01-01 → 2009-12-31 (505 rows each, 0 missing, XOM 8
  dividends, no splits) via scripts/download_initial_dataset.py START END; loader.load_prices_with_warmup joins
  warm-up + main (join validated on the NYSE calendar; real files join 2009-12-31 → 2010-01-04 with no warnings);
  RunConfig.warmup_start + run_engine(trade_start). strategies/indicators.py: split-adjusted-as-of-T closes (never
  close_adj), z-score (window incl. T, ddof 1), SMA, strong uptrend. S3 MeanReversion (k × w grid); S4
  TrendFilteredProfitTarget / TrendFilteredPullback (no sell in a strong uptrend; S4 on all 16 X/Y — §10).
  WARM-UP PROOF: S0 ×2 + all 64 S1/S2 re-run with warm-up rows → 66 of 66 final values identical to the saved
  report, to the cent (reproductions under /data/runs/_reproductions/).
  DEVELOPMENT-PERIOD RESULTS (SIMULATED, HISTORICAL, exploration only — reports/experiments/s3_s4_dev_2010-2016.md):
    Beat S0 / stranded: AAPL S3 0/6, 5 stranded · S4-S1 0/16, 16 stranded · S4-S2 14/16, 0 stranded (5% days in cash)
                        XOM  S3 1/6, 6 stranded · S4-S1 7/16, 12 stranded · S4-S2 9/16, 0 stranded
    Filter helped (S4 − base): AAPL S4-S1 16/16, S4-S2 16/16 · XOM S4-S1 8/16, S4-S2 12/16.
  CHECKED, NOT A BUG: S4-S2 AAPL beats S0 by up to +217 pts while mostly invested — all 12 round trips of the top run
    sold above entry and 10/12 rebought cheaper; the biggest gain is the 2015-08-24 crash-day open (−18.2% vs the
    sale). Few large dips carry it → Phase 6 "best 3 trades removed" needed. Caveat written into the report.
  Mutation checks: close_adj instead of split-adjusted → 1 test fails; z window ending at T+1 (engine passes one
  extra row) → 9 look-ahead checks fail (S3, S4-S1, S4-S2); "SMA rising" dropped → 2 tests fail; all restored.

- Steps 5.5 + 5.7 + pre-registration — DONE 2026-10-25 (prompt 15, plan approved; branch phase5-close, merged):
  5.5: NO hybrid (Goggy) — EXPERIMENT_PLAN §2 + §10. 5.7: scripts/phase5_comparison.py →
  reports/experiments/phase5_comparison_dev_2010-2016.md, computed from the SAVED run records (66 at 987c81c + 78 at
  8f3cf46). CONSISTENCY PROOF: capital, period, price files + download times, broker, spread, share mode, FX source +
  files + rates, start cash, reinvest rule, min order, D8 flag, clean code and the S0 benchmark identical in every run
  (per ticker); only difference by design = S3/S4's warm-up file (66/66 proof). Roll-up: settings tried 70 per stock;
  beat S0: AAPL 14/70 (all S4-S2), XOM 24/70; plain-words multiple-testing note; no winner, no ranking.
  PRE-REGISTRATION: research/PREREGISTRATION.md v1, git tag prereg-v1 (on commit e8152d8) — written before any
  2017–2020 price data exists: S0–S4 all settings, 8 stocks, validation 2017–2020, MAIN + sensitivity, EXPERIMENT_PLAN
  §6 copied word for word (diff-checked), S3 rule-2 = at least 4 of 6 (Goggy), robustness checks 6.3–6.6, S4-S2 AAPL
  no special treatment. (The RBA 2014-2017.xls file contains 2017 FX rates; no strategy has run on them.)
  Found + fixed: saved config.yaml stored dates as text → not reloadable; writer fixed (round-trip test), old records
  read with date fields converted.
- PHASE 5 CHECK (2026-10-25, by Claude Code) — NOT marked Verified:
  each strategy has explicit rules ✓ (EXPERIMENT_PLAN §2 incl. exact S3/S4 choices + split rule; code docstrings) ·
  strategies pass independent tests ✓ (hand-worked unit tests + look-ahead spy checks; chat Claude's independent
    re-implementations: S1/S2 64 cells (63 exact, 1 rounding) + Appendix A trades; S3/S4 76 cells + both trade lists) ·
  results can be reproduced ✓ (5 random saved configs re-run → 5/5 identical final USD + AUD; warm-up proof 66/66) ·
  no winner selected by trade count ✓ (no winner selected at all; reports state roadmap 5.7) ·
  all strategies compared against buy-and-hold ✓ (every run has excess vs S0; consistency proof shows the same S0).
  → Phase 5: ready for verification

- PHASE 5 VERIFIED (2026-10-25) — Verified by chat Claude: tag prereg-v1 on e8152d8 (2026-10-25 20:56 +1100),
  PREREGISTRATION.md unchanged since the tag, no 2017–2020 price files on disk; consistency proof over 144 runs +
  5/5 reproductions accepted.
- 2026-10-25: Pre-registration change (§9, before any validation data): regime rule for H5 (Goggy's decision).

- Phase 6 data step — DONE 2026-10-25 (prompt 16, plan approved incl. the RBA trim + no after-end estimate; branch
  phase6-data, merged to main). DATA QUALITY ONLY — no strategy, backtest, metric or summary stat of 2017–2020 prices.
  Downloads: 20 Tiingo calls (MSFT KO PG INTC T SPY × 3 periods + AAPL/XOM 2017–2020) → 24 files total; 8 Yahoo requests
  (2008–2020, cache); RBA 2018-2022.xls once → kept ONLY ≤ 2020-12-31 (755 rates), original deleted.
  Validation (reports/data_validation/phase6_all_stocks_2008-2020.md): all 24 files 0 ERROR / 0 WARNING; joins
  warm-up → dev → validation clean (3,274 NYSE sessions each). Splits: AAPL 7:1 2014-06-09, AAPL 4:1 2020-08-31,
  KO 2:1 2012-08-13. Dividends: 8 / 28 / 16 per file (AAPL: 0 / 18 / 16). SPY behaves like the stocks (no splits,
  quarterly dividends). No special distributions / odd split factors (same-share-basis rule). Yahoo agrees on days,
  splits, dividend dates for all 8.
  FINDINGS: (1) Tiingo bad bar INTC 2014-06-13 (O=H=L=C=27.96, prior close repeated, volume 3.6× median; Yahoo +6.8%)
  — reported, NOT fixed; only flat bar in 24 files; the 9 checks don't detect flat bars. (2) Yahoo applies a later
  non-split adjustment to T prices (not dividends) → compared with a constant factor whose value is never reported (D8).
  (3) 2014-07-28 cross-source differences for XOM (+1.085%) and T (−1.953%). (4) First naive dividend flag rule gave 8
  false AAPL alarms (pre-split dividends) → rule fixed to one share basis before reporting.
  Stake tradeability: all 8 VERIFIED on Stake AU Wall St pages (incl. SPY). Lock: tests pass, manual 2021 run REFUSED
  before loading; 1,773 date columns/files scanned — nothing ≥ 2021-01-01; downloader now refuses END ≥ 2021-01-01.

- Phase 6 data step verified by chat Claude 2026-10-25: 24 files + 8 joins 0 ERROR/0 WARNING; NYSE sessions match;
  RBA trimmed to 2020-12-31, no ≥2021 data on disk; Stake tradeability 8/8 verified; prereg diff since tag = regime
  rule only.

- Steps 6.1–6.6 validation runs — DONE 2026-10-25 (prompt 17): CommSec double-FX bug fixed + logged in §9 BEFORE any
  run; 3,976 runs (8 stocks × 71 settings × 7 variants) from clean commit 786e699, 0 failed, 359 s. A first batch was
  set aside (data/runs/validation_ABORTED_20261025_227-dirty-records — a file I created mid-run marked 227 records
  dirty); ALL runs were restarted. Report: reports/experiments/validation_2017-2020.md (pre-registered rules unchanged).
  VERDICTS (SIMULATED, HISTORICAL, validation 2017–2020): S1 REJECTED · S2 REJECTED · S3 REJECTED · S4-S1 REJECTED ·
  S4-S2 REJECTED (R1 stocks: 0, 0, 3, 1, 1 of 8). Checked, not a bug: XOM and T never closed ≥ 2% above the Jan-2017
  entry (best later close −2.30% / −0.72%), so S1/S2/S4 never sold there (excess exactly 0).
  NOT YET DONE (usage limit): report sections not reviewed in detail; DATA/CHANGELOG notes; chat Claude re-check.

- VALIDATION VERIFIED by chat Claude 2026-10-26: all 3,976 run records from one clean commit 786e699, all end 2020-12-31.
  prereg-v1.1 tagged 21:36 before the CommSec fix (21:38, logged in §9) and the run script (21:39). Independent
  re-implementation reproduced all 8 S0 finals to the cent (AAPL 34,304.60 · MSFT 26,943.60 · KO 10,492.79 ·
  PG 13,034.01 · XOM 3,865.36 · INTC 10,600.24 · T 5,861.44 · SPY 12,681.98), Appendix B (S4-S2 AAPL 2/4: 23 fills,
  22,849.41) and Appendix C (S1 KO 3/3: 10 fills, 8,688.15) exactly. Verdict: S1, S2, S3, S4-S1, S4-S2 all REJECTED.

- Step 6.7 + Phase 6 close — DONE 2026-10-26 (prompt 18, docs + one report script):
  reports/RESULTS_SUMMARY.md (plain English; every number copied from a generated report with its section);
  research/FAILED_EXPERIMENTS.md (S1–S4 verdicts, S0 sanity trip + 5%→1% rule, split-as-dip, CommSec double FX,
  aborted 227-dirty batch, one-cent withholding); research/FINAL_TEST_OPTIONS.md (options a/b, neutral — NO
  decision, NO unlock); scripts/validation_headline.py → reports/experiments/validation_headline_2017-2020.md
  (headline table + S0 USD/AUD from saved run records); README "Findings so far".
  PHASE 6 CHECK (report only, not marked Verified): out-of-sample results reported ✓ (validation report §1–§2) ·
  cost sensitivity documented ✓ (§4, 7 variants) · parameter sensitivity documented ✓ (§3 grids) · limitations
  explicit ✓ (RESULTS_SUMMARY §5, DATA_SOURCES §8) · not presented as proof of future profitability ✓
  ("simulated, historical" + not-financial-advice lines) → Phase 6: ready for verification.

- Phase 7 Steps 7.1 + 7.2 — DONE 2026-10-26 (prompt 19; data + calculations only, no ranking):
  SEC EDGAR companyfacts for 7 companies (SPY = fund, excluded from 7.1), facts filed > 2020-12-31 dropped before
  saving (DATA_SOURCES §11). CIKs: AAPL 320193 · MSFT 789019 · KO 21344 · PG 80424 · XOM 34088 (override: SEC's
  list today maps XOM to ExxonMobil Holdings Corp 2115436 — nothing before 2021) · INTC 50863 · T 732717.
  Point-in-time rule (filed strictly before T; restatements from their own filing date) + 8 indicators in
  src/quant_research/screening/fundamentals.py; trading indicators in screening/trading.py.
  Report: reports/screening/indicators_2010-2020.md — coverage F 385 · fallback 174 · MISSING 21 · CONFLICT 4.
  Bug found + fixed during the step: fiscal-year detection picked stray facts dated after the filing (INTC, PG, T)
  → rule now "latest year end before the filing (≤ 180 days), ≥ 5 facts". Revenue tags that disagree > 0.5%
  → CONFLICT (PG FY2014 `Revenues` 29.4bn vs `SalesRevenueNet` 83.1bn; XOM FY2019).

- Steps 7.1–7.2 checked by chat Claude 2026-10-26 against the filings: AAPL FY2019 — all 10 sampled values match Apple's
  FY19 consolidated statements (net sales 260,174; NI 55,256; EPS 11.89 / FY18 11.91; assets 338,516; liabilities 248,028;
  current assets 162,819; current liabilities 105,718; OCF 69,391; capex 10,495). KO FY2019 balance sheet matches the 10-K
  (R4: assets 86,381; total equity incl. NCI 21,098; current assets 20,411; current liabilities 26,973); NI 8,920 matches.
  Open-question rulings (chat Claude, 2026-10-26): CONFLICT values (PG FY2014, XOM FY2019 revenue) are NOT used in any
  score — treated as unavailable; T FY2016 NI stays MISSING (later-filed data can't be used for that year); INTC
  liabilities fallback kept as a labelled ASSUMPTION (no material non-controlling interest before 2022).

- Phase 7 Steps 7.3–7.5 + Phase 7 check — DONE 2026-10-26 (prompt 20):
  research/SCREENING_METHOD.md v1 committed BEFORE any score (f66e267, pushed on the branch). screening/score.py
  (rank sub-scores with tie averaging, ≥ 4-of-5 rule, "why" lines, Spearman, as-of 10-K selection).
  scripts/build_screening.py → reports/screening/screening_2010-2020.md: scores per 31 Dec 2009–2020 (2009 only
  for the development comparison — only AAPL had an XBRL 10-K, so that score is the neutral 0.5), selection-bias
  section, company comparison, Spearman (8 points, not evidence), Q4.11 answer: no stock type where any strategy
  reliably beat buy-and-hold; 5 of 40 strategy–stock pairs above 0 in validation (S4-S1 INTC, S3 T/XOM/INTC,
  S4-S2 MSFT), 0 above 0 in both periods. research/IDEAS_FOR_LATER.md (3 untested hypotheses). DATA_SOURCES §8: 3 rows.
  Fixed during the step: a pre-written "falling stocks" sentence contradicted the data (INTC, MSFT rose) → the
  paragraph is now computed.
  PHASE 7 CHECK (report only, not marked Verified): screening criteria documented ✓ (SCREENING_METHOD.md, report §1)
  · rankings explainable ✓ (computed "why" line + sub-scores for every company and date, §3) · data limitations
  visible ✓ (report §8, indicators report §4, DATA_SOURCES §8/§11) · historical conclusions account for selection
  bias where possible ✓ (point-in-time filings + tests, XOM CIK, survivors + hindsight stated, fair-universe needs
  listed as a limitation — not fixable with free data) → Phase 7: ready for verification.

- PHASE 7 VERIFIED (2026-10-26) — Verified by chat Claude: SCREENING_METHOD.md committed alone in f66e267 (16:57)
  before the scoring code + scores in 3ef65c2 (17:01); the 5 positive strategy–stock pairs of 40 re-computed from the
  run records (S4-S1 INTC +63.4, S3 T +25.2, S3 XOM +16.9, S3 INTC +3.6, S4-S2 MSFT +1.9) — identical. All 4 roadmap
  criteria met.

- Phase 8 Steps 8.1, 8.2, 8.4, 8.5 — DONE 2026-10-26 (prompt 21): Streamlit dashboard that VIEWS saved results.
  uv group `dashboard` (streamlit 1.66.1, altair 6.3.0 — altair is already a streamlit dependency). Pages: Overview
  (key results, pre-registered verdict table copied from the validation report, write-ups), Company research
  (screening scores / why lines / MISSING-CONFLICT reasons / trading profile), Performance (equity vs S0 USD/AUD,
  drawdown, cash vs invested, cumulative fees + spread; dividends: run total only — per day "not available"),
  Trade explorer (fills, orders incl. EXPIRED with reasons, one trade's effect on cash and position).
  src/quant_research/dashboard/data.py: read-only shaping; numbers via metrics/ (new metrics.drawdown_series, tested
  = max_drawdown) and screening/; D8 guard (LockedPeriodError). .streamlit/config.toml: localhost, no usage stats.
  Consistency test S4-S2 AAPL 2%/4%: final US$22,849.41 and 23 fills = validation report Appendix B; S0 AAPL max DD
  −38.46% = report §2. Smoke check (scripts/smoke_dashboard.py, Streamlit AppTest): 4 pages, 0 errors, banner on each.
  Real server: health endpoint "ok" (HTTP 200) on localhost:8501.
  Screenshots (Goggy approved Playwright Chromium, project only, 2026-10-26): uv group `screenshots` (playwright
  1.64.1), browser in git-ignored .playwright-browsers/ (581 MB); scripts/dashboard_screenshots.py → 4 PNGs in
  data/screenshots/ (git-ignored), each on S4-S2 · AAPL · X 2% / Y 4% (validation). Checked by eye: final
  US$22,849.41, start US$7,200.18, 23 fills / 23 FILLED orders. Long Overview values moved out of the number tiles
  (they were cut off with "…").
  Browser check afterwards (in-app browser attached to the running server — the preview launcher may not read the
  Desktop folder, so the server is started from the shell): fixed 3 things — sidebar choice now survives page changes,
  page folder renamed pages/ → views/ (Streamlit auto-listed raw file names), "Deploy" button hidden
  (client.toolbarMode = minimal); verdict table shown without the report's heading line (+ test).

- Steps 8.1, 8.2, 8.4, 8.5 checked by chat Claude 2026-10-26 from the 4 screenshots: Overview final US$22,849.41,
  10 round trips, fees 69.00 (23 × 3), CAGR 33.55% consistent with 217.34% over 4 years; Trade explorer 23 fills /
  23 orders, trade #1 = Appendix B; banner, verdicts and assumptions visible on every page.

- Phase 8 Steps 8.3, 8.6, 8.7 + polish + Phase 8 check — DONE 2026-10-26 (prompt 22):
  Polish (commit 22e90ed): money in cents (portfolio.money.to_display), shares 6 dp, prices as stored; "—" for P&L on
  buys; plain chart labels; "Costs" chart (dividends are saved only as a run total — no per-day line, no new maths);
  full-width drawdown chart with S0 as a second line.
  Strategy lab (dashboard/lab.py + views/lab.py): any X/Y/k/w, development or validation only, 7 cost variants (same
  as scripts/run_validation.py — tested); runs ONLY via backtesting.run.run_backtest together with S0 on the same
  settings; saved under data/runs/lab/ with lab.json "EXPLORATORY — NOT PRE-REGISTERED"; off-grid settings use run.py's
  grid_override; dirty tree → warning + recorded dirty (D6). Engine lock tested through the lab (2021 refused before
  any data loads). Demo lab run S4-S2 AAPL validation main 2%/4% → US$22,849.41 (identical to the pre-registered run;
  paired S0 US$34,304.60 = Appendix A), recorded clean.
  Reports (reporting/run_report.py) + exports (dashboard/export.py): report.md, trades.csv, orders.csv, equity.csv,
  config.yaml, chart.png (vl-convert-python), LICENCE.txt → data/exports/<run id>/ (git-ignored), licence header on
  every text file. Round trip: exported config.yaml → run.py → US$22,849.41, same AUD, fees, 23 fills (test).
  Fixed during the step: two "US$" on one Markdown line rendered as a maths formula → report line split, "$" escaped
  in previews. Screenshots: 6 PNGs in data/screenshots/ (git-ignored).
  PHASE 8 CHECK (report only, not marked Verified): dashboard uses the validated engine ✓ (lab runs only via
  run_backtest; views read run records) · results consistent with independent calculations ✓ (Appendix B consistency
  test: 22,849.41 / 23 fills; S0 max DD −38.46% = report; lab rerun identical; chat Claude's screenshot checks) ·
  important assumptions visible ✓ (assumptions box on every results page, banner on every page) · failed experiments
  not hidden ✓ (REJECTED verdict table on Overview + lab, FAILED_EXPERIMENTS linked) · results exportable and
  reproducible ✓ (6 export files + licence; config round-trip test) → Phase 8: ready for verification.

- DECISION 2026-10-27 (Goggy): Phase 9 scope = free sources only — market context from existing data + company events from SEC 8-K filings (item codes + acceptance time). Optional AI labelling of 8-K text = exploratory side test later.
- PHASE 9 PLAN: 23 = data + features + leakage rules (no backtests, no return analysis) · 24 = pre-registration v2 of the Phase 9 strategies (before any backtest with the new data) · 25 = runs, comparisons (9.5–9.6), Phase 9 check; then the one-time final test 2021+ for everything (Goggy unlocks).

- Phase 9 Steps 9.1–9.4 — DONE 2026-10-27 (prompt 23; data + features + leakage rules ONLY — no returns, no
  backtests, nothing about what happened after events):
  8-K / 8-K/A lists for 7 companies from the SEC submissions API (older pages followed; fields checked in the real JSON:
  form, filingDate, acceptanceDateTime, items, accessionNumber, primaryDocument, reportDate). D8 trim at download:
  AAPL 49 · MSFT 54 · KO 75 · PG 114 · XOM 93 · INTC 94 · T 111 dropped; 1,359 filings in 2010–2020 (1,341 8-K, 18 8-K/A).
  TIMEZONE: acceptanceDateTime is TRUE UTC — Apple earnings 8-Ks 2019-10-30T20:30:40Z (EDT) and 2020-01-28T21:30:40Z
  (EST) both = 16:30:40 ET; converted to US/Eastern (tests incl. a DST switch).
  Categories from the official item codes (SEC Form 8-K, SEC 873 (02-25)); pre-2004 codes 1/2/4/5/7/9/12 reported
  as UNRECOGNISED (all 1994–2004, none in 2010–2020). Timing 2010–2020: 331 before open · 340 during trading ·
  688 after close · 0 non-trading day.
  Availability rule (DATA_SOURCES §12): usable at the close of the first NYSE day whose close (16:00, 13:00 on early
  closes — stricter than a fixed 16:00) is after acceptance; 8-K/A = own event. Events spy check
  check_events_no_lookahead catches a leaky decision. Market context features (news/context.py; new indicator
  functions in strategies/indicators.py): full coverage 2010–2020 for all 8 tickers (warm-up from 2008 data).
  Report: reports/phase9/context_and_events_2010-2020.md (counts + timing only).
- Steps 9.1–9.4 checked by chat Claude 2026-10-28: UTC evidence accepted (Apple 16:30 NY release = 20:30Z in Oct 2019,
  21:30Z in Jan 2020). Rulings: (1) AT&T 8-K 2012-01-13 (accession 0000732717-12-000006) is tagged item 1.03 but its own
  heading reads 'Item 1.03 Entry into a Material Definitive Agreement' and it concerns reducing a US$5bn credit facility to
  US$3bn — a filer coding error; reclassify THIS filing only to 'deal signed (1.01-type), reclassified' via a logged
  override list with the SEC URL https://www.sec.gov/Archives/edgar/data/732717/000073271712000006/creditfacility_8k.htm.
  (2) XOM's higher 2.02 count is real: ~7 per year to 2016 (quarterly results + extra annual/reserves updates, filed as
  2.02 + 7.01) — keep as filed; note it.
- Prompt 24 — DONE 2026-10-28 (labels + PRE-REGISTRATION v2 + C1/C2/E1 code; NO real-data strategy runs):
  PART 0 plain-English names (display only; IDs unchanged everywhere): strategies/labels.py — S0 Buy-and-hold ·
  S1 Profit target · S2 Pullback from peak · S3 Mean reversion · S4-S1 Trend filter + profit target · S4-S2 Trend
  filter + pullback · C1 Market-trend gate · C2 Market-gated pullback · E1 Earnings cool-off; shown as "Name (ID)" with
  the one-liner under every strategy menu / heading; dashboard (all pages, menus, tables, chart legends), run report,
  exports. Smoke check now fails on any ID shown without its name (checked: breaking it gives FAIL). Commit e689d19.
  PART A research/PREREGISTRATION_V2.md, tag **prereg-v2** = commit 4497870 (2026-10-28 16:27:46 +1100), pushed —
  before any C1/C2/E1 run on real data. H7 judged per strategy vs its TWIN (C1 vs S0; C2, E1 vs S4-S2, same 16 X/Y),
  validation 2017–2020, R1–R6 as PREREGISTRATION §9; also reported vs S0 (descriptive). Decisions 1–5 (Goggy):
  E1 cool-off = usable day + next trading day; E1 does not block entry / dividend top-ups, P keeps updating, 8-K/A
  counts; C2 day-1 entry not blocked; C1 starts in cash if the SPY condition is false; missing SPY day → run stops.
  PART B strategies/information.py (C1 MarketTrendGate, C2 MarketGatedPullback, E1 EarningsCoolOff), registry +
  config (c1_market_gate, c2_market_gated_pullback, e1_earnings_cooloff) + lab; SPY / events loaded only after the
  D8 lock check; backtesting.lookahead.check_market_no_lookahead; news/events.py OVERRIDES (AT&T 1.03 → reclassified,
  Phase 9 report regenerated: only that row moved) + load_events. Load-only wiring check (no strategy run): SPY
  2015-01-02 → 2020-12-31 (1,511 rows); T events 547, bankruptcy 0, reclassified 1.
- Prompt 24 verified by chat Claude 2026-10-28: prereg-v2 tag on 4497870 (16:27:46 +1100); no C1/C2/E1 run records
  exist before it; labels shipped (display only).
- Phase 9 Steps 9.5–9.6 — DONE 2026-10-28 (prompt 25; rules exactly PREREGISTRATION_V2, tag prereg-v2):
  3,200 runs from clean commit 3b86c53 (validation: C1 8 + C2 128 + E1 128 + twins S0 8 + S4-S2 128 = 400 × 7 variants
  = 2,800; development MAIN 400), 0 failed, 250 s, under data/runs/phase9/. Run script kept OUTSIDE the repo during the
  batch, copied in afterwards (sha256 6bed0791…66a6 = file that ran; then ruff-formatted → 1252506c…10c3, same program
  checked by AST comparison). TWIN CONSISTENCY: all 952 twin runs (136 MAIN) identical to the Phase 6 records (final
  USD + AUD to the cent, every fill), e.g. S0 AAPL 34,304.60, S4-S2 AAPL 2/4 22,849.41.
  VERDICTS vs twin (SIMULATED, HISTORICAL, validation 2017–2020, prices already seen for the twins): C1 Market-trend
  gate REJECTED (R1 1/8; median −43.4 pp vs S0) · C2 Market-gated pullback REJECTED (R1 1/8; −0.5 pp) · E1 Earnings
  cool-off REJECTED (R1 3/8, R2 13/16 but R4/R5/R6 fail; +0.0 pp) → H7 NOT supported for any of the three.
  Report: reports/experiments/phase9_information_2017-2020.md (verdicts, 9.5 vs twin + vs S0, 9.6 per variant / top-3
  trades / regime / dev vs val, appendix: C1 finals, C1 AAPL + E1 KO 3/3 trade lists with the earnings events behind
  the 2 skipped signals). Dashboard shows the Phase 9 runs (names) + Phase 9 verdict table on Overview.
  PART D AI labelling side test (EXPLORATORY, Goggy approved): 40 random 2010–2020 8-Ks (seed 20261028), item codes +
  official titles masked, labelled by Claude Code (claude-opus-5-5) → 37/40 exact agreement with the item codes, 40/40
  share ≥ 1 category; 3 disagreements listed for Goggy's spot-check; 5 masking leaks (titles split over a line break)
  reported. reports/phase9/ai_labels_sample.md.
  PHASE 9 CHECK (report only, NOT marked Verified): news sources + limitations documented ✓ (DATA_SOURCES §12, Phase 9
  report §9) · historical decisions use only available information ✓ (availability rule tests, events spy check, SPY
  spy check, 3 mutation checks in prompt 24) · AI interpretations distinguished from verified facts ✓ (AI labels only
  in the exploratory side test, never in any verdict; item codes = facts) · added complexity justified by evidence or
  labelled exploratory ✓ (pre-registered test said NO for C1/C2/E1 — not adopted).
- Phase 9 VERIFIED by chat Claude 2026-10-28: 3,200 runs from clean 3b86c53; independent re-implementation
  reproduced all 8 C1 finals (AAPL 27,274.87 · MSFT 18,995.15 · KO 9,694.31 · PG 9,003.55 · XOM 3,764.25 · INTC 6,675.66 ·
  T 6,181.34 · SPY 10,360.50) and all 27 C1 AAPL trades exactly. C1, C2, E1 REJECTED vs twins; H7 not supported.
- FINAL TEST pre-registration written 2026-10-28 BEFORE any 2021+ data: research/FINAL_TEST_PREREG.md (tag
  prereg-final) — 2021 → 2025-12-31, 7 stocks (T excluded: 2022 spin-off), thresholds ≥ 6 of 7 / REJECTED ≤ 2 of 7,
  rules otherwise unchanged, 5,096 runs, run ONCE.
- FINAL TEST 2021–2025 — DONE 2026-10-28 (prompt 26), run ONCE:
  ORDER: tag prereg-final 16:48:19 +1100 (commit 17d62ed) → first 2021+ download 18:51:52 +1100. (The three
  "period will be USED" notes in PREREGISTRATION §9 / FINAL_TEST_OPTIONS / DATA_SOURCES missed the tagged commit
  because my edit script stopped part-way; added in 726c16b at 16:48:42, still before any download. The binding rules
  file FINAL_TEST_PREREG.md, incl. its "USED" section, is in the tag.)
  DATA (reports/data_validation/final_2021-2025.md): Tiingo 7 stocks × 1,255 sessions, 0 ERROR, 1 WARNING (INTC
  2024-08-02 −26.1%, real; Yahoo agrees), no split rows, joins to 2020 with no gap, Yahoo 0 day/split differences and
  0 closes > 0.5% apart; INTC dividend stopped in 2024 (not an unsupported action); 0 corporate-action flags. RBA
  1,254 rates 2021-01-04 → 2025-12-31 (official files trimmed, 207 rows of 2026 never saved; curl used — certificate
  check kept on). SEC 8-Ks to 2025-12-31: Exxon's new holding company CIK 2115436 filed no 8-K before 2026 → all
  2021–2025 Exxon 8-Ks are from CIK 34088. Goggy approved the data report before any run.
  RUNS: 5,096 (7 stocks × 104 settings × 7 variants) from clean commit b3287e4, 0 failed, 363 s; run script outside
  the repo during the batch (sha256 6366c484… = file that ran; ruff-formatted copy fdec5961…, same program by AST).
  VERDICTS (SIMULATED, HISTORICAL, FINAL TEST; reports/experiments/FINAL_TEST_2021-2025.md): S1 REJECTED (R1 2/7) ·
  S2 REJECTED (2/7) · S3 REJECTED (2/7) · S4-S1 REJECTED (2/7) · S4-S2 REJECTED (0/7) · C1 REJECTED (2/7) · C2 REJECTED
  (1/7) · E1 REJECTED (2/7). No verdict changed from validation. H1, H3, H4, H7 rejected; H2, H5, H6 not judged.
  Start: AUD 10,000 at RBA 0.7701 (2021-01-05) → US$7,658.64. S0 finals: AAPL 16,485.23 · MSFT 17,613.26 ·
  KO 11,559.85 · PG 8,798.98 · XOM 26,057.70 · INTC 6,305.17 · SPY 14,963.53.
  Dashboard: period picker final / validation / development (final page may show 2021–2025, nothing ≥ 2026).
  2021–2025 is now USED — nothing later run on it is out-of-sample.
- FINAL TEST VERIFIED by chat Claude 2026-10-28: prereg-final tagged 17d62ed at 16:48:19 +1100, first 2021+ download
  07:51:54Z (18:51:54 +1100); T not downloaded; 5,096 runs from clean b3287e4. Independent re-implementation reproduced
  all 7 S0 finals (AAPL 16,485.23 · MSFT 17,613.26 · KO 11,559.85 · PG 8,798.98 · XOM 26,057.70 · INTC 6,305.17 ·
  SPY 14,963.53) and all 23 C1 SPY trades (final 13,005.76) exactly. All 8 strategies REJECTED in both validation and
  final test. The 3 'used' notes committed 23 s after the tag, before any download — accepted.
- Phase 10 (Steps 10.1–10.6) — DONE 2026-10-28 (prompt 27; no new research, no runs on 2021+):
  10.1 tests/integration/: end-to-end on made-up data (mocked Tiingo → save → loader+validation → run_backtest S0 + S4-S2
  → run record → metrics → report → dashboard data), every value by hand (S4-S2 last close US$7,501.74, AUD 10,648.25;
  S0 US$7,093.05, AUD 10,067.92); replay of 20 seeded saved runs (validation/phase9/final) → identical finals and fills
  (skips without data/). 10.2 tests/test_error_handling.py (34 cases). FIXES: (1) registry read the 2020 8-K files for
  every config — a final-test E1 config re-run from its saved settings would silently miss 2021–2025 earnings (the
  final batch itself passed the 2025 events directly, so no result changes; mutation: old behaviour → 1 replay fails);
  (2) invalid JSON from Tiingo / SEC; (3) non-numeric Tiingo values; (4) empty CSV / no date column / bad dates;
  (5) broken or non-mapping YAML; (6) unknown strategy / broker / spread / share mode and AUD ≤ 0 now refused by
  parse_config (were accepted, failed mid-run); (7) unreadable RBA file — all now clear messages.
  10.3 scripts/scan_secrets.py over ALL refs (8 refs, 4 tags, 95 commits, 516 file versions; real Tiingo key + SEC
  email from .env checked without printing): 0 findings (one named exemption: the scanner's own self-test with FAKE
  shapes, real values still checked there); no data/, .env, Excel or price CSV ever committed. uvx pip-audit 2.10.1 on
  65 locked packages: no known vulnerabilities. gh: repo PRIVATE.
  10.4 scripts/reproduce_reports.py: 11/12 generated reports byte-identical, 1 (2010-2016_AAPL_XOM.md) differs only in
  its "generated on" date; 6 not regenerated, each with its reason. reports/ENVIRONMENT.md (Python 3.13.16, uv 0.13.2,
  64 packages). Fresh clone: uv sync --all-groups → 428 passed, 22 skipped (data-dependent, reasons printed); plain
  uv sync → 431 passed, 23 skipped.
  10.5 performance table in PROJECT_GUIDE §2 (suite ≈ 17 s, one backtest 0.6–0.9 s, batches 249–362 s, dashboard pages
  ≤ 1.1 s) — nothing optimised. --help on all 28 scripts (scripts/_help.py; describes + exits, does nothing else).
  10.6 RESEARCH_METHODOLOGY.md + TESTING.md created; README updated (final-test findings, .env keys, groups, fresh
  clone note, period picker, six pages); PROJECT_GUIDE folder map rewritten from the real tree (research/ module never
  created); every command in README / PROJECT_GUIDE / TESTING checked to exist and run.
  PHASE 10 CHECK (report only, NOT marked Verified): core workflows reproducible ✓ (replay 20/20, reports 11/12 + 1
  date stamp, fresh clone) · integration tests pass ✓ · important failures handled clearly ✓ (34 cases, 7 fixes) ·
  secrets / licensed data protected ✓ (history scan 0, pip-audit clean, repo private) · known limitations documented ✓
  (DATA_SOURCES §8, TESTING.md "not tested", RESULTS_SUMMARY §5).

IN PROGRESS:
- none (Phase 9 ready for verification)

BLOCKED / OPEN QUESTIONS:
- (resolved 2026-10-26, see the Steps 7.1–7.2 check) T FY2016 NI, PG FY2014 / XOM FY2019 revenue CONFLICT, INTC liabilities.
- Stake fractional-share precision UNVERIFIED (D3 assumes 6 dp — check in Phase 3)
- RBA 2018–2020: done (trimmed from 2018-2022.xls). 2021+ rates NOT downloaded — needed only for the final test (D8).
- (1) INTC 2014-06-13 bad Tiingo bar (flat O=H=L=C, prior close repeated) — DEVELOPMENT period only, so it does not
  touch the validation judgement; left unchanged, documented (DATA_SOURCES §8).
- (2) BEFORE any final-test unlock: check 2021+ corporate actions the ledger doesn't support (e.g. AT&T's 2022
  WarnerMedia spin-off is public knowledge) — decide how to handle T in the final test before looking at any results.
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
- DECISION 2026-10-27 (Goggy): Phase 9 scope = free sources only — market context from existing data + company events from SEC 8-K filings (item codes + acceptance time). Optional AI labelling of 8-K text = exploratory side test later.
- 2026-10-28 (Goggy): PRE-REGISTRATION v2 approved and tagged prereg-v2 (C1, C2, E1 vs twins; decisions 1–5 —
  research/PREREGISTRATION_V2.md). Strategy display names (display only) approved — strategies/labels.py.
- DECISION 2026-10-26 (Goggy): final test 2021+ stays LOCKED until after Phase 9; then it is run ONCE for S1–S4 and any Phase 9 model together, under a new pre-registration tag. Until then nothing dated ≥ 2021-01-01 is downloaded, stored or summarised.
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
- 2026-10-21: Dividend reinvestment only when cash ≥ US$100 (reinvest_min_cash_usd), every strategy (Goggy, option b).
- 2026-10-21: S0 sanity gap (7.06 / 5.14 pts) accepted by Goggy after investigation; check uses a relative limit (5%).
- 2026-10-25: Phase 2 report reports/data_validation/2010-2016_AAPL_XOM.md regenerated WITHOUT the after-the-end
  estimates and the Yahoo later-split ratio / per-stretch factors (Goggy, consistency with the D8 decision of the same
  day). All other numbers identical (diff-checked); INFO counts AAPL 5→4, XOM 3→2. Left as historical log entries (not
  edited): PROJECT_STATUS Step 2.3 findings (×4.35 gap — measured to the 2026 download date, so it includes post-2020
  dividends), DATA_SOURCES §2/§8 notes on AAPL's later 4:1 split (2020-08-31 = validation period, now seen in-table).
- 2026-10-25: PRE-REGISTRATION v1 frozen (research/PREREGISTRATION.md, tag prereg-v1); S3 rule-2 = ≥ 4 of 6 (Goggy).
- 2026-10-25: Step 5.5 — NO hybrid (S5) strategy (Goggy): S4 already combines trend filter + profit target; more
  variants on the same data raise the fluke risk. S0–S4 frozen for validation.
- 2026-10-25: S1/S2 remembered prices (E, S, P) are divided by the snapped split ratio on split days (Goggy).
- 2026-10-25: Sanity rule changed, approved by Goggy (chat Claude: 5% too loose): (1) S0 < adjusted-price return;
  (2) no-withholding what-if within 1.0% relative of the adjusted return. Re-run: AAPL −0.39%, XOM −0.52% — pass;
  S0 numbers identical (308.13% / 53.63%), only the check text changed.
- 2026-10-21: S0 "buy at the first open" = first possible open after the first close (EXPERIMENT_PLAN §10).
- 2026-10-20: Dividend withholding = 15% of the gross rounded DOWN to cents, then rounded UP (Goggy, golden scenario).
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
- Chat Claude verifies Phase 10; then Phase 11 (prompt 28): README polish, demo, diagrams, CV bullets, interview prep,
  decide public vs private.

TESTS RUN (2026-10-28, prompt 27 — Phase 10):
- uv run pytest -q → 454 passed in 17.15s · uv run ruff check . → All checks passed! ·
  uv run ruff format --check . → 191 files already formatted · smoke_dashboard → PASS · scan_secrets → findings: 0 ·
  reproduce_reports → 11 identical + 1 date stamp · fresh clone (--all-groups) → 428 passed, 22 skipped.

TESTS RUN (2026-10-28, prompt 26 — final test):
- uv run pytest -q → 392 passed in 4.47s · uv run ruff check . → All checks passed! ·
  uv run ruff format --check . → 178 files already formatted · smoke_dashboard → 6 pages, 0 errors, bare IDs none,
  PASS (final period default); S1 / S4-S2 / C1 / E1 final runs opened on the report page → 0 exceptions.
  validate_final_data → 0 errors, 0 corporate-action flags. report_final_test → all checks passed (5,096 runs, one
  clean commit, every run 2021-01-04 → 2025-12-31, final_test_unlocked only in these configs).

TESTS RUN (2026-10-28, prompt 25):
- uv run pytest -q → 388 passed in 4.51s · uv run ruff check . → All checks passed! ·
  uv run ruff format --check . → 171 files already formatted · smoke_dashboard → 6 pages, 0 errors, bare IDs none,
  PASS; C1 + E1 runs opened on 4 pages headless → 0 exceptions. report_phase9 → twin consistency 952/952, 0 differences.

TESTS RUN (2026-10-28, prompt 24):
- uv run pytest -q → 387 passed in 4.15s · uv run ruff check . → All checks passed! ·
  uv run ruff format --check . → 165 files already formatted · smoke_dashboard → 6 pages, 0 errors, bare strategy
  IDs none, PASS. Mutations (each restored): E1 uses the filing date → 3 tests fail (incl. events spy check);
  C1 reads SPY up to the next day → 5 fail (incl. market spy check); C2 ignores the SPY gate → 1 fails; smoke check
  with the raw verdict table → FAIL (5 bare IDs); menu without names → FAIL (24).

TESTS RUN (2026-10-27, Steps 9.1–9.4):
- uv run pytest -q → 366 passed in 5.08s · uv run ruff check . → All checks passed! ·
  uv run ruff format --check . → 159 files already formatted. Mutation: event at exactly 16:00:00 counted at that
  close (< → <=) → 1 test fails (restored).

TESTS RUN (2026-10-26, Steps 8.3, 8.6, 8.7):
- uv run pytest -q → 341 passed in 4.90s · uv run --group dashboard pytest -q tests/dashboard → 20 passed ·
  uv run ruff check . → All checks passed! · uv run ruff format --check . → 149 files already formatted ·
  uv run --group dashboard python scripts/smoke_dashboard.py → 6 pages, 0 errors, smoke check: PASS.

TESTS RUN (2026-10-26, Steps 8.1, 8.2, 8.4, 8.5):
- uv run pytest -q → 329 passed in 2.38s · uv run ruff check . → All checks passed! ·
  uv run ruff format --check . → 139 files already formatted ·
  uv run --group dashboard python scripts/smoke_dashboard.py → 4 pages, 0 errors, smoke check: PASS.

TESTS RUN (2026-10-26, Steps 7.3–7.5):
- uv run pytest -q → 320 passed in 2.51s · uv run ruff check . → All checks passed! ·
  uv run ruff format --check . → 127 files already formatted. Mutation: as-of filter "filed <= D" → 1 test fails (restored).

TESTS RUN (2026-10-26, Steps 7.1–7.2):
- uv run pytest -q → 310 passed in 2.28s · uv run ruff check . → All checks passed! ·
  uv run ruff format --check . → 120 files already formatted. Mutation checks: "filed <= T" usable → 2 tests fail;
  returns without split ratio → 3 tests fail (both restored).

PHASE 6 VERIFIED by chat Claude 2026-10-26: main at abd0d8d. Re-computed from the 640 MAIN run records: median excess
S1 −43.9 · S2 −12.1 · S3 −19.4 · S4-S1 −32.2 · S4-S2 −2.3; stranded 96 · 47 · 38 · 93 · 7 — identical to
RESULTS_SUMMARY / validation_headline. All 5 roadmap criteria met.

TESTS RUN (2026-10-26, Step 6.7 / Phase 6 close):
- uv run pytest -q → 275 passed in 2.24s · uv run ruff check . → All checks passed! ·
  uv run ruff format --check . → 109 files already formatted. No logic changed (docs + one report script).

TESTS RUN (2026-10-25, Phase 6 data step):
- uv run pytest → "269 passed in 2.23s" · ruff check → "All checks passed!" · ruff format --check → "99 files already formatted"
- scripts/validate_phase6_data.py → 24 files + 8 joins: 0 ERROR, 0 WARNING; 0 flags; 1 flat bar (INTC 2014-06-13)
- lock: 2 lock tests pass; manual 2021-03-31 run REFUSED (loader not called); 0 dates ≥ 2021-01-01 on disk

TESTS RUN (2026-10-25, Steps 5.5–5.7):
- uv run pytest → "267 passed in 3.40s" (+ config.yaml round-trip test)
- uv run ruff check . → "All checks passed!" · uv run ruff format --check . → "96 files already formatted"
- scripts/phase5_comparison.py → consistency proof passed, reproducibility 5/5 identical

TESTS RUN (2026-10-25, Steps 5.3–5.4):
- uv run pytest → "266 passed in 2.13s" (+ indicators 7, s3_s4 12, loader warm-up 3, engine 2, run 1)
- uv run ruff check . → "All checks passed!" · uv run ruff format --check . → "92 files already formatted"
- scripts/run_s3_s4_dev.py → 78 runs (76 S3/S4 + 2 S0) + 64 reproductions; warm-up proof 66/66; commit 8f3cf46 (clean)

TESTS RUN (2026-10-25, Steps 5.1–5.2):
- uv run pytest → "241 passed in 2.22s" (+ profit_target 14, metrics +2, run +1)
- uv run ruff check . → "All checks passed!" · uv run ruff format --check . → "85 files already formatted"
- scripts/run_s1_s2_dev.py → 66 runs (64 S1/S2 + 2 S0), report written, code commit 987c81c (clean)

TESTS RUN (2026-10-21, Steps 4.4–4.6):
- uv run pytest → "224 passed in 1.53s" (+ fx 7, buy_and_hold 6, performance 10, edge_cases 11, run +1)
- uv run ruff check . → "All checks passed!" · uv run ruff format --check . → "80 files already formatted"
- scripts/run_s0_dev.py --report → real runs AAPL + XOM, sanity check passed (relative rule), report written

TESTS RUN (2026-10-21, Steps 4.1–4.3):
- uv run pytest → "189 passed in 1.39s" (backtesting: engine 15, fills 18, run 5; accounting 73; data 78)
- uv run ruff check . → "All checks passed!" · uv run ruff format --check . → "65 files already formatted"
- Mutation: fill at T's close → "9 failed, 29 passed" (backtesting); restored → 38 passed

TESTS RUN (2026-10-20, Steps 3.7–3.8):
- uv run pytest → "151 passed in 1.49s" (accounting 73: corporate_actions 17, costs 15, golden 2, ledger 22,
  money 8, valuation 9; data 78)
- uv run ruff check . → "All checks passed!" · uv run ruff format --check . → "54 files already formatted"
- Mutation: market value UP → "3 failed, 70 passed"; unrealised sign flip → "4 failed, 69 passed"; restored → 73 passed

TESTS RUN (2026-10-20, Steps 3.4–3.6):
- uv run pytest → "139 passed in 1.50s" (accounting: corporate_actions 16, costs 15, ledger 22, money 8; + 78 data)
- uv run ruff check . → "All checks passed!" · uv run ruff format --check . → "50 files already formatted"
- Mutation check: withholding DOWN → "5 failed, 56 passed"; split basis × ratio → "4 failed, 57 passed"; restored → 61 passed

TESTS RUN (2026-10-20, Steps 3.1–3.3):
- uv run pytest → "107 passed in 1.12s" (accounting/test_ledger 21, accounting/test_money 8, + 78 earlier)
- uv run ruff check . → first run "Found 12 errors" (FURB157: Decimal("10") → Decimal(10), style only) → fixed →
  "All checks passed!" · uv run ruff format --check . → "44 files already formatted"

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
