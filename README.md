# AgentShield
A lightweight, three-layer defence against indirect prompt injection in local AI assistants


## Project Management

Development tasks and progress are tracked using our [AgentShield Development Board](https://github.com/users/MohammedAlamadi/projects/2/views/1).

## Dashboard (Phase 5)

Interactive Streamlit dashboard with a live attack simulator (real runner, local Ollama), evaluation results and an evidence explorer.

- **Windows:** double-click `run_dashboard.bat`, or run `.venv\Scripts\python -m streamlit run dashboard\app.py`.
- **Requirements:** `requirements.txt` plus `requirements-dashboard.txt`; Ollama with `llama3.2:3b` for live runs.
- **Details** (architecture, live vs replay, viva demo, troubleshooting): `docs/D2_dashboard.md`.
