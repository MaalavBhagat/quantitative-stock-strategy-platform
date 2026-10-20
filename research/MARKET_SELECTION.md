# MARKET_SELECTION.md — Step 0.2
Status: Draft v1 (2026-10-17) — awaiting Goggy's review
Checked: 2026-10-17. Provider terms change — re-check in Phase 2 before building.
Labels: [SOURCED] = link given · [UNVERIFIED] = Claude's general knowledge, must check · [DECISION] = agreed with Goggy

---

## 1. Market comparison (US vs Australia vs India)
| Factor | US (NYSE/Nasdaq) | Australia (ASX) | India (NSE/BSE) |
|---|---|---|---|
| Free historical daily data | Best — several free APIs (section 2) | Some (Yahoo ".AX" tickers; EODHD paid) [UNVERIFIED depth/quality] | Some (Yahoo ".NS" tickers) [UNVERIFIED depth/quality] |
| Tiingo free API covers it? | Yes [SOURCED: portfoliooptimizer] | No — Tiingo is US-focused [SOURCED: portfoliooptimizer] | No [SOURCED: same] |
| Dividends + splits data | Good on Tiingo / Yahoo | Patchy on free sources [UNVERIFIED] | Patchy on free sources [UNVERIFIED] |
| Can Goggy trade it on Stake? | Yes (Stake Wall St) | Yes (Stake AUS) [UNVERIFIED — check fees] | No — Stake does not offer India [UNVERIFIED]; buying Indian shares from Australia is restricted/complex [UNVERIFIED] |
| Currency | USD → AUD/USD FX risk | AUD — no FX | INR → extra FX + access issues |
| Data volume for research | Huge, many liquid stocks | Smaller, fewer liquid stocks | Large, but access is the issue |
| Research suitability | High | Medium | Low (for now) |

**[DECISION] Start with the US market.** (Goggy agreed 2026-10-17.)
- Why: best free data, Stake supports it, deep and liquid market.
- Australia = good Phase-later extension (no FX, Stake supports it).
- India / Reliance = keep on the list but likely out of scope for real trading;
  could still be studied as research-only if data is good enough. Flag for Step 0.3.

Note from roadmap: "easiest data ≠ cheapest to trade". For Goggy on Stake, US trading
costs ~0.09% per round trip on AUD 10k (see BROKER_FEES.md), so US is both easy AND cheap.
The one-off AUD→USD FX (0.55% on deposit, 0.55% on withdrawal) is a real cost — it hits
buy-and-hold too, so it does not change the comparison, but it reduces total return.

---

## 2. Free / cheap US data providers
| Provider | Cost | Free limits | History | Dividends & splits | Raw + adjusted prices? | Licence | Source |
|---|---|---|---|---|---|---|---|
| **Tiingo** | Free tier | 500 unique symbols/month, 50 req/hour, 1,000 req/day | 30+ years | Yes (full dividend history in EOD endpoint) | Yes — raw and adjusted fields [UNVERIFIED field names until Phase 2] | Personal/internal use only | [QuantStart – Tiingo](https://www.quantstart.com/articles/evaluating-data-coverage-with-tiingo/), [PortfolioOptimizer (2022)](https://portfoliooptimizer.io/blog/selecting-a-stock-market-data-web-api-not-so-simple/) |
| **Yahoo Finance via yfinance** | Free | Unofficial; rate limits/blocks happen | Long | Yes | Yes (Close + Adj Close) | "Intended for personal use only" | [yfinance on PyPI](https://pypi.org/project/yfinance/0.2.39) |
| **Alpha Vantage** | Free tier | 25 requests/day, 5/min | Long | Daily *adjusted* endpoint was premium-only (2022) [check now] | Raw free; adjusted maybe paid | Check ToS | [Macroption – AV limits](https://www.macroption.com/alpha-vantage-api-limits/), [PortfolioOptimizer](https://portfoliooptimizer.io/blog/selecting-a-stock-market-data-web-api-not-so-simple/) |
| **EODHD** | Free / US$19.99 per month | Free: 20 calls/day, 1 year history | Paid: full | Yes on free & paid EOD plans | Yes | Check ToS | [EODHD pricing](https://eodhd.com/pricing) |
| **Stooq** | Free | Manual download (CAPTCHA), no API | 30+ yrs some stocks | Close appears already split-adjusted; dividends unclear | NO separate raw price | Check ToS | [QuantStart – Stooq](https://www.quantstart.com/articles/an-introduction-to-stooq-pricing-data) |

Quality notes:
- Tiingo's adjusted close matched a CRSP reference exactly in a 2022 test; EODHD failed
  the same test (rounding / a wrong close). [SOURCED: PortfolioOptimizer, 2022 — old, re-test]
- Stooq gives only adjusted close → breaks our rule "never trade at adjusted prices". Not usable as main source.

## 3. Recommendation
- **Primary source: Tiingo free tier.** Free, US-wide, long history, raw + adjusted + dividends,
  limits are plenty for a few stocks. Needs a free API key (stored in .env, never in Git).
- **Cross-check source: yfinance.** Compare a sample of prices/dividends against Tiingo
  to catch data errors (Phase 2 Step 2.3).
- **Paid fallback (only if needed): EODHD ~US$20/month** — also covers ASX later.
- Not used: Stooq (no raw prices), Alpha Vantage free (25/day too small; adjusted may be paid).

## 4. Licence warning (important for the GitHub plan)
Tiingo and Yahoo free data are for **personal use**. So:
- Do NOT commit downloaded price data to the public GitHub repo.
- The repo will contain CODE that downloads data with the user's own key.
- Charts/screenshots of results are normally fine; raw data files are not. [UNVERIFIED legal reading — not legal advice]

## 5. Limits of this choice
- Free data = today's listed companies mostly → survivorship bias stays a risk (Step 0.3 / Phase 7).
- Daily bars only → can't tell intraday order of high/low.
- No historical bid-ask spread in free data → spread must be an assumption.
- Free-tier terms can change without notice.

## 6. Open items
- Goggy: OK with US first + Tiingo primary + yfinance cross-check?
- Phase 2: verify Tiingo's current limits and field names on tiingo.com directly.
