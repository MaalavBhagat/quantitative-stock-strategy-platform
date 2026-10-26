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


def pick_run() -> tuple[str, dd.RunRecord, dd.RunRecord | None]:
    """Sidebar: period → stock → strategy → setting. Returns (period, run, S0 of the same stock and period)."""
    st.sidebar.header("Saved run")
    period = st.sidebar.radio("Period", ["validation", "development"], key="period")
    idx = index(period)
    tickers = sorted({t for _, t, _ in idx})
    ticker = st.sidebar.selectbox("Stock", tickers, key=f"ticker_{period}")
    labels = [lbl for lbl in ORDER if any(k[0] == lbl and k[1] == ticker for k in idx)]
    label = st.sidebar.selectbox("Strategy", labels, key=f"label_{period}")
    settings = sorted(s for lbl, t, s in idx if lbl == label and t == ticker)
    setting = st.sidebar.selectbox("Setting", settings, key=f"setting_{period}_{label}")
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
