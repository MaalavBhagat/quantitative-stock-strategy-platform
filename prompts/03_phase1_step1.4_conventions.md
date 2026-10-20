You are working on the Quantitative Stock Strategy Research Platform.

Read first: CLAUDE.md, PROJECT_BRIEF.md, PROJECT_STATUS.md, research/EXPERIMENT_PLAN.md,
and Phase 1 Step 1.4 + Phase 3/4 in "Quantitative Stock Strategy Research Platform.txt".

TASK: Phase 1, Step 1.4 — Write PROJECT_GUIDE.md (development conventions). Then check Phase 1.

OBJECTIVE: One clear rulebook so every future coding session (human or AI) writes code the same,
safe way. Written in simple language — Goggy has no coding background. Keep it short: aim for
~150–250 lines, tables and bullets, no essays.

CONSTRAINTS:
- Documentation only. Do NOT create new Python modules or folders (no empty modules — roadmap rule).
- Do not repeat CLAUDE.md word-for-word; link to it.
- Anything that is a choice (not a fact) is marked DECISION and listed in section 9 for Goggy to approve.

PROJECT_GUIDE.md MUST COVER:
1. How to start a session (read order: CLAUDE.md → PROJECT_STATUS.md → task prompt) and how to end one
   (tests, ruff, update PROJECT_STATUS.md, commit).
2. Folder map: what lives where now, and the PLANNED modules from the roadmap
   (data, portfolio, execution, backtesting, strategies, metrics, reporting, dashboard, news)
   with ONE line each on its job and what it must NOT do (e.g. strategies never touch cash directly).
   Mark planned ones "not created yet".
3. Naming: files, functions, classes, tests, config files, branches, commit messages.
4. Units and conventions (critical for correctness):
   - Money currency always explicit (USD vs AUD) in variable names or types.
   - Percentages stored as decimals (0.02 = 2%).
   - Dates: trading dates as dates (no time-of-day) in US market calendar; never mix timezones.
   - Prices: raw vs adjusted always named explicitly (e.g. close_raw, close_adj). Trading uses raw only.
   - Number type for money: PROPOSE float vs Decimal with pros/cons, recommend one, mark DECISION.
   - Rounding rule for cash and shares (e.g. cents; fractional share precision), mark DECISION.
5. Testing rules: what needs tests (all accounting + execution logic always), hand-calculated
   examples for accounting, synthetic price series for backtests, test naming, how to run.
   No test may download live data (use small fixture files).
6. Error handling: fail loudly on bad data/config (no silent fixes), clear error messages,
   never swallow exceptions, logging instead of print in library code.
7. Config: experiment settings in YAML under config/ (when created), never hard-coded thresholds
   in strategy code; every run saves its config + data date + git commit (per EXPERIMENT_PLAN §8).
8. Git workflow: small commits; commit message style; when to use a branch; never commit data/ or .env;
   push after each completed task.
9. Open DECISIONS for Goggy (numbered list, each with your recommendation in 1 line).

THEN — PHASE 1 CHECK:
Go through the roadmap's Phase 1 completion criteria one by one and report met / not met with evidence:
- runs in a clean environment · dependencies documented · Git configured · tests can be executed ·
  project guide explains how to begin development.
Run `uv run pytest` and `uv run ruff check .` and show real output.
Do NOT mark Phase 1 Verified yourself — write "Phase 1: ready for verification" in PROJECT_STATUS.md;
Goggy + chat Claude will verify after the DECISIONS are answered.

FINISH:
- Update PROJECT_STATUS.md (Step 1.4 status, tests run + real results, open decisions, next action).
- Update CHANGELOG.md. Commit ("Phase 1: add PROJECT_GUIDE.md") and push.

COMPLETION REPORT: files changed · the DECISIONS list · Phase 1 criteria table · tests run + real results ·
known issues · recommended next task.
Do not claim anything is done unless the evidence supports it.
