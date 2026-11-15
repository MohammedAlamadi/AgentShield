# Report Evidence Map

Links each D2 report section, research question and claim to concrete evidence in this repository. Only evidence that exists is marked **available**.

| Report section / claim | Evidence | Artifact | Status |
|---|---|---|---|
| Experimental setup: hardware, OS, software versions | Phase 0 audit and setup log | `docs/D2_implementation_notes.md` (Phase 0), `requirements.txt`, `configs/models.lock.json` | available |
| Setup: environment is verifiable | `python -m agentshield check` output | Command; Fig_02 | available (screenshot requested) |
| Methodology: five configurations from one code base | Config files plus loop enforcement that layers match the config | `configs/*.json`, `src/agentshield/agent.py`, `tests/test_agent_loop.py::test_config_files_define_the_five_d1_configurations` | available |
| Methodology: identical initial state per run | sha256 `initial_state_id` in each run log | `src/agentshield/environment.py`, `tests/test_environment_tools.py::test_reset_gives_identical_state_and_id` | available |
| Methodology: six-tool-call limit | Loop logic and tests | `src/agentshield/agent.py`, `tests/test_agent_loop.py` (limit tests) | available |
| Methodology: tools are simulated only | Tests showing no real file or email is touched | `tests/test_environment_tools.py` | available |
| Methodology: model pilot (D1 §III-I) and model choice | Pilot logs and summary for both models | `results/pilot/20261113T123402Z/` (valid run), `results/pilot/20261113T122447Z/` (invalid: Ollama 0.9.0 tool-parser failure); decision in implementation notes | available |
| Deviations from D1 | Deviation register | `docs/implementation_deviations.md` | available (ongoing) |
| Implementation: baseline tool calling works | Pilot P01–P03 and P05 passed for llama3.2:3b | Pilot logs; Fig_03 | available (screenshot requested) |
| Limitation: small-model reliability (P04 reply without reading the inbox; hallucinated success claim) | Pilot logs `P04.jsonl` for both models | `results/pilot/20261113T123402Z/*/P04.jsonl` | available |
| Architecture matches implementation | Generated figure + code | Fig_01, `scripts/make_fig01_architecture.py`, `src/agentshield/agent.py` | available |
| L3 rules (Table IV, reply metadata rule, one action, deny by default) | Component tests | `tests/test_guard.py`, `tests/test_pipeline_integration.py` | available (component tests only) |
| L2 delimiting + escaping | Component tests | `tests/test_isolation.py` | available |
| L1 labels, 512 limit, chunking strategy | Verified facts + tests | Implementation notes (Phase 2), `tests/test_detector.py`, deviation D4 | available |
| Layers work end to end with the real model | 15 smoke runs | `results/phase2_smoke/20261113/` | available (dev only, not evaluation) |
| Small-model behaviour: refusals and fabricated answers | Smoke and pilot logs | D01 and D03 logs, pilot attempt 3 P01 | available (indicative) |
| Tool interface and prompt frozen before evaluation (D6, D7) | Pilot attempt 4 (v1 vs v2), hash tests | `results/pilot/20261113T130844Z/`, `results/pilot/20261113T130852Z/`, `tests/test_frozen_interface.py` | available |
| Evaluation datasets prepared per D1, independently, and audited | Draft datasets, audit, review notes | `data/eval/*_v1_draft.*`, `docs/D2_dataset_audit.md`, `docs/D2_dataset_review_notes.md` | available (draft, awaiting freeze) |
| Dataset labels and scenarios reviewed by a second member (D1); findings resolved | Completed review workbooks (hashed), resolution log, regression tests | `docs/evidence/dataset_review/`, `docs/D2_dataset_review_resolution.md`, `tests/test_review_round1.py` | available (120/120 labels confirmed; rounds 1–2 plus approval) |
| Evaluation datasets frozen before any evaluation run, with approvals and hashes | Manifest, freeze script, hash tests | `data/eval/FROZEN_MANIFEST.json`, `scripts/dataset/freeze_datasets.py`, `tests/test_frozen_datasets.py` | available |
| Manual adjudication and scoring-quality audit fixed in advance | Rubric v1.0, audit plan v1.0 (hashed in the manifest) | `docs/manual_adjudication_rubric.md`, `docs/scoring_quality_audit_plan.md` | available (procedures; results in Phase 4) |
| Phase 4 tooling: frozen-only runner, outcome classes, blinded adjudication, quality-audit sampler | Code and tests (fake model only) | `src/agentshield/{frozen,evaluation,outcomes,adjudication,quality_audit}.py`, `tests/test_phase4_prereqs.py` | available (no results yet) |
| RQ1: detector precision/recall/F1/FPR | Detector run on frozen eval-v1 (120 examples) | `results/detector_eval/20261113T185711Z/` (scores, metrics, manifest with hashes) | available |
| Scoring quality of automatic verdicts (limitations) | Stage 1 audit: 40 items, ChatGPT-assisted double labelling, merged | `docs/D2_quality_audit_findings.md`, `results/eval/20261113T190040Z/quality_audit/`, `docs/evidence/quality_audit/` | available |
| Supplementary: task completion without recorded attack success | Derived from unchanged logs | `results/eval/20261113T190040Z/supplementary/` | available |
| C3: false blocks (Layer 3), investigated | Stage 2 review of 12 non-attacker blocks: 0 false blocks | `docs/D2_l3_block_review.md`, `docs/evidence/l3_block_review/` | available |
| RQ2/RQ3 with repeated measurements (R1, 10 reps, scenario-clustered) | Stage 4 | `results/eval/R1_rep*/`, `results/eval/aggregates/R1_20261113T212758Z/`, `docs/D2_stage4_r1_results.md` | available |
| Second model under D1's inconclusive rule (qwen3:4b, Q1, 1 repetition; runtime gate failed) | Stage 5 | `results/eval/Q1_rep01_a1_20261113T214010Z/`, `results/eval/aggregates/Q1_20261114T030846Z/`, `docs/evidence/q1_rep1/`, `docs/D2_stage5_q1_rep1_results.md` | available; final as 1 repetition (gate failed, team decision 14 Nov 2026); 3 manual-review items pending; 19 inconclusive |
| Q1 manual-review evidence (3 items, labels pending) and UD04 Layer 3 investigation (provisional) | Stage 5 follow-up | `docs/evidence/q1_rep1_adjudication/`, `docs/evidence/q1_rep1_supplementary/ud04_full_denials.json` | available (awaiting human review) |
| Q1 interpretation audit: explicit denominators, timeouts per configuration, MR and missing-data bounds | Stage 5 follow-up | `docs/evidence/q1_rep1_supplementary/interpretation_audit.json`, `docs/D2_stage5_q1_rep1_results.md` §1.1, §2 | available |
| Stage 6 (S1): sampling-on stability check (llama3.2:3b, unprotected + full, temperature 0.8, seeds 1–5) | Stage 6 | `results/eval/S1_rep0*_a1_*/`, `results/eval/aggregates/S1_20261114T033648Z/`, `docs/evidence/s1/`, `docs/D2_stage6_s1_plan.md`, `docs/D2_stage6_s1_results.md` | available (4 manual-review items pending) |
| Final review package (A: 7 attack items; B: R1 20-case L3 sample; C: Q1+S1 11-case L3 sample) | Pre-Phase 5 | `docs/evidence/final_review_package/` | prepared; awaiting team review |
| Consolidated results inventory (detector, R1, Q1, S1) | Pre-Phase 5 | `docs/D2_results_inventory.md` | available |
| Completed review workbooks (snapshot), validation, draft consolidation under reviewed labels | Pre-Phase 5 | `docs/evidence/final_review_completed/`, `docs/evidence/final_review_validation/`, `docs/evidence/final_results_draft/`, `docs/D2_final_review_validation.md` | draft: 3 issues need team action (A05 reviewer, LS03 category, AI disclosure) |
| Final reviewed results: corrections, AI-assisted methodology, revalidation, overrides, new aggregates | Pre-Phase 5 | `docs/evidence/final_review_corrected/`, `docs/D2_review_methodology.md`, `docs/evidence/final_review_validation_v2/`, `docs/evidence/final_review_overrides/`, `results/eval/aggregates/Q1_20261114T131523Z/`, `results/eval/aggregates/S1_20261114T131526Z/`, `docs/D2_results_inventory.md` §6 | 37/38 final; A05 unresolved single review (bounds); `docs/evidence/final_review_a05/` |
| Phase 5 dashboard (live simulator, results, evidence explorer) | Phase 5 | `dashboard/`, `src/agentshield/dashboard/`, `tests/test_dashboard.py`, `docs/D2_dashboard.md` | available (read-only on evidence; live runs sandboxed) |
| RQ2: ASR by configuration, blocked by layer | 200 runs on frozen eval-v1 | `results/eval/20261113T190040Z/` (logs, manifest, summary, classified runs) | available (raw; analysis pending) |
| RQ3: legitimate success, false blocks/quarantines, latency | Same run set | `results/eval/20261113T190040Z/` | available (raw; analysis pending) |
| C1–C5 answers | — | Phase 5 | not yet |
