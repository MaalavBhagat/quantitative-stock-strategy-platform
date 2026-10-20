# PROJECT_STATUS.md
Last updated: 2026-10-20

CURRENT PHASE: Phase 1 — Development Environment and Repository (In progress)
CURRENT TASK: Step 1.4 — development conventions doc (prompt not written yet)

PHASE STATES (Not started / In progress / Blocked / Verified):
- Phase 0  Feasibility & research design ........ VERIFIED (2026-10-18)
- Phase 1  Dev environment & repository ......... In progress
- Phase 2  Historical market data ............... Not started
- Phase 3  Portfolio accounting engine .......... Not started
- Phase 4  Backtesting engine ................... Not started
- Phase 5  Strategy laboratory .................. Not started
- Phase 6  Research validation .................. Not started
- Phase 7  Company research & screening ......... Not started
- Phase 8  Interactive dashboard ................ Not started
- Phase 9  Market context & AI news ............. Not started
- Phase 10 Integration, security, reliability ... Not started
- Phase 11 CV & GitHub portfolio ................ Not started

COMPLETED:
- Master roadmap written (Quantitative Stock Strategy Research Platform.txt)
- Roadmap reviewed by Claude; PROJECT_BRIEF.md + this file created
- Open questions Q1–Q6 answered (2026-10-17)
- Step 0.1 research/RESEARCH_QUESTIONS.md v3 — DONE, approved by Goggy 2026-10-17
- Step 0.2 research/MARKET_SELECTION.md v1 — DONE, approved by Goggy 2026-10-17
- Step 0.3 research/INITIAL_UNIVERSE.md v2 — DONE: 8 tickers (AAPL MSFT KO PG XOM INTC T SPY); start with AAPL + XOM
- Step 0.4 research/SMALL_ACCOUNT_FEASIBILITY.md v1 + calc_feasibility.py — DONE, approved by Goggy 2026-10-17
  Result: Stake round trip ≈0.19%; CommSec ≈1.44%. Feasible to test on Stake/IBKR costs.
- Step 0.5 research/EXPERIMENT_PLAN.md v1 — DONE, approved 2026-10-18
- PHASE 0 CHECK (2026-10-18): hypothesis defined ✓ · market selected with reasons ✓ ·
  data providers evaluated ✓ · experiment plan ✓ · limitations documented (EXPERIMENT_PLAN §9) ✓ ·
  no profitability claim ✓  → Phase 0 VERIFIED
- CLAUDE.md created (auto-read rules for Claude Code)
- Step 1.1 Mac inspection — DONE 2026-10-20 (report reviewed by Claude in chat; results under SETUP FACTS)
- Steps 1.2 + 1.3 repo + Python + tests — DONE 2026-10-20 (prompt 02):
  pyproject.toml, .python-version (3.13), uv.lock, .gitignore, .env.example, README.md, CHANGELOG.md,
  src/quant_research/__init__.py (version 0.1.0), tests/test_smoke.py. Dev deps: pytest 9.1.1, ruff 0.17.1.
  Git repo initialised (branch main); pushed to PRIVATE GitHub repo
  https://github.com/MaalavBhagat/quantitative-stock-strategy-platform
  Fresh clone + `uv sync` + `uv run pytest` + `uv run ruff check .` all worked (README steps verified).
  Style-only fix to research/calc_feasibility.py (ruff PLC0206), output diffed identical — approved by Goggy.

IN PROGRESS:
- Phase 1: Step 1.4 remaining

BLOCKED / OPEN QUESTIONS:
- Stake withdrawal FX not confirmed (check AU_Pricing.pdf in Phase 2)

SETUP FACTS (stated by Goggy, 2026-10-17):
- Computer: Mac. Coding tool: Claude Code in the Claude desktop app (2026-10-20).
- Connectors added 2026-10-20: GitHub, Alpha Vantage, Financial Datasets, alphaXiv, StockPortfolio.pro.
- Broker: Stake = MAIN cost case (Goggy knows it). Also model IBKR (LOW) + CommSec (HIGH).
- Market: start with US (others later).
- Data budget: free preferred; small monthly cost OK.
- Capital: AUD 10,000 (changed from AUD 1,000 on 2026-10-17; overrides master roadmap Step 0.4).
- Rise/dip starting range: 2–5% each.
- Time: 1–2 hours daily, no deadline.
- GitHub: has account; repo can be public later.

Mac environment (checked 2026-10-20 by Claude Code, read-only commands):
- macOS 26.6.2 (build 25G83), MacBook Air, Apple Silicon M2 (arm64).
- Python: main = Homebrew Python 3.14.6 (/opt/homebrew/bin/python3). Also Apple's built-in 3.9.6 (/usr/bin/python3) — don't use.
  No pyenv, no conda.
- Xcode Command Line Tools: installed.
- uv: NOT installed. pip: pip3 26.1.2 (Homebrew). pipx: NOT installed.
- Homebrew: 6.0.17 (/opt/homebrew).
- Git: 2.55.0 (Homebrew). user.name / user.email: NOT set.
- GitHub CLI (gh): NOT installed.
- VS Code: NOT installed (no `code` command, no app in /Applications).
- Free disk: 23 GiB of 228 GiB (data volume 89% used).
- This folder is NOT a git repo yet.
  UPDATE after Step 1.2–1.3 (2026-10-20): installed uv 0.13.2 + gh 2.102.0 (Homebrew; brew auto-cleanup ran);
  uv-managed Python 3.13.16; git user.name = MaalavBhagat, user.email = GitHub noreply address;
  gh logged in as MaalavBhagat (keyring, https). Folder is now a git repo.

KNOWN BUGS:
- None known

IMPORTANT DECISIONS:
- 2026-10-17: Work in small, single tasks. Every task ends by updating this file.
- 2026-10-17: Facts (fees, data prices, provider limits) must have a source link
  or be labelled "UNVERIFIED / ASSUMPTION".
- 2026-10-17: Starting capital AUD 10,000 (was 1,000).
- 2026-10-17: Model 3 cost levels — LOW (IBKR-like), MID (Stake-like), HIGH (CommSec standard).
- 2026-10-17: Stake is the MAIN cost case.
- 2026-10-17: US market first (agreed). Data: Tiingo primary, yfinance cross-check (agreed).
- 2026-10-18: Repo root = this folder (Desktop/Share research). GitHub repo name: quantitative-stock-strategy-platform.
- 2026-10-20: Git identity = MaalavBhagat + GitHub noreply email. GitHub repo created PRIVATE.
- 2026-10-20: Tooling = uv; project Python pinned to 3.13 via uv (Homebrew 3.14 left alone); gh CLI for GitHub. Goggy approved brew install uv + gh.
- 2026-10-18: Q4.11 added — which market/company types suit the strategy (answer after Phase 6/7).
- 2026-10-17: Starting pair AAPL (with momentum) + XOM (without steady momentum) — Goggy's choice. Downloaded data never goes into the public repo (licence).
- 2026-10-17: H1 v2 + H2–H7 approved. H1 v2 is the main hypothesis. H2–H6 tested only after H1 baseline; H7 exploratory.

NEXT ACTION:
- Step 1.4 — development conventions doc (naming, module responsibilities, testing, error handling,
  coding-agent rules, documentation). Needs a prompt (03) written first.

TESTS RUN (2026-10-20):
- uv run pytest  (in project folder AND in a fresh clone)
- uv run ruff check .  (in project folder AND in a fresh clone)

TEST RESULTS (real output):
- pytest: "1 passed in 0.04s" (fresh clone: "1 passed in 0.03s") — tests/test_smoke.py
- ruff: first run "Found 1 error." (PLC0206 in research/calc_feasibility.py) → fixed → "All checks passed!"
- calc_feasibility.py output before vs after fix: identical (diff)
