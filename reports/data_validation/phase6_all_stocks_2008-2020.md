# Phase 6 data validation — 8 stocks, 2008–2020 (prompt 16)

> Data quality only. Counts, dates and % only — no price series (Tiingo licence). No strategy, backtest,
> metric or summary statistic of 2017–2020 prices is computed. Not reported (Goggy 2026-10-25, D8): the
> adjustment estimate after each file's end and the later-split ratio implied by Yahoo's basis, because both
> would summarise corporate actions from the locked final-test period.

**ERRORS: 0** — every file passed.

## 1. Every file (same 9 checks as Step 2.3)

| Ticker | File | Rows | NYSE sessions | ERROR | WARNING | INFO | Splits (date, factor → ratio) | Dividends |
|---|---|---|---|---|---|---|---|---|
| AAPL | warm-up | 505 | 505 | 0 | 0 | 2 | none | 0 |
| AAPL | development | 1762 | 1762 | 0 | 0 | 4 | 2014-06-09 7.000007 → 7:1 | 18 |
| AAPL | validation | 1007 | 1007 | 0 | 0 | 4 | 2020-08-31 4.0 → 4:1 | 16 |
| MSFT | warm-up | 505 | 505 | 0 | 0 | 2 | none | 8 |
| MSFT | development | 1762 | 1762 | 0 | 0 | 2 | none | 28 |
| MSFT | validation | 1007 | 1007 | 0 | 0 | 2 | none | 16 |
| KO | warm-up | 505 | 505 | 0 | 0 | 2 | none | 8 |
| KO | development | 1762 | 1762 | 0 | 0 | 4 | 2012-08-13 2.0 → 2:1 | 28 |
| KO | validation | 1007 | 1007 | 0 | 0 | 2 | none | 16 |
| PG | warm-up | 505 | 505 | 0 | 0 | 2 | none | 8 |
| PG | development | 1762 | 1762 | 0 | 0 | 2 | none | 28 |
| PG | validation | 1007 | 1007 | 0 | 0 | 2 | none | 16 |
| XOM | warm-up | 505 | 505 | 0 | 0 | 2 | none | 8 |
| XOM | development | 1762 | 1762 | 0 | 0 | 2 | none | 28 |
| XOM | validation | 1007 | 1007 | 0 | 0 | 2 | none | 16 |
| INTC | warm-up | 505 | 505 | 0 | 0 | 2 | none | 8 |
| INTC | development | 1762 | 1762 | 0 | 0 | 2 | none | 28 |
| INTC | validation | 1007 | 1007 | 0 | 0 | 2 | none | 16 |
| T | warm-up | 505 | 505 | 0 | 0 | 2 | none | 8 |
| T | development | 1762 | 1762 | 0 | 0 | 2 | none | 28 |
| T | validation | 1007 | 1007 | 0 | 0 | 2 | none | 16 |
| SPY | warm-up | 505 | 505 | 0 | 0 | 2 | none | 8 |
| SPY | development | 1762 | 1762 | 0 | 0 | 2 | none | 28 |
| SPY | validation | 1007 | 1007 | 0 | 0 | 2 | none | 16 |

**Warnings per file:** none.

## 2. Joins: warm-up → development → validation (NYSE calendar, 2008-01-01 → 2020-12-31)

| Ticker | Rows joined | NYSE sessions | Boundaries (last → first) | ERROR | WARNING |
|---|---|---|---|---|---|
| AAPL | 3274 | 3274 | 2009-12-31 → 2010-01-04; 2016-12-30 → 2017-01-03 | 0 | 0 |
| MSFT | 3274 | 3274 | 2009-12-31 → 2010-01-04; 2016-12-30 → 2017-01-03 | 0 | 0 |
| KO | 3274 | 3274 | 2009-12-31 → 2010-01-04; 2016-12-30 → 2017-01-03 | 0 | 0 |
| PG | 3274 | 3274 | 2009-12-31 → 2010-01-04; 2016-12-30 → 2017-01-03 | 0 | 0 |
| XOM | 3274 | 3274 | 2009-12-31 → 2010-01-04; 2016-12-30 → 2017-01-03 | 0 | 0 |
| INTC | 3274 | 3274 | 2009-12-31 → 2010-01-04; 2016-12-30 → 2017-01-03 | 0 | 0 |
| T | 3274 | 3274 | 2009-12-31 → 2010-01-04; 2016-12-30 → 2017-01-03 | 0 | 0 |
| SPY | 3274 | 3274 | 2009-12-31 → 2010-01-04; 2016-12-30 → 2017-01-03 | 0 | 0 |

**Join warnings:** none.

## 3. Yahoo cross-check (yfinance, auto_adjust=False, one request per ticker 2008-01-01 → 2020-12-31)

| Ticker | File | Days only-Tiingo / only-Yahoo | Split basis explained | Splits same | Dividends T / Y, max diff | Closes max / median diff, days > 0.5% |
|---|---|---|---|---|---|---|
| AAPL | warm-up | 0 / 0 | yes | yes | 0 / 0, 0.0000% | 0.309% / 0.0000%, 0 |
| AAPL | development | 0 / 0 | yes | yes | 18 / 18, 0.0004% | 0.318% / 0.0000%, 0 |
| AAPL | validation | 0 / 0 | yes | yes | 16 / 16, 0.0000% | 0.004% / 0.0000%, 0 |
| MSFT | warm-up | 0 / 0 | yes | yes | 8 / 8, 0.0000% | 0.336% / 0.0000%, 0 |
| MSFT | development | 0 / 0 | yes | yes | 28 / 28, 0.0000% | 0.136% / 0.0000%, 0 |
| MSFT | validation | 0 / 0 | yes | yes | 16 / 16, 0.0000% | 0.000% / 0.0000%, 0 |
| KO | warm-up | 0 / 0 | yes | yes | 8 / 8, 0.0000% | 0.817% / 0.0000%, 1 |
| KO | development | 0 / 0 | yes | yes | 28 / 28, 0.0000% | 0.004% / 0.0000%, 0 |
| KO | validation | 0 / 0 | yes | yes | 16 / 16, 0.0000% | 0.000% / 0.0000%, 0 |
| PG | warm-up | 0 / 0 | yes | yes | 8 / 8, 0.0000% | 0.799% / 0.0000%, 1 |
| PG | development | 0 / 0 | yes | yes | 28 / 28, 0.0831% | 0.718% / 0.0000%, 1 |
| PG | validation | 0 / 0 | yes | yes | 16 / 16, 0.0747% | 0.023% / 0.0000%, 0 |
| XOM | warm-up | 0 / 0 | yes | yes | 8 / 8, 0.0000% | 0.810% / 0.0000%, 2 |
| XOM | development | 0 / 0 | yes | yes | 28 / 28, 0.0000% | 1.085% / 0.0000%, 3 |
| XOM | validation | 0 / 0 | yes | yes | 16 / 16, 0.0000% | 0.030% / 0.0000%, 0 |
| INTC | warm-up | 0 / 0 | yes | yes | 8 / 8, 0.3922% | 0.398% / 0.0000%, 0 |
| INTC | development | 0 / 0 | yes | yes | 28 / 28, 0.3175% | 6.831% / 0.0000%, 1 |
| INTC | validation | 0 / 0 | yes | yes | 16 / 16, 0.1835% | 0.014% / 0.0000%, 0 |
| T | warm-up | 0 / 0 | yes (constant non-split factor, value not shown — D8) | yes | 8 / 8, 0.0000% | 0.458% / 0.0000%, 0 |
| T | development | 0 / 0 | yes (constant non-split factor, value not shown — D8) | yes | 28 / 28, 0.0000% | 1.953% / 0.0000%, 2 |
| T | validation | 0 / 0 | yes (constant non-split factor, value not shown — D8) | yes | 16 / 16, 0.0000% | 0.014% / 0.0000%, 0 |
| SPY | warm-up | 0 / 0 | yes | yes | 8 / 8, 0.0766% | 0.000% / 0.0000%, 0 |
| SPY | development | 0 / 0 | yes | yes | 28 / 28, 0.0791% | 0.113% / 0.0000%, 0 |
| SPY | validation | 0 / 0 | yes | yes | 16 / 16, 0.0347% | 0.000% / 0.0000%, 0 |

**Close differences > 0.5% (tested against the data):** 
- KO warm-up 2009-09-10: +0.817% → difference equals the next day's dividend (day before ex-date)
- PG warm-up 2009-07-21: +0.799% → difference equals the next day's dividend (day before ex-date)
- PG development 2010-01-19: +0.718% → difference equals the next day's dividend (day before ex-date)
- XOM warm-up 2008-01-31: -0.810% → unexplained
- XOM warm-up 2009-11-06: +0.582% → difference equals the next day's dividend (day before ex-date)
- XOM development 2010-02-05: +0.652% → difference equals the next day's dividend (day before ex-date)
- XOM development 2010-05-10: +0.679% → difference equals the next day's dividend (day before ex-date)
- XOM development 2014-07-28: +1.085% → unexplained
- INTC development 2014-06-13: +6.831% → unexplained
- T development 2011-10-27: +1.132% → unexplained
- T development 2014-07-28: -1.953% → unexplained

## 4. Flat bars (open = high = low = close) — stale / repeated bars, reported, NOT fixed

- INTC 2014-06-13: flat bar, volume 3.6× the ticker's median

## 5. Possible unsupported corporate actions (flagged for a human look, not handled)

- none found (all split factors near simple ratios; no dividend > 2× the median on one share basis).

## 6. Errors

- none.
