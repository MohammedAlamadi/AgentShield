"""AgentShield D2 dashboard. Launch from the repository root:

    run_dashboard.bat            (Windows)
    .venv\\Scripts\\python -m streamlit run dashboard\\app.py

Read-only on every evaluation artifact. Live runs use the real runner and write logs only to dashboard_runs/.
Design system: dashboard/DESIGN_SYSTEM.md (theme in .streamlit/config.toml).
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (ROOT / "src", HERE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="AgentShield", page_icon=str(HERE / "assets" / "agentshield_icon.svg"), layout="wide",
                   initial_sidebar_state="collapsed")

import components as ui  # noqa: E402

ui.inject_css()
import components_v2  # noqa: E402

components_v2.inject_css2()
st.logo(str(HERE / "assets" / "agentshield_logo.svg"), size="large")

PAGE_DIR = HERE / "app_pages"
pages = [
    st.Page(PAGE_DIR / "overview.py", title="Overview", url_path="overview", default=True),
    st.Page(PAGE_DIR / "simulator.py", title="Simulator", url_path="simulator"),
    st.Page(PAGE_DIR / "results.py", title="Results", url_path="results"),
    st.Page(PAGE_DIR / "evidence.py", title="Evidence", url_path="evidence"),
    st.Page(PAGE_DIR / "methodology.py", title="Methodology", url_path="methodology"),
]
st.navigation(pages, position="top").run()
