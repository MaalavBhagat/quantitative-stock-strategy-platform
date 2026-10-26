You are working on the Quantitative Stock Strategy Research Platform.
Read first: CLAUDE.md, PROJECT_GUIDE.md, PROJECT_STATUS.md, research/PREREGISTRATION.md, src/quant_research/{backtesting,dashboard}/,
the dashboard app, and Phase 8 Steps 8.3, 8.6, 8.7 + completion criteria in the roadmap.

STEP 0 (docs → main): PROJECT_STATUS.md — add "Steps 8.1, 8.2, 8.4, 8.5 checked by chat Claude 2026-10-26 from the 4
screenshots: Overview final US$22,849.41, 10 round trips, fees 69.00 (23 × 3), CAGR 33.55% consistent with 217.34% over 4
years; Trade explorer 23 fills / 23 orders, trade #1 = Appendix B; banner, verdicts and assumptions visible on every page."
Commit + push.

TASK: Phase 8 Steps 8.3 (strategy lab), 8.6 (research reports), 8.7 (export) + polish + Phase 8 check.
Branch: `phase8-lab-export`. Show a short plan and WAIT for OK.

PART A — Polish from chat Claude's screenshot review (do first, separate commit):
1. Trade explorer: money columns (spread cost, P&L, fees) rounded to cents for DISPLAY (PROJECT_GUIDE §4 display rule);
   shares 6 dp; prices as stored.
2. Realised P&L on buys: show "—" (not applicable), not "not available" (which means missing data).
3. Performance "Costs and dividends" chart: add the cumulative net dividends line from the saved data, or rename the
   chart to "Costs" — whichever the saved files support without new maths.
4. Chart legends/axes: plain labels ("Cash", "Invested", "Fees (cumulative)", "Spread cost (cumulative)") — no code names.
5. Drawdown chart: same width as the other charts; title says which series (strategy) and add S0's drawdown as a second
   line for comparison.

PART B — Strategy lab (8.3)
- A page to pick: stock, strategy (S0–S4), settings, period (development or validation ONLY), cost variant
  (main / tight / wide / ibkr / commsec / whole / stress). It runs through the SAME `run.py` engine — no new logic in the app.
- Any X/Y/k/w may be entered (it's a lab), but every lab run is labelled EXPLORATORY — NOT PRE-REGISTERED, saved under
  /data/runs/lab/ (never mixed with /data/runs/validation/), and its page shows the matching S0 run for the same period +
  settings and the pre-registered verdict for that strategy next to it.
- D8: the period picker cannot offer 2021+; the engine's lock still applies (test it through the app function).
- Runs require a clean commit like every other run; if the tree is dirty, the lab says so and labels the run "dirty" (D6).
- Update PROJECT_GUIDE §2 dashboard row: "views saved results; may START runs only through run.py (lab runs labelled
  exploratory); holds no strategy or accounting logic."

PART C — Research reports (8.6): button → a Markdown report for the selected run (generated from the run record by a
function in src/quant_research/reporting/): settings, data provenance, results vs S0, costs, round trips, stranded,
the pre-registered verdict for that strategy, limitations (link DATA_SOURCES §8), "SIMULATED, HISTORICAL — not financial
advice". Saved to /data/exports/ (git-ignored).

PART D — Export (8.7): download buttons for trade log CSV, equity CSV, config YAML, the Markdown report, and a chart PNG.
All exports go to /data/exports/ (git-ignored) and each file starts with (or is accompanied by) a header: source data
licences (Tiingo internal use, RBA personal non-commercial with attribution) — "personal use; do not redistribute".
Reproducibility: an exported config YAML, fed back into run.py, gives the identical final value (test it).

TESTS: lab run function (uses run.py, labels exploratory, refuses 2021+, dirty flag), report generator (contains the
required sections + banner), export round-trip (config → identical rerun), display formatting (cents, "—").
Smoke check headless + retake the 4 screenshots + 2 new ones (lab, report) into /data/screenshots/.

PART E — PHASE 8 CHECK (report only; don't mark Verified): dashboard uses the validated engine · results consistent with
independent calculations (cite the Appendix B consistency test + chat Claude's checks) · important assumptions visible ·
failed experiments not hidden · results exportable and reproducible.

FINISH: pytest / ruff check / ruff format --check (real output) · safety checks · commit → merge → push → delete branch ·
README (lab + export, licence note) · PROJECT_STATUS (Phase 8 "ready for verification"; next = "chat Claude verifies
Phase 8, then Phase 9 plan") · CHANGELOG.

COMPLETION REPORT: polish done · lab behaviour · report sample (first 30 lines) · export round-trip result · Phase 8
criteria table · tests + output · screenshots saved.
Do not claim anything is done unless the evidence supports it.
