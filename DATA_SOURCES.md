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
| 6 | Dividends | `div_cash_usd` sits on the **ex-date** row. Entitled = holding shares at the close of the trading day **before** the ex-date. Cash credited **on the ex-date** [ASSUMPTION — Tiingo has no pay date; §8]. US withholding 15% with W-8BEN, taken from the gross rounded down to cents, rounded up (VERIFIED — link in EXPERIMENT_PLAN §1). Same rule for every strategy. |
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
| **Unsupported:** reverse splits that leave a fraction in whole-share mode (cash-in-lieu) | Can't model the cash paid for the fraction | Ledger raises NotImplementedError (none in our data so far). Fractional mode rounds down to 6 dp and notes the dropped fraction |
| Other corporate actions (spin-offs, mergers, special distributions in `splitFactor`) | Not modelled | Checked for all 8 tickers 2008–2020 (Phase 6): only splits found — AAPL 7:1 2014-06-09, AAPL 4:1 2020-08-31, KO 2:1 2012-08-13; no split factor away from a simple ratio; no dividend > 2× the median on one share basis. Check again for any new ticker or period |

| **Tiingo bad bar (found Phase 6):** INTC 2014-06-13 has open = high = low = close = 27.96 (the previous close repeated) with volume 3.6× median; Yahoo shows the real day (+6.8%) | Signals/fills on that day would use a stale price (development period only) | Reported in reports/data_validation/phase6_all_stocks_2008-2020.md §4; NOT fixed. It is the only flat bar in all 24 files. The 9 checks don't catch it (no rule for flat bars) |
| Yahoo applies a later NON-split adjustment to AT&T (T) prices but not its dividends (found Phase 6) | A plain Yahoo comparison for T fails ("basis not explained") | crosscheck(allow_constant_later_factor=True): a constant factor, value never reported (it describes the locked period, D8); T then agrees with Tiingo on days, splits and dividends |
| Same-day cross-source differences on 2014-07-28 for XOM (+1.085%) and T (−1.953%) | Unknown which source is right | Listed, not fixed (third source needed) |

## 9. AUD/USD exchange rate source (chosen 2026-10-20, for portfolio start/end conversion)
| Item | Value | Label / source |
|---|---|---|
| Source | Reserve Bank of Australia (RBA) historical exchange rates (daily) | [OFFICIAL] [RBA exchange rates](https://www.rba.gov.au/statistics/frequency/exchange-rates.html), files on [RBA historical data](https://www.rba.gov.au/statistics/historical-data.html#exchange-rates) |
| What the USD rate is | WM/Reuters AUD fix at **4.00 pm Sydney** (since 1 Jul 2008); before that, RBA's own 4 pm mid-rate | [OFFICIAL] [RBA definitions](https://www.rba.gov.au/statistics/frequency/definitions-sources.html) |
| Days | NSW business days only (no rate on NSW public/bank holidays) | [OFFICIAL] |
| Licence | Personal, non-commercial use, unaltered, attributed to the RBA | [OFFICIAL] [RBA copyright](https://www.rba.gov.au/copyright/) → store under /data/, cite RBA in reports |
| Timing rule | 4 pm Sydney is BEFORE the US open of the same calendar day. Conversion on US trading day T uses the latest RBA rate dated ≤ T (Sydney date). No rate that day → previous available rate, logged; more than 5 calendar days old → ERROR. [ASSUMPTION] | implemented: `data/fx.py` (`FxSeries.on`) |
| Exact file names / columns | `2010-2013.xls`, `2014-2017.xls` (old Excel .xls, read with `xlrd`), sheet **Data**, header row "Series ID", USD column **FXRUSD** ("A$1=USD", WM/Reuters), dates in column 1. 2010–2013: 1,003 rates; 2014–2017: 1,003 rates (+1 "N/A" on 2015-05-25, skipped). Downloaded once 2026-10-21 to /data/raw/rba/ with .meta.json | [CHECKED — our download] |
| 2018–2020 file | `2018-2022.xls` downloaded once 2026-10-25 to a scratch folder, ONLY rows ≤ 2020-12-31 kept as `data/raw/rba/2018-2020_from_2018-2022.csv` (755 rates, 2018-01-02 → 2020-12-31; 501 later rows dropped), original deleted (Goggy's decision, D8). The loader refuses a trimmed file with any row after 2020-12-31 | [CHECKED] |
| Coverage 2010–2020 | 2,761 rates 2010-01-04 → 2020-12-31, range 0.5571–1.1055; every NYSE session 2010–2020 (2,769) has a rate ≤ 5 days old (77 use an earlier day's rate) | [CHECKED] |
| Coverage check | 2,006 rates 2010-01-04 → 2017-12-29, range 0.6867–1.1055. Every NYSE session 2010–2016 has a rate ≤ 5 days old (50 sessions use an earlier day's rate). Longest gap between RBA rows: 6 days (Easter + Anzac Day 2011) | [CHECKED] |

## 10. Phase 6 data inventory (downloaded 2026-10-25, prompt 16)
| Data | Files | Notes |
|---|---|---|
| Tiingo daily prices | 24: AAPL MSFT KO PG XOM INTC T SPY × warm-up 2008–2009, development 2010–2016, validation 2017–2020 | 20 new API calls; every file 0 ERROR / 0 WARNING; joins clean on the NYSE calendar (3,274 sessions each) |
| Yahoo cross-check cache | 8: one per ticker, 2008-01-01 → 2020-12-31 (data/cache/yfinance/) | 8 yfinance requests; days, splits, dividend dates agree everywhere |
| RBA AUD/USD | 2010-2013.xls, 2014-2017.xls, 2018-2020_from_2018-2022.csv | see §9 |
| Nothing dated ≥ 2021-01-01 | — | scan of every data file on disk, 2026-10-25: 0 found (D8) |
Report: reports/data_validation/phase6_all_stocks_2008-2020.md.

## 11. Company financials — SEC EDGAR XBRL (Phase 7, Step 7.1; downloaded 2026-10-26, prompt 19)
(Prompt 19 calls this "new §10"; §10 was already the Phase 6 inventory, so it is §11.)
| Item | Fact | Source |
|---|---|---|
| API | `companyfacts`: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json (10-digit CIK); free, **no API key** | [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) |
| Fair access | max **10 requests/second**; declare a User-Agent with name + contact email. We use ≥ 1 s between requests; User-Agent = `SEC_USER_AGENT` in .env (never printed, logged or saved) | [Accessing EDGAR data](https://www.sec.gov/os/accessing-edgar-data) |
| Reuse / licence | "Information presented on sec.gov is considered public information and may be copied or further distributed"; SEC asks to be cited as the source. Stored under data/raw/sec/ (git-ignored) like all downloaded data | [sec.gov/privacy](https://www.sec.gov/privacy) |
| Ticker → CIK | https://www.sec.gov/files/company_tickers.json — SEC: "do not guarantee accuracy or scope". A **current** snapshot (10,425 rows); only our 8 rows kept (data/raw/sec/cik_map.json) | [EDGAR search assistance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) |
| Field names (checked in the real JSON) | top: `cik`, `entityName`, `facts` → taxonomy (`us-gaap`, `dei`, …) → tag → `label`, `description`, `units` → unit (`USD`, `USD/shares`, `shares`, `pure`) → list of facts with `accn`, `end`, `filed`, `form`, `fp`, `fy`, `val`, plus `start` (duration facts only) and sometimes `frame`. `fy`/`fp` describe the FILING, not the period — we use `start`/`end` | downloaded files |
| D8 trim | facts filed after 2020-12-31 dropped in memory BEFORE saving; counts in each .meta.json. Dropped: AAPL 6,890 · MSFT 11,466 · KO 12,968 · PG 8,288 · XOM 6,901 · INTC 9,613 · T 12,465. Latest filed kept ≤ 2020-11-05 | data/raw/sec/*.meta.json |
| XOM entity | SEC's list today maps XOM to ExxonMobil Holdings Corp (CIK 2115436, 0 facts before 2021). 2010–2020 filer = EXXON MOBIL CORP (formerly EXXON CORP), **CIK 34088** (checked on SEC's submissions API) → explicit override in scripts/download_sec_companyfacts.py. Wrong-entity file set aside (data/raw/sec/set_aside_wrong_entity/), not deleted | SEC submissions API |
| SPY | a fund (SPDR S&P 500 ETF Trust, CIK 884394) — no company financials; excluded from 7.1, kept in 7.2 | — |
| Not available (D8) | FY2020 10-Ks filed in 2021 (KO, XOM, INTC, T) | — |
| Known gaps | T FY2016: no net income / EPS fact from the original 10-K (filed 2017-02-17) in companyfacts — only from 2018+ filings → MISSING. XOM FY2010 revenue first tagged in the 2012 10-K → MISSING. PG FY2014 and XOM FY2019: revenue tags disagree → CONFLICT (not picked). INTC never tags total liabilities or non-controlling interest → derived fallback (ASSUMPTION: no NCI) | reports/screening/indicators_2010-2020.md §4 |
| Spreads | NOT in free daily data (Tiingo or SEC) → only the ASSUMED spread levels are used | EXPERIMENT_PLAN |
