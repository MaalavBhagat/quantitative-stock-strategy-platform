You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md (esp. §2 module jobs, §4 timing + daily order, D6, D8), PROJECT_STATUS.md,
research/EXPERIMENT_PLAN.md §1 + §8, DATA_SOURCES.md §7 + §9, src/quant_research/{data,portfolio,execution}/,
and Phase 4 Steps 4.1–4.3 in the roadmap.

STEP 0 (docs → main): commit PROJECT_STATUS.md, DATA_SOURCES.md (§9 RBA source), prompts/11_*.md —
"Phase 3 verified by chat Claude; AUD/USD source chosen". Push.

PHASE 4 PLAN: prompt 11 = engine core (timeline, look-ahead guard, order execution) — synthetic data only ·
prompt 12 = buy-and-hold benchmark on real AAPL + XOM, RBA FX, metrics, edge cases, Phase 4 check.

TASK: Phase 4, Steps 4.1 (timeline), 4.2 (no look-ahead), 4.3 (order execution). Branch: `phase4-engine-core`.
FIRST: show Goggy a short plan (with a simple day-by-day diagram in text) and WAIT for OK.

PART A — Timeline (4.1) → `src/quant_research/backtesting/engine.py`
For each NYSE trading day T in [start, end], in this exact order (PROJECT_GUIDE §4):
  1. OPEN: corporate actions for T from the data → split (split_factor ≠ 1) → dividend (div_cash_usd > 0).
  2. OPEN: execute orders that were created at the previous day's close, at T's open_raw (Part C).
  3. CLOSE: valuation snapshot at close_raw (ledger.valuation).
  4. CLOSE: the strategy sees data up to and including T's close and returns order intents → queued for T+1 open.
  5. Orders still queued after the last day are recorded as EXPIRED (never filled at a made-up price).
End of run: open positions shown at last close AND as "liquidation value" = what selling at last close would give after
spread + fee (EXPERIMENT_PLAN §1). Don't actually sell; report both.
The engine contains NO strategy rules and NO fee numbers (PROJECT_GUIDE §2) — it calls strategies and execution.

PART B — No look-ahead (4.2)
- Strategy interface (Protocol): `on_close(day, history, portfolio_view) -> list[OrderIntent]`.
  `history` = price table for that ticker ending at T (rows after T must be physically absent, not just "not used").
  `portfolio_view` = read-only (cash, quantity, average cost) — strategies can't change the ledger.
- OrderIntent: side (buy/sell), ticker, size = shares | "all" | "max_affordable". No price field — strategies can't
  choose their fill price.
- Generic look-ahead test harness: run a spy strategy on a synthetic series, then change ALL data after day T
  (prices, dividends) and re-run → every signal and order up to T must be identical. Run it for each strategy we
  ever add (make it reusable).
- A test proving a signal made at T's close fills at T+1's OPEN, never at T's close.

PART C — Order execution (4.3) → `src/quant_research/execution/fills.py`
`fill_order(intent, day, open_raw, ledger, broker, spread_level, share_mode, min_order_usd)` → FillResult or Rejection.
- Reference price = T's open_raw (Decimal via to_decimal_price). Fill price via costs.apply_spread; fee via costs.fee_usd.
- "max_affordable" buys: size so fill × qty + fee ≤ cash (fee depends on value → compute safely, test the IBKR 1% cap and
  CommSec % fee cases, where fee grows with size).
- Price gaps: fill at the open, whatever it is; record gap % vs previous close in the fill record.
- Unavailable funds / shares / below US$10 minimum → REJECTED with a reason, recorded, run continues (not a crash).
  Bad inputs (negative qty, unknown ticker) → error (a bug, not a market event).
- Missing open price on a trading day → error (loader should never allow this; double safety).
- Order log (every intent: created day, intended day, status FILLED/REJECTED/EXPIRED, reason) and fill log
  (reference, fill, spread cost, fee breakdown) — separate from the ledger, kept for reports.

PART D — Run guard + run record
- `RunConfig` (dataclass, loaded from YAML in `config/` — create the folder with one example: S0 buy-and-hold AAPL,
  2010-01-04 → 2016-12-30, stake, normal spread, fractional, start AUD 10,000, final_test_unlocked: false).
- D8: any date ≥ 2021-01-01 with final_test_unlocked false → refuse before loading anything. Test it.
- Run record (EXPERIMENT_PLAN §8): config, data provenance (from loader), git commit + dirty flag (D6), start/end
  timestamps, order log, fill log, daily equity. Save under `/data/runs/<run_id>/` (git-ignored: equity curves are
  derived from licensed prices). Only summary numbers may go into `reports/` later.
- FX at start/end: the rate comes from config for now (`usd_per_aud_start`, `usd_per_aud_end`); prompt 12 replaces
  it with the RBA series. Mark the config fields "temporary".

TESTS (synthetic only, no internet, no real data): every timeline step order · split + dividend + order on the same day ·
look-ahead harness · T close → T+1 open · rejections (cash, shares, min order) logged and run continues ·
max_affordable with each broker never overspends · gap fill · expired orders · D8 lock · run record contents ·
cash identity still exact at the end of a multi-day synthetic run.

FINISH: pytest / ruff check / ruff format --check (real output) · mutation check (make fills use T's close instead of
T+1 open once — the look-ahead tests must fail; restore) · safety checks · commit → merge → push → delete branch ·
PROJECT_GUIDE (backtesting/ created, config/ created) · PROJECT_STATUS (Steps 4.1–4.3, next = prompt 12) · CHANGELOG.

COMPLETION REPORT: files · day-by-day diagram · how look-ahead is prevented (plain words) · rejection rules ·
tests + real output · mutation check · assumptions · open questions.
Do not claim anything is done unless the evidence supports it.
