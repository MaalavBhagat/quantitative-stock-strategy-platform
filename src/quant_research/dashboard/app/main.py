"""Dashboard entry point. Run:  uv run --group dashboard streamlit run src/quant_research/dashboard/app/main.py

Local only (localhost) — never deploy: it shows Tiingo and RBA data under personal-use licences.
"""

from pathlib import Path

import streamlit as st

HERE = Path(__file__).parent / "views"
st.set_page_config(page_title="Strategy research (simulated)", layout="wide")
nav = st.navigation(
    [
        st.Page(HERE / "overview.py", title="Overview", default=True),
        st.Page(HERE / "company.py", title="Company research"),
        st.Page(HERE / "performance.py", title="Performance"),
        st.Page(HERE / "trades.py", title="Trade explorer"),
    ]
)
nav.run()
