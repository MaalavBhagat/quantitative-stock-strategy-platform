# CV and interview notes — Quantitative Stock Strategy Research Platform

Maalav Bhagat (Goggy) · Applied Finance + Professional Accounting, Macquarie University · project 2026-10-17 → 2026-10-30.
Every number below comes from the generated reports (sources in brackets). All results are **simulated, historical**.

## Title and description
**Title:** Pre-registered backtest of "sell after a small rise, buy back after a dip" vs buy-and-hold (Python).

**Description:** A research platform that tests whether a popular retail trading rule beats simply holding a stock
after real Australian-investor costs (AUD 10,000, Stake brokerage, FX, spread, US dividend withholding). It simulates
trading day by day without look-ahead, fixes its test rules in advance (three git-tagged pre-registrations), and judges
8 strategies on up to 8 large US stocks across a development, a validation and a one-time final test period. Every
strategy was rejected in both judged periods — the rule does not survive costs and strong rising markets.

## CV bullets — finance-role version
- Designed and ran a pre-registered study of 8 rule-based trading strategies against buy-and-hold on up to 8 US
  large caps (2010–2025); all 8 rejected in both the 2017–2020 validation and the one-time 2021–2025 final test
  [reports/RESULTS_SUMMARY.md].
- Modelled real retail costs for an AUD 10,000 account — Stake, IBKR and CommSec brokerage, 0.55% FX, bid-ask spread,
  15% US dividend withholding — and showed the main "profit target" rule finished a median 68.7 percentage points
  behind buy-and-hold in the final test [reports/experiments/FINAL_TEST_2021-2025.md].
- Fixed the pass/fail rules (6 tests incl. cost stress and "remove the best 3 trades") before seeing results, across
  12,272 simulated runs, and reported the negative result honestly [research/PREREGISTRATION.md].
- Read SEC EDGAR filings point-in-time (company facts and 1,359 Form 8-K events) to test whether earnings and market
  information improved timing; it did not [reports/experiments/phase9_information_2017-2020.md].

## CV bullets — data / tech-role version
- Built a Python 3.13 backtesting platform (exact Decimal ledger, next-open execution, cost models, run records) with
  460 automated tests, incl. end-to-end, error-handling and look-ahead "spy" tests [TESTING.md].
- Ran 12,272 reproducible simulations from clean git commits; 20 randomly sampled saved runs replay to identical
  results, and 11 of 12 generated reports rebuild byte-identical (the 12th differs only in its date stamp)
  [tests/integration/, scripts/reproduce_reports.py].
- Engineered data pipelines for Tiingo prices, RBA exchange rates and SEC EDGAR APIs with validation (9 checks, Yahoo
  cross-check), rate limiting and clear failure messages; licensed data never committed (history scan: 0 findings).
- Built a local Streamlit dashboard and a no-data demo (synthetic prices, fixed seed, < 3 s) so anyone can run the real
  engine in two minutes [scripts/demo.py].

## Technologies actually used
Python 3.13 · uv · pandas · NumPy · httpx · exchange-calendars · PyYAML · python-dotenv · xlrd · Altair + vl-convert ·
Streamlit · pytest · ruff · Playwright (screenshots) · yfinance (cross-check only) · git, GitHub, gh CLI · SEC EDGAR
APIs · Tiingo API · RBA historical exchange-rate files · Claude Code.

## GitHub
- **Description (≤ 350 chars):** Pre-registered Python backtest: does "sell after a small rise, buy back after a dip"
  beat buy-and-hold after real costs for an AUD 10,000 investor? 8 strategies, up to 8 US stocks, 3 periods, 12,272
  simulated runs, 460 tests. Answer: no — every strategy rejected. Simulated, historical; not financial advice.
- **Topics:** backtesting · quantitative-finance · python · pre-registration · reproducible-research · streamlit ·
  stock-market · trading-strategies

## How AI was used (honest)
Claude Code (an AI coding tool) wrote the code and reports under my direction, one numbered task at a time, and had to
show real test output for every step. A separate chat with Claude designed those task prompts and independently
re-checked key results with its own code (e.g. it reproduced all buy-and-hold final values and full trade lists to the
cent). **I made every research decision**, including:
- 2026-10-17 — the question (H1 v2), AUD 10,000 capital, US stocks, Stake as the main broker, three cost levels, the
  first two stocks (AAPL + XOM).
- 2026-10-20 / 21 — coding conventions (Decimal money, rounding against the investor), 15% withholding rounding,
  reinvest dividends only once cash ≥ US$100.
- 2026-10-25 — froze pre-registration v1; no extra "hybrid" strategy; tightened the sanity rule.
- 2026-10-26 — keep the 2021+ final test locked until after the information-strategy phase.
- 2026-10-27 — free data sources only for news (SEC 8-K item codes); AI labelling only as an exploratory side test.
- 2026-10-28 — approved pre-registration v2 (5 rule decisions), then unlocked the one-time final test, excluding AT&T
  because its 2022 spin-off can't be modelled.
- 2026-10-30 — MIT licence for the code; dashboard theme.

## 2-minute interview demo
1. **README (20 s):** the question, the headline table — every strategy REJECTED in two periods.
2. **`uv run python scripts/demo.py` (30 s):** real engine on made-up prices; point at buy-and-hold vs the rules.
3. **Dashboard, demo period (30 s):** Performance (burgundy strategy vs dashed buy-and-hold), Trade explorer (order at
   one close, filled at the next open).
4. **`research/FINAL_TEST_PREREG.md` + `git tag` (20 s):** rules written and tagged before the 2021+ data existed.
5. **`TESTING.md` (20 s):** 460 tests, mutation checks, what is NOT tested.

## Interview answers (say out loud, ≤ 120 words each)

**How does the backtest engine work?**
It walks through trading days one at a time. Each morning it applies splits and dividends, then fills yesterday's
orders at today's opening price plus spread and fees. At the close it values the portfolio, then shows the strategy
only the data up to that close and collects its new orders for tomorrow. All cash and share amounts go through one
ledger that uses exact decimals and rounds to cents against the investor. Every run saves its settings, the data
files used, the git commit and every order and fill, so any result can be traced and re-run.

**How is look-ahead bias prevented?**
Four ways. First, timing: a decision at day T's close can only trade at day T+1's open. Second, the strategy gets a
copy of the price table that physically ends at day T, and indicators use prices adjusted only for splits already
known at T. Third, company filings count only from the first market close after the SEC accepted them, using New
York time and the real exchange calendar. Fourth, "spy" tests: change all data after day T and check that no decision
up to T changes. We also broke the rules on purpose to prove those tests fail.

**How are dividends handled?**
Cash arrives on the ex-dividend date, because the free data has no pay date; that's a stated assumption, applied
equally to every strategy. As an Australian holder with a W-8BEN, 15% US withholding is taken off. To stop a US$3 fee
eating a tiny dividend, it's reinvested only once cash reaches US$100. Strategies that are out of the market simply
keep the cash.

**How are trading costs modelled?**
Three brokers: Stake (the main case), IBKR (low cost) and CommSec (high cost), each with its own brokerage and
currency-conversion fees; Stake charges 0.55% to convert AUD to USD and back. On top of that, every fill pays a
bid-ask spread: 0.05% per side normally, tested at 0.02% and 0.10% too. Fills happen at the next open, so overnight
gaps are real. Results are reported for seven cost variants, and a rule only passes if it survives the worst
combination, a wide spread plus CommSec.

**How were the strategies compared?**
Against buy-and-hold on the same stock, period and costs, or against their "twin" (the same strategy without the
extra information). Six pass/fail rules were fixed before the runs: beat the benchmark on most stocks; most settings
win on average; drawdown no more than 5 points worse; still wins with high costs; still wins without its best three
trades; enough trades to judge. All six must pass for "supported"; losing on five or more stocks means "rejected".
The rules were git-tagged before each test, so I couldn't move the goalposts.

**What do the results show, and not show?**
They show that, for these large US stocks from 2017 to 2025, these simple rules ended with less money than holding,
after realistic costs. They don't prove the idea can never work: the stocks were chosen with hindsight and are all
survivors, there are only seven or eight of them, I used daily prices (not intraday), assumed spreads rather than
measured ones, and ignored tax. A different market, different stocks or real intraday data could behave differently,
and that would need its own pre-registered test.

**Why did it fail?**
Mainly because good stocks go up more often than they dip enough. Selling after a small rise and waiting for a dip
often left the money in cash while prices kept climbing; in the 2017–2020 test, three quarters of the basic profit-target
runs ended stranded in cash. Each round trip also costs fees and spread. The rules did help on falling or flat stocks
and in down years, but those gains were smaller than what they missed in rising years, and earlier winners didn't
repeat.

**What would you do next?**
Test the three ideas I logged as hypotheses, each with a new pre-registration, because my 2021–2025 data is now used.
One: dip-buying rules lose less than holding on stocks in a long decline — but "in decline" must be a rule known in
advance. Two: a higher dividend yield at the start goes with less-bad results. Three: a lower quality score does too.
Both correlations came from only 7–8 stocks and may just mean "the stock fell". A fair test needs many more stocks,
including delisted ones, a new period, and significance levels stated before looking.

**What did you do, and what did the AI do?**
I set the question, the budget, the broker and every research rule: what counts as a pass, which stocks, which
periods, when to unlock the final test, and how to handle problems like AT&T's spin-off. Claude Code wrote the code
under my direction, one task at a time, and had to show real test output. A separate Claude chat helped design the
tasks and re-checked key numbers with independent code. I reviewed every result and decision before moving on, and
the decision log shows the dates.

## Five tough questions — honest answers

**"So you built something that doesn't work?"**
I built something that answers a question reliably. The strategy doesn't beat holding; the platform shows that with
evidence that would also have caught a "yes". A careful "no" saves real money for anyone tempted by the rule.

**"Isn't 7–8 stocks far too few?"**
For a general claim, yes, and I say so. The question was about a small investor's single-stock approach, and the rules
required a win on most stocks. Wider coverage, including delisted stocks, is the obvious next step.

**"You used AI — how do I know you understand it?"**
Ask me to walk through any part: the T close → T+1 open timing, the withholding maths, the R1–R6 rules. I made the
decisions, and the results were re-checked independently, not just trusted.

**"Couldn't you have tuned it until it worked?"**
That's exactly what the pre-registration prevents. The rules and settings were git-tagged before each test, all
12,272 runs were reported, and lab experiments are labelled exploratory and never count.

**"Would this work with lower costs?"**
Not on this evidence. In the final test the medians of all five basic rules (S1–S4) stayed negative even with tight
spreads or IBKR's low fees (e.g. profit target −67.2 and −68.4 points vs −68.7 at Stake); costs made it worse, but the
main loss came from missing rises, not from fees.
