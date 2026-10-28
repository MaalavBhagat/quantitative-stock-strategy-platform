# Quantitative Stock Strategy Research Platform

A research tool that tests one question honestly: does "sell after a small rise, buy back
after a dip" beat simply buying and holding, after real costs, on an AUD 10,000 account
(US stocks, Stake as the main broker)? A "no" answer is a valid result.
All results are **simulated, historical** — nothing here is a claim of profitability or
investment advice.

See `PROJECT_BRIEF.md` (summary), `PROJECT_STATUS.md` (progress), `research/` (design and pre-registrations),
[`RESEARCH_METHODOLOGY.md`](RESEARCH_METHODOLOGY.md) (how the research was done) and [`TESTING.md`](TESTING.md).

## Findings

- **Answer: no.** In the one-time final test (2021–2025, 7 stocks, rules fixed and git-tagged before any 2021+ data
  was downloaded) every strategy was **REJECTED**: the five "sell after a rise, rebuy after a dip" variants against
  buy-and-hold, and the three that add market or earnings information against the same strategy without it. The same
  verdicts came out on the 2017–2020 validation period. Simulated, historical; not financial advice.
- Main reasons: selling early left the strategies in cash while prices kept rising; they only helped on falling or flat
  stocks and in down years, and earlier "winners" did not persist.
- Plain-English summary with sources: [`reports/RESULTS_SUMMARY.md`](reports/RESULTS_SUMMARY.md); full final-test
  report: [`reports/experiments/FINAL_TEST_2021-2025.md`](reports/experiments/FINAL_TEST_2021-2025.md).

## Setup (macOS)

1. Install [uv](https://docs.astral.sh/uv/) once: `brew install uv`
2. In this folder, create the environment (installs Python 3.13 if needed, plus dev tools):

   ```bash
   uv sync
   ```

   Optional package groups: `dashboard`, `crosscheck` (Yahoo), `screenshots` — or everything at once with
   `uv sync --all-groups`.

3. Only needed to DOWNLOAD data: copy `.env.example` to `.env` and fill in `TIINGO_API_KEY` (Tiingo) and
   `SEC_USER_AGENT` (your name + email, SEC fair-access rule). `.env` is git-ignored — never commit it.

## Run the tests and the code checker

```bash
uv run pytest
uv run ruff check .
```

On a fresh clone there is no `data/` folder (licensed data is never committed), so the tests that replay saved runs
skip themselves and say why; everything else runs. More checks (dashboard smoke test, report reproduction, secrets
scan): [`TESTING.md`](TESTING.md). Every script explains itself with `--help`.

## Data

Downloaded market data goes in `data/`, which is git-ignored (personal-use licence).
Rules for using it: `DATA_SOURCES.md` §7 (conventions) and §8 (limitations).

- The results cannot be re-created from a fresh clone alone: the price data has to be downloaded again with your own
  Tiingo key (the downloaders and dates are in `scripts/` and DATA_SOURCES.md §10–§13).
- Download the initial dataset (2 Tiingo calls, needs `.env`): `uv run python scripts/download_initial_dataset.py`
- Validate it + write the report (Yahoo cross-check needs the optional group): `uv run --group crosscheck python scripts/validate_initial_dataset.py`
- Yahoo cross-check only: `uv run --group crosscheck python scripts/crosscheck_yfinance.py`
- Code style check: `uv run ruff format --check .`

## How to open the dashboard

```bash
uv run --group dashboard streamlit run src/quant_research/dashboard/app/main.py
```

Then open http://localhost:8501 in your browser. The dashboard only **views saved results** (run records,
reports, screening) — it runs no new experiments and downloads nothing. The sidebar's period picker shows the
**final** test (2021–2025), **validation** (2017–2020) and **development** (2010–2016) runs; strategies are shown by
name with their ID, e.g. "Trend filter + pullback (S4-S2)".

**Local only — never deploy or share it.** It shows Tiingo price data and RBA exchange rates, which are licensed
for personal use only (DATA_SOURCES.md). `.streamlit/config.toml` binds it to `localhost` and turns off
Streamlit's usage statistics.

Screenshots of the pages (saved to `data/screenshots/`, git-ignored because they show licensed prices), with
the dashboard running (it also presses the export button and starts one exploratory lab run):

```bash
uv run --group screenshots python scripts/dashboard_screenshots.py
```

The first time, download the project-only browser (≈ 580 MB, into the git-ignored `.playwright-browsers/`):

```bash
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers uv run --group screenshots playwright install chromium
```

### Strategy lab, reports and exports

- **Strategy lab** page: choose stock, strategy, settings, period (development or validation only) and cost variant;
  it runs through the same validated engine (`run.py`) together with buy-and-hold on the same settings. Lab runs are
  saved under `data/runs/lab/` and labelled **EXPLORATORY — NOT PRE-REGISTERED** — a good lab result is not evidence.
- **Report & export** page (and the bottom of the lab page): a Markdown research report plus trade log CSV, equity CSV,
  config YAML and a chart PNG, saved to `data/exports/<run id>/`. Every file carries the licence note:
  **personal use; do not redistribute** (Tiingo: internal use only; RBA: personal, non-commercial, with attribution).
- An exported `config.yaml` fed back into `run.py` gives the identical result (tested).

