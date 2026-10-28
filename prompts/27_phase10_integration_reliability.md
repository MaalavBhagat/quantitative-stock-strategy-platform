You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, README.md, DATA_SOURCES.md, CHANGELOG.md, and Phase 10 in the roadmap.

STEP 0 (docs → main): PROJECT_STATUS — add "FINAL TEST VERIFIED by chat Claude 2026-10-28: prereg-final tagged 17d62ed at
16:48:19 +1100, first 2021+ download 07:51:54Z (18:51:54 +1100); T not downloaded; 5,096 runs from clean b3287e4.
Independent re-implementation reproduced all 7 S0 finals (AAPL 16,485.23 · MSFT 17,613.26 · KO 11,559.85 · PG 8,798.98 ·
XOM 26,057.70 · INTC 6,305.17 · SPY 14,963.53) and all 23 C1 SPY trades (final 13,005.76) exactly. All 8 strategies
REJECTED in both validation and final test. The 3 'used' notes committed 23 s after the tag, before any download — accepted."
CURRENT PHASE = Phase 10. Commit + push.

TASK: Phase 10 (Steps 10.1–10.6) — make it stable, safe, reproducible, and documented. No new research, no new strategies,
no runs on 2021+ (that period is used). Branch: `phase10-reliability`. Show a short plan and WAIT for OK.

10.1 Integration tests (tests/integration/): one end-to-end test on small FIXTURE data only (no internet): mocked Tiingo
download → validation → loader → engine (S0 + one S4-S2 setting) → metrics → run record → report generator → dashboard
data functions. Assert exact final values computed by hand in comments. Plus one test that re-runs 20 random saved configs
(seeded) from /data/runs/{validation,phase9,final} and gets identical finals — skipped automatically if /data is absent
(e.g. on a fresh clone), with the reason printed.

10.2 Error handling — tests that each failure gives a CLEAR message and never a silent wrong result:
network timeout / connection error / HTTP 429 / 500 / 401 (bad key) for Tiingo and SEC (mocked); malformed or truncated
JSON/CSV; missing columns; wrong dtypes; missing .env key; invalid YAML configs (wrong types, unknown keys, reversed dates,
out-of-grid without override, 2021+ without unlock in a non-final config); RBA file with an unexpected layout. Fix any
place that currently fails with a confusing traceback. List every fix.

10.3 Security:
- Secrets scan of the WHOLE git history (all branches + tags), with a small script in scripts/ using patterns for the Tiingo
  key (read from .env without printing), generic API-key/token shapes, email addresses (allow only the GitHub noreply), and
  private keys. Report: 0 findings expected — show the real output.
- Licensed-data scan of history: no file under data/, no CSV with > 100 price-like rows, no .xls, ever committed.
- Dependency audit: run `pip-audit` through uv as a one-off tool (`uvx pip-audit` — ask Goggy first; it installs nothing
  into the project). Report findings; upgrade only if needed and tests still pass.
- Confirm the GitHub repo is still PRIVATE (gh repo view). Don't change visibility.

10.4 Reproducibility: `scripts/reproduce_reports.py` regenerates EVERY generated report from saved run records and diffs
against the committed versions — must be byte-identical (or explain each difference). Record Python + package versions in
reports/ENVIRONMENT.md. Fresh-clone check (temp folder): clone → `uv sync --all-groups` → `uv run pytest` (data-dependent
tests skip cleanly) — show real output.

10.5 Performance and usability: measure (don't optimise unless something is > 10× slower than needed): full test suite time,
one backtest, the 5,096-run batch time from records, dashboard page load. One small table in PROJECT_GUIDE. Usability: every
script has `--help` that explains what it does in one line.

10.6 Documentation audit — instructions must match the code:
- Create the two roadmap docs still missing: RESEARCH_METHODOLOGY.md (how the research was done: hypotheses, data, no
  look-ahead rules, pre-registration + tags, periods, verdict rules, independent checks by chat Claude — short, links to the
  detailed files) and TESTING.md (how to run tests, what each folder covers, mutation checks done, integration + error tests,
  what is NOT tested).
- Walk through README from a fresh clone; fix anything wrong. Check every command in README/PROJECT_GUIDE actually runs.
- PROJECT_GUIDE folder map matches the real tree.

PHASE 10 CHECK (report only; don't mark Verified): core workflows reproducible · integration tests pass · important failures
handled clearly · secrets/licensed data protected · known limitations documented.

FINISH: pytest / ruff check / ruff format --check (real output) · commit → merge → push → delete branch · PROJECT_STATUS
(Phase 10 "ready for verification"; next = "chat Claude verifies, then Phase 11") · CHANGELOG.
COMPLETION REPORT: tests added (counts) · error-handling fixes · security scan outputs · pip-audit result · report
reproduction result · fresh-clone output · performance table · docs created/fixed · Phase 10 criteria table.
Do not claim anything is done unless the evidence supports it.
