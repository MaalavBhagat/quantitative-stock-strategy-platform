You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_STATUS.md, PROJECT_GUIDE.md.

TASK: Apply Goggy's answers to PROJECT_GUIDE.md §9 (D1–D9), apply ruff format, close Step 1.4.
Only run this prompt if Goggy has said he agrees with the decisions below.

GOGGY'S DECISIONS (approved in chat with Claude, 2026-10-20):
- D1 APPROVED: hybrid — Decimal in portfolio/ + execution/ (cash, fees, shares); float for prices, signals, metrics; one tested conversion point at the fill.
- D2 APPROVED: round cash to cents at each ledger entry, against us (pay → up, receive → down).
- D3 APPROVED: fractional shares 6 dp, shares bought round down [ASSUMPTION — check Stake's real precision in Phase 3].
- D4 APPROVED: NYSE calendar library added in Phase 2; date mismatches fail loudly.
- D5 APPROVED: docs straight to main; each code task on a phase<N>-<task> branch, merged when tests pass. Claude Code handles the branch commands and explains them.
- D6 APPROVED: dirty runs allowed in development, labelled "dirty"; validation + final-test runs must be clean.
- D7 APPROVED: adopt ruff format.
- D8 APPROVED WITH CHANGE: the lock sits in the BACKTEST / EXPERIMENT RUNNER, not in data loading.
  Data download and data-quality checks may cover all years (incl. 2021+), because checking for missing
  dates or bad prices is not strategy testing. But no strategy, backtest or metric may run on dates
  ≥ 2021-01-01 unless the setting `final_test_unlocked: true` is set — and only Goggy sets it.
  Also: no charts or summary stats of 2021+ prices are produced before unlock.
- D9 APPROVED: type hints required on every function in src/; no type-checker yet.

STEPS:
1. Edit PROJECT_GUIDE.md: remove the word DECISION from approved items, record each as "Approved 2026-10-20",
   rewrite D8 to the changed version above (in §4/§7/§9 wherever it appears). Keep the file under ~250 lines.
2. Add the D1–D9 summary to PROJECT_STATUS.md "IMPORTANT DECISIONS".
3. Run `uv run ruff format .` — show which files changed. Then show `git diff --stat`.
   Re-run `uv run python research/calc_feasibility.py` before/after and confirm output identical.
   Commit separately: "Phase 1: apply ruff format (no logic change)".
4. Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` — real output.
5. PROJECT_STATUS.md: Step 1.4 DONE; Phase 1 "ready for verification — all criteria met, decisions applied";
   NEXT ACTION = "Chat Claude verifies Phase 1, then Phase 2 Step 2.1 (DATA_SOURCES.md)".
6. CHANGELOG.md entry. Commit "Phase 1: record approved conventions D1–D9" and push.

COMPLETION REPORT: files changed · commits · tests + real output · anything you could not do.
