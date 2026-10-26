"""Steps 8.6 + 8.7 — research report and exports for the selected saved run."""

import streamlit as st

from quant_research.dashboard.app import ui

period, run, s0 = ui.pick_run()
st.title("Report & export")
ui.banner(period)
st.subheader(f"{run.ticker} · {run.label} · {run.setting}")
ui.report_and_exports(run, s0, exploratory=False)
ui.assumptions(run)
