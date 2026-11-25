# AgentShield D2: final reproducibility audit

**Date:** 20 Nov 2026.

**Scope:** whether someone with no access to the team's machines can:
- clone the repository, install it and run AgentShield;
- reproduce the reported evaluation metrics from the official records;
- use the dashboard.

**Evidence:** the command logs are in `docs/evidence/reproducibility_audit_20261120/`. Local user paths are replaced by `<HOME>` and `<SCRATCH>`.

**Rule followed:**
- No experiment campaign was re-run.
- No frozen dataset, run log, adjudication, verifier, configuration, defence layer, dashboard file or report was changed.
- Nothing was committed or pushed.

---

## 1. Overall verdict

| What was tested | Verdict |
|---|---|
| **Public GitHub repository as it is now** (`origin/main` = `f1a3898`) | **Partially reproducible** |
| **Working tree with the proposed fixes, once committed** (tested as an isolated copy) | **Fully reproducible** for the saved results; **operational** for new runs. A new LLM run is not guaranteed to give the same outcome, by nature |

### Public repository today
**Works:**
- Installation follows the pinned locks.
- 278 of 279 offline tests pass.
- The frozen datasets verify.
- R1 and Q1 reproduce exactly.
- Ollama and the detector work.
- The dashboard runs.

**Fails or is wrong:**
- **S1 does not reproduce the reported final numbers.** The final A05 adjudication is not on GitHub.
- **The dashboard on GitHub is the old design,** not the approved five-page version.
- **The README has no setup or reproduction steps.**
- **`python -m agentshield` fails** until the package is installed, which is undocumented.
- **One test fails on every fresh clone.**

### Working tree with the proposed fixes
Followed step by step from the new README, in a separate copy, everything passed:
- installation;
- all 279 offline tests;
- exact reproduction of R1, Q1 and the final S1;
- `agentshield check`;
- the Ollama and detector tests;
- all five dashboard pages, which show the final S1 value.

**This becomes true for GitHub only after the files in §3 are committed and pushed.**

---

## 2. Genuine fresh-clone test (public GitHub)

**Clone:** `git clone https://github.com/MohammedAlamadi/AgentShield-D2.git`, without authentication, outside the working repository, at commit `f1a3898` with 3,033 files.

**Environment:** a fresh `py -3.11 -m venv` (Python 3.11.9) on Windows 11. Nothing was copied from the working repository.

| # | Step (as documented, or as needed) | Result |
|---|---|---|
| 1 | `pip install -r requirements.txt` and `-r requirements-dashboard.txt` in a clone under a long path (the 108-character scratch folder) | **Failed** (exit 1): `OSError: [Errno 2] No such file or directory` inside `torch\include\...` and `streamlit\.agents\...`. This is the Windows 260-character path limit (`A2_install.log`) |
| 1b | Same, with the clone at a short path (`<HOME>\asr\gh`) | **OK** (exit 0); `pip check`: no broken requirements (`A2_install_shortpath.log`) |
| 2 | `python -m agentshield --help` | **Failed:** `No module named agentshield`. The README does not say to install the package. **Workaround W2:** `pip install -e . --no-deps`, using the clone's own `pyproject.toml` |
| 3 | `pytest -m "not ollama and not detector"` | **278 passed, 1 failed:** `test_frozen_files_are_read_only`. Git does not store the read-only attribute, so this fails on every clone. The hash-integrity tests passed (`A2_pytest_offline.log`) |
| 4 | Frozen-data integrity (`verify_frozen()`) | **OK:** manifest hash, dataset hashes, verifier, rubric and audit-plan hashes |
| 5 | `python -m agentshield aggregate R1`, `Q1`, `S1`, compared with the official aggregates | **R1 and Q1 exact. S1 matches only the superseded 14 Nov aggregate,** not the reported final one; see §7 (`A2_aggregate.log`) |
| 6 | `python -m agentshield check` (Ollama started locally) | **CHECK PASSED:** Ollama 0.40.16 as locked; `llama3.2:3b` and `qwen3:4b` digests OK (`A2_online.log`) |
| 7 | `pytest -m "ollama or detector"` | **4 passed** |
| 7b | `pytest -m detector` with an **empty** Hugging Face cache (`HF_HOME` set to a new folder) | **3 passed.** The detector downloaded publicly at pinned revision `90c9989b…` (715 MB, about 2 min) (`A2_detector_freshcache.log`) |
| 8 | `agentshield run --scenarios data/eval/scenarios_v1.json --id LD01 --id AS06 --config configs/full.json` | **OK:** LD01 legitimate success; AS06 legitimate success, attack not attempted (`A2_run.log`). See §7B |
| 9 | `streamlit run dashboard/app.py` with a headless browser smoke test | **All 4 pages render, 0 exceptions.** This is the **old** four-page design; the approved redesign is not on GitHub |
| 10 | Commands in the README | Only the dashboard commands existed. They work once the environment is set up, but the README did not explain how to set it up |

---

## 3. Missing or uncommitted files that prevent reproduction

Git state on the working branch `redesign/dashboard-ui`, which has not been pushed (`origin` has only `main`):
- **17 tracked files modified** before this audit, plus `README.md` modified by this audit;
- **3,338 untracked files** before this audit;
- **ignored:** `.venv/`, `dashboard_runs/` (live sandbox logs), `docs/reference/` (local D1 reference material), caches, `.claude/`.

### A. Required for the reported results (must be committed)
| File | Why |
|---|---|
| `results/eval/S1_rep02_a1_20261114T032637Z/adjudication/manual_adjudication.csv` *(tracked, modified)* | The A05 second review (18 Nov), which finalises AM03/Full in S1 rep 2. Without it, S1 reproduces conditional ASR 0.30 instead of the reported **0.35**, among 18 differing values |
| `results/eval/aggregates/S1_20261118T154119Z/` *(untracked)* | The official final S1 aggregate cited by the report and the dashboard |
| `docs/evidence/final_review_a05_second_review/` *(untracked, 7 files)* | Evidence and hashes for the A05 second review |
| `docs/D2_results_inventory.md`, `docs/D2_final_review_validation.md`, `docs/D2_review_methodology.md`, `docs/D2_implementation_notes.md` *(tracked, modified)* | They document the A05 finalisation (§7 of the results inventory) |

### B. Required for the approved dashboard (must be committed)
- **Modified, tracked:**
  - `dashboard/app.py`, `components.py`, `view_*.py`;
  - `src/agentshield/dashboard/data.py`, `story.py`;
  - `tests/test_dashboard.py`;
  - `.streamlit/config.toml`;
  - `docs/D2_dashboard.md`, `docs/D2_dashboard_validation_report.md`.
- **Untracked:** `dashboard/app_pages/`, `dashboard/assets/`, `dashboard/components_v2.py`, `dashboard/view_overview.py`, `dashboard/DESIGN_SYSTEM.md`.

### C. Produced by this audit (should be committed)
- `README.md`: setup and reproduction section.
- `scripts/eval/verify_reproduction.py`.
- `docs/REPRODUCIBILITY_AUDIT_FINAL.md` (this file).
- `docs/evidence/reproducibility_audit_20261120/`.

### D. Team decision (not needed to reproduce the results)
- **`report_draft/`** (entirely untracked): the approved D2 report, its sources, the figures (including the frozen Fig. 1 and the candidate Fig. 2) and the change logs.
  - Commit it if the report should live in the repository.
  - `report_draft/*/_pkg/` contains build temporaries.
- **`migration_kit/` (3,097 files) and `_backups/`:** temporary project material, kept as instructed. They probably should not be pushed.

---

## 4. Dependencies and environment requirements
| Requirement | Detail | Documented now? |
|---|---|---|
| **Python** | 3.11 only (`requires-python >=3.11,<3.12`) | Yes (README §1) |
| **Python packages** | Fully pinned lock in `requirements.txt`, using the CPU PyTorch index (`torch==2.15.0+cpu`), plus `requirements-dashboard.txt` (Streamlit 1.67.0). All were publicly installable on 20 Nov 2026 | Yes |
| **The package itself** | `pip install -e . --no-deps` | Yes (new) |
| **Windows path length** | Clone to a short path or enable long paths | Yes (new) |
| **Ollama** | Server 0.40.16; `llama3.2:3b` digest `a80c4f17…`, `qwen3:4b` digest `359d7dd4…` (`configs/models.lock.json`) | Yes (new). Upstream tags can move; `agentshield check` detects this |
| **Layer 1 detector** | `protectai/deberta-v3-base-prompt-injection-v2` at revision `90c9989b1a342275dd0d1a95aad283c04e075671`, about 715 MB, downloaded automatically | Yes (new) |
| **Hardware** | CPU is enough for the detector; the LLM runs in Ollama | — |
| **Platforms** | Tested on Windows 11. Linux commands are given but untested. macOS is untested, and the `+cpu` torch wheels are not published for macOS | Stated in README |
| **Hard-coded paths** | No absolute paths in `src/`, `scripts/`, `dashboard/`, `configs/` or `tests/`. Everything resolves from the repository root | — |

---

## 5. Automated test results
| Environment | Offline tests (`not ollama and not detector`) | Ollama and detector tests |
|---|---|---|
| GitHub clone | 278 passed, **1 failed** (read-only attribute) | 4 passed; 3 detector tests passed with an empty cache |
| Isolated copy with fixes, following the new README | **279 passed, 0 failed** | **4 passed** |
| Working repository | **279 passed, 0 failed** | not re-run (same code) |

---

## 6. Frozen-data integrity
- **Manifest:** `verify_frozen()` passed in all three environments. `FROZEN_MANIFEST.json` = `744c6273…`, status FROZEN, version eval-v1.
- **Datasets:**
  - `scenarios_v1.json` = `d08a2dd7…` (40 scenarios, 26 attacks);
  - `detector_examples_v1.jsonl` = `cb3b7afb…` (120 examples).
- **Scoring files:**
  - `verifiers.py` = `532ff071…`;
  - rubric = `ccffa785…`;
  - audit plan = `32cab979…`;

  all equal to the manifest.
- **Unchanged by this audit:** these hashes and all files under `data/`, `results/` and `src/`. The working-tree hashes were checked after the audit.

---

## 7. Were the official evaluation metrics reproduced exactly?

### A. Reproducing saved results from the official records: yes, exactly
**Method:** `scripts/eval/verify_reproduction.py`. It uses the same code path as `agentshield aggregate`, writes to a temporary folder and compares every value in `aggregate.json` (ignoring only the timestamp) and the bytes of `per_scenario.csv`.

| Experiment | Official aggregate | GitHub clone (today) | Working tree / isolated copy |
|---|---|---|---|
| R1: llama3.2:3b, 10 repetitions × 200 = 2,000 runs | `R1_20261113T212758Z` | **Exact** | **Exact** |
| Q1: qwen3:4b, 1 × 200 runs | `Q1_20261114T131523Z` | **Exact** | **Exact** |
| S1: llama3.2:3b sampling, 5 seeds × 80 = 400 runs | `S1_20261118T154119Z` (final) | **Not reproduced.** Reproduces `S1_20261114T131526Z`, which is superseded, exactly. Full conditional ASR 0.30 vs **0.35**; attack success 0.0615 vs **0.0692**; 18 values differ | **Exact** |

**Traceability chain (checked):**
1. Frozen scenarios (hash-verified).
2. Configuration files and model settings: temperature 0, seed 42, `num_ctx` 4096 (S1: temperature 0.8, seed = k), recorded in every run's `run_start` event, with the model digests in the lock file.
3. 2,600 original run logs: 2,000 + 200 + 400.
4. Automatic verifiers (hash-verified).
5. Manual adjudications and override files.
6. Aggregates, reproduced exactly.
7. Report claims: R1 1.00 → 0.55, Q1 1.00 → 0.22 (2 of 9), S1 0.60 → 0.35, all equal to the aggregates. The claim-to-file map is in `docs/report_evidence_map.md`.

### B. Re-running new LLM experiments: works, but outcomes are not guaranteed identical
- **What was run:** only one legitimate scenario (LD01) and one attack scenario (AS06) under Full, as a functional check.
- **AS06 result:** the attack was **not attempted** in the new run. The official R1 repetition 1 shows the attack attempted and **blocked by L3**.
- **Comparison with the records:** the new trajectory (delete the file, then an invalid `read_file` call) is identical to official R1 repetitions 3, 4, 5, 8, 9 and 10. Repetitions 1, 2, 6 and 7 show the blocked email.
- **Conclusion:** with fixed settings and model digests, the local model still varies between recorded behaviours. New runs therefore check that the system works; they do not regenerate the reported numbers. The full campaign was **not** re-run.

---

## 8. Dashboard verification
| Version | Pages | Result |
|---|---|---|
| GitHub (old design) | Attack Simulator, Results, Evidence Explorer, How it works | All render, 0 exceptions. Not the approved design |
| Working tree / isolated copy (approved five-page design) | Overview, Simulator, Results, Evidence, Methodology | All render, 0 exceptions. The Results summary shows **S1 60.0% → 35.0%** (final values) and R1 100% → 55% |

- **Earlier audit:** the dashboard audit (`scripts/eval/dashboard_audit.py`) was re-run on the final dashboard on 19 Nov. Result: 2,600 recorded runs and 90 live logs, 0 mismatches.
- **Not available after cloning:** live runs need Ollama. The 90 live sandbox logs are in the ignored `dashboard_runs/` and are not in the repository by design, because they are demonstration records, not evaluation evidence.

---

## 9. Problems found and corrections made
| # | Problem | Severity | Correction | Affects evaluation? |
|---|---|---|---|---|
| P1 | The final S1 adjudication (A05), its evidence and the final S1 aggregate are uncommitted, so GitHub reproduces the superseded S1 values | **Blocker** | None. They must be committed by the team (§3A); I do not commit | No; the records exist and reproduce exactly |
| P2 | The approved dashboard redesign is uncommitted | **Blocker for the demonstration** | None; commit §3B | No |
| P3 | The README had no installation or reproduction instructions | High | **Fixed:** new "Reproducing the results" section | No |
| P4 | `python -m agentshield` fails because the package install is undocumented | High | **Fixed:** README step `pip install -e . --no-deps` | No |
| P5 | `test_frozen_files_are_read_only` fails on every clone (Git drops the read-only attribute) | Medium | **Fixed in the documentation:** README step 2 sets the attribute (`attrib +R` / `chmod a-w`). The test was **not** changed | No; integrity is enforced by SHA-256 |
| P6 | Windows 260-character path limit breaks `pip install` under long folders | Medium | **Documented:** clone to a short path or enable long paths | No |
| P7 | No one-command way to check the official numbers; the CLI `aggregate` writes new folders into `results/` | Medium | **Added** `scripts/eval/verify_reproduction.py` (read-only, temporary output, exact comparison) | No; it reuses the aggregation code unchanged |
| P8 | Ollama model tags can change upstream; the exact digests may become unavailable | Low (inherent) | Documented; `agentshield check` reports a mismatch | Affects new runs only |
| P9 | `report_draft/D2_IEEE_Final_Dashboard_Change_Log.md` contains the word "Colab" in its content-scan sentence (stating that the report does not mention it) | Low | **Not changed**, because it is an approved document. If no trace of the cancelled experiment may remain, delete that phrase from the change log | No |

**Colab check:**
- **Repository:** no Colab files, notebooks, results or charts, whether tracked, untracked or ignored.
- **Device:** no Colab leftovers in Downloads, Desktop or Documents. The only `.ipynb` files are unrelated course notebooks. The earlier cleanup (19 Nov) stands.
- **Not Colab-related, left untouched:** `Desktop\AgentShield` (an older project copy) and `Downloads\AgentShield-main.zip`.

---

## 10. Remaining blockers and exact steps before submission
1. **Commit and push the reproduction-critical files (§3A).** Check afterwards that `git status` shows no changes under `results/` or `docs/evidence/`.
2. **Commit the approved dashboard (§3B)** and merge `redesign/dashboard-ui` into `main`, or push the branch and point reviewers to it.
3. **Commit the audit outputs (§3C)**: README, `verify_reproduction.py`, this report and its logs.
4. **Decide on `report_draft/`, `migration_kit/` and `_backups/` (§3D).** Recommendation:
   - do not push `migration_kit/` and `_backups/`;
   - push `report_draft/` only if the report sources belong in the repository, without the `_pkg/` build folders.
5. **After pushing, repeat the fresh-clone check:**
   1. clone to a short path;
   2. follow README §1–4;
   3. expect `279 passed` and `ALL OFFICIAL AGGREGATES REPRODUCED`;
   4. start the dashboard and confirm the five pages and S1 60% → 35%.
6. **Optional:** resolve P9.

**Test copies left on this PC for re-checking**, all safe to delete: `<HOME>\asr\gh` (GitHub clone), `<HOME>\asr\wt` (isolated copy with fixes), `<HOME>\asr\hf_fresh` (715 MB detector cache). Each includes a full virtual environment.
