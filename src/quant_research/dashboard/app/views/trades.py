"""Step 8.5 — Trade explorer: every fill and every order (incl. REJECTED / EXPIRED) and a trade's effect."""

import streamlit as st

from quant_research.dashboard import data as dd
from quant_research.dashboard.app import ui

period, run, _ = ui.pick_run()
st.title("Trade explorer")
ui.banner(period)
ui.title(run)

st.markdown(f"### Fills ({len(run.fills)})")
st.caption(
    "Reference open = that day's raw open; fill = open ± spread; fee = brokerage + FX (simulated)."
)
st.dataframe(dd.fills_table(run), hide_index=True, width="stretch")

orders = dd.orders_table(run)
counts = orders["status"].value_counts().to_dict()
st.markdown("### Orders — " + ", ".join(f"{k} {v}" for k, v in counts.items()))
st.dataframe(orders, hide_index=True, width="stretch")

st.markdown("### Effect of one trade on cash and position")
if run.fills:
    i = st.selectbox(
        "Trade",
        range(len(run.fills)),
        format_func=lambda k: f"#{k + 1} {run.fills[k]['day']} {run.fills[k]['side']}",
    )
    st.table(dd.trade_effect(run, i))
else:
    st.markdown("This run made no trades.")
ui.assumptions(run)
