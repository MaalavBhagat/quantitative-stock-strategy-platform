# DATA_SOURCES.md — Phase 2, Step 2.1
Status: v1 (2026-10-20). Checked on official pages where possible. Re-check before relying on limits.
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
| Python 3.13 support | Newer versions exist (4.13.x listed); 3.13 support [UNVERIFIED] — `uv add` will tell us | test in Step 2.3 |
| Fallback | `pandas_market_calendars` | if the above fails on 3.13 |

## 4. Known gaps and how we handle them
| Gap | Effect | Handling (to confirm in Step 2.4 conventions) |
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
- Why: contains AAPL's 2014 split [UNVERIFIED — confirm from `splitFactor`] and regular XOM dividends,
  so split + dividend handling get tested early. Small: ~1,760 rows per ticker, 2 API calls.
