# AgentShield
A lightweight, three-layer defence against indirect prompt injection in a small, local, tool-using AI assistant (CSCY413, Deliverable 2).

## Project Management

Development tasks and progress are tracked using our [AgentShield Development Board](https://github.com/users/MohammedAlamadi/projects/2/views/1).

## Final deliverables

| Deliverable | File |
|---|---|
| Final report (submitted version, editable source) | [`deliverables/report/AgentShield_D2_Final_Report.docx`](deliverables/report/AgentShield_D2_Final_Report.docx) |
| Final report (PDF exported from that DOCX with Microsoft Word) | [`deliverables/report/AgentShield_D2_Final_Report.pdf`](deliverables/report/AgentShield_D2_Final_Report.pdf) |
| Final poster (submitted PDF) | [`deliverables/poster/AgentShield_D2_Poster.pdf`](deliverables/poster/AgentShield_D2_Poster.pdf) |

The mapping from statements in the report to the files that support them is in [`docs/report_evidence_map.md`](docs/report_evidence_map.md) and [`docs/D2_results_inventory.md`](docs/D2_results_inventory.md).

## What AgentShield is
An assistant that reads emails and documents and then acts through tools can be steered by instructions hidden in that content (indirect prompt injection). AgentShield places three existing, lightweight defences around a small local model (`llama3.2:3b` or `qwen3:4b` through Ollama) and measures what each one actually does.

Every proposed tool call passes through this pipeline (`src/agentshield/agent.py`):

1. **Argument validation.** Malformed calls return an error and are not executed.
2. **Layer 3, deterministic guard** (`guard.py`, `scope.py`). A deny-by-default check of the call against the task scope chosen by the user (allowed tools, permitted recipients, target file). It never consults the language model. A denied call is not executed; the model receives a policy message.
3. **Tool execution.** The four tools (`read_inbox`, `read_document`, `send_email`, `delete_file`) act on a simulated, in-memory mailbox and file store. No real email is sent and no real file is touched.
4. **Layer 1, AI detector** (`detector.py`). The pretrained classifier `protectai/deberta-v3-base-prompt-injection-v2` (pinned revision, CPU, threshold 0.5) scores the tool output. A flagged output is withheld entirely and replaced by a quarantine notice.
5. **Layer 2, content isolation** (`isolation.py`). Untrusted email and document text is wrapped in `<untrusted_content>` delimiters, and the system prompt tells the model to treat it as data. This is advisory only.

Only Layer 1 uses a machine-learning model. Layer 3 does not inspect the final answer or the body of an otherwise permitted email. Every step of a run is written to a JSON-lines log.

## Repository structure
```
src/agentshield/          Core package: agent loop, three layers, tools, verifiers, experiments, aggregation, CLI
  dashboard/              Data loading, trace and story building, live sandbox runner used by the dashboard
dashboard/                Streamlit application (app.py, app_pages/, view_*.py, components*.py, assets/)
configs/                  The five evaluated configurations and models.lock.json (pinned Ollama and detector versions)
data/eval/                Frozen eval-v1 datasets, FROZEN_MANIFEST.json (SHA-256 hashes) and dataset review records
scripts/dataset/          Scripts that built, reviewed and froze the datasets
scripts/eval/             Analysis, review and validation scripts, and verify_reproduction.py
results/eval/             The 2,600 recorded evaluation runs (R1, Q1, S1), adjudication records and aggregates
results/detector_eval/    Layer 1 detector evaluation on the 120 frozen examples
results/                  Also: dataset audit, pilot and phase-2 smoke runs, early demo runs (runs/), architecture figure
tests/                    Automated tests (pytest)
docs/                     Methodology, implementation notes, review and audit records
docs/evidence/            Review workbooks, adjudication evidence and validation records, each with SHA256SUMS.txt
docs/report_history/      Change log of the final corrections made to the report's values
deliverables/             Submitted report (DOCX and PDF) and poster (PDF)
run_dashboard.bat         Windows launcher for the dashboard
```

The experiment logs, aggregates, frozen datasets and review evidence are kept exactly as recorded. `results/eval/aggregates/` also holds earlier aggregates that were superseded after manual review; the official ones are named below.

Some documents in `docs/` were written during development and refer to the development repository `AgentShield-D2` and to its local folders (for example `report_draft/`). Those references describe the state at the time; this repository is the final copy of that work.

## Setup
Prerequisites: Git, Python **3.11** (`pyproject.toml`: `>=3.11,<3.12`), an internet connection for the first installation, and a few GB of free disk space (PyTorch, the detector model and, for live runs, the Ollama models). The commands below were tested on Windows 11 with Python 3.11.9; on Linux, use `python3.11 -m venv .venv` and `.venv/bin/python`. macOS is untested.

```powershell
git clone https://github.com/MohammedAlamadi/AgentShield.git
cd AgentShield
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pip install -r requirements-dashboard.txt
.venv\Scripts\python -m pip install -e . --no-deps
```

- `requirements.txt` is a full lock, including CPU-only PyTorch from the PyTorch index. `requirements-dashboard.txt` adds Streamlit.
- The last command installs the `agentshield` package, which `python -m agentshield` needs.
- **Windows path length:** PyTorch and Streamlit contain very deep file paths. Clone into a short folder (for example `C:\src\AgentShield`) or enable Windows long-path support, otherwise `pip` can fail with `OSError: [Errno 2] No such file or directory`.

**Protect the frozen datasets (once, after cloning).** Git does not store the read-only attribute, and `tests/test_frozen_datasets.py::test_frozen_files_are_read_only` checks it:
```powershell
attrib +R data\eval\detector_examples_v1.jsonl
attrib +R data\eval\scenarios_v1.json
attrib +R data\eval\FROZEN_MANIFEST.json
```
On Linux: `chmod a-w data/eval/detector_examples_v1.jsonl data/eval/scenarios_v1.json data/eval/FROZEN_MANIFEST.json`. Integrity itself is verified by SHA-256, not by this attribute.

### Local models (needed only for live runs)
1. Install [Ollama](https://ollama.com). The evaluation used server version 0.40.16.
2. Pull the models:
   ```powershell
   ollama pull llama3.2:3b
   ollama pull qwen3:4b
   ```
3. Run `.venv\Scripts\python -m agentshield check`. It compares the Ollama version and the model digests with `configs/models.lock.json`. If a model tag has been updated upstream since November 2026, the digest check fails, and new runs then use a different model build.
4. The Layer 1 detector downloads automatically from Hugging Face on first use (pinned revision `90c9989b1a342275dd0d1a95aad283c04e075671`, about 715 MB).

## Verifying the results
All commands run from the repository root.

**1. Frozen datasets.** `verify_frozen()` checks the manifest and the SHA-256 of both datasets, the verifier code and the adjudication rubric:
```powershell
.venv\Scripts\python -c "from agentshield.frozen import verify_frozen; print(verify_frozen().version)"
```
Expected output: `eval-v1`. Any mismatch raises an error.

**2. Tests.**
```powershell
.venv\Scripts\python -m pytest -m "not ollama and not detector"
```
This subset needs no model. With Ollama running and the detector downloaded, `.venv\Scripts\python -m pytest` runs the whole suite.

**3. Reproduce the official aggregates from the recorded runs.**
```powershell
.venv\Scripts\python scripts\eval\verify_reproduction.py
```
The script verifies the frozen datasets, re-aggregates R1, Q1 and S1 from the saved logs and adjudication records into a temporary folder, and compares the result with the official aggregates `results/eval/aggregates/R1_20261113T212758Z`, `Q1_20261114T131523Z` and `S1_20261118T154119Z`. Expected last line: `ALL OFFICIAL AGGREGATES REPRODUCED`. Nothing under `results/` is changed. No model is needed.

The CLI equivalent, `python -m agentshield aggregate R1` (or `Q1`, `S1`), writes a new timestamped folder under `results/eval/aggregates/`.

## Inspecting the recorded results
- **Runs:** `results/eval/<run set>/runs/<scenario>__<config>.jsonl`, one JSON-lines log per run. R1 repetition 1 is `results/eval/20261113T190040Z/`; the other run sets are named `R1_repNN_…`, `Q1_rep01_…` and `S1_repNN_…`.
- **Adjudication:** `results/eval/<run set>/adjudication/`.
- **Aggregates:** `results/eval/aggregates/<experiment>_<timestamp>/aggregate.json` and `per_scenario.csv`.
- **Detector:** `results/detector_eval/`.
- The dashboard's Results and Evidence pages present the same files.

## Dashboard
A Streamlit dashboard with five pages: Overview, Simulator, Results, Evidence and Methodology.

- **Windows:** double-click `run_dashboard.bat`; it opens http://localhost:8501 in your browser. Alternatively run `.venv\Scripts\python -m streamlit run dashboard\app.py` and open http://localhost:8501 yourself.
- **Linux:** `.venv/bin/python -m streamlit run dashboard/app.py`, then open http://localhost:8501.
- **Simulator sources:**
  - *Live execution* runs a scenario through the real pipeline with the local model and writes its log only to `dashboard_runs/` (git-ignored, never evaluation evidence). It needs Ollama with `llama3.2:3b`.
  - *Recorded replay* shows a stored evaluation run and is labelled as such. Replay, Results and Evidence work without Ollama.
- Details: [`docs/D2_dashboard.md`](docs/D2_dashboard.md).

## Running scenarios (optional)
```powershell
.venv\Scripts\python -m agentshield run --scenarios data\eval\scenarios_v1.json --id LD01 --id AS06 --config configs\full.json --out audit_runs
```
- Configurations: `configs/unprotected.json`, `l1_only.json`, `l2_only.json`, `l3_only.json`, `full.json`.
- To repeat the evaluation protocol on new runs, use `evaluate` with an output folder outside `results/`, for example `.venv\Scripts\python -m agentshield evaluate --id AS06 --config full --out audit_eval --confirm-real-evaluation` (omit `--id` and `--config` for all 40 scenarios and five configurations). Without `--out` it writes to `results/eval/`.
- `python -m agentshield experiment-run` reproduces the registered R1/Q1/S1 schedule, but every registered repetition in this repository is already finished or gated, so it refuses to start. It never overwrites recorded runs.

## Reproducibility limitations
- **Recorded results are exact; new model runs are not.** The 2,600 recorded runs reproduce exactly from the logs. New runs use the same settings (temperature 0, seed 42, `num_ctx` 4096, pinned digests), but a local LLM does not guarantee identical outputs: scenario AS06 under Full took two different paths across the ten R1 repetitions.
- **Model availability.** The pinned Ollama digests may no longer be served under the same tags.
- **Hardware.** The evaluation ran on one consumer laptop with partial CPU offloading. Timings depend on hardware.
- **Scope of the evidence.** `llama3.2:3b` attempted only 2 of 26 attacks unprotected, so R1's security results are inconclusive. The `qwen3:4b` campaign (Q1) is one repetition, with 19 client timeouts. Layer 3 directly blocked the attacker's action in 6 of the 2,600 runs; most of the reduction under full protection came from attacks that were no longer attempted, which is not counted as prevention.
- **Detector.** Precision 0.860 and recall 0.717 on the frozen 120 examples at threshold 0.5. Recall is below the brief's 0.80 target, and a flagged harmless document is withheld entirely, which lowers legitimate-task success.
- **Attacks inside permitted actions or the final answer.** Layer 3 does not check the body of a permitted email or the final answer, and such attacks still succeeded with all layers on (AM01, AM03, AM04 and RA05; AM03 in every configuration).
- **Not tested.** Adaptive attackers and larger models.
