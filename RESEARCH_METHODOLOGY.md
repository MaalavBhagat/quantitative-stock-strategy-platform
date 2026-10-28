# RESEARCH_METHODOLOGY.md — how the research was done

Short overview; every point links to the file with the detail. All results are **SIMULATED, HISTORICAL** — not a
prediction, not financial advice.

## 1. The question and the hypotheses
**H1 (main):** starting with AUD 10,000 in one US large-cap stock, does "sell after a rise of X%, buy back after a fall
of Y%" (X, Y = 2–5%) end with more money than buying and holding the same stock with dividends reinvested — after
brokerage, currency conversion and spread, on years not used to choose the settings? "No" is a valid answer.
Secondary: H2 risk-adjusted result · H3 trend filter · H4 mean reversion · H5 market regime · H6 stock type ·
H7 extra information (market context, SEC 8-K events). → research/RESEARCH_QUESTIONS.md

## 2. Data
- Prices: Tiingo daily raw prices + dividends + split factors (personal-use licence, never committed); Yahoo
  (yfinance) only as an independent cross-check. AUD/USD: RBA historical daily rates. Company facts and 8-K filing lists:
  SEC EDGAR (public). → DATA_SOURCES.md (sources, licences, every known limitation in §8)
- 8 stocks chosen in 2026 (survivors, hindsight — stated as a limitation): AAPL, MSFT, KO, PG, XOM, INTC, T, SPY.
  → research/INITIAL_UNIVERSE.md
- Every file is validated before use (9 checks: NYSE calendar, positives, OHLC, splits, dividends, big moves, …) and
  the loader refuses data with any ERROR; nothing is filled or "fixed". → reports/data_validation/

## 3. Simulation rules (no look-ahead)
- A decision at day T's close uses only data up to T; the order fills at day T+1's OPEN (never the same close).
- Trades use RAW prices; indicators use prices split-adjusted as of T (never the provider's adjusted series, which
  contains later dividends and splits). Daily bars only: if a high and a low were both hit, the worse order is assumed.
- Costs: Stake brokerage + 0.55% FX in and out (MAIN), spread 0.05% per side; variants for tight / wide spread, IBKR,
  CommSec, whole shares, and a stress case. Cash rounded to cents against us. Dividends net of 15% US withholding,
  reinvested only once cash ≥ US$100. → research/EXPERIMENT_PLAN.md, research/BROKER_FEES.md, PROJECT_GUIDE.md §4
- Company facts usable only after their filing date; 8-K events only from the close of the first NYSE day after their
  acceptance time (US/Eastern, early closes included). → DATA_SOURCES.md §11–§12
- Enforced by tests: a "spy" harness changes all data after T and checks every decision up to T is unchanged (prices,
  SPY market data, events); deliberate mutations prove the checks fail when the rule is broken. → TESTING.md

## 4. Pre-registration — rules written and git-tagged BEFORE the data they judge was run
| Tag | File | Fixed before | Covers |
|---|---|---|---|
| `prereg-v1` / `prereg-v1.1` | research/PREREGISTRATION.md | any 2017–2020 run (2026-10-25) | S0–S4, 70 settings per stock, R1–R6 |
| `prereg-v2` | research/PREREGISTRATION_V2.md | any C1/C2/E1 run on real data (2026-10-28) | C1, C2, E1 vs their twins |
| `prereg-final` | research/FINAL_TEST_PREREG.md | any 2021+ download (2026-10-28 16:48 vs 18:51) | one-time final test, 7 stocks |
Every later change is logged in the file's change log with date and reason, before the results it affects were seen.

## 5. Periods
| Period | Dates | Use |
|---|---|---|
| Development | 2010–2016 (warm-up 2008–2009) | build and explore; nothing judged |
| Validation | 2017–2020 | pre-registered dress rehearsal (S0–S4, then C1/C2/E1) |
| Final test | 2021–2025 | run ONCE (5,096 runs), every strategy, T excluded (2022 spin-off) — now USED |

## 6. Verdict rules
Per strategy, MAIN settings, against its benchmark (Buy-and-hold for S1–S4 and C1; the twin S4-S2 for C2 and E1):
R1 beats the benchmark on most stocks (median excess across settings) · R2 most settings beat it on average ·
R3 drawdown not more than 5 pp worse · R4 still passes at wide spread + CommSec · R5 still passes without the best 3
trades · R6 enough round trips. SUPPORTED = all pass; REJECTED = loses on 5+ stocks; else INCONCLUSIVE.
→ research/PREREGISTRATION.md §5 + §9, research/PREREGISTRATION_V2.md §6, research/FINAL_TEST_PREREG.md §4

## 7. Independent checks (chat Claude, separate from the code that produced the results)
| Date | What was re-checked |
|---|---|
| 2026-10-20 / 25 | Phase 1 setup; Phase 4 engine — S0 rebuilt independently from the raw CSVs |
| 2026-10-26 | Validation: all 8 S0 finals and two full trade lists reproduced to the cent by a separate re-implementation |
| 2026-10-28 | Phase 9: all 8 C1 finals and all 27 C1 AAPL trades reproduced exactly |
| 2026-10-28 | Final test: all 7 S0 finals and all 23 C1 SPY trades reproduced exactly; tag before download confirmed |
Plus, in code: the twin re-runs in Phase 9 matched Phase 6 to the cent (952 runs); Phase 10 replays 20 random saved
runs and regenerates every report (11 of 12 byte-identical, 1 differs only in its date stamp).

## 8. Results and what they do not show
All eight strategies were REJECTED in validation and again in the final test (H1, H3, H4, H7 rejected; H2, H5, H6 have
no verdict rule). → reports/RESULTS_SUMMARY.md, research/FAILED_EXPERIMENTS.md. Limits: survivors chosen with hindsight,
daily bars, assumed spreads, no tax, one main data source — reports/RESULTS_SUMMARY.md §5, DATA_SOURCES.md §8.
