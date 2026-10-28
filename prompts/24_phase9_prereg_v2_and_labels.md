You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, research/PREREGISTRATION.md, research/EXPERIMENT_PLAN.md (§2, §6),
research/RESEARCH_QUESTIONS.md (H7), reports/phase9/context_and_events_2010-2020.md, src/quant_research/{news,strategies}/,
the dashboard, and Phase 9 Steps 9.5–9.6 in the roadmap.

STEP 0 (docs → main): PROJECT_STATUS.md — add:
"Steps 9.1–9.4 checked by chat Claude 2026-10-28: UTC evidence accepted (Apple 16:30 NY release = 20:30Z in Oct 2019,
21:30Z in Jan 2020). Rulings: (1) AT&T 8-K 2012-01-13 (accession 0000732717-12-000006) is tagged item 1.03 but its own
heading reads 'Item 1.03 Entry into a Material Definitive Agreement' and it concerns reducing a US$5bn credit facility to
US$3bn — a filer coding error; reclassify THIS filing only to 'deal signed (1.01-type), reclassified' via a logged
override list with the SEC URL https://www.sec.gov/Archives/edgar/data/732717/000073271712000006/creditfacility_8k.htm.
(2) XOM's higher 2.02 count is real: ~7 per year to 2016 (quarterly results + extra annual/reserves updates, filed as
2.02 + 7.01) — keep as filed; note it." Commit + push.

PART 0 — Plain-English strategy names (Goggy's request 2026-10-28). DISPLAY ONLY — the IDs (S0…S4-S2) stay unchanged in
code, configs, run records and the pre-registration. Add one shared mapping in src/quant_research/strategies/labels.py and
use it in the dashboard (all pages, dropdowns, tables, charts), generated reports and exports:
| ID | Display name | One-line explanation |
| S0 | Buy-and-hold | Buy on day 1 and keep it; dividends reinvested once cash reaches US$100. |
| S1 | Profit target | Sell after the price rises X% above the buy price; buy back after it falls Y% below the sell price. |
| S2 | Pullback from peak | Sell after an X% rise; buy back after a Y% fall from the highest price since selling. |
| S3 | Mean reversion | Sell when the price is k standard deviations above its w-day average; buy back when it's k below. |
| S4-S1 | Trend filter + profit target | S1, but never sell while the stock is in a strong uptrend (above a rising 200-day average). |
| S4-S2 | Trend filter + pullback | S2, but never sell in a strong uptrend. |
| C1, C2, E1 | (names below) | (explanations below) |
Show as "Buy-and-hold (S0)" etc., with the one-liner as a caption/tooltip wherever a strategy is chosen or titled.
Test: every strategy ID in the registry has a label; no page shows a bare ID without its name. Separate commit.

PART A — PRE-REGISTRATION v2 → `research/PREREGISTRATION_V2.md` (proposed by chat Claude 2026-10-28; Goggy approves
by running this prompt). Commit, then tag `prereg-v2`, BEFORE any Phase 9 strategy touches real data.
Hypothesis H7: adding market context or 8-K events improves results vs the SAME strategy without that information
(its "twin"), after costs, out of sample.
Three information strategies — few on purpose (fewer tries = fewer flukes):
- C1 "Market-trend gate" (twin: S0): hold the stock only while SPY is above its 200-day average AND that average is higher
  than 20 days ago (same split-adjusted-as-of-T method); otherwise sell all and hold cash; rebuy when the condition
  returns. Signals at close, fills next open, MAIN rules (reinvest ≥ US$100 while holding). No parameters.
- C2 "Market-gated pullback" (twin: S4-S2, same 16 X/Y settings): S4-S2, but NO rebuy while SPY is below its 200-day
  average.
- E1 "Earnings cool-off" (twin: S4-S2, same 16 X/Y settings): S4-S2, but after an earnings event (item 2.02) becomes
  usable (Phase 9 availability rule), ignore all buy/sell signals for the next 2 trading days; signals resume on day 3.
- Not tested, declared now: event-risk exits on 4.02 / 2.06 / 1.03 / 3.01 — too few events in 2010–2020 (report §counts),
  so any result would be noise.
Periods: development 2010–2016 = build + sanity only (allowed to look). Judged period = validation 2017–2020 — with an
honest note that the price data there was already seen for the twins, so the clean test is the final 2021+ run.
Judgement per information strategy, MAIN settings, using R1–R6 exactly as in PREREGISTRATION §9 but with the TWIN as the
benchmark (R1: median excess vs twin > 0 on ≥ 6/8 stocks; R2: ≥ 60% of settings — C1 has one setting, so R2 = "its one
setting has mean excess vs twin > 0"; R3–R6 as written, R6 counted on the information strategy's own round trips).
H7 SUPPORTED for a strategy only if SUPPORTED vs its twin; also report every result vs S0 (descriptive). Any bug during
runs → fix, log, re-run ALL. AI labelling of 8-K text: exploratory only, never part of a verdict.

PART B — implement C1, C2, E1 (src/quant_research/strategies/), registry + labels, config support. Tests ONLY on synthetic
data: hand-worked cycles for each; C1 switches exactly when the SPY condition flips; C2 blocks rebuys only under the SPY
condition; E1 ignores signals for exactly 2 trading days after an event's usable close (weekend/holiday case); all pass the
price spy check AND the events spy check. Mutation checks: E1 using the filing date instead of the availability rule →
a test fails; C1 using today's SPY close for a fill → spy check fails. NO real-data runs in this prompt.

FINISH: pytest / ruff check / ruff format --check (real output) · safety · commit → tag prereg-v2 (push tag) → merge → push →
delete branch · PROJECT_STATUS (prereg-v2 tagged; next = "prompt 25: Phase 9 runs + comparisons") · CHANGELOG.
COMPLETION REPORT: labels table as shown in the app + 1 screenshot of the Overview dropdown (data/screenshots/) ·
prereg-v2 summary + tag commit/time · strategy rules in plain words · tests + output · mutation checks.
Do not claim anything is done unless the evidence supports it.
