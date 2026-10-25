# Phase 5 comparison — S0 to S4, development period 2010–2016

> **SIMULATED, HISTORICAL, DEVELOPMENT PERIOD — exploration only, not evidence (EXPERIMENT_PLAN §4).**
> Computed by `scripts/phase5_comparison.py` from the SAVED run records (nothing typed by hand).
> No winner is picked and strategies are NOT ranked by return or by number of trades (roadmap 5.7).

## 1. Consistency proof

Runs used: 66 from the S1/S2 report (commit 987c81c) + 78 from the S3/S4 report (commit 8f3cf46). Within each ticker, every one of these is **identical** across all runs:

| Field | AAPL | XOM |
|---|---|---|
| initial capital (AUD) | 10000 | 10000 |
| period | ('2010-01-04', '2016-12-30') | ('2010-01-04', '2016-12-30') |
| price file + download time | ('AAPL_2010-01-01_2016-12-31.csv', '2026-10-20T05:38:33+00:00') | ('XOM_2010-01-01_2016-12-31.csv', '2026-10-20T05:38:35+00:00') |
| broker | stake | stake |
| spread level | normal | normal |
| share mode | fractional | fractional |
| FX source + files | ('rba', ('2010-2013.xls', '2014-2017.xls')) | ('rba', ('2010-2013.xls', '2014-2017.xls')) |
| FX rates used (start, end) | ('0.9133', '0.7236') | ('0.9133', '0.7236') |
| start cash (USD) | 9082.76 | 9082.76 |
| reinvest rule (US$) | 100 | 100 |
| min order (US$) | 10 | 10 |
| final test locked | False | False |
| uncommitted code changes (git_dirty) | False | False |
| S0 benchmark final value (USD) | 37069.58 | 13954.00 |

One difference by design: S3 and S4 runs also read a 2008–2009 **warm-up** file AAPL_2008-01-01_2009-12-31.csv, XOM_2008-01-01_2009-12-31.csv for indicators only. The S3/S4 report proved that S0/S1/S2 give identical results with warm-up rows present
(66 of 66 to the cent). Every sell in every run is a full exit (size "all"), so round trips = number of sells.

## 2. Roll-up per ticker (excess = strategy total return − S0 total return, percentage points, USD)

**AAPL** — S0 total return 308.13%

| Strategy | Settings tried | Beat S0 | Median excess | Best excess | Worst excess | Stranded at end | Median % days in cash | Median round trips |
|---|---|---|---|---|---|---|---|---|
| S1 | 16 | 0 | -304.0 | -294.8 | -306.6 | 16 | 97% | 1 |
| S2 | 16 | 0 | -164.3 | -62.7 | -224.5 | 0 | 19% | 21.5 |
| S3 | 6 | 0 | -261.9 | -202.7 | -269.3 | 5 | 65% | 12.5 |
| S4-S1 | 16 | 0 | -250.0 | -228.4 | -255.1 | 16 | 79% | 2 |
| S4-S2 | 16 | 14 | +73.7 | +217.1 | -23.5 | 0 | 5% | 7.5 |

**XOM** — S0 total return 53.63%

| Strategy | Settings tried | Beat S0 | Median excess | Best excess | Worst excess | Stranded at end | Median % days in cash | Median round trips |
|---|---|---|---|---|---|---|---|---|
| S1 | 16 | 4 | -24.2 | +23.5 | -48.8 | 16 | 84% | 4 |
| S2 | 16 | 3 | -6.6 | +7.2 | -23.6 | 0 | 16% | 8.5 |
| S3 | 6 | 1 | -30.9 | +2.4 | -44.4 | 6 | 45% | 12.5 |
| S4-S1 | 16 | 7 | -4.0 | +24.4 | -48.8 | 12 | 72% | 6 |
| S4-S2 | 16 | 9 | +2.9 | +35.1 | -27.2 | 0 | 8% | 6 |

## 3. How many settings we tried — and why a win here is not evidence

Settings tried per stock: 70 (S1 16, S2 16, S3 6, S4-S1 16, S4-S2 16). AAPL: 14 of 70 beat S0; XOM: 24 of 70 beat S0.

In plain words: when you try 70 different settings on the same seven years of two stocks, some of them
will beat buy-and-hold by luck alone — the same way that if 70 people each toss a coin ten times, a few
will get eight heads. So a development-period win is a **hypothesis to test**, not evidence that the idea
works. That is why the next step tests ALL settings (not just the ones that looked good) on new years
(validation 2017–2020) and more stocks, with the rules fixed in advance (research/PREREGISTRATION.md).
The large S4-S2 AAPL result rests on a few big dips (see the S3/S4 report) and gets no special treatment.

## 4. Reproducibility check (5 saved configs chosen at random, seed 20261025, re-run from config.yaml)

| Saved run | Final USD saved | Final USD re-run | Final AUD saved | Final AUD re-run | Identical |
|---|---|---|---|---|---|
| 20261025T093545Z_s3_xom_mr_k2.0_mr_window20_dev | 10830.07 | 10830.07 | 14884.60 | 14884.60 | yes |
| 20261025T093524Z_s4s2_aapl_profit_target_x0.04_rebuy_dip_y0.02_dev | 37961.55 | 37961.55 | 52142.20 | 52142.20 | yes |
| 20261025T091930Z_s2_xom_x0.03_y0.05_dev | 12476.72 | 12476.72 | 17135.01 | 17135.01 | yes |
| 20261025T091929Z_s2_xom_x0.02_y0.02_dev | 14377.45 | 14377.45 | 19746.04 | 19746.04 | yes |
| 20261025T093548Z_s4s1_xom_profit_target_x0.02_rebuy_dip_y0.03_dev | 12542.75 | 12542.75 | 17238.47 | 17238.47 | yes |

Re-runs are kept under /data/runs/_reproductions/phase5_check_*/ (git-ignored).
