# Changelog

## 0.1.0 — 2026-10-20
- Phase 1 (Steps 1.2 + 1.3): project skeleton.
  - uv-managed environment, Python pinned to 3.13 (`.python-version`), `uv.lock` committed.
  - Dev tools: pytest, ruff. No runtime dependencies yet.
  - `src/quant_research` package with version string; one smoke test.
  - `.gitignore` excludes `.env`, `data/`, `.venv/` and caches. `.env.example` template added.
- Style-only fix in `research/calc_feasibility.py` (ruff PLC0206: loop now uses `.items()`).
  Printed output verified identical before/after (diff, 2026-10-20). Approved by Goggy.

## 2026-10-20 — Step 1.4 (docs only, version stays 0.1.0)
- Phase 1 (Step 1.4): added `PROJECT_GUIDE.md` v1 — session start/end, folder map with planned
  modules, naming, units & conventions, testing, error handling, config, Git workflow,
  and open DECISIONS D1–D9 for Goggy. Documentation only; no code changed.
- PROJECT_STATUS.md: Phase 1 check done → "Phase 1: ready for verification".
