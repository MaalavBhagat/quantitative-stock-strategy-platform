# DATA_SOURCES.md — Phase 2, Step 2.1
Status: v1.1 (2026-10-20; §7 conventions + §8 limitations added in Steps 2.4–2.5). Checked on official pages where possible. Re-check before relying on limits.
Labels: [OFFICIAL] = provider's own page · [SECONDARY] = third-party page · [UNVERIFIED] = must test ourselves

## 1. Primary source — Tiingo (free plan)
| Item | Value | Label / source |
|---|---|---|
| Price | US$0 | [OFFICIAL] [Tiingo EOD product page](https://www.tiingo.com/products/end-of-day-stock-price-data) |
| Limits | 50 requests/hour, 1,000/day, 1 GB/month | [OFFICIAL] same page |
| Unique symbols | ~500 per month (older) or per day (2026 profile) — not on official page | [SECONDARY] [QuantStart](https://www.quantstart.com/articles/evaluating-data-coverage-with-tiingo/), [APIs.io](https://apis.io/rate-limits/tiingo/tiingo-rate-limits/) — irrelevant for our 8 tickers |
| Licence | "Internal Use Only", individual | [OFFICIAL] → never commit data; never publish raw data |
| History | Back to 1962 for long-listed stocks ("50+/60+ years") | [OFFICIAL] |
| Endpoint | `https://api.tiingo.com/tiingo/daily/<ticker>/prices?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD` | [OFFICIAL] [Tiingo EOD docs](https://www.tiingo.com/documentation/end-of-day) |
| Meta endpoint | `/tiingo/daily/<ticker>` → ticker, name, exchangeCode, startDate, endDate | [OFFICIAL] same |
| Raw fields | `date, open, high, low, close, volume` | [OFFICIAL] |
| Adjusted fields | `adjOpen, adjHigh, adjLow, adjClose, adjVolume` (CRSP method: splits + dividends) | [OFFICIAL] |
| Dividends | `divCash` on the **ex-date** row | [OFFICIAL] |
| Splits | `splitFactor` (also used for some distributions) | [OFFICIAL] |
| Timezone of `date` | Docs don't state it. Real download (2026-10-20): every value is midnight with a UTC label, e.g. `2010-01-04T00:00:00.000Z`; all 1,762 dates (AAPL, XOM 2010–2016) match the NYSE XNYS calendar exactly and Yahoo's New-York-dated rows → it is the US trading date. Code drops the time part; any non-midnight time fails loudly | [CHECKED — our data] reports/data_validation/2010-2016_AAPL_XOM.md |
| Release time | ~5:30 PM US Eastern, corrections until 8 PM | [OFFICIAL] |
| Rate-limit error | HTTP 429 → wait and retry with backoff | [SECONDARY] APIs.io |
| Delisted stocks | Docs don't say. Official [supported_tickers.zip](https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip) (downloaded 2026-10-20; columns ticker, exchange, assetType, priceCurrency, startDate, endDate; 109,085 rows) lists 3,019 US-exchange USD stocks with endDate before 2020 → some delisted tickers ARE listed. But LEH, LEHMQ, ENRNQ, WAMUQ not found by symbol → coverage looks partial. Price download for delisted tickers NOT tested | [CHECKED — list only; downloadability UNVERIFIED] report §5 |
| Dividend **pay date** | NOT provided (only ex-date + amount) | [OFFICIAL — absent from field list] → see §4 |

## 2. Cross-check source — yfinance (Yahoo)
| Item | Value | Label / source |
|---|---|---|
| Status | Unofficial client, not a contracted API; rate limits (HTTP 429) without notice | [SECONDARY] [guide](https://thelinuxcode.com/what-the-yfinance-library-is-and-isnt-a-practical-guide-to-yahoo-finance-data-in-python/) |
| Licence | "Intended for personal use only" | [OFFICIAL-ish] [yfinance PyPI](https://pypi.org/project/yfinance/0.2.39) |
| Gotcha | `auto_adjust` changes what "Close" means. Default has changed across versions [UNVERIFIED which] | → **always pass `auto_adjust=False` explicitly** |
| Basis (checked 2026-10-20, yfinance 1.7.0) | Even with `auto_adjust=False`, Yahoo `Close`, `Dividends` and `Volume` are split-adjusted for ALL splits incl. later ones (AAPL 2010–2014 close = Tiingo raw ÷ 28 = 7×4). Must convert back before comparing | [CHECKED — our data] report §4 |
| Use | Spot-check Tiingo raw closes, dividends, splits (Step 2.3). Never the main source. | decision |

## 3. Trading calendar (D4)
| Item | Value | Label / source |
|---|---|---|
| Library | `exchange_calendars`, calendar code `XNYS` (NYSE) | [OFFICIAL] [PyPI](https://pypi.org/project/exchange-calendars/4.1) |
| Licence | Apache 2.0 | [OFFICIAL] |
| Python 3.13 support | 4.13.2 installs and runs on Python 3.13.16 (Step 2.3, 2026-10-20); fallback not needed | [CHECKED — our setup] |
| Fallback | `pandas_market_calendars` | if the above fails on 3.13 |

## 4. Known gaps and how we handle them
| Gap | Effect | Handling (now fixed in §7 conventions and §8 limitations) |
|---|---|---|
| No dividend pay date | Can't credit cash on the real pay date | [ASSUMPTION] credit cash on ex-date (+ optional fixed lag). Same rule for all strategies. Documented limitation. |
| No historical bid-ask spread | Spread must be assumed | 3 spread levels (EXPERIMENT_PLAN §1) |
| Daily bars only | Intraday order unknown | T close → T+1 open; worse-order rule |
| Delisted coverage unknown | Survivorship bias | Test in Phase 2; document result |
| Adjusted prices are recomputed by provider over time | Old downloads may differ from new | Save raw data + download date; trade on raw only |

## 5. Broker facts confirmed while doing this step
- Stake withdrawal FX: **0.55% USD→AUD (US$0.55 per A$100), no separate withdrawal fee** —
  [OFFICIAL] [Stake support: withdrawals](https://hellostake.com/support/funding-and-withdrawal/withdrawal/26014595952153). Closes the open item from Step 0.4.
- Stake fractional-share precision: still [UNVERIFIED] (D3 assumes 6 dp).

## 6. Initial dataset for Step 2.2 (roadmap: start small)
- Tickers: AAPL, XOM. Period: 2010-01-01 → 2016-12-31 (inside the development period).
- Why: contains AAPL's 2014 split (confirmed: `splitFactor` 7.000007 on 2014-06-09, Yahoo shows 7:1 — Step 2.3) and regular XOM dividends,
  so split + dividend handling get tested early. Small: ~1,760 rows per ticker, 2 API calls.

## 7. Data conventions (Phase 2, Step 2.4)
These rules are what the code does now (`src/quant_research/data/`); Phase 3+ code must follow them.

| # | Topic | Rule |
|---|---|---|
| 1 | Timestamps | Tiingo sends midnight with a UTC label (`2010-01-04T00:00:00.000Z`). We store a plain **US trading date** (no time). Any other time of day → ERROR (`tiingo.parse_prices`). |
| 2 | Calendar | NYSE = `exchange_calendars` 4.13.2, code `XNYS` (D4). Data dates must match it **exactly**: a missing or extra day → ERROR (`validation.check_calendar`). |
| 3 | Currency | All Tiingo prices and dividends are **USD**. Evidence: AAPL (NASDAQ) and XOM (NYSE) have `priceCurrency` = USD in Tiingo's supported_tickers file (2026-10-20). Column names say so (`div_cash_usd`). AUD appears only at portfolio start/end via the FX cost (EXPERIMENT_PLAN §1). |
| 4 | Raw vs adjusted | Trading and accounting use `*_raw` columns **only**. `*_adj` is for analysis/validation only and the loader leaves it out unless `include_adjusted=True`. Adjusted values change with the download date → never compare adjusted values across downloads. |
| 5 | Splits | `split_factor` is snapped to the nearest realistic ratio (n:1, 1:n, or p:q ≤ 10 — as `validation.nearest_simple_ratio` does; 7.000007 → 7:1). On the split date, shares held × ratio; raw prices on that row already reflect the split. Exact rule built and tested in Phase 3. |
| 6 | Dividends | `div_cash_usd` sits on the **ex-date** row. Entitled = holding shares at the close of the trading day **before** the ex-date. Cash credited **on the ex-date** [ASSUMPTION — Tiingo has no pay date; §8]. US withholding 15% with W-8BEN (VERIFIED — link in EXPERIMENT_PLAN §1). Same rule for every strategy. |
| 7 | Missing data | Never filled, interpolated or forward-filled. Any validation ERROR → `loader.load_prices` stops with a clear message. WARNINGs are logged, data returned. |
| 8 | Caching | A saved file is reused; the loader never downloads. Re-downloading needs `overwrite=True` (`storage.save_raw_prices`) and writes a new download timestamp in `.meta.json`. Yahoo cross-check data is cached under `data/cache/yfinance/`. |
| 9 | Versioning | File name = `TICKER_<requested start>_<requested end>.csv`; `.meta.json` = source, endpoint (no key), download time (UTC), row count, first/last date, git commit, dirty flag. Every load returns `Provenance` (file name, downloaded_at_utc, git commit, rows) for the run record. |
| 10 | Source disagreements | **Tiingo is the source of truth.** Known Tiingo-vs-Yahoo differences are listed, not "fixed": XOM 2010-02-05 (+0.652%) and 2010-05-10 (+0.679%) — Yahoo higher by exactly the next day's dividend; XOM 2014-07-28 (+1.085%) — unexplained. A third source (Financial Datasets) was tried by chat Claude — no credits; left unresolved, impact judged tiny (3 of 3,524 rows, signal-day closes only). |

## 8. Known limitations (Phase 2, Step 2.5)
| Limitation | Effect on results | What we do about it |
|---|---|---|
| Daily bars only — intraday order of high/low unknown | Can't tell if a buy or sell level was hit first inside a day | Decide at T close → trade at T+1 open; where a limit-order test is added, assume the worse order (EXPERIMENT_PLAN §1) |
| No dividend pay date (ex-date + amount only) | Cash arrives earlier in the model than in real life (usually a few weeks) | Credit cash on the ex-date for every strategy alike [ASSUMPTION]; documented here |
| No historical bid-ask spread | Real trading cost per trade unknown | Model 3 spread levels (tight/normal/wide) and report each (EXPERIMENT_PLAN §1) |
| Partial delisted coverage | Survivorship bias — results too optimistic, especially for "buy the dip" | Official supported_tickers list has 3,019 US-exchange stocks with endDate before 2020, but Lehman/Enron/WaMu (LEH, LEHMQ, ENRNQ, WAMUQ) are absent under the symbols checked; delisted price download untested. Our 8 stocks are all survivors → stated in every result (INITIAL_UNIVERSE.md) |
| Adjusted prices drift with download date | Old and new downloads of `*_adj` differ (e.g. AAPL 2016 adj values include a later ~4:1 split, implied by the ratio) | Trade on raw only; save raw + download date; never compare `*_adj` across downloads |
| Single primary source | Errors in Tiingo would pass into results | Yahoo used only as a cross-check: days, splits, dividends agree; 3 XOM closes differ > 0.5% (§7 row 10). Report re-run per new dataset |
| Licence: Tiingo "Internal Use Only" | Raw data can't be shared or published | `/data/` git-ignored; reports show counts, dates and % only |
| Split factor not exact (AAPL 7.000007) | Using it as-is would create fractional share drift | Snap to nearest realistic ratio (§7 row 5); WARNING if not within 1e-4 of one |
| Yahoo values split-adjusted even with `auto_adjust=False` | Naive comparisons would look wildly wrong | Basis detected from the data and converted (`crosscheck.detect_split_basis`); fails loudly if unexplained |
