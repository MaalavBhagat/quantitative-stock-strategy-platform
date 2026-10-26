# Quantitative Stock Strategy Research Platform

A research tool that tests one question honestly: does "sell after a small rise, buy back
after a dip" beat simply buying and holding, after real costs, on an AUD 10,000 account
(US stocks, Stake as the main broker)? A "no" answer is a valid result.
All results are **simulated, historical** — nothing here is a claim of profitability or
investment advice.

See `PROJECT_BRIEF.md` (summary), `PROJECT_STATUS.md` (progress) and `research/` (design).

## Findings so far

- On the 2017–2020 validation period, all five "sell after a rise, rebuy after a dip" strategies were **REJECTED** against buy-and-hold under rules fixed in advance (simulated, historical; not financial advice).
- Main reasons: selling early left the strategies stranded in cash while prices kept rising, and earlier "winners" did not persist.
- Plain-English summary with sources: [`reports/RESULTS_SUMMARY.md`](reports/RESULTS_SUMMARY.md). The 2021+ final test has not been run.

## Setup (macOS)

1. Install [uv](https://docs.astral.sh/uv/) once: `brew install uv`
2. In this folder, create the environment (installs Python 3.13 if needed, plus dev tools):

   ```bash
   uv sync
   ```

3. Optional, for later phases: copy `.env.example` to `.env` and add your own API key.
   `.env` is git-ignored — never commit keys.

## Run the tests and the code checker

```bash
uv run pytest
uv run ruff check .
```

## Data

Downloaded market data goes in `data/`, which is git-ignored (personal-use licence).
Rules for using it: `DATA_SOURCES.md` §7 (conventions) and §8 (limitations).

- Download the initial dataset (2 Tiingo calls, needs `.env`): `uv run python scripts/download_initial_dataset.py`
- Validate it + write the report (Yahoo cross-check needs the optional group): `uv run --group crosscheck python scripts/validate_initial_dataset.py`
- Yahoo cross-check only: `uv run --group crosscheck python scripts/crosscheck_yfinance.py`
- Code style check: `uv run ruff format --check .`

## How to open the dashboard

```bash
uv run --group dashboard streamlit run src/quant_research/dashboard/app/main.py
```

Then open http://localhost:8501 in your browser. The dashboard only **views saved results** (run records,
reports, screening) — it runs no new experiments and downloads nothing.

**Local only — never deploy or share it.** It shows Tiingo price data and RBA exchange rates, which are licensed
for personal use only (DATA_SOURCES.md). `.streamlit/config.toml` binds it to `localhost` and turns off
Streamlit's usage statistics.

Screenshots of the four pages (saved to `data/screenshots/`, git-ignored because they show licensed prices), with
the dashboard running:

```bash
uv run --group screenshots python scripts/dashboard_screenshots.py
```

The first time, download the project-only browser (≈ 580 MB, into the git-ignored `.playwright-browsers/`):

```bash
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers uv run --group screenshots playwright install chromium
```

