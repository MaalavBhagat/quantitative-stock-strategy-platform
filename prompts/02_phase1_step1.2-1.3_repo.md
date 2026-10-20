You are working on the Quantitative Stock Strategy Research Platform.

Read first: CLAUDE.md, PROJECT_BRIEF.md, PROJECT_STATUS.md (incl. the Mac environment block from Step 1.1),
and Phase 1 Steps 1.2–1.4 in "Quantitative Stock Strategy Research Platform.txt".

TASK: Phase 1, Steps 1.2 + 1.3 — Turn THIS folder into a clean Python project + git repo.

OBJECTIVE: A minimal, working foundation: one command sets up the environment, one command runs tests.
Nothing more. No strategy or data code yet.

DECISIONS ALREADY MADE (from Step 1.1, 2026-10-20):
- Use uv. Goggy APPROVES: `brew install uv` and `brew install gh`. Nothing else system-wide without asking.
- Python for the project: 3.13, installed and pinned by uv (`uv python install 3.13`, `.python-version` = 3.13).
  Do NOT use Apple's /usr/bin/python3 (3.9). Do NOT change Homebrew's Python 3.14.
- Git identity: ask Goggy for the name + email to use, then set with `git config --global`.
  Suggest his GitHub "noreply" email (GitHub → Settings → Emails) so his real email isn't public.
- `gh auth login`: Goggy types the login himself in the browser flow. Never handle passwords or tokens.

CONSTRAINTS:
- Repo root = this folder. Keep all existing files where they are (research/, prompts/, *.md, the .txt roadmap).
- Smallest dependency set: dev = pytest, ruff. Runtime deps: none yet (pandas etc. come in Phase 2).
- Do NOT create empty modules just to make it look complete (roadmap rule).
- .gitignore MUST exclude: .env, data/, .venv/, __pycache__/, .DS_Store, *.pyc, .pytest_cache/, .ruff_cache/
- No real API keys anywhere.

IMPLEMENTATION:
1. Show me the plan (files you'll create) in simple words. Wait for my OK.
2. Create: pyproject.toml, .gitignore, .env.example (TIINGO_API_KEY=your_key_here),
   README.md (short: what the project is, how to set up, how to run tests),
   src/quant_research/__init__.py, tests/test_smoke.py (one test: package imports + a version string),
   data/.gitkeep is NOT needed (data/ is ignored entirely), CHANGELOG.md (start entry).
3. Set up the environment with uv (`uv sync`) and add dev deps (`uv add --dev pytest ruff`). Commit uv.lock.
4. Run: `uv run pytest`  and  `uv run ruff check .`  — show the REAL output.
5. git init (if not already), first commit: "Phase 1: project skeleton".
   Before committing, run `git status` and confirm no data/ or .env files are staged.
6. GitHub: after `gh auth login` (Goggy does the login), create a PRIVATE repo named
   quantitative-stock-strategy-platform and push. If not, give me step-by-step instructions instead.
7. Update PROJECT_STATUS.md: mark Steps 1.2 + 1.3 done (or what failed), tests run + real results,
   next action = Step 1.4 (development conventions doc).

ACCEPTANCE CRITERIA:
- `uv run pytest` passes (1 test) and `uv run ruff check .` shows no errors — real output shown.
- .python-version says 3.13 and uv.lock is committed.
- Repo exists on GitHub as PRIVATE and the push succeeded.
- `git status` clean after commit; .env and data/ not tracked.
- README setup steps work from a fresh terminal.

COMPLETION REPORT: files changed · what works · commands I should remember · tests run + real results ·
known issues · recommended next task.
Do not claim the task is complete unless the evidence supports it.
