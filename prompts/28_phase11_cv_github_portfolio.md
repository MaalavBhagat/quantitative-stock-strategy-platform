You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_STATUS.md, README.md, reports/RESULTS_SUMMARY.md, RESEARCH_METHODOLOGY.md, TESTING.md,
research/FAILED_EXPERIMENTS.md, and Phase 11 in the roadmap. Goggy = Maalav Bhagat, first-year Applied Finance +
Professional Accounting student at Macquarie University.

STEP 0 (docs → main): PROJECT_STATUS — mark Phase 10 VERIFIED (2026-10-30) with: "Verified by chat Claude: git history
(all branches/tags) has 0 files under data/, 0 .env, 0 .xls; Tiingo key in 0 commits; only fake test emails
(example.com/.invalid) besides the noreply address; RESEARCH_METHODOLOGY.md, TESTING.md, integration tests present.
Dashboard theme (f9ec41e) checked from screenshots: banner, REJECTED boxes and dashed S0 line all clear."
Also TIDY PROJECT_STATUS: move resolved/stale items out of "BLOCKED / OPEN QUESTIONS" into a short "Resolved" list; keep
only genuinely open items (Stake fractional precision, XOM 2014-07-28 diff, XOM pre-ex-date diffs, delisted price access).
CURRENT PHASE = Phase 11. Commit + push.

TASK: Phase 11 (Steps 11.1–11.5) — present the work professionally WITHOUT exaggerating. Branch `phase11-portfolio`.
Show a short plan and WAIT for OK. Nothing here may claim profitability; the headline result is a well-tested NO.

11.1 Final docs: README rewritten for a recruiter/interviewer who has 2 minutes:
  - 3-sentence summary: the question, the method (pre-registered, 3 periods, independent checks), the answer (rejected).
  - Headline verdict table (validation + final test) from RESULTS_SUMMARY, labelled SIMULATED, HISTORICAL.
  - "How it works" with an architecture diagram in Mermaid (data → validation → loader → engine (ledger, execution,
    strategies) → metrics → reports/dashboard; plus the pre-registration + lock flow).
  - What makes it trustworthy: no look-ahead rules, Decimal ledger, pre-registration tags, independent re-implementations,
    mutation checks, ~456 tests. Link the detailed docs. Licence section: code licence (propose MIT — ask Goggy), data NOT
    included (Tiingo internal-use, RBA non-commercial, SEC) and how to get your own key.
  - Keep PROJECT_GUIDE, RESEARCH_METHODOLOGY, DATA_SOURCES, TESTING, CHANGELOG consistent with it.

11.2 Reproducible demo anyone can run WITHOUT licensed data: `scripts/demo.py` + `uv run python scripts/demo.py` →
  generates a synthetic price series (fixed seed), runs S0 + S4-S2 + C1 through the real engine, prints a results table and
  saves charts to demo_output/ (git-ignored except a committed sample image). Test that it runs in a fresh clone in < 2 min.

11.3 Screenshots + diagrams for the README, ALL clearly labelled "Simulated":
  - Architecture diagram (Mermaid, in README).
  - Strategy comparison chart, equity curve, drawdown chart: made from the SYNTHETIC demo (safe to publish).
  - Dashboard screenshots: taken on the synthetic demo data if possible; if a screenshot shows real-data charts, keep it
    OUT of the repo (licence) and note in README "dashboard screenshots on real data available on request".
  - Example trade analysis (from the demo run's trade explorer).
  Small polish found in chat Claude's review: show years on chart date axes; don't truncate legend labels.

11.4 CV content → `docs/CV_AND_INTERVIEW.md` (commit it):
  - One-line project title + one-paragraph description.
  - 3–5 CV bullets, each with a REAL number from the reports (e.g. runs, tests, periods, strategies) and an honest result;
    no "profitable", no "beat the market". Draft 2 versions: finance-role focus and data/tech-role focus.
  - Technologies actually used (only what's in pyproject/uv.lock + tools used: Python 3.13, uv, pandas, httpx, Streamlit,
    pytest, ruff, git/GitHub, SEC EDGAR, Tiingo, RBA data, Claude Code).
  - GitHub repo description (≤ 350 chars) + 5–8 topics.
  - An honest line on how AI was used: Claude Code wrote code under Goggy's direction; chat Claude designed prompts and
    independently re-checked results; Goggy made every research decision (list the main ones with dates).
  - 2-minute interview demo outline (what to open, in what order).

11.5 Technical interview prep (same file): plain-English answers Goggy can say out loud, ≤ 120 words each, to:
  how the backtest engine works · how look-ahead bias is prevented (T close → T+1 open, history copy, availability rule for
  filings, spy checks) · how dividends are handled (ex-date, 15% withholding, reinvest ≥ US$100) · how trading costs are
  modelled (Stake/IBKR/CommSec, spread, FX) · how strategies were compared (R1–R6, twins, pre-registration) · what the
  results do and do NOT show (survivorship, 7–8 large US stocks, daily data, no tax) · "why did it fail?" · "what would you
  do next?" (from IDEAS_FOR_LATER, framed as hypotheses) · "what did you personally do vs the AI?".
  Also 5 likely tough questions with honest answers.

GitHub: set the repo description + topics via gh. Do NOT change visibility — ask Goggy at the end: "make it public now?"
(code + docs only; .gitignore already blocks data). If he says yes, first run scripts/scan_secrets.py once more and show
the output, then `gh repo edit --visibility public --accept-visibility-change-consequences`.

Cleanup after the last screenshot: delete .playwright-browsers/ (~573 MB, git-ignored) and remove the screenshots
dependency group only if no script still needs it — say what was freed.

PHASE 11 CHECK (report only): repository understandable · setup instructions work (fresh clone) · reproducible
demonstration exists · CV summary reflects actual accomplishments · no unsupported claims about profitability/reliability.

FINISH: pytest / ruff check / ruff format --check (real output) · safety scan · commit → merge → push → delete branch ·
PROJECT_STATUS (Phase 11 "ready for verification"; next = "chat Claude verifies Phase 11 → project complete") · CHANGELOG
(version 1.0.0 entry) · tag `v1.0.0` after merge.
COMPLETION REPORT: README preview (first 40 lines) · demo output · CV bullets (both versions) · interview answers file path ·
GitHub description/topics · visibility decision · space freed · Phase 11 criteria table · tests + output.
Do not claim anything is done unless the evidence supports it.
