# PROJECT_BRIEF.md — one-page summary (read this first every session)

## What we are building
A Python research platform that tests one question honestly:
> Does "sell after a small rise, buy back after a dip" beat simply buying and holding —
> after real costs, on an AUD $10,000 account? (changed from $1,000 on 2026-10-17)

It is a RESEARCH tool, not a money-making bot. A "no, it doesn't beat buy-and-hold"
answer is a valid, CV-worthy result.

## The order things get built (and why)
1. Phase 0 — Paper research only (no code). Is it even feasible with AUD 10,000 after costs?
2. Phase 1 — Set up repo, Python, Git, tests.
3. Phase 2 — Get clean price + dividend + split data.
4. Phase 3 — Accounting engine (cash, shares, fees, dividends). MOST IMPORTANT.
5. Phase 4 — Backtester + buy-and-hold benchmark. No look-ahead.
6. Phase 5 — Strategies (profit target, pullback, mean reversion, trend filter).
7. Phase 6 — Robustness: out-of-sample, cost & parameter sensitivity, regimes.
8. Phase 7 — Company screening.
9. Phase 8 — Streamlit dashboard.
10. Phase 9 — News / AI features (only if baseline is solid).
11. Phase 10 — Hardening.  Phase 11 — CV + GitHub write-up.

## Non-negotiable rules (anti-hallucination)
- No number (fee, price, data cost) without a source link, or the label UNVERIFIED.
- No claim of profitability. Results are "simulated, historical".
- Signals use only data available at decision time; trades fill next session.
- Never use adjusted close as the price you actually trade at.
- On a daily bar where both buy and sell levels are hit, assume the WORSE order.
- A phase is "Verified" only when deliverables exist + tests pass + limits documented.
- Every session: read PROJECT_BRIEF.md + PROJECT_STATUS.md first, update STATUS last.

## Biggest risks Claude sees (honest view)
- Frequent trading: costs can eat the edge. CommSec standard ≈1.3% per round trip
  (FX charged every trade); IBKR/Stake ≈0.03–0.1%. See research/BROKER_FEES.md.
- Testing only Apple/Microsoft = survivorship bias (they are winners we picked today).
- Daily data can't tell which happened first intraday (high or low).
- Scope is large (12 phases). Phases 0–6 are the real core; 7–9 are extras.

## Files
- Quantitative Stock Strategy Research Platform.txt — master roadmap (source of truth)
- PROJECT_BRIEF.md — this summary
- PROJECT_STATUS.md — live progress tracker
- research/ — Phase 0 research files
