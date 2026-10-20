# EXPERIMENT_PLAN.md — Step 0.5
Status: v1 — APPROVED by Goggy 2026-10-18
Rule: this plan is fixed BEFORE any backtest. Any later change is logged in section 10 with the reason.
Labels: [ASSUMPTION] = our choice, can change · [UNVERIFIED] = fact still to check

---

## 1. Common setup (same for EVERY strategy)
| Item | Setting |
|---|---|
| Capital | AUD 10,000 → USD at start after one-off FX (Stake 0.55%) |
| Stocks | Start AAPL + XOM; then all 8 from INITIAL_UNIVERSE.md |
| One stock per test | Each strategy runs on one stock at a time (no portfolio mixing yet) |
| Data | Daily OHLC + dividends + splits from Tiingo; raw prices for trading |
| Timing (no look-ahead) | Decide on day T's **close** → trade at day T+1's **open** |
| Gaps | If T+1 opens far past the threshold, we fill at that open (could be better or worse) |
| Shares | MAIN = fractional (Stake allows). Sensitivity = whole shares only |
| Costs | MAIN = Stake + normal spread (0.05%/side). Also LOW (IBKR), HIGH (CommSec), tight/wide spread |
| Dividends | Entitled if holding at the close before the ex-date; cash credited ON the ex-date [ASSUMPTION — Tiingo gives no pay date; same rule for all strategies]. US withholding tax 15% with W-8BEN (30% without) — VERIFIED 2026-10-20, [Stake support](https://hellostake.com/au/support/documents-and-statements/taxes-and-forms/26011219005337) |
| Cash | Earns 0% interest [ASSUMPTION — conservative; Stake cash interest not modelled] |
| End of test | Any open position valued at last close minus selling costs (fair to both sides) |
| Currency | Results reported in USD (main) and AUD (secondary) |

Why close → next open: daily data can't tell if the high or low came first. Using next open
avoids that problem completely for the baseline. (A limit-order version is tested later in Phase 4
using the "assume the worse order" rule.)

## 2. Strategies (exact rules)

**S0 — Buy-and-hold (benchmark)**
- Buy at the first open. Hold to the end. Reinvest dividends at the next open after pay date.

**S1 — Fixed profit target (tests H1)**
- Start: buy at first open. Entry price E = buy price.
- SELL when close ≥ E × (1 + X). Sale price S = next open.
- REBUY when close ≤ S × (1 − Y). New E = next open.
- If the price never falls Y% below S, we stay in cash. (This is the honest "missed upside" test.)
- Dividends received while holding go to cash and are used in the next buy.

**S2 — Pullback from peak (tests H1 variant / Q4.4)**
- SELL rule same as S1.
- After selling, track the highest close since the sale = P.
- REBUY when close ≤ P × (1 − Y).
- Difference from S1: if the stock keeps rising, S2 still gets back in after a dip from the new high.
  It can rebuy higher than it sold. This limits "stranded in cash" but may lose money per trade.

**S3 — Mean reversion (tests H4)**
- z = (close − 20-day average) ÷ 20-day standard deviation.
- SELL when z ≥ +k. REBUY when z ≤ −k.  Starts invested.

**S4 — Trend-filtered (tests H3)**
- Same as S1 or S2, but **no selling** while close > 200-day average AND the 200-day average is
  higher than it was 20 days ago (= strong uptrend). Rebuy rules unchanged.

**S5 — Hybrid** — NOT designed yet. Only built after S1–S4 are evaluated (roadmap Step 5.5).

## 3. Parameter grid (kept small on purpose)
| Strategy | Parameters | Combos |
|---|---|---|
| S1, S2 | X ∈ {2, 3, 4, 5}% · Y ∈ {2, 3, 4, 5}% | 16 each |
| S3 | k ∈ {1.5, 2.0, 2.5} · window ∈ {20, 50} | 6 |
| S4 | S1/S2 best-region X/Y + trend filter on/off | ≤ 8 |

No fine-tuning beyond this grid (e.g. no X = 3.17%). That prevents overfitting.

## 4. Time periods (train → check → final test)
[ASSUMPTION — confirm data coverage in Phase 2]
| Period | Dates | Use | Includes |
|---|---|---|---|
| Development | 2005-01-01 → 2016-12-31 | Build rules, explore grid freely | 2008 crash, 2009–16 recovery |
| Validation | 2017-01-01 → 2020-12-31 | Check choices from development | 2018 drop, 2020 COVID crash |
| Final test (hold-out) | 2021-01-01 → latest full year | Run ONCE at the end | 2022 bear market, 2023–25 |

- The final test is opened **once**, after all rules are frozen. Results are recorded whatever they are.
- If we change any rule after seeing the final test, we must write "final test used — results no
  longer out-of-sample" in section 10.
- Phase 6 adds walk-forward tests (rolling windows) on top of this.

## 5. Metrics recorded for every run
- Growth: final value, total return, CAGR, excess return vs S0.
- Risk: max drawdown, annual volatility, Sharpe ratio (risk-free = 0% [ASSUMPTION]), worst year.
- Behaviour: number of round trips, % of days in cash, longest time in cash,
  "stranded" episodes (sold, never rebought within test), dividends received vs S0, total costs paid.
- Reliability: result with best 3 trades removed; result at each cost/spread level.

## 6. What counts as a meaningful result for H1 (decided now)
H1 is **SUPPORTED** only if ALL of these are true on the **final test period**, MAIN costs:
1. Beats S0 (after costs) on at least **6 of 8** stocks.
2. At least **60% of the 16 X/Y combos** beat S0 on average across stocks (not one lucky setting).
3. Max drawdown no more than **5 percentage points worse** than S0.
4. Still beats S0 with **wide spread** and with **HIGH (CommSec)** costs OR it's documented that it only works on low-cost brokers.
5. Still beats S0 after **removing its best 3 trades**.
6. At least **10 round trips** per stock in the test period (enough evidence).

H1 is **REJECTED** if it loses to S0 on the majority (5+) of stocks in the final test at MAIN costs.
Anything in between = **INCONCLUSIVE** (say so honestly; do not round up to "works").

Same structure applies to H2–H6 (H2 uses Sharpe / drawdown instead of final value).

## 7. Evidence that would make us drop the original idea
- S1 and S2 both REJECTED, AND trend filter (S4) doesn't fix it.
- Gains disappear when spread moves from normal to wide.
- Wins only on XOM-type stocks and loses on everything else → idea is "regime-only" (H5), not general.

## 8. Logging rules (anti-hallucination)
- Every run saves: config file, data source + download date, code version (git commit), results table.
- Failed and losing runs are kept, never deleted (roadmap Step 6.7).
- Charts and reports are generated from saved results only — never typed by hand.

## 9. Known limitations (Phase 0 summary)
| Limitation | Effect | Where documented |
|---|---|---|
| Survivorship bias (no bankrupt stocks on free data) | Results too optimistic for "buy the dip" | INITIAL_UNIVERSE.md |
| Hindsight in stock choice | Some bias remains | INITIAL_UNIVERSE.md |
| Daily data only | Can't model intraday fills exactly → next-open rule | this file |
| No historical spread data | Spread is assumed, tested at 3 levels | SMALL_ACCOUNT_FEASIBILITY.md |
| Tax (CGT) ignored | Real life favours buy-and-hold more | SMALL_ACCOUNT_FEASIBILITY.md |
| Free data licence = personal use | Data not shared on GitHub | MARKET_SELECTION.md |
| Fixed AUD/USD in fee maths | Small error in cost estimates | SMALL_ACCOUNT_FEASIBILITY.md |
| Cash earns 0% | Slightly unfair to active strategies | this file |
| Single stock per test | No diversification effects | this file |

## 10. Change log
- 2026-10-17: v1 created.
- 2026-10-20: Dividend withholding 15% (W-8BEN) verified on Stake support page.
- 2026-10-20: Dividend cash timing changed from 'pay date' to 'ex-date' — Tiingo has no pay date (DATA_SOURCES.md). Before any backtest, so no results affected.
- 2026-10-18: Approved. Q4.11 (suitability profile) to be answered from H5/H6 results.
