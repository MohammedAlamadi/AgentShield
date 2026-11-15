"""AgentShield D2 dashboard (Phase 5). Launch from the repository root:

    run_dashboard.bat            (Windows)
    .venv\\Scripts\\python -m streamlit run dashboard\\app.py

Read-only on every evaluation artifact. Live runs use the real runner and write logs only to dashboard_runs/.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", Path(__file__).resolve().parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="AgentShield D2", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

import components as ui  # noqa: E402
import state  # noqa: E402
import view_about  # noqa: E402
import view_explorer  # noqa: E402
import view_results  # noqa: E402
import view_simulator  # noqa: E402

ui.inject_css()

PAGES = {
    "🎯  Attack Simulator": view_simulator.render,
    "📊  Results": view_results.render,
    "🔎  Evidence Explorer": view_explorer.render,
    "🧭  How it works & limits": view_about.render,
}
HINTS = {
    "🎯  Attack Simulator": "Run or replay one attack and see, step by step, what the AI did and how each layer responded.",
    "📊  Results": "What 2,600 recorded runs show: fewer successful attacks? any cost to normal tasks? what still got through?",
    "🔎  Evidence Explorer": "Search any recorded run and read what happened in plain English, with the raw evidence on demand.",
    "🧭  How it works & limits": "The three layers in one picture, and the honest limitations of the evaluation.",
}

with st.sidebar:
    ui.hero("AgentShield", "Defence against indirect prompt injection")
    page = st.radio("Navigate", list(PAGES), label_visibility="collapsed", key="nav")
    st.markdown(f"<div class='as-note' style='margin-top:6px'>{HINTS[page]}</div>", unsafe_allow_html=True)
    st.divider()
    try:
        idx = state.run_index()
        ov = state.overview()
        st.markdown(f"<div class='as-note'><b>{ov['total_runs']:,}</b> end-to-end runs indexed<br>"
                    + "<br>".join(f"{e}: {v['runs']:,} runs · {', '.join(v['model'])}" for e, v in ov["experiments"].items())
                    + "<br>Reference evaluation = R1 repetition 1 (counted once)</div>", unsafe_allow_html=True)
    except Exception as exc:  # malformed or missing artifacts must not crash the app
        st.error(f"Could not load the evaluation artifacts: {exc}")
    st.divider()
    st.markdown("<div class='as-note'>Read-only on all frozen data, logs, aggregates and review records. "
                "Live runs are sandboxed (simulated tools, logs in <code>dashboard_runs/</code>).</div>", unsafe_allow_html=True)

PAGES[page]()
