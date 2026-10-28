"""Step 8.3 — Strategy lab: START a run through backtesting.run (no logic here). Every lab run is EXPLORATORY."""

from decimal import Decimal
from pathlib import Path

import streamlit as st

from quant_research.dashboard import data as dd
from quant_research.dashboard import lab
from quant_research.dashboard.app import ui
from quant_research.data.storage import git_state
from quant_research.strategies import labels

st.title("Strategy lab")
st.error(
    f"**{lab.LABEL}.** Lab runs are saved under data/runs/lab/ — never mixed with the pre-registered runs. "
    "Trying many settings and keeping the best is exactly the over-fitting the pre-registration prevents: a good "
    "lab result is not evidence.",
    icon="🧪",
)
period = st.radio("Period", list(lab.PERIODS), horizontal=True)
ui.banner(period)
dirty = git_state(dd.PROJECT_ROOT)["git_dirty"]
if dirty:
    st.warning(
        "The code has uncommitted changes: lab runs started now are recorded as **dirty** (D6)."
    )

c1, c2, c3 = st.columns(3)
ticker = c1.selectbox("Stock", ["AAPL", "MSFT", "KO", "PG", "XOM", "INTC", "T", "SPY"])
label = c2.selectbox("Strategy", list(lab.STRATEGIES), format_func=labels.display)
c2.caption(ui.explanation(label))
variant = c3.selectbox("Cost variant", list(lab.VARIANTS), help=str(lab.VARIANTS))
x = y = k = w = None
if label in ("S1", "S2", "S4-S1", "S4-S2"):
    a, b = st.columns(2)
    x = Decimal(str(a.number_input("X (profit target)", 0.005, 0.50, 0.02, 0.005, format="%.3f")))
    y = Decimal(str(b.number_input("Y (dip)", 0.005, 0.50, 0.04, 0.005, format="%.3f")))
elif label == "S3":
    a, b = st.columns(2)
    k = Decimal(str(a.number_input("k (z-score)", 0.5, 5.0, 2.0, 0.5, format="%.1f")))
    w = int(b.number_input("w (window, days)", 5, 250, 20, 5))
spec = lab.LabSpec(ticker, label, period, variant, x=x, y=y, k=k, w=w)
if st.button(
    f"Run (through run.py) — plus {labels.display('S0')} with the same settings", type="primary"
):
    with st.spinner("Running the validated engine…"):
        st.session_state["lab_result"] = lab.run_lab(spec)

past = lab.lab_runs()
if not past:
    st.info("No lab runs yet.")
    st.stop()
latest = st.session_state.get("lab_result")
choices = [p for p, m in past if m["paired_s0_run"] != p.parent.name] or [p for p, _ in past]
default = choices.index(latest.run_json) if latest and latest.run_json in choices else 0
chosen = st.selectbox(
    "Lab run to show", choices, index=default, format_func=lambda p: p.parent.name
)
marker = dict(past)[chosen]
r = dd.load_run(Path(chosen), marker["spec"]["period"])
s0_json = chosen.parent.parent / marker["paired_s0_run"] / "run.json"
s0 = dd.load_run(s0_json, marker["spec"]["period"]) if s0_json != chosen else None

st.markdown(f"### {r.title} · {marker['spec']['variant']} — {lab.LABEL}")
st.caption(ui.explanation(r.label))
st.caption(
    f"On the pre-registered grid: {marker['on_pre_registered_grid']} · code dirty when run: {marker['git_dirty']}"
)
left, right = st.columns(2)
left.markdown("**This lab run**")
left.table(ui.results_table(dd.key_results(r, s0)))
right.markdown(f"**{labels.display('S0')} — same stock, period and costs**")
right.table(
    ui.results_table(dd.key_results(s0, None)) if s0 else {labels.display("S0"): dd.NOT_AVAILABLE}
)
verdict = dd.verdict_for(r.label)
st.markdown("**Pre-registered verdict for this strategy (validation 2017–2020, MAIN settings):**")
st.markdown(
    labels.name_ids(verdict)
    if verdict
    else f"{labels.display('S0')} is the benchmark — no verdict."
)
ui.assumptions(r)
ui.report_and_exports(r, s0, exploratory=True)
