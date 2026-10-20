# INITIAL_UNIVERSE.md — Step 0.3
Status: v2 (2026-10-17) — starting pair changed to AAPL + XOM by Goggy
Labels: [ROADMAP] = named in master roadmap · [UNVERIFIED] = general knowledge, confirm with data in Phase 2

---

## 1. How stocks are picked (the rule)
- Pick by **ROLE** (what kind of price behaviour it tests), not by "it went up a lot".
- The list is fixed **before** any backtest is run. No adding/removing stocks after seeing results
  (if we do, it must be logged here with the reason).
- Must include stocks that did badly or went sideways — otherwise we only test winners.
- Must be tradeable on Stake (US) and covered by Tiingo free data. [UNVERIFIED — check in Phase 2]

Honest limit: we already know how most of these did, so some hindsight is unavoidable.
We reduce it by picking roles and by including weak performers on purpose.

## 2. Initial universe (8 tickers)
| # | Ticker | Company | Role in the test | Why it's useful |
|---|--------|---------|------------------|-----------------|
| 1 | AAPL | Apple | Strong long-term winner [ROADMAP] | Tests the "sold and never got back in" risk |
| 2 | MSFT | Microsoft | Strong long-term winner [ROADMAP] | Second winner — check results aren't Apple-only |
| 3 | KO | Coca-Cola | Low-volatility dividend payer | Tests: do we lose dividends while out of the stock? Calm price = fewer signals |
| 4 | PG | Procter & Gamble | Defensive, low volatility | Second calm stock |
| 5 | XOM | ExxonMobil | Cyclical — long up/down swings with oil [UNVERIFIED detail] | Tests different market regimes (H5) |
| 6 | INTC | Intel | Former leader with a long decline [UNVERIFIED detail] | Key "non-winner": does buying dips keep losing money? |
| 7 | T | AT&T | Long sideways/weak period + corporate actions (spin-off) [UNVERIFIED detail] | Tests sideways markets AND corporate-action handling |
| 8 | SPY | S&P 500 ETF | Whole-market benchmark | Shows if results are just "the market went up"; ETF on Stake [UNVERIFIED] |

Mix: 2 winners · 2 calm/defensive · 1 cyclical · 2 weak/sideways · 1 market ETF.

## 3. Start small (roadmap Step 2.2)
- [DECISION 2026-10-17, Goggy] Phase 2 pipeline is built and validated on **AAPL + XOM** first:
  - **AAPL = WITH momentum** — long, strong uptrend. Tests "sold and never got back in".
  - **XOM = WITHOUT steady momentum** — cyclical, trends that reverse with oil. Tests choppy/regime behaviour.
  - Bonus: XOM pays a sizeable dividend [UNVERIFIED size], so it also tests dividend accounting
    (this was KO's job in v1).
- Note (Claude): XOM still has multi-year trends, just ones that reverse. For a truly calm,
  low-momentum case, KO is the next stock to add.
- The other 6 are added only after data checks pass.

## 4. Considered and left out (for now)
| Candidate | Decision | Reason |
|---|---|---|
| Reliance Industries [ROADMAP] | Parked — research-only, later | Not on Stake; Indian data/access outside US scope (see MARKET_SELECTION.md) |
| Companies that went bankrupt / delisted (e.g. Lehman-type cases) | Wanted, but likely not possible on free data | Free sources mostly cover listed stocks → survivorship bias limit. Check in Phase 2 if Tiingo has delisted tickers [UNVERIFIED] |
| GE, BA, NVDA, TSLA etc. | Not now | Keep list small; can add in Phase 7 screening |

## 5. Rules from the roadmap we follow
- No company is described as "can't go bankrupt".
- Today's winners are not used as the only basis for conclusions.
- Results must be reported per stock AND overall — no hiding the bad ones.

## 6. Open items
- 8-stock list kept; starting pair = AAPL + XOM (Goggy, 2026-10-17).
- Phase 2: confirm every ticker is on Tiingo free + Stake; confirm the [UNVERIFIED] notes from price data.
