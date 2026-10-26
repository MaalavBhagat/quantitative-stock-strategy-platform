"""Step 8.4 — Performance: equity vs S0, drawdown, cash vs invested, cumulative costs — from saved files."""

import altair as alt
import pandas as pd
import streamlit as st

from quant_research.dashboard import data as dd
from quant_research.dashboard.app import ui

period, run, s0 = ui.pick_run()
st.title("Performance")
ui.banner(period)
st.subheader(f"{run.ticker} · {run.label} · {run.setting}")
currency = st.radio("Currency", ["USD", "AUD"], horizontal=True)
col = "total_usd" if currency == "USD" else "total_aud"
fx = ui.fx() if currency == "AUD" else None

eq = dd.equity_table(run, fx)
lines = [eq.assign(series=f"{run.label} {run.setting}")[["day", col, "series"]]]
if s0 is not None and run.label != "S0":
    lines.append(dd.equity_table(s0, fx).assign(series="S0 buy-and-hold")[["day", col, "series"]])
both = pd.concat(lines)
st.markdown(f"### Total value ({currency}, at each close)")
st.altair_chart(
    alt.Chart(both)
    .mark_line()
    .encode(x="day:T", y=alt.Y(f"{col}:Q", title=currency), color="series:N"),
    width="stretch",
)
if currency == "AUD":
    st.caption(
        "AUD = USD value ÷ RBA rate of that day (latest rate dated ≤ day) — same rule as the run."
    )

st.markdown("### Drawdown (value ÷ highest value so far − 1)")
st.altair_chart(
    alt.Chart(eq)
    .mark_area(opacity=0.5)
    .encode(x="day:T", y=alt.Y("drawdown:Q", axis=alt.Axis(format="%"))),
    width="stretch",
)

st.markdown("### Cash vs invested (USD)")
held = eq.melt("day", ["cash_usd", "invested_usd"], var_name="part", value_name="usd")
st.altair_chart(
    alt.Chart(held).mark_area().encode(x="day:T", y="usd:Q", color="part:N"),
    width="stretch",
)

st.markdown("### Costs and dividends (USD)")
costs = dd.costs_table(run)
if costs.empty:
    st.markdown("No trades — no fees or spread cost.")
else:
    cum = costs.melt(
        "day", ["cumulative_fees_usd", "cumulative_spread_usd"], var_name="cost", value_name="usd"
    )
    st.altair_chart(
        alt.Chart(cum)
        .mark_line(interpolate="step-after")
        .encode(x="day:T", y="usd:Q", color="cost:N"),
        width="stretch",
    )
c1, c2, c3 = st.columns(3)
c1.metric("Fees total (run record)", f"US${float(run.summary['total_fees_usd']):,.2f}")
c2.metric(
    "Spread cost total (fills)",
    f"US${costs['spread_usd'].sum():,.2f}" if not costs.empty else "US$0.00",
)
c3.metric("Dividends net (run record)", f"US${float(run.summary['dividends_net_usd']):,.2f}")
st.caption(
    f"Dividends over time: {dd.NOT_AVAILABLE} — the run record saves only the total, so no daily line is drawn."
)
ui.assumptions(run)
