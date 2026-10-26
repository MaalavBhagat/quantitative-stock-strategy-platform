"""Shared Streamlit pieces: banner, run picker, assumptions box. Display only — numbers come from dashboard.data."""

import pandas as pd
import streamlit as st

from quant_research.dashboard import data as dd
from quant_research.data.fx import load_usd_per_aud

ORDER = ["S0", "S1", "S2", "S3", "S4-S1", "S4-S2"]


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


def banner(period: str) -> None:
    st.warning(dd.banner(period), icon="⚠️")


def _kept(widget, label: str, options: list, name: str):
    """A sidebar widget whose choice survives page changes (Streamlit clears widget state when a page changes,
    so the choice is copied to a plain session key and used as the starting index next time)."""
    store = f"keep_{name}"
    saved = st.session_state.get(store)
    choice = widget(
        label, options, index=options.index(saved) if saved in options else 0, key=f"w_{name}"
    )
    st.session_state[store] = choice
    return choice


def pick_run() -> tuple[str, dd.RunRecord, dd.RunRecord | None]:
    """Sidebar: period → stock → strategy → setting. Returns (period, run, S0 of the same stock and period)."""
    st.sidebar.header("Saved run")
    period = _kept(st.sidebar.radio, "Period", ["validation", "development"], "period")
    idx = index(period)
    tickers = sorted({t for _, t, _ in idx})
    ticker = _kept(st.sidebar.selectbox, "Stock", tickers, "ticker")
    labels = [lbl for lbl in ORDER if any(k[0] == lbl and k[1] == ticker for k in idx)]
    label = _kept(st.sidebar.selectbox, "Strategy", labels, "label")
    settings = sorted(s for lbl, t, s in idx if lbl == label and t == ticker)
    setting = _kept(st.sidebar.selectbox, "Setting", settings, "setting")
    chosen = run(idx[(label, ticker, setting)], period)
    s0_key = ("S0", ticker, "—")
    s0 = run(idx[s0_key], period) if s0_key in idx else None
    if period == "development":
        st.sidebar.caption(
            "Development = exploration only (2010–2016, AAPL + XOM). No verdict is judged on it."
        )
    return period, chosen, s0


def assumptions(r: dd.RunRecord) -> None:
    with st.expander("Assumptions of this run (from the saved run record)", expanded=True):
        a = dd.assumptions(r)
        st.table(pd.DataFrame({"value": list(a.values())}, index=list(a)))


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
        st.markdown(Path(saved["report.md"]).read_text(encoding="utf-8"))
