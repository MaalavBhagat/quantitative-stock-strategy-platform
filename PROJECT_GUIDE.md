# PROJECT_GUIDE.md — how we write code in this project (Phase 1, Step 1.4)
Status: v1.1 — 2026-10-20. Conventions D1–D9 approved by Goggy 2026-10-20 (summary in §9).
Rules for Claude Code live in [CLAUDE.md](CLAUDE.md) — this guide adds the *how*, it does not repeat them.
Labels: [ASSUMPTION] = our choice, can change · [UNVERIFIED] = fact still to check.

---

## 1. Starting and ending a session

**Start (read in this order)**
1. [CLAUDE.md](CLAUDE.md) — hard rules (read automatically by Claude Code).
2. [PROJECT_STATUS.md](PROJECT_STATUS.md) — current phase, task, NEXT ACTION, decisions.
3. The task prompt in `prompts/` (or Goggy's instruction) + the `research/` file it names.
4. This guide, for anything about code style, units, tests or Git.

**During:** one task only. Explain the plan in plain words before editing. Ask before installing
anything system-wide.

**End (every task, in this order)**
| Step | Command / action | Must show |
|---|---|---|
| 1 | `uv run pytest` | all tests pass (real output pasted in the report) |
| 2 | `uv run ruff check .` | "All checks passed!" |
| 3 | `uv run ruff format --check .` | no files to reformat (D7) |
| 4 | Update `PROJECT_STATUS.md` + `CHANGELOG.md` | completed, decisions, next action, tests + results |
| 5 | `git status` → commit → `git push` | no `data/` or `.env` staged; tree clean afterwards |

---

## 2. Folder map

**What exists now**
| Path | What it holds |
|---|---|
| `CLAUDE.md`, `PROJECT_BRIEF.md`, `PROJECT_STATUS.md`, `PROJECT_GUIDE.md` | rules, summary, progress, this guide |
| `Quantitative Stock Strategy Research Platform.txt` | master roadmap (source of truth for phases) |
| `README.md`, `CHANGELOG.md` | setup instructions; list of changes per task |
| `research/` | Phase 0 design docs + `calc_feasibility.py` (a one-off calculator) + `PREREGISTRATION.md` (Phase 6 tests, frozen at tag `prereg-v1`) |
| `prompts/` | the task prompts Goggy gives to Claude Code |
| `src/quant_research/` | the Python package: `__init__.py` (version) + `data/` (Phase 2, see below) |
| `tests/` | one test file per module + `fixtures/` (small made-up data files) |
| `scripts/` | runnable steps: `download_initial_dataset.py`, `crosscheck_yfinance.py`, `validate_initial_dataset.py` |
| `reports/` | generated reports, e.g. `data_validation/`, `accounting/` (counts, dates, % only — no prices) |
| `config/` | run settings as YAML (`RunConfig`), e.g. `s0_buy_and_hold_aapl_dev.yaml`; money/rates quoted, `final_test_unlocked: false` |
| `data/runs/` (git-ignored) | one folder per run: run.json (config, data provenance, git commit + dirty, times, summary), orders/fills/equity CSVs |
| `pyproject.toml`, `uv.lock`, `.python-version` | project settings, exact package versions, Python 3.13 |
| `.gitignore`, `.env.example` | what Git must never save; template for API keys |
| `data/` (git-ignored) | downloaded market data — never committed (licence): `raw/tiingo/`, `raw/rba/`, `raw/sec/`, `cache/yfinance/`, `reference/tiingo/` |

**Modules** — inside `src/quant_research/`. `data/` (Phase 2), `portfolio/` + `execution/` (Phase 3), `backtesting/`, `strategies/` and `metrics/` (Phase 4) exist; the rest are
*not created yet* and get created only when a phase needs them (no empty modules).
| Module | Phase | Its job | It must NOT |
|---|---|---|---|
| `data/` — **created** (`tiingo`, `storage`, `validation`, `crosscheck`, `loader`, `fx`, `sec`) | 2 | Download, validate, cache and load prices, dividends, splits (all years, incl. 2021+, for quality checks only — D8). Conventions: DATA_SOURCES §7 | trade, compute signals, chart or summarise 2021+ prices, or silently fill/fix bad data |
| `portfolio/` — **created** (`money`, `ledger`) | 3 | The ledger: cash, shares, costs, dividends, valuation (the only place cash changes) | decide when to trade or read future prices |
| `execution/` — **created** (`costs`, `orders`, `fills`) | 3–4 | Turn an order into a fill: next-open price, gaps, costs, rounding | decide *whether* to trade; use the signal day's close as the fill price |
| `backtesting/` — **created** (`engine`, `run`, `lookahead`, `synthetic`) | 4 | Run the day-by-day timeline: data → signal → order → fill → ledger. Strategy interface: `on_close(day, history, portfolio_view) -> list[OrderIntent]` (no price field) | contain strategy rules or fee numbers; run on dates ≥ 2021-01-01 while locked (D8) |
| `strategies/` — **created** (`buy_and_hold` = S0, `profit_target` = S1, S2, S4, `mean_reversion` = S3, `indicators`, `registry`) | 4–5 | Read past data, return order intents (reinvest only when cash ≥ `reinvest_min_cash_usd`) | touch cash or shares directly; see any data after day T |
| `metrics/` — **created** (`performance`) | 4, 6 | Returns, CAGR, drawdown + dates, volatility, Sharpe, worst year, costs, dividends, time in cash, round trips (floats OK) | change results or re-run trades |
| `research/` | 6 | Experiment runner: grids, periods, walk-forward, saving run records | run anything on dates ≥ 2021-01-01 unless `final_test_unlocked: true` (D8) |
| `screening/` — **created** (`fundamentals`, `trading`, `score`) | 7 | Company indicators (SEC XBRL, point-in-time: usable only on days AFTER the filing date; restatements from their own filing date) and trading indicators; later screens + suitability profiles | feed results back into backtests silently; use a fact on or before its filing date; fill a MISSING value |
| `reporting/` | 6+ | Tables and charts built from saved results only | type or edit any number by hand |
| `dashboard/` — **created** (`data` + `app/`: `main`, `ui`, `views/overview`, `company`, `performance`, `trades`) | 8 | Streamlit app (uv group `dashboard`) to VIEW saved results; numbers only from run records, saved reports, metrics/ and screening/; D8 guard; localhost only | run new experiments, hold logic of its own, estimate a missing number, show dates ≥ 2021-01-01, be deployed |
| `news/` | 9 | News / AI context (only if the baseline is solid) | influence past backtests with information from later dates |

Planned test folders (roadmap): `tests/unit/`, `tests/accounting/`, `tests/backtesting/`,
`tests/integration/`, plus `tests/fixtures/` for small data files. `config/`, `reports/`, `scripts/` exist.

---

## 3. Naming

| Thing | Rule | Example |
|---|---|---|
| Python files / modules | lowercase with underscores | `cash_ledger.py` |
| Functions, variables | lowercase with underscores, a verb for functions | `apply_dividend()`, `cash_usd` |
| Classes | CapitalWords | `Portfolio`, `FillResult` |
| Constants | CAPITALS | `MAIN_SPREAD_PER_SIDE` |
| Tests | file `test_<module>.py`; function `test_<what>_<expected>` | `test_buy_with_too_little_cash_raises` |
| Config files | lowercase, underscores, `.yaml` | `config/s1_aapl_dev.yaml` |
| Branches | `phase<N>-<short-task>` | `phase3-cash-ledger` |
| Commit messages | `Phase N: <what changed>` (plain English, present tense) | `Phase 3: add cash ledger with fee tests` |
| Strategies | ID from EXPERIMENT_PLAN + name | `s1_profit_target`, `s0_buy_and_hold` |

Names say what a thing *is*, including its unit (see §4). No single letters except loop counters.
D9: every function in `src/` has type hints (e.g. `def apply_fee(cash_usd: Decimal) -> Decimal:`); no type-checker tool yet.

---

## 4. Units and conventions (most important section — wrong units = wrong results)

| Topic | Rule |
|---|---|
| Currency | Every money name ends in its currency: `cash_usd`, `capital_aud`, `fee_usd`. Never a bare `cash`. Converting needs an explicit `aud_per_usd` / `usd_per_aud` rate, named that way. |
| Percentages | Stored as decimals: `0.02` means 2%. Names end in `_pct` only if they hold decimals too (`target_rise_pct = 0.03`). Multiply by 100 **only** when printing. |
| Dates | Trading days are plain dates (no time of day), on the US stock-market (NYSE) calendar. Never mix timezones; never store a timestamp where a date is meant. D4: an NYSE calendar library is added in Phase 2 and the data's dates are checked against it — mismatches fail loudly. |
| Prices | Raw vs adjusted always in the name: `open_raw`, `close_raw`, `close_adj`. **Trading uses raw prices only.** Adjusted prices are for analysis (e.g. total-return checks) only. |
| Timing | Decision on day T close → fill at day T+1 open (EXPERIMENT_PLAN §1). Code must make the T+1 step explicit. |
| Same-bar conflicts | If one daily bar hits both a buy and a sell level, assume the worse order for us. |
| Shares | Fractional shares are the MAIN case; whole shares is a sensitivity setting (EXPERIMENT_PLAN §1). |
| Final test period (D8) | Data for 2021+ may be downloaded and quality-checked (missing dates, bad prices). But no strategy, backtest or metric runs on dates ≥ 2021-01-01, and no charts or summary stats of 2021+ prices are made, unless `final_test_unlocked: true` — set only by Goggy. |

**Number type for money — D1, approved 2026-10-20: hybrid**
| Option | Pros | Cons |
|---|---|---|
| `float` everywhere | simple; fast; works directly with pandas | tiny rounding errors (0.1 + 0.2 ≠ 0.3) that build up over thousands of trades; hand-calculated tests need "approximately equal" |
| `Decimal` everywhere | exact cents; tests match hand calculations exactly | slower; awkward with pandas price tables |
| **Hybrid (recommended)** | `Decimal` inside `portfolio/` + `execution/` (cash, fees, shares); `float` for price tables, signals and metrics; convert at one place (the fill) | two number types to keep apart (the conversion point must be tested) |

Chosen: **hybrid** — `Decimal` in `portfolio/` + `execution/` (cash, fees, shares); `float` for prices,
signals and metrics; **one tested conversion point at the fill**. Reason: the ledger is where an error
makes a losing strategy look profitable, so it must be exact; the speed cost is small.

**Rounding — D2 and D3, approved 2026-10-20**
- Cash: round to whole cents (0.01 USD / 0.01 AUD) at every ledger entry, **against us**: costs and
  amounts we pay round *up*, amounts we receive round *down*. This keeps results conservative.
- Fractional shares: store up to **6 decimal places** [ASSUMPTION — Stake's real precision is
  UNVERIFIED, check in Phase 3]; shares bought round *down* so we never spend cash we don't have.
- Whole-share mode: shares bought round down to a whole number; leftover cash stays as cash.
- Fees are rounded up to the cent too (we pay them). Approved by Goggy 2026-10-20 (prompt 08).

**Profit and loss — average cost [ASSUMPTION, approved 2026-10-20]**
- Realised/unrealised P&L uses the average cost of all shares held (no tax lots, no tax modelling).
- Buy fees are part of the cost basis; sell fees come off the proceeds → P&L is after all costs.
- Minimum order US$10 (Stake, BROKER_FEES §4) applies to buys and partial sells; selling a whole
  position is allowed below it [ASSUMPTION — Stake doesn't say].
- Only one function turns a float price into Decimal: `portfolio.money.to_decimal_price`.

**Display rule (Phase 3, Step 3.7)**
- Inside the code every value stays exact `Decimal` (e.g. cost basis after a partial sell).
- Anything shown or saved in a report is rounded to cents with ROUND_HALF_EVEN (`portfolio.money.to_display`),
  only at that last step. A displayed value is never fed back into the ledger.
- Valuation: market value = quantity × close rounded DOWN to cents; unrealised P&L = market value − cost basis;
  a held ticker without a close price is an error (never valued at 0 or at an old price).
- Dividend withholding = 15% of the cents-rounded gross, rounded UP (decided by Goggy 2026-10-20, golden scenario).

**Indicators (Phase 5)** — always from `indicators.split_adjusted_closes(history)` (raw closes ÷ splits up to T).
Never `close_adj` in a strategy: it contains later splits and dividends (look-ahead). Long windows use warm-up
rows (`RunConfig.warmup_start`, `load_prices_with_warmup`); trading and metrics start at `start`.

**Strategy price memory (Phase 5, Goggy 2026-10-25)** — a strategy that remembers a price (entry E, sale S,
peak P) must divide it by the snapped split ratio on a split day, before reading that day's fills. Strategies
learn their own fill prices only from `PortfolioView.fills` (read-only, past fills only). X/Y come from config and
must be on the EXPERIMENT_PLAN §3 grid (`grid_override: true` = exploratory, logged).

**Daily event order — rule (Phase 3, approved 2026-10-20)**
- Each day, per ticker: **split → dividend → trades (at the open)**. The ledger refuses any other order.
- Why: the split changes the share count the dividend is paid on, and dividend entitlement is the holding at the
  previous close — so both must be booked before any trade that day.
- Split ratios are snapped by `quant_research.ratios.nearest_simple_ratio` (shared with data validation).
- All cost numbers live in ONE table: `execution.costs.COST_TABLE` (source link or [ASSUMPTION] per row).

---

## 5. Testing rules

| Rule | Detail |
|---|---|
| What must be tested | **All** accounting and execution logic, always — every fee, fill, dividend, split and rounding path. Plus data validation checks and every strategy's signal rules. |
| Accounting tests | Small examples worked out by hand first (write the hand calculation in the test as a comment), then the code must match exactly. |
| Backtest tests | Synthetic (made-up) price series: steadily rising, falling, sideways, a gap, a same-bar high+low hit. Known answer → check it. |
| Look-ahead test | Every strategy gets a test proving that changing day T+1 data does not change the day T signal. |
| No live data | No test may download anything. Use small fixture files in `tests/fixtures/` (made-up or tiny, licence-safe). |
| Failure cases | Test that bad inputs fail loudly (e.g. buying with too little cash raises an error). |
| Naming | `test_<what>_<expected>` (see §3). One idea per test. |
| How to run | `uv run pytest` (all) · `uv run pytest tests/test_smoke.py` (one file) · `uv run pytest -k cash` (by name) |
| Honesty | Report the real pytest output. A skipped or failing test is reported as such, never hidden. |

---

## 6. Error handling

- **Fail loudly.** Bad data or bad config stops the run with an error. No silent fixes (no quietly
  filling a missing price, dropping a row, or swapping in an adjusted price).
- **Clear messages** that say what, where and what to do: `"AAPL 2008-03-14: open_raw is missing —
  check data/raw download"`, not `"error"`.
- **Never swallow exceptions** (no bare `except:` or `except Exception: pass`). Catch an error only
  to add context and raise it again.
- **Validate at the edges:** data checked when loaded; config checked when read; orders checked
  before they reach the ledger (enough cash, enough shares, positive quantity and price).
- **Logging, not print,** in library code (`src/`): use Python's built-in `logging`. `print` is fine
  in one-off scripts like `research/calc_feasibility.py`.
- Known data problems that we choose to handle (e.g. a documented holiday gap) are handled by a
  named rule and logged — never silently.

---

## 7. Config and run records

- Experiment settings (strategy, stock, X/Y, cost level, dates, share mode) live in YAML files under
  `config/` (folder created in the phase that first needs it).
- **No hard-coded thresholds in strategy code.** `X = 0.03` comes from config, not from the code.
  Broker fees live in one config section with a source link or [UNVERIFIED] label.
- API keys come only from `.env` (copy of `.env.example`), never from config files or code.
- Every run saves (EXPERIMENT_PLAN §8): the exact config, data source + download date, git commit,
  and the results table. Failed and losing runs are kept, never deleted.
- D8 lock: every experiment config has `final_test_unlocked: false` by default. The backtest /
  experiment runner refuses dates ≥ 2021-01-01 while it is false. Only Goggy changes it to `true`.
- D6: runs with uncommitted code changes are allowed while developing but labelled "dirty" in their
  record. Validation and final-test runs must come from a clean, committed state.

---

## 8. Git workflow

| Rule | Detail |
|---|---|
| Small commits | One task = one commit (or a few). Message style: `Phase N: <what changed>`. |
| Before committing | `git status` — check no `data/`, `.env`, `.venv/` files are listed. Tests + ruff pass. |
| Branches | Docs-only tasks may go straight to `main`. Code tasks from Phase 2 on use a branch `phase<N>-<task>`, merged into `main` when tests pass (D5). Claude Code runs the branch commands and explains each one. |
| Never commit | `data/` (licence), `.env` (keys), anything with a real API key. `.gitignore` enforces the first and last; check anyway. |
| Push | After each completed task: `git push`. GitHub repo stays **private** until Goggy decides otherwise. |
| History | Never rewrite pushed history (no force-push) without Goggy's OK. |

---

## 9. Approved conventions (Goggy, 2026-10-20)

| # | Topic | Approved rule |
|---|---|---|
| D1 | Number type for money | Hybrid: `Decimal` in `portfolio/` + `execution/` (cash, fees, shares); `float` for prices, signals, metrics; one tested conversion point at the fill. |
| D2 | Cash rounding | Round to cents at each ledger entry, against us (pay → up, receive → down). |
| D3 | Fractional share precision | 6 decimal places, shares bought round down [ASSUMPTION — check Stake's real precision in Phase 3]. |
| D4 | Trading calendar | NYSE calendar library added in Phase 2; date mismatches fail loudly. |
| D5 | Branches | Docs straight to `main`; each code task on a `phase<N>-<task>` branch, merged when tests pass. Claude Code runs and explains the branch commands. |
| D6 | Dirty runs | Allowed in development, labelled "dirty"; validation and final-test runs must be clean. |
| D7 | Code formatter | `ruff format` adopted (applied 2026-10-20, no logic change). |
| D8 | Final-test lock (changed from proposal) | Lock sits in the backtest / experiment runner, not data loading. Download + quality checks may cover all years. No strategy, backtest, metric, chart or summary stat on dates ≥ 2021-01-01 unless `final_test_unlocked: true` — set only by Goggy. |
| D9 | Type hints | Required on every function in `src/`; no type-checker yet. |

Changing any of these later: log it in CHANGELOG.md and PROJECT_STATUS.md "IMPORTANT DECISIONS".
