# SCREENING_METHOD.md — Phase 7 Step 7.3, fixed BEFORE any score is computed

Version: **v1 — 2026-10-26** (prompt 20). Committed on its own, before the scoring code or any score exists, so the
method cannot be tuned to the result. Any later change goes in the change log below, with date and reason.

> This is a transparent, reproducible **SCREEN**, not a buy list and not financial advice. **Nothing in it has been
> tested out of sample.** It describes companies; it does not predict returns.

## 1. Universe and dates
- **Companies:** the 7 with SEC data — AAPL, MSFT, KO, PG, XOM, INTC, T. SPY is excluded from scoring (a fund, no
  company financials); it appears only in the trading profile.
- **As-of dates:** 31 December of each year 2010 … 2020. **Extra as-of date 31 December 2009** — used ONLY for the
  development-period comparison (period start 2010-01-04; Goggy, 2026-10-26).
- **Point-in-time (Step 7.1 rule):** on as-of date D a company is described by its **latest annual report (10-K)
  filed strictly before D**, with every value as known before D (a later restatement counts only if it was filed
  before D). Nothing filed or dated after 2020-12-31 is used (D8).
- **Trading data:** Tiingo raw data for the calendar year that ends on D (rows dated ≤ D), plus the year before only
  as history (first daily return; trailing 12-month dividends).

## 2. Quality score (equal weights, ranks only)
Five inputs, from the Step 7.1 indicators of the 10-K chosen above:

| Input | Better is |
|---|---|
| Return on assets (ROA) | higher |
| FCF margin | higher |
| Liabilities ÷ assets | lower |
| Current ratio | higher |
| EPS-growth std dev (5 years) | lower (steadier earnings) |

- **Sub-score** = the company's rank among the companies that HAVE that input on that as-of date, scaled so the
  best = 1.0 and the worst = 0.0: sub-score = (n − place) ÷ (n − 1), place 1 = best, n = companies with the input.
- **Ties:** tied companies share the average of the places they occupy (e.g. two tied for places 2–3 both get 2.5).
- **Only one company has an input:** sub-score 0.5 (neutral — a rank of one says nothing).
- **Quality score** = plain average of the company's available sub-scores. A company needs **at least 4 of the 5
  inputs**; with fewer it is **NOT SCORED**, and the report says which inputs are missing and why.
- **MISSING and CONFLICT inputs count as missing** (chat Claude ruling 2026-10-26: CONFLICT values are never used).
- No input is filled, estimated or replaced by a later-filed value.

## 3. Trading profile (reported, NOT scored)
Volatility (annualised), median daily dollar volume, median daily range, trailing 12-month dividend yield — the
Step 7.2 definitions. Not part of the score: there is no evidence that any trading profile helps.

## 4. "Why this score"
Each scored company gets one plain-English line, built by code from its sub-scores: its strongest and weakest
inputs (with the sub-score), and any input left out. No line is typed by hand.

## 5. What this method does NOT do
- It does not pick stocks to trade, choose strategy settings, or feed anything back into a backtest.
- It is not tested out of sample, has no evidence of predictive value, and ranks only 7 companies chosen with
  hindsight (see the selection-bias section of the screening report and DATA_SOURCES §8).

## Change log
- 2026-10-26: v1 written and committed before any score was computed.
