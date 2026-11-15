@echo off
REM AgentShield D2 dashboard launcher (Windows). Run from anywhere; uses the project .venv.
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [AgentShield] .venv not found. Create it first:  py -3.11 -m venv .venv  and install requirements.txt + requirements-dashboard.txt
  exit /b 1
)
".venv\Scripts\python.exe" -c "import streamlit" 2>nul
if errorlevel 1 (
  echo [AgentShield] Streamlit missing. Installing pinned dashboard dependencies...
  ".venv\Scripts\python.exe" -m pip install -r requirements-dashboard.txt || exit /b 1
)
curl -s -m 2 http://127.0.0.1:11434/api/version >nul 2>&1
if errorlevel 1 (
  echo [AgentShield] Ollama is not responding. Live execution will be unavailable until you start Ollama
  echo               ^(Start menu: Ollama, or run "ollama serve"^). Recorded replay and results still work.
)
echo [AgentShield] Opening http://localhost:8501  (Ctrl+C to stop)
start "" http://localhost:8501
".venv\Scripts\python.exe" -m streamlit run dashboard\app.py --server.port 8501 --server.headless true
endlocal
