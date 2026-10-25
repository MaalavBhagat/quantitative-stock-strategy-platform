# PREREGISTRATION.md — what Phase 6 will test, fixed BEFORE any 2017–2020 data is run

Version: **v1 — 2026-10-25** (git tag `prereg-v1`). Written at the end of Phase 5, before any validation-period
(2017–2020) price data has been downloaded or run. Purpose: the tests and the pass/fail rules are written down
now, so results cannot move the goalposts. Any later change is logged in §9 **with date and reason, before the
results it affects are seen**.

All results stay **SIMULATED, HISTORICAL**. A "SUPPORTED" outcome on validation is a dress rehearsal, not proof.

## 1. Strategies — all of them, with ALL grid settings (no pruning)
| Strategy | Settings | Count |
|---|---|---|
| S0 buy-and-hold (benchmark) | — | 1 |
| S1 fixed profit target | X × Y ∈ {2, 3, 4, 5}% × {2, 3, 4, 5}% | 16 |
| S2 pullback from peak | X × Y as S1 | 16 |
| S3 mean reversion | k ∈ {1.5, 2.0, 2.5} × w ∈ {20, 50} | 6 |
| S4-S1 trend filter on S1 | X × Y as S1 | 16 |
| S4-S2 trend filter on S2 | X × Y as S1 | 16 |

Rules exactly as in research/EXPERIMENT_PLAN.md §2 (incl. the split rule and the S3/S4 exact choices) at tag
`prereg-v1`. No setting is dropped or added because of development-period (2010–2016) results. **S5 (hybrid) is
not built** (decision 2026-10-25). **The S4-S2 AAPL development result (best +217 points) gets NO special
treatment** — it is one of 70 settings per stock, judged by the same rules as all others.

## 2. Stocks — all 8 from research/INITIAL_UNIVERSE.md
AAPL, MSFT, KO, PG, XOM, INTC, T, SPY. Only AAPL and XOM have data today; MSFT, KO, PG, INTC, T and SPY still need
data downloaded and validated (Phase 6 task — same downloader, same validation, same conventions, DATA_SOURCES §7).
If a stock's data fails validation, that is reported; the stock is not silently dropped.

## 3. Periods
| Period | Dates | Status |
|---|---|---|
| Development | 2010-01-04 → 2016-12-30 | done (Phase 5) — exploration only |
| **Validation** | **2017-01-01 → 2020-12-31** | Phase 6 — this pre-registration |
| Final test | 2021-01-01 → latest full year | **LOCKED (D8)** until Goggy unlocks it after Phase 6 |

Indicator warm-up rows (before the period start) are allowed, as in Phase 5; trading and metrics start on the
period's first trading day.

## 4. Settings
- **MAIN** (decides the outcome): Stake fees, normal spread (0.05%/side), fractional shares, AUD 10,000 → USD at
  the RBA rate (latest rate ≤ day), dividends reinvested only when cash ≥ US$100, 15% withholding.
- **Sensitivity** (reported for every strategy and setting, used in rule 4 below): tight spread (0.02%) and wide
  spread (0.10%); IBKR fixed costs (LOW) and CommSec standard costs (HIGH); whole shares instead of fractional.

## 5. Judgement — EXPERIMENT_PLAN §6, copied word for word
> H1 is **SUPPORTED** only if ALL of these are true on the **final test period**, MAIN costs:
> 1. Beats S0 (after costs) on at least **6 of 8** stocks.
> 2. At least **60% of the 16 X/Y combos** beat S0 on average across stocks (not one lucky setting).
> 3. Max drawdown no more than **5 percentage points worse** than S0.
> 4. Still beats S0 with **wide spread** and with **HIGH (CommSec)** costs OR it's documented that it only works on low-cost brokers.
> 5. Still beats S0 after **removing its best 3 trades**.
> 6. At least **10 round trips** per stock in the test period (enough evidence).
>
> H1 is **REJECTED** if it loses to S0 on the majority (5+) of stocks in the final test at MAIN costs.
> Anything in between = **INCONCLUSIVE** (say so honestly; do not round up to "works").
>
> Same structure applies to H2–H6 (H2 uses Sharpe / drawdown instead of final value).

**How it is applied in Phase 6 (dress rehearsal):** the same six rules and three outcomes, applied **per strategy on
the VALIDATION period** (2017–2020), MAIN settings — outcome SUPPORTED / REJECTED / INCONCLUSIVE for each of S1, S2,
S3, S4-S1, S4-S2.
- **Interpretation note for rule 2 (approved by Goggy, 2026-10-25):** for S3, which has 6 k/w settings instead of
  16 X/Y combos, "60%" means **at least 4 of its 6 settings**. For S1, S2, S4-S1, S4-S2: at least 10 of 16 (60% of 16 = 9.6).
- "Beats S0" = higher total return in USD than S0 on the same stock, same period, same settings.

## 6. Robustness checks to run (roadmap Steps 6.3–6.6)
1. Parameter sensitivity: X×Y and k×w heatmaps of excess return per stock — is any result a single lucky cell?
2. Cost sensitivity: every result at tight / normal / wide spread and LOW / MAIN / HIGH broker costs.
3. Best 3 trades removed: each run's result without its 3 most profitable round trips.
4. Regime split: results by year type — up / down / sideways years. Rule (fixed 2026-10-25, see §9): each
   calendar year is labelled per stock from that stock's S0 (buy-and-hold, MAIN settings) total return for that
   year: ≥ +10% = UP, ≤ −10% = DOWN, otherwise SIDEWAYS. Partial first/last years use the days available.
5. Consistency: across the 8 stocks and across the 4 validation years.
6. Dependence on a few trades: share of the total gain coming from the top 1 / top 3 round trips.

## 7. What is NOT allowed
- Changing any rule, setting or threshold after seeing validation results (any change goes in §9 first).
- Picking a "best" setting from development results and testing only that one.
- Preferring a setting because it traded more (roadmap 5.7).
- Opening the final test period before Goggy unlocks it (D8).

## 8. Records
Every validation run saves its full record under /data/runs/ (config, data provenance, git commit + dirty flag,
times, orders, fills, equity). Reports contain summary numbers only (licence). Failed and losing runs are kept.

## 9. Change log
- 2026-10-25: v1 created and tagged `prereg-v1` — before any 2017–2020 data was downloaded or run.
- 2026-10-25: Regime rule (H5, Goggy's decision): each calendar year is labelled per stock from that stock's S0
  (buy-and-hold, MAIN settings) total return for that year: ≥ +10% = UP, ≤ −10% = DOWN, otherwise SIDEWAYS.
  Partial first/last years use the days available. Decided before any 2017–2020 data exists. (Added to §6 item 4.)
- 2026-10-25: Operational definitions for §5 (Goggy approved chat Claude's definitions 2026-10-25; added BEFORE any
  validation run; tagged `prereg-v1.1`):
  "Operational definitions for §5 (validation period 2017-01-03 → 2020-12-31, MAIN settings unless stated):
   - excess(setting, stock) = strategy total return − S0 total return, USD, percentage points.
   - R1 'beats S0 on a stock' = the MEDIAN excess across that strategy's grid settings is > 0 on that stock.
     Pass if true on ≥ 6 of 8 stocks.
   - R2 'settings' = a setting passes if its MEAN excess across the 8 stocks is > 0. Pass if ≥ 60% of settings pass
     (S1, S2, S4-S1, S4-S2: ≥ 10 of 16; S3: ≥ 4 of 6).
   - R3 drawdown: per stock, MEDIAN across settings of (strategy max drawdown − S0 max drawdown), in pp, must be ≥ −5.
     Pass if true on ≥ 6 of 8 stocks.
   - R4 costs: re-evaluate R1 and R2 at the combined stress setting (wide spread AND CommSec). If R1+R2 pass at MAIN
     but fail under stress → label 'low-cost only' (not a pass). Also report tight / wide / IBKR / CommSec / whole
     shares one at a time (sensitivity, not judged).
   - R5 best-3 removed: per run, final value minus the realised P&L (after fees) of its 3 most profitable round trips
     (fewer if it has fewer); recompute R1 + R2. Pass if both still pass.
   - R6 evidence: per stock, MEDIAN round trips across settings ≥ 10. If fewer than 6 of 8 stocks meet it → the verdict
     can be at most INCONCLUSIVE (too few trades), never SUPPORTED.
   - Verdict per strategy: SUPPORTED = R1–R6 all pass. REJECTED = R1 count ≤ 3 of 8 (loses on 5+ stocks).
     INCONCLUSIVE = anything else.
   - S0 itself is the benchmark (no verdict). Regime rule as logged above. Any bug found during runs → STOP, report,
     fix, log here, re-run ALL runs; never re-run only the ones that changed."
- 2026-10-25: Cost-model correction BEFORE any validation run (Goggy approved): CommSec converts AUD↔USD inside every
  trade (0.55% FX charged per trade), so the separate start/end AUD↔USD conversion fee for CommSec is now 0 — before,
  the FX was counted twice on the first buy and on the final conversion. Stake and IBKR unchanged (they convert once at
  deposit / withdrawal). No earlier result used CommSec, so nothing already reported changes. Affects the CommSec and
  stress (wide + CommSec) variants in §4 / R4.
- 2026-10-26: DECISION 2026-10-26 (Goggy): final test 2021+ stays LOCKED until after Phase 9; then it is run ONCE for S1–S4 and any Phase 9 model together, under a new pre-registration tag. Until then nothing dated ≥ 2021-01-01 is downloaded, stored or summarised. Rules for that run (stock list incl. AT&T's 2022 spin-off, dates, data) will be written and tagged BEFORE any 2021+ data is downloaded.
