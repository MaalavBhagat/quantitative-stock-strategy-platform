"""Shared Streamlit pieces: banner, run picker, assumptions box. Display only — numbers come from dashboard.data."""

import pandas as pd
import streamlit as st

from quant_research.dashboard import data as dd
from quant_research.data.fx import load_usd_per_aud
from quant_research.strategies import labels

ORDER = ["S0", "S1", "S2", "S3", "S4-S1", "S4-S2", "C1", "C2", "E1"]


@st.cache_data(show_spinner=False)
def index(period: str) -> dict:
    return {k: str(v) for k, v in dd.run_index(period).items()}


@st.cache_resource(show_spinner=False)
def run(path: str, period: str) -> dd.RunRecord:
    from pathlib import Path

    return dd.load_run(Path(path), period)


@st.cache_resource(show_spinner=False)
def fx():
    return load_usd_per_aud()


def explanation(strategy_id: str) -> str:
    """The one-line explanation, with any strategy it mentions named too."""
    return labels.name_ids(labels.explain(strategy_id))


def title(r: dd.RunRecord) -> None:
    """Page sub-heading for a run: stock · name (ID) · setting, with the one-line explanation."""
    st.subheader(r.title)
    st.caption(explanation(r.label))


# Theme details that config.toml cannot set (Goggy's theme 2026-10-30; colours in .streamlit/config.toml). Display only.
# Captions / metric labels: Streamlit fades them to ~60% of the text colour, which failed WCAG AA (3.04–4.14:1), so
# they get a solid #42342F (10.44 on the page, 8.12 on cream-beige, 4.88 on the sage sidebar).
STYLE = """<style>
h1, h2, h3, h4, [data-testid="stHeading"] h1, [data-testid="stHeading"] h2, [data-testid="stHeading"] h3,
[data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3 { color: #590907 !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *,
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { color: #42342F !important; opacity: 1 !important; }
.sim-banner { background: #E8D2B5; color: #2B1D1A; border-left: 6px solid #590907; border-radius: 0.5rem;
              padding: 0.75rem 1rem; margin-bottom: 1rem; font-weight: 600; }
</style>"""


def banner(period: str) -> None:
    """The SIMULATED, HISTORICAL banner (cream-beige card, burgundy edge) + the shared page styling."""
    import html

    st.markdown(STYLE, unsafe_allow_html=True)
    st.markdown(
        f'<div class="sim-banner">⚠️ {html.escape(dd.banner(period))}</div>', unsafe_allow_html=True
    )


def _kept(widget, label: str, options: list, name: str, **kwargs):
    """A sidebar widget whose choice survives page changes (Streamlit clears widget state when a page changes,
    so the choice is copied to a plain session key and used as the starting index next time)."""
    store = f"keep_{name}"
    saved = st.session_state.get(store)
    choice = widget(
        label,
        options,
        index=options.index(saved) if saved in options else 0,
        key=f"w_{name}",
        **kwargs,
    )
    st.session_state[store] = choice
    return choice


def pick_run() -> tuple[str, dd.RunRecord, dd.RunRecord | None]:
    """Sidebar: period → stock → strategy → setting. Returns (period, run, S0 of the same stock and period)."""
    st.sidebar.header("Saved run")
    periods = ["final", "validation", "development"]
    if dd.run_index("demo"):  # only after `uv run python scripts/demo.py` (made-up data)
        periods.append("demo")
    period = _kept(st.sidebar.radio, "Period", periods, "period")
    idx = index(period)
    tickers = sorted({t for _, t, _ in idx})
    ticker = _kept(st.sidebar.selectbox, "Stock", tickers, "ticker")
    ids = [lbl for lbl in ORDER if any(k[0] == lbl and k[1] == ticker for k in idx)]
    label = _kept(st.sidebar.selectbox, "Strategy", ids, "label", format_func=labels.display)
    st.sidebar.caption(explanation(label))
    settings = sorted(s for lbl, t, s in idx if lbl == label and t == ticker)
    setting = _kept(st.sidebar.selectbox, "Setting", settings, "setting")
    chosen = run(idx[(label, ticker, setting)], period)
    s0_key = ("S0", ticker, "—")
    s0 = run(idx[s0_key], period) if s0_key in idx else None
    if period == "demo":
        st.sidebar.caption(
            "Demo = MADE-UP prices from scripts/demo.py (stock 'DEMO'), safe to share; says nothing about real stocks."
        )
    if period == "final":
        st.sidebar.caption(
            "Final test = the ONE-TIME run on 2021–2025 (7 stocks, T excluded), rules fixed in advance (prereg-final)."
        )
    if period == "development":
        st.sidebar.caption(
            "Development = exploration only (2010–2016, AAPL + XOM). No verdict is judged on it."
        )
    return period, chosen, s0


def assumptions(r: dd.RunRecord) -> None:
    with st.expander("Assumptions of this run (from the saved run record)", expanded=True):
        a = dd.assumptions(r)
        st.table(pd.DataFrame({"value": list(a.values())}, index=list(a)))


def results_table(results: dict[str, str]) -> dict[str, str]:
    """Key results with any strategy ID in a row name given its name ('Excess vs Buy-and-hold (S0) …')."""
    return {labels.name_ids(k): v for k, v in results.items()}


def report_and_exports(r: dd.RunRecord, s0: dd.RunRecord | None, exploratory: bool) -> None:
    """Report button + download buttons. Every file is also saved to data/exports/<run id>/ (git-ignored)."""
    from quant_research.dashboard import export as ex

    st.markdown("### Research report and exports")
    st.caption(
        "Personal use; do not redistribute — Tiingo data: internal use only; RBA rates: personal, non-commercial, "
        "with attribution. Files are also saved in data/exports/<run id>/ (never committed)."
    )
    if st.button("Generate report + export files", key=f"export_{r.record['run_id']}"):
        paths = ex.write_exports(r, s0, exploratory)
        st.session_state[f"exported_{r.record['run_id']}"] = {k: str(v) for k, v in paths.items()}
    saved = st.session_state.get(f"exported_{r.record['run_id']}")
    if not saved:
        return
    from pathlib import Path

    st.success(f"Saved to {Path(saved['report.md']).parent.relative_to(dd.PROJECT_ROOT)}")
    cols = st.columns(3)
    for i, (name, mime) in enumerate(
        [
            ("trades.csv", "text/csv"),
            ("equity.csv", "text/csv"),
            ("config.yaml", "text/yaml"),
            ("report.md", "text/markdown"),
            ("chart.png", "image/png"),
            ("LICENCE.txt", "text/plain"),
        ]
    ):
        cols[i % 3].download_button(
            f"Download {name}",
            Path(saved[name]).read_bytes(),
            file_name=f"{r.record['run_id']}_{name}",
            mime=mime,
        )
    with st.expander("Report preview", expanded=True):
        # escape "$" so Streamlit never reads two dollar amounts on one line as a maths formula
        st.markdown(Path(saved["report.md"]).read_text(encoding="utf-8").replace("$", "\\$"))
