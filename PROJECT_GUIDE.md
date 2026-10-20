# PROJECT_GUIDE.md — how we write code in this project (Phase 1, Step 1.4)
Status: v1 draft — 2026-10-20. Items marked **DECISION** wait for Goggy's approval (list in §9).
Rules for Claude Code live in [CLAUDE.md](CLAUDE.md) — this guide adds the *how*, it does not repeat them.
Labels: [ASSUMPTION] = our choice, can change · [UNVERIFIED] = fact still to check.

---

## 1. Starting and ending a session

**Start (read in this order)**
1. [CLAUDE.md](CLAUDE.md) — hard rules (read automatically by Claude Code).
2. [PROJECT_STATUS.md](PROJECT_STATUS.md) — current phase, task, NEXT ACTION, open decisions.
3. The task prompt in `prompts/` (or Goggy's instruction) + the `research/` file it names.
4. This guide, for anything about code style, units, tests or Git.

**During:** one task only. Explain the plan in plain words before editing. Ask before installing
anything system-wide.

**End (every task, in this order)**
| Step | Command / action | Must show |
|---|---|---|
| 1 | `uv run pytest` | all tests pass (real output pasted in the report) |
| 2 | `uv run ruff check .` | "All checks passed!" |
| 3 | `uv run ruff format --check .` | no files to reformat (once DECISION D7 is approved) |
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
| `research/` | Phase 0 design docs + `calc_feasibility.py` (a one-off calculator, not platform code) |
| `prompts/` | the task prompts Goggy gives to Claude Code |
| `src/quant_research/` | the Python package (only `__init__.py` with the version so far) |
| `tests/` | `test_smoke.py` (one test) |
| `pyproject.toml`, `uv.lock`, `.python-version` | project settings, exact package versions, Python 3.13 |
| `.gitignore`, `.env.example` | what Git must never save; template for API keys |
| `data/` (git-ignored) | downloaded market data — never committed (licence). Not created yet. |

**Planned modules** — inside `src/quant_research/`. *All not created yet.* Created only when a
phase needs them (no empty modules).
| Module | Phase | Its job | It must NOT |
|---|---|---|---|
| `data/` | 2 | Download, validate, cache and load prices, dividends, splits | trade, compute signals, or silently fill/fix bad data |
| `portfolio/` | 3 | The ledger: cash, shares, costs, dividends, valuation (the only place cash changes) | decide when to trade or read future prices |
| `execution/` | 3–4 | Turn an order into a fill: next-open price, gaps, costs, rounding | decide *whether* to trade; use the signal day's close as the fill price |
| `backtesting/` | 4 | Run the day-by-day timeline: data → signal → order → fill → ledger | contain strategy rules or fee numbers |
| `strategies/` | 5 | Read past data, return "buy / sell / hold" signals | touch cash or shares directly; see any data after day T |
| `metrics/` | 4, 6 | Returns, drawdown, Sharpe, round trips, time in cash | change results or re-run trades |
| `research/` | 6 | Experiment runner: grids, periods, walk-forward, saving run records | open the final test period without Goggy's go-ahead |
| `screening/` | 7 | Company screens and suitability profiles | feed results back into backtests silently |
| `reporting/` | 6+ | Tables and charts built from saved results only | type or edit any number by hand |
| `dashboard/` | 8 | Streamlit app to view saved results | run new experiments or hold logic of its own |
| `news/` | 9 | News / AI context (only if the baseline is solid) | influence past backtests with information from later dates |

Planned test folders (roadmap): `tests/unit/`, `tests/accounting/`, `tests/backtesting/`,
`tests/integration/`, plus `tests/fixtures/` for small data files. Planned: `config/`, `reports/`, `scripts/`.

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

---

## 4. Units and conventions (most important section — wrong units = wrong results)

| Topic | Rule |
|---|---|
| Currency | Every money name ends in its currency: `cash_usd`, `capital_aud`, `fee_usd`. Never a bare `cash`. Converting needs an explicit `aud_per_usd` / `usd_per_aud` rate, named that way. |
| Percentages | Stored as decimals: `0.02` means 2%. Names end in `_pct` only if they hold decimals too (`target_rise_pct = 0.03`). Multiply by 100 **only** when printing. |
| Dates | Trading days are plain dates (no time of day), on the US stock-market (NYSE) calendar. Never mix timezones; never store a timestamp where a date is meant. |
| Prices | Raw vs adjusted always in the name: `open_raw`, `close_raw`, `close_adj`. **Trading uses raw prices only.** Adjusted prices are for analysis (e.g. total-return checks) only. |
| Timing | Decision on day T close → fill at day T+1 open (EXPERIMENT_PLAN §1). Code must make the T+1 step explicit. |
| Same-bar conflicts | If one daily bar hits both a buy and a sell level, assume the worse order for us. |
| Shares | Fractional shares are the MAIN case; whole shares is a sensitivity setting (EXPERIMENT_PLAN §1). |
| Final test period | Data from 2021-01-01 onward stays closed until Goggy says so (see DECISION D8). |

**Number type for money — DECISION D1**
| Option | Pros | Cons |
|---|---|---|
| `float` everywhere | simple; fast; works directly with pandas | tiny rounding errors (0.1 + 0.2 ≠ 0.3) that build up over thousands of trades; hand-calculated tests need "approximately equal" |
| `Decimal` everywhere | exact cents; tests match hand calculations exactly | slower; awkward with pandas price tables |
| **Hybrid (recommended)** | `Decimal` inside `portfolio/` + `execution/` (cash, fees, shares); `float` for price tables, signals and metrics; convert at one place (the fill) | two number types to keep apart (the conversion point must be tested) |

Recommendation: **hybrid**. The ledger is where an error makes a losing strategy look profitable,
so it should be exact; the speed cost is small (a few thousand trades per run).

**Rounding — DECISION D2 and D3**
- Cash: round to whole cents (0.01 USD / 0.01 AUD) at every ledger entry, **against us**: costs and
  amounts we pay round *up*, amounts we receive round *down*. This keeps results conservative.
- Fractional shares: store up to **6 decimal places** [ASSUMPTION — Stake's real precision is
  UNVERIFIED, check in Phase 3]; shares bought round *down* so we never spend cash we don't have.
- Whole-share mode: shares bought round down to a whole number; leftover cash stays as cash.

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
- Runs with uncommitted code changes are marked "dirty" in their record (DECISION D6).

---

## 8. Git workflow

| Rule | Detail |
|---|---|
| Small commits | One task = one commit (or a few). Message style: `Phase N: <what changed>`. |
| Before committing | `git status` — check no `data/`, `.env`, `.venv/` files are listed. Tests + ruff pass. |
| Branches | Docs-only tasks may go straight to `main`. Code tasks from Phase 2 on use a branch `phase<N>-<task>`, merged into `main` when tests pass (DECISION D5). |
| Never commit | `data/` (licence), `.env` (keys), anything with a real API key. `.gitignore` enforces the first and last; check anyway. |
| Push | After each completed task: `git push`. GitHub repo stays **private** until Goggy decides otherwise. |
| History | Never rewrite pushed history (no force-push) without Goggy's OK. |

---

## 9. Open DECISIONS for Goggy

| # | Decision | Recommendation (1 line) |
|---|---|---|
| D1 | Number type for money | Hybrid: exact `Decimal` in the ledger (portfolio/execution), `float` for prices, signals, metrics. |
| D2 | Cash rounding | Round to cents at each ledger entry, against us (pay → up, receive → down). |
| D3 | Fractional share precision | 6 decimal places, round shares bought down [ASSUMPTION until Stake's real precision is checked in Phase 3]. |
| D4 | Trading calendar | Use an NYSE calendar library (added in Phase 2) and check the data's dates against it; mismatches fail loudly. |
| D5 | Branches | `main` for docs; a `phase<N>-<task>` branch for each code task, merged when tests pass. |
| D6 | Dirty runs | Allowed while developing but marked "dirty"; validation and final-test runs must be from a clean, committed state. |
| D7 | Code formatter | Adopt `ruff format` (same tool, no new dependency). First run would only re-space `research/calc_feasibility.py` — no logic change; apply it in its own small commit. |
| D8 | Final-test lock in code | `data/` loading refuses dates ≥ 2021-01-01 unless a setting named for Goggy's go-ahead is switched on. |
| D9 | Type hints | Required on every function in `src/` (they make units and money types visible); no type-checker tool yet. |

Once approved, each line moves to PROJECT_STATUS.md "IMPORTANT DECISIONS" and the word DECISION is
removed from this file (logged in CHANGELOG.md).
