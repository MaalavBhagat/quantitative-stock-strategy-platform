"""Step 8.1 — Overview: the chosen run's key results, the pre-registered verdicts, links to the write-ups."""

import streamlit as st

from quant_research.dashboard import data as dd
from quant_research.dashboard.app import ui
from quant_research.strategies import labels

S0 = labels.display("S0")

period, run, s0 = ui.pick_run()
st.title("Overview")
ui.banner(period)
ui.title(run)

st.markdown("### Pre-registered verdicts (validation 2017–2020, MAIN settings)")
st.error(
    "All five strategies were **REJECTED** against buy-and-hold under rules fixed in advance.",
    icon="❌",
)
st.markdown(dd.named_verdict_table())

st.markdown("### Key results of this run")
results = ui.results_table(dd.key_results(run, s0))
LONG = (
    "Starting capital",
    "Test period",
    "Max drawdown",
)  # too long for a number tile — shown as text
for name in LONG:
    st.markdown(f"**{name}:** {results[name]}")
short = {k: v for k, v in results.items() if k not in LONG}
cols = st.columns(3)
for i, (name, value) in enumerate(short.items()):
    cols[i % 3].metric(name, value)
if s0 is not None and run.label != "S0":
    st.caption(
        f"Excess = this run's total return − {S0} total return on {run.ticker}, same period."
    )
ui.assumptions(run)

st.markdown("### Write-ups (saved files)")
for title, path in [
    ("Results summary", dd.REPORTS_DIR / "RESULTS_SUMMARY.md"),
    (
        "Failed experiments and our own mistakes",
        dd.PROJECT_ROOT / "research" / "FAILED_EXPERIMENTS.md",
    ),
]:
    with st.expander(f"{title} — {path.relative_to(dd.PROJECT_ROOT)}"):
        text = labels.name_ids(path.read_text(encoding="utf-8"))
        st.markdown(text.replace("$", "\\$"))  # "$" is not maths
