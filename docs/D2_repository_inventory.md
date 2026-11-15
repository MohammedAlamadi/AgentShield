# AgentShield D2: repository inventory (read-only inspection)

**Date:** 15 Nov 2026.

**Scope:** inspection only. Nothing was modified, moved, deleted, committed, branched, pushed or pulled. This file is the only thing the inspection created.

**Sizes:** exclude `.venv/` and `.git/`. The whole project, without the virtual environment, is about 31 MB in about 3,170 files. No file is larger than 2 MB.

---

## 1. Git status and repository details

| Item | Value |
|---|---|
| Current branch | `main`, tracking `origin/main`, in sync (no local commits ahead) |
| Remote `origin` | `https://github.com/MohammedAlamadi/AgentShield-D2.git` (fetch and push) |
| Branches | Local `main`; remote `origin/main` (`origin/HEAD` → `origin/main`). No other branches |
| Commit history | 1 commit: `fa2f78a` "Initialize AgentShield D2 project structure", by MohammedAlamadi, 13 Nov 2026 14:34 +0400 |
| Repository object store | 6 loose objects, 687 bytes (only the skeleton commit) |
| `core.autocrlf` | `true` (Git for Windows default) |
| `.gitattributes` | **None** |
| Python | 3.11.9 (`pyproject.toml` requires `>=3.11,<3.12`) |

### Tracked files (8 in total; all from the skeleton commit)

```
.gitignore         (modified)
README.md          (modified)
requirements.txt   (modified)
data/.gitkeep
docs/.gitkeep
results/.gitkeep
src/.gitkeep
tests/.gitkeep
```

Uncommitted modifications to tracked files: `.gitignore` +11/−1, `README.md` +8, `requirements.txt` +62 (the full pinned lock).

### Untracked (everything else that is not ignored)

`.claude/`, `.streamlit/`, `configs/`, `dashboard/`, `data/demo/`, `data/eval/`, `data/pilot/`, all `docs/*.md` except `.gitkeep`, `docs/evidence/`, `pyproject.toml`, `requirements-dashboard.txt`, `results/*` (all seven subfolders), `run_dashboard.bat`, `scripts/`, `src/agentshield/`, and all of `tests/` except `.gitkeep`. That is about 3,150 files, so **all D2 work is currently uncommitted**.

### Ignored by `.gitignore`

| Path | What it is |
|---|---|
| `.venv/` | Local Python environment (large; per machine) |
| `.pytest_cache/` | pytest cache |
| `__pycache__/` (in `dashboard/`, `scripts/eval/`, `src/agentshield/`, `src/agentshield/dashboard/`) | Python bytecode |
| `src/agentshield.egg-info/` | Created by `pip install -e .` |
| `dashboard_runs/` | 62 live-dashboard sandbox logs (not evaluation evidence) |
| `docs/reference/` | Course brief (.docx), D1 report (.docx), `AGENTSHIELD_D2_HANDOVER.md`, `master prompt .txt` |
| `docs/desktop.ini` | Windows/OneDrive folder metadata |

The rules also cover `venv/`, `.env`, `.vscode/` and `~$*` (Office lock files), which are not currently present.

---

## 2. Complete directory tree

Repetitive run folders are collapsed with their file pattern and count; every other file is listed. Sizes are approximate.

```
AgentShield-D2/
├── .gitignore                         310 B   (tracked, modified)
├── README.md                          766 B   (tracked, modified)
├── requirements.txt                   1.3 KB  (tracked, modified) pinned evaluation lock, Windows CPU torch
├── requirements-dashboard.txt         0.7 KB  Streamlit/Altair pins
├── pyproject.toml                     0.7 KB  package metadata, pytest config and markers
├── run_dashboard.bat                  1.1 KB  Windows dashboard launcher
├── .claude/
│   └── launch.json                    0.3 KB  Claude Code preview config (assistant tooling)
├── .streamlit/
│   └── config.toml                    0.3 KB  dashboard theme and server settings
├── configs/                                    defence configurations (hashed into run manifests)
│   ├── full.json  l1_only.json  l2_only.json  l3_only.json  unprotected.json
│   └── models.lock.json               1.1 KB  Ollama model digests and detector revision pin
├── dashboard/                                  Streamlit UI (about 93 KB)
│   ├── app.py                         2.8 KB
│   ├── components.py                  17 KB
│   ├── state.py                       1.1 KB
│   ├── view_simulator.py              22 KB
│   ├── view_results.py                33 KB
│   ├── view_explorer.py               8.5 KB
│   └── view_about.py                  8.6 KB
├── data/
│   ├── .gitkeep                       (tracked)
│   ├── demo/demo_scenarios.json       4 KB    phase-2 demo scenarios D01–D03
│   ├── pilot/pilot_scenarios.json     5 KB    pilot scenarios P01–P0x
│   └── eval/                                   FROZEN eval-v1
│       ├── FROZEN_MANIFEST.json       8 KB    sha256 744c6273…
│       ├── scenarios_v1.json          100 KB  sha256 d08a2dd7… (40 scenarios)
│       ├── scenarios_v1_draft.json    100 KB  pre-freeze source (listed in the manifest)
│       ├── detector_examples_v1.jsonl 52 KB   sha256 cb3b7afb… (120 examples)
│       ├── detector_examples_v1_draft.jsonl 52 KB  byte-identical to the frozen file (listed in the manifest)
│       └── review/
│           ├── detector_label_review.csv / .xlsx
│           ├── scenario_review.csv / .xlsx
│           └── scenario_review_round2.xlsx
├── docs/
│   ├── .gitkeep                       (tracked)
│   ├── desktop.ini                    (ignored)
│   ├── reference/                     (ignored, local only; 4 files, about 200 KB)
│   ├── D2_dashboard.md                19 KB
│   ├── D2_dashboard_validation_report.md 11 KB
│   ├── D2_dataset_audit.md            6.7 KB
│   ├── D2_dataset_review_notes.md     13 KB
│   ├── D2_dataset_review_resolution.md 21 KB  (hashed in FROZEN_MANIFEST)
│   ├── D2_final_review_validation.md  13 KB
│   ├── D2_implementation_notes.md     51 KB   running engineering log
│   ├── D2_l3_block_review.md          8 KB
│   ├── D2_phase4_continuation_plan.md 14 KB
│   ├── D2_quality_audit_findings.md   9 KB
│   ├── D2_repository_inventory.md     (this file)
│   ├── D2_results_inventory.md        15 KB   final headline numbers
│   ├── D2_review_methodology.md       4.6 KB
│   ├── D2_stage4_l3_denials.md        8 KB
│   ├── D2_stage4_r1_results.md        11 KB
│   ├── D2_stage5_q1_rep1_results.md   19 KB
│   ├── D2_stage6_s1_plan.md           3.6 KB
│   ├── D2_stage6_s1_results.md        11 KB
│   ├── figure_manifest.md             5.4 KB
│   ├── implementation_deviations.md   6.3 KB
│   ├── manual_adjudication_rubric.md  7.6 KB  (frozen scoring doc, hashed)
│   ├── report_evidence_map.md         8.5 KB
│   ├── scoring_quality_audit_plan.md  3.6 KB  (frozen scoring doc, hashed)
│   └── evidence/                               about 1.5 MB, 66 files; most folders carry SHA256SUMS.txt
│       ├── Fig_02_Ollama_Selected_Model_Running.png  Fig_03_Baseline_Tool_Calling_Run.png
│       ├── Fig_04_L1_Quarantine.png  Fig_05_L2_Isolated_Content.png
│       ├── dashboard_audit/           audit.json, SHA256SUMS.txt
│       ├── dataset_review/            4 .xlsx (round 1, MF12-completed, round 2 completed), SHA256SUMS
│       ├── final_results_draft/       consolidated_draft.json, SHA256SUMS
│       ├── final_review_a05/          A workbook, A05 override CSV, change_log.json, SHA256SUMS
│       ├── final_review_completed/    3 returned workbooks (A, C, R1 L3), SHA256SUMS
│       ├── final_review_corrected/    3 corrected workbooks, change_log.json, SHA256SUMS
│       ├── final_review_overrides/    3 override CSVs (Q1, S1 rep 3, S1 rep 4), overrides_record.json, SHA256SUMS
│       ├── final_review_package/      A workbook and key, C workbook and sample, README, REVIEWER_CHECKLIST, SHA256SUMS
│       ├── final_review_validation/   validation.json (v1), SHA256SUMS
│       ├── final_review_validation_v2/ validation.json (v2), SHA256SUMS
│       ├── l3_block_review/           Stage 2 L3 block workbook (blank and completed), blocks JSON, SHA256SUMS
│       ├── l3_block_review_r1/        l3_denials_r1.json, review workbook, reconciliation, sample, SHA256SUMS
│       ├── q1_rep1/                   analysis.json, per_scenario.csv, validation.json, SHA256SUMS
│       ├── q1_rep1_adjudication/      workbook and key, SHA256SUMS
│       ├── q1_rep1_supplementary/     interpretation_audit.json, ud04_full_denials.json, SHA256SUMS
│       ├── quality_audit/             2 reviewer workbooks, SHA256SUMS
│       └── s1/                        analysis.json, per_scenario.csv, validation.json, SHA256SUMS
├── results/                                    about 27 MB, 2,833 files (generated experimental evidence)
│   ├── .gitkeep                       (tracked)
│   ├── dataset_audit/audit_v1_draft.json        (hashed in FROZEN_MANIFEST)
│   ├── detector_eval/20261113T185711Z/          detector_metrics.json, detector_scores.jsonl, run_manifest.json
│   ├── figures/Fig_01_AgentShield_Architecture.png   292 KB
│   ├── phase2_smoke/20261113/                   15 jsonl (D01–D03 × 5 configs)
│   ├── phase2_smoke/20261113_post_D6/           15 jsonl
│   ├── pilot/20261113T122447Z … 20261113T130852Z/   5 runs, 40 files (per-model jsonl and summaries)
│   ├── runs/20261113T124719Z, …131250Z, …131423Z/   3 single-run debug logs (P03, D01×2)
│   └── eval/
│       ├── *_console.log  (16 files, 94–339 KB each): console transcripts of the reference run, R1 reps 2–10, Q1 rep 1, S1 reps 1–5
│       ├── 20261113T190040Z/                    R1 rep 1 (200-run reference)
│       │   ├── run_manifest.json  summary.json  classified_runs.csv
│       │   ├── runs/<SCENARIO>__<config>.jsonl   200 files
│       │   ├── adjudication/   4 files (key, reviewer 1/2 CSVs, export)
│       │   ├── quality_audit/  11 files (PROCESS_NOTE, sample, reviewer CSVs, stats, report, review_workbooks/)
│       │   └── supplementary/task_completion_without_recorded_attack_success.json
│       ├── R1_rep02_a1_20261113T203947Z/ … R1_rep10_a1_20261113T212212Z/   9 folders × 207 files
│       │       (run_manifest, summary, classified_runs, runs/ 200 jsonl, adjudication/ 4)
│       ├── Q1_rep01_a1_20261113T214010Z/        qwen3:4b; runs/ 200 jsonl, adjudication/ 5 (incl. manual_adjudication.csv override)
│       ├── S1_rep01 … S1_rep05_a1_20261114T03xxxxZ/   5 folders; runs/ 80 jsonl each;
│       │       adjudication/ 4–5 (manual_adjudication.csv in reps 2, 3, 4)
│       └── aggregates/
│           ├── R1_20261113T212758Z/   aggregate.json, per_scenario.csv   (validated)
│           ├── Q1_20261114T030846Z/   original (kept unchanged)
│           ├── Q1_20261114T131523Z/   validated, with finalised overrides
│           ├── S1_20261114T033648Z/   original (kept unchanged)
│           └── S1_20261114T131526Z/   validated, with finalised overrides
├── scripts/
│   ├── make_fig01_architecture.py     5 KB
│   ├── dataset/
│   │   ├── scenarios_source.py        48 KB   scenario authoring source
│   │   ├── detector_examples_source.py 19 KB
│   │   ├── build_and_audit.py         25 KB
│   │   ├── freeze_datasets.py         7.7 KB
│   │   ├── make_review_sheets.py      2.5 KB  (CSV review sheets)
│   │   ├── make_review_xlsx.py        10 KB
│   │   └── make_review_round2_xlsx.py 17 KB
│   └── eval/
│       ├── classify_l3_denials_r1.py  make_l3_block_review.py
│       ├── analyse_q1_rep1.py  q1_rep1_supplementary.py  make_q1_adjudication_workbook.py
│       ├── analyse_s1.py
│       ├── make_final_review_package.py  validate_final_reviews.py  consolidate_reviewed_results.py
│       ├── apply_review_corrections.py  write_review_overrides.py
│       └── dashboard_audit.py
├── src/
│   ├── .gitkeep                       (tracked)
│   ├── agentshield.egg-info/          (ignored)
│   └── agentshield/                            about 280 KB of source
│       ├── __init__.py  __main__.py
│       ├── detector.py      Layer 1     isolation.py   Layer 2     guard.py  scope.py   Layer 3
│       ├── agent.py  llm.py  prompts.py  tools.py  environment.py   agent and Ollama
│       ├── scenarios.py  frozen.py                                  datasets and freeze verification
│       ├── cli.py  config.py  experiments.py  evaluation.py  logging_jsonl.py   execution
│       ├── verifiers.py  outcomes.py  aggregate.py  adjudication.py  quality_audit.py  review_workbooks.py   scoring and analysis
│       └── dashboard/  __init__.py  data.py  trace.py  story.py  summary.py  live.py
├── tests/                                      23 files, about 150 KB
│   ├── .gitkeep  __init__.py  conftest.py
│   ├── fixtures/live_AS06_full_delete_first.jsonl, live_AS06_full_read_same_turn.jsonl
│   └── test_agent_loop.py  test_dashboard.py  test_datasets.py  test_detector.py  test_environment_tools.py
│       test_frozen_datasets.py  test_frozen_interface.py  test_guard.py  test_isolation.py
│       test_l3_denial_classifier.py  test_merge_reviewers.py  test_phase4_prereqs.py  test_pipeline_integration.py
│       test_review_round1.py  test_review_round2.py  test_review_workbooks.py  test_stage3_repetitions.py  test_verifiers.py
├── dashboard_runs/                    (ignored) 62 live sandbox logs, about 0.5 MB
├── .pytest_cache/                     (ignored)
└── .venv/                             (ignored) Python 3.11.9 environment
```

---

## 3. Component → file map

| # | Component | Files | Role |
|---|---|---|---|
| 1 | **Layer 1: injection detection** | `src/agentshield/detector.py` | ProtectAI DeBERTa v3 (`protectai/deberta-v3-base-prompt-injection-v2`), revision pinned in `configs/models.lock.json`; sliding-window scoring; threshold 0.5; quarantines flagged tool output |
| | | `data/eval/detector_examples_v1.jsonl`, `results/detector_eval/…` | Frozen detector test set and its standalone evaluation |
| | | `tests/test_detector.py` | Unit tests plus a `detector`-marked test needing the downloaded model |
| 2 | **Layer 2: untrusted-content isolation** | `src/agentshield/isolation.py` | Wraps untrusted tool output in labelled delimiters and neutralises delimiter spoofing |
| | | `tests/test_isolation.py` | |
| 3 | **Layer 3: tool authorisation** | `src/agentshield/guard.py` | Deny-by-default `AuthorizationGuard` for high-risk tools (send/delete) |
| | | `src/agentshield/scope.py` | `TaskScope`: what the user's request authorises (recipients, file, kind) |
| | | `tests/test_guard.py` | |
| 4 | **AI agent and Ollama integration** | `src/agentshield/agent.py` | Tool-calling loop (`run_scenario`), turn and call limits, JSONL event logging |
| | | `src/agentshield/llm.py` | Ollama client wrapper, model info and digest, timeouts |
| | | `src/agentshield/prompts.py` | Versioned system prompts (prompt hash recorded per run) |
| | | `src/agentshield/tools.py`, `environment.py` | Simulated inbox, files and outbox; tool implementations |
| | | `src/agentshield/logging_jsonl.py` | Event log writer |
| | | `configs/models.lock.json` | Pinned model digests (llama3.2:3b, qwen3:4b) and detector revision |
| 5 | **Attack scenarios and datasets** | `data/eval/scenarios_v1.json` and `FROZEN_MANIFEST.json` | Frozen 40-scenario suite (26 attack, 14 benign) and its hash manifest |
| | | `data/eval/*_draft.*`, `data/eval/review/*` | Pre-freeze sources and dataset review records (all hashed in the manifest) |
| | | `scripts/dataset/*.py` | Scenario and detector-example authoring, build/audit, freeze, review-sheet generators |
| | | `src/agentshield/scenarios.py`, `frozen.py` | Scenario model; fail-closed `verify_frozen()` |
| | | `data/demo/`, `data/pilot/` | Early demo and pilot scenarios (pre-freeze) |
| | | `tests/test_datasets.py`, `test_frozen_datasets.py`, `test_frozen_interface.py` | |
| 6 | **Experimental execution** | `src/agentshield/cli.py` | `agentshield` CLI: `build_layers`, `make_model`, eval and repetition commands |
| | | `src/agentshield/experiments.py`, `evaluation.py`, `config.py` | Run-set orchestration, manifests, config loading |
| | | `configs/*.json` | The five defence configurations |
| | | `results/eval/*`, `results/pilot`, `results/phase2_smoke`, `results/runs` | Run logs (evidence) |
| | | `tests/test_agent_loop.py`, `test_pipeline_integration.py`, `test_stage3_repetitions.py`, `test_phase4_prereqs.py`, `test_environment_tools.py` | |
| 7 | **Evaluation and statistics** | `src/agentshield/verifiers.py` | Frozen attack and legitimate-task verifiers (hashed) |
| | | `src/agentshield/outcomes.py` | Outcome classes; applies manual adjudication overrides |
| | | `src/agentshield/aggregate.py` | Cross-repetition aggregation, bootstrap CIs, paired differences |
| | | `src/agentshield/adjudication.py`, `quality_audit.py`, `review_workbooks.py` | Two-reviewer adjudication, scoring quality audit, Excel workbooks |
| | | `scripts/eval/*.py` | Stage-specific analyses (Q1, S1), L3 denial classification, final review package, validation, overrides, dashboard audit |
| | | `docs/manual_adjudication_rubric.md`, `docs/scoring_quality_audit_plan.md` | Frozen scoring documents |
| | | `results/eval/aggregates/*`, `docs/evidence/*` | Aggregates and hashed analysis evidence |
| | | `tests/test_verifiers.py`, `test_l3_denial_classifier.py`, `test_merge_reviewers.py`, `test_review_*.py` | |
| 8 | **Streamlit dashboard** | `dashboard/app.py`, `components.py`, `state.py`, `view_*.py` | UI pages: Attack Simulator, Results, Evidence Explorer, How it works |
| | | `src/agentshield/dashboard/data.py`, `trace.py`, `story.py`, `summary.py`, `live.py` | Back end: run index, trace parsing, plain-English story, workflow evidence, live runner (sandboxed to `dashboard_runs/`) |
| | | `.streamlit/config.toml`, `run_dashboard.bat`, `requirements-dashboard.txt` | Config and launcher |
| | | `scripts/eval/dashboard_audit.py`, `tests/test_dashboard.py`, `tests/fixtures/*` | Audit and 38 tests |
| 9 | **Automated tests** | `tests/` (18 test modules, `conftest.py`, `fixtures/`) | 283 tests; markers `ollama` and `detector` in `pyproject.toml` (deselect with `-m "not ollama and not detector"`) |
| 10 | **Documentation and setup** | `README.md` | Short; covers the dashboard only (no install, test or experiment instructions) |
| | | `pyproject.toml`, `requirements.txt`, `requirements-dashboard.txt` | Package, pytest config, pinned dependencies |
| | | `docs/D2_*.md`, `docs/report_evidence_map.md`, `docs/figure_manifest.md`, `docs/implementation_deviations.md` | Stage reports, methodology, inventories, evidence map |
| | | `docs/reference/` (ignored) | Brief, D1 report, handover and assistant prompt (local only) |

---

## 4. Potentially unnecessary files

### A. Essential to retain (do not remove)

- **All source and tests:** `src/agentshield/`, `dashboard/`, `tests/` (including `fixtures/`), `scripts/`.
- **Configuration:** `configs/`, `pyproject.toml`, `requirements*.txt`, `.streamlit/config.toml`, `run_dashboard.bat`, `.gitignore`.
- **Frozen data:** all of `data/eval/`, **including `*_draft.*` and `review/`**. They look like duplicates, but `FROZEN_MANIFEST.json` lists and hashes them as the freeze provenance. `detector_examples_v1_draft.jsonl` is byte-identical to the frozen file by design.
- **Experiment evidence:** all of `results/eval/` (every run set, including the original Q1 and S1 aggregates, which must stay unchanged), `results/detector_eval/`, `results/dataset_audit/` (hashed in the manifest) and `results/figures/`.
- **Documentation and evidence:** all `docs/*.md` (the rubric, audit plan and review resolution are hashed) and all of `docs/evidence/`, including the superseded-looking `final_review_validation/` (v1) and `final_results_draft/`. Those are the audit trail that `D2_final_review_validation.md` and `report_evidence_map.md` cite.

### B. Possibly unnecessary: requires team review

| Path | Why it might go | Why it might stay | Note |
|---|---|---|---|
| `results/pilot/` (40 files), `results/phase2_smoke/` (30), `results/runs/` (3) | Pre-freeze development runs, not part of R1/Q1/S1 | Cited in `D2_implementation_notes.md`, `report_evidence_map.md` and `figure_manifest.md` (phase 2 and figure evidence) | Retention recommended; small (about 0.7 MB) |
| `data/demo/`, `data/pilot/` | Pre-freeze scenarios | Inputs to the runs above; cited in notes and figure manifest | Keep if those results are kept |
| `results/eval/*_console.log` (16 files, about 3.4 MB) | Duplicate the JSONL logs; contain the local absolute path `C:\Users\<username>\OneDrive\…` | Console record of each experimental run | Privacy decision: commit as-is (shows a Windows username) or keep out of Git. Do not edit them; they are logs |
| `docs/D2_phase4_continuation_plan.md` | Historical planning document, superseded by the stage results | Shows how the plan evolved | Could move to an archive folder later |
| `scripts/dataset/make_review_sheets.py` | Early CSV sheet generator, likely superseded by `make_review_xlsx.py` | Produced `data/eval/review/*.csv` (hashed) | Keep as provenance unless the team confirms it is unused |
| `.claude/launch.json` | Assistant tooling (Claude Code preview config) | Harmless; documents how the dashboard is launched | Decide: commit, or add `.claude/` to `.gitignore` |
| `dashboard_runs/` (ignored, 62 files) | Live demo sandbox; not evidence | `D2_dashboard.md` §11 discusses one AS06 log, now copied into `tests/fixtures/` | Already ignored; local deletion optional |
| `docs/reference/` (ignored) | Contains `AGENTSHIELD_D2_HANDOVER.md` and `master prompt .txt` (assistant context) plus the brief and D1 report | Needed locally for writing the report | Keep ignored. Share the brief and D1 report with the team outside Git if needed |
| `README.md` project-board link | Points to a personal GitHub project board | Team tracking | Confirm the board is shared with all five members |

### C. Safe-to-remove candidates (regenerable, all already ignored or trivial)

| Path | Why it is safe |
|---|---|
| `__pycache__/` folders (4) | Bytecode, regenerated automatically; ignored |
| `.pytest_cache/` | Test cache; ignored |
| `src/agentshield.egg-info/` | Regenerated by `pip install -e .`; ignored |
| `docs/desktop.ini` | Windows/OneDrive metadata; ignored |
| `data/.gitkeep`, `docs/.gitkeep`, `results/.gitkeep`, `src/.gitkeep`, `tests/.gitkeep` | Tracked placeholders; redundant once the folders' real contents are committed |

`.venv/` is also regenerable but is the working environment. Each member creates their own; it is never committed.

---

## 5. Observations for a five-member Git workflow

### Critical: fix before the first real commit

1. **Line endings will break the frozen-hash checks.**
   - `verify_frozen()` and the evidence `SHA256SUMS.txt` files hash raw bytes.
   - The repository has `core.autocrlf=true` and **no `.gitattributes`**.
   - The files currently have a mix of line endings:
     - frozen JSON, `verifiers.py` and the rubric are LF;
     - `results/dataset_audit/audit_v1_draft.json` and `data/eval/review/scenario_review.csv` are CRLF;
     - `detector_label_review.csv` and 12 other CSV/MD files have mixed endings;
     - 193 text files are CRLF in total.
   - When committed, Git normalises CRLF to LF. On checkout:
     - a Windows member with the default `autocrlf=true` gets CRLF in every text file;
     - a macOS or Linux member gets LF.

     Either way some hashed files change bytes, `verify_frozen()` fails closed, and tests, experiments and the dashboard stop working on teammates' machines.
   - Git already warns about this: "LF will be replaced by CRLF the next time Git touches it".
   - **A `.gitattributes` that stores `data/`, `results/`, `docs/evidence/`, the hashed docs and `verifiers.py` byte-for-byte (`-text`) is needed before the first commit.** Otherwise the original bytes are lost from history.
2. **All D2 work (about 3,150 files) is uncommitted, on one OneDrive-synced laptop.**
   - There is no backup in Git yet, and authorship of the initial import still needs a decision (pending your Git-authorship review).

### Workflow risks

3. **The repository lives inside OneDrive.** OneDrive syncing `.git/` and `.venv/` can corrupt objects, lock files during Git operations and create `desktop.ini` files. Teammates should clone outside OneDrive.
4. **Nothing technically protects frozen artifacts.**
   - Anyone can edit `data/eval/`, `results/`, `verifiers.py` or the rubric.
   - There is no CI, branch protection or CODEOWNERS file.
   - A CI job running `pytest -m "not ollama and not detector"` (which includes `verify_frozen()`), plus CODEOWNERS/required review on frozen paths, would catch accidental edits.
5. **Some scripts write fixed output folders** (for example `docs/evidence/s1/`, `final_review_validation_v2/`, the aggregates). If two members rerun an analysis, they create conflicting regenerated evidence. A rule is needed: only explicitly approved reruns, and never rerun R1, Q1 or S1.
6. **Binary review workbooks** (`.xlsx` in `data/eval/review/`, `docs/evidence/`, `results/eval/*/quality_audit/review_workbooks/`) cannot be merged. Concurrent edits mean lost work, so they should be treated as write-once.
7. **The environment is Windows-specific.**
   - `requirements.txt` pins `torch==2.15.0+cpu` from the PyTorch CPU index (Windows/Linux wheels; not macOS), and Python is restricted to 3.11.
   - `run_dashboard.bat` and `.claude/launch.json` assume `.venv\Scripts`.
   - macOS members would need an alternative install route.
8. **Each member needs heavy local setup:**
   - Ollama with `llama3.2:3b` (and `qwen3:4b`), whose digests must match `configs/models.lock.json` for comparable live runs;
   - the ProtectAI detector, downloaded from Hugging Face at the pinned revision on first use.

   Tests marked `ollama` and `detector` need these. Results produced on other hardware are not comparable to the frozen runs.
9. **Documentation is fragmented.**
   - There are 20+ `D2_*.md` files with overlapping content and no index.
   - `README.md` has no install, test or experiment instructions.
   - There is no CONTRIBUTING guide, LICENSE or `.editorconfig`.
10. **Personal data in files.**
    - The console logs contain the local Windows username path.
    - The review workbooks contain reviewer names (expected).
    - Commit metadata will carry each member's Git e-mail. Each member should decide whether to use a GitHub no-reply address.
11. **The remote is a personal-account repository.** The four other members need collaborator access. Branch protection and visibility (public or private) were not checked; that would need GitHub access.
12. **Repository size is fine.** About 31 MB and about 3,150 files is well within GitHub limits; no Git LFS is needed. But the first import commit will be large and hard to review on GitHub.

---

## 6. Information needed before planning the workflow

1. The four other members' **GitHub usernames**, and whether each already has collaborator access.
2. Each member's **OS** (Windows/macOS) and whether they will run Ollama, the detector or experiments locally, or only edit docs, dashboard and code.
3. **How the pre-Git work should be attributed.** For example: a single import commit with `Co-authored-by` trailers for all five, versus a series of component commits. This is part of your pending authorship review.
4. Whether the **repository is or will be public or private**, and the course rules on publishing the D1 report, the brief, reviewer names and console logs.
5. Decisions on the section 4B items: commit `.claude/`? commit the console logs? keep the pilot and smoke results?
6. The desired **review rules**: PRs required? how many approvals? who can merge to `main`? protection for frozen paths?
7. The **deadline and remaining deliverables** (final report, presentation, viva demo), so branches can follow the work still to do.
8. Whether the existing **GitHub Project board** will remain the task tracker.
