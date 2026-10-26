"""Step 8.2 — Company research: quality score, sub-scores, why lines, data problems, trading profile."""

import pandas as pd
import streamlit as st

from quant_research.dashboard import data as dd
from quant_research.dashboard.app import ui
from quant_research.screening.score import INPUTS

st.title("Company research")
ui.banner("screen")
st.caption(
    "Descriptive screen — not a recommendation, not financial advice. Method fixed before any score: "
    "research/SCREENING_METHOD.md (commit f66e267). 7 companies chosen with hindsight; nothing tested out of sample."
)


@st.cache_data(show_spinner="Reading the saved SEC files…")
def rows() -> dict:
    return dd.screening_rows()


@st.cache_data(show_spinner=False)
def profile(ticker: str) -> pd.DataFrame:
    return dd.trading_profile(ticker)


company = st.selectbox("Company", dd.COMPANIES + ["SPY"])
if company == "SPY":
    st.info("SPY is a fund: no company financials, so no quality score (trading profile only).")
else:
    years = rows()[company]
    table = pd.DataFrame(
        {
            "as of": [str(y.as_of) for y in years],
            "10-K used": [y.ten_k for y in years],
            "quality score": [
                dd.show(y.quality, "{:.2f}") if y.quality is not None else "NOT SCORED"
                for y in years
            ],
            **{
                lbl: [dd.show(y.subscores.get(k), "{:.2f}") for y in years]
                for k, (lbl, _) in INPUTS.items()
            },
        }
    )
    st.markdown("### Quality score and sub-scores (best 1.00 … worst 0.00 among the 7)")
    st.dataframe(table, hide_index=True, width="stretch")
    st.markdown("### Why this score")
    for y in years:
        st.markdown(f"- **{y.as_of}** — {y.why}")
    st.markdown("### Missing or conflicting inputs (never filled)")
    problems = [(y.as_of, p) for y in years for p in y.problems]
    if problems:
        for d, p in problems:
            st.markdown(f"- **{d}** — {p}")
    else:
        st.markdown("- none")
st.markdown("### Trading profile per calendar year (reported, not scored)")
st.dataframe(profile(company), hide_index=True, width="stretch")
st.caption(
    "Spreads: not available in free daily data — only the assumed levels are used in the backtests."
)
