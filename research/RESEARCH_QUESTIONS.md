# RESEARCH_QUESTIONS.md — Step 0.1
Status: v4 (2026-10-18) — APPROVED. H1 v2 main; H2–H7; Q4.11 added by Goggy
Scope (stated by Goggy): US market first, AUD 10,000 start (changed from 1,000 on 2026-10-17),
daily data, free data where possible. Broker costs: MAIN case = Stake (MID); LOW = IBKR-like,
HIGH = CommSec standard — see BROKER_FEES.md.

---

## 1. The main question (plain words)
If I sell a share after it rises a little, and buy it back after it drops,
do I end up with more money than if I had just bought it and held it?

## 2. Hypotheses
- **H1 v1 (original, confirmed):** "Sell on small rise, rebuy on dip" ends with a higher
  portfolio value than buy-and-hold, after all costs, same stock, same period, same capital.

- **H1 v2 (MAIN hypothesis — confirmed by Goggy 2026-10-17):** Starting with AUD 10,000 in a single US large-cap stock,
  a rule that sells after a rise of X% and rebuys after a fall of Y% from the sale price
  (X, Y between 2% and 5%) ends with a higher final value than buying and holding the
  same stock with dividends reinvested —
  1. after brokerage, FX and spread,
  2. on test data that was NOT used to pick X and Y,
  3. without a clearly bigger maximum drawdown,
  4. for most stocks tested and most X/Y values, not just one lucky setting.

  Why v2 is better: it is measurable, names the benchmark exactly (dividends included),
  and builds in the fairness checks so a lucky backtest can't "prove" it.

### Secondary hypotheses (from master roadmap — tested only after H1 baseline works)
Each is compared against BOTH buy-and-hold and the plain H1 rule.

- **H2 — Risk-adjusted win (roadmap objective 2):** Even if the rule does not beat
  buy-and-hold on final value, it gives a better return per unit of risk
  (higher Sharpe ratio / smaller max drawdown) after costs.
  → Matters because a smoother ride with slightly less return can still be useful.
- **H3 — Trend filter (roadmap Step 5.4):** Adding a simple trend filter
  (e.g. don't sell while price is above its 200-day average and rising) reduces
  "sold and never got back in" losses and improves H1 results out-of-sample.
- **H4 — Mean reversion vs fixed % (roadmap Step 5.3):** Using a statistical reference
  (e.g. distance from a moving average in standard deviations) instead of fixed X%/Y%
  gives better or more stable results.
- **H5 — Market regime (roadmap Step 6.5):** The rule works in sideways/choppy or
  high-volatility periods but loses in strong trends. If true, the rule is only
  useful when combined with a regime check.
- **H6 — Stock type (roadmap Phase 7):** Results differ by stock type
  (e.g. high vs low volatility, large vs mid cap). The rule is not universal.

### Later / exploratory (roadmap Phase 9 — only if baseline is solid)
- **H7 — Extra information:** Adding market context or news signals improves
  out-of-sample results after costs, compared with price-only rules.
  Labelled EXPLORATORY until tested.

### Hypothesis rules
- H1 is tested first and alone. H2–H6 only after H1 baseline is verified.
- Every hypothesis gets the same fairness checks (section 5) and the same 3 cost levels.
- We record failures, not just wins (roadmap Step 6.7).

- **H0 (default for every hypothesis above):** It does NOT beat buy-and-hold after costs.
  Any win is luck, market trend, or bad testing.

## 3. What "better" means — 3 objectives
| # | Objective | How we measure it |
|---|-----------|-------------------|
| 1 | Growth | Final value; total return; CAGR; excess return vs buy-and-hold |
| 2 | Risk | Max drawdown; volatility; time below starting value |
| 3 | Reliability | Out-of-sample result; other stocks; other periods; higher costs; not driven by a few trades |

## 4. Sub-questions
**Costs** (answered partly in BROKER_FEES.md)
- Q4.1 Cost of one round trip at each cost level (LOW / MID / HIGH)  → Step 0.4
- Q4.2 Break-even % move per round trip at each level  → Step 0.4
- Q4.3 Whole vs fractional shares: how much cash sits idle?  → Step 0.4

**Strategy behaviour**
- Q4.4 How often does it sell and never get to buy back? How much growth is missed?
- Q4.5 How often does it rebuy and the stock keeps falling?
- Q4.6 Share of time spent in cash
- Q4.7 Dividends missed while out of the stock

**Where it might work**
- Q4.8 Sideways vs uptrend vs downtrend markets
- Q4.9 High- vs low-volatility stocks
- Q4.10 Does a trend filter help?

**Suitability (added by Goggy 2026-10-18) — answer at end of Phase 6 / Phase 7**
- Q4.11 What kind of MARKET and COMPANY is this strategy suitable for (if any)?
  Measured by comparing results across: volatility level, trend strength, sideways vs trending
  periods, dividend size, liquidity/spread, sector, company size — and later ASX vs US.
  Output: a short "fits / doesn't fit" profile, backed by the backtest tables (H5 + H6 feed this).

## 5. Other explanations to rule out
| Possible cause | How we check |
|---|---|
| Luck | Count trades; remove best 3 trades and re-test |
| Market trend | Always compare to buy-and-hold of the same stock |
| Survivorship bias | Include weaker companies; document the limit |
| Overfitting | Hidden test period; parameter sensitivity |
| Look-ahead bias | Signal at day T close → trade at day T+1 open |
| Unrealistic fills | If high and low both hit in one day, assume the worse order |
| Ignoring costs | Run LOW / MID / HIGH cost scenarios |
| Ignoring dividends | Count dividends for both strategies |

## 6. Early stop signals (final in Step 0.5)
- Break-even move per round trip ≥ the rise we sell at (already close at HIGH cost level).
- Loses to buy-and-hold on most stocks/periods out-of-sample.
- Win turns into loss with small changes in X, Y or costs.

## 7. Out of scope (for now)
Real-money trading, intraday data, options/shorting/leverage, tax/CGT (noted as limit), news/AI (Phase 9).

## 8. Decisions (2026-10-17)
- H1 v2 confirmed by Goggy.
- H2–H7 added (proposed by Claude from master roadmap) — Goggy asked for additions.
- Main broker cost case: Stake (Goggy already uses/knows it).
- Starting range: rise X = 2–5%, dip Y = 2–5% (Goggy agreed).
- Capital: AUD 10,000.
