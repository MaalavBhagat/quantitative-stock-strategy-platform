You are working on the Quantitative Stock Strategy Research Platform.

Read these files first: CLAUDE.md, PROJECT_BRIEF.md, PROJECT_STATUS.md,
and Phase 1 in "Quantitative Stock Strategy Research Platform.txt".

TASK: Phase 1, Step 1.1 — Inspect my development environment. REPORT ONLY.

OBJECTIVE: Find out what is already installed on my Mac so the next step uses my real setup,
not assumptions. I have no coding background, so explain results in simple words.

CONSTRAINTS:
- FIRST run `uname -a` and `sw_vers`. If this is NOT macOS (e.g. a Linux cloud container), STOP and tell me:
  "I'm not running on your Mac — start a local session on the Share research folder."
- Do NOT install, update, or change anything. Read-only commands only.
- Do NOT create or edit any files except PROJECT_STATUS.md at the very end.
- If a command fails, report the failure — don't work around it.

CHECK AND REPORT:
1. macOS version and chip (Apple Silicon or Intel).
2. Python: which python3, python3 --version. Any other Pythons (Homebrew, pyenv, conda)?
3. Package tools: is `uv` installed? `pip`? `pipx`?
4. Homebrew: installed? version?
5. Git: git --version, and is user.name / user.email configured? (show if set; don't change)
6. GitHub CLI: is `gh` installed? Am I logged in? (gh auth status)
7. Editor: is VS Code installed (`code` command)?
8. Free disk space on the main drive.
9. Is this folder already a git repo? (git status)

COMPLETION REPORT (simple language, as a table):
- Each item: found / not found / version.
- What is MISSING for Phase 1, and the safest way to install each (don't install yet).
- Your recommendation: uv or python venv for this project, and why (1–2 lines).
- Then add to PROJECT_STATUS.md under "SETUP FACTS": a short "Mac environment (checked <date>)" block
  with the real results. Change nothing else.

Do not claim anything you didn't actually check with a command.
