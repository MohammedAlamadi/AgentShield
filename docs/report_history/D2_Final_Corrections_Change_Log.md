# D2 Final Corrections: Change Log (18 Nov 2026)

**Report:** `AgentShield_D2_Final_Report_REVISED.docx` (SHA-256 `4bd5719b…`) and `.pdf` (`b1ce3f22…`), rebuilt from `report_draft/work_rev/`.

**Previous version:** docx `7ae9751f…`, pdf `ab5fcf7a…`. A copy of it and of the sources is kept in the session scratchpad (`before_final/`).

**Checklist:** `D2_Final_Proofreading_Findings.md`.

**Unchanged:** source code, frozen datasets (`scenarios_v1.json` still `d08a2dd7…`), results, logs and GitHub. Nothing was committed or pushed.

## Layout

| | Before | After |
|---|---|---|
| Pages | 20 | 20 |
| Where the references start | About 40% of the way down page 19 (left column) | About 60% of the way down page 19 (left column) |
| Body (excluding references) | Under 19 pages | Under 19 pages; well within the 15–20 page limit |

- Figures 1–7 and Tables I–XVIII stay numbered in order of first citation, and all 33 references are cited.
- D1 sentences kept verbatim (strict count): 136 of 200 before, 136 of 200 after.

## 1. Methodology statements (blind authoring)

| Where | Change |
|---|---|
| III-D | D1's "Scenarios were created without considering the Layer 3 rules … and vice versa" is replaced. The new text says: the scenarios were developed from the D1 attack categories after the defences were implemented, with AI assistance and with knowledge of how the three layers work; team review corrected the scoring and verification logic; the requests, scopes, attacker texts, objectives, attack styles and categories are identical in the first review sheet and in the frozen dataset; neither llama3.2:3b nor qwen3:4b was run on an evaluation scenario before the freeze; the scenarios were unchanged through every evaluation run. Kept from D1: "remained unchanged after the freeze, through every evaluation run, meaning that the rules are not specifically designed for the scenarios". Added: "The reverse cannot be claimed, so scenario-selection bias is possible (Section VI-J)." The D1 sentence "Attacks were intentionally selected…" is unchanged. |
| VI-J | "blind authoring and freezing" → "team review and freezing". A new sentence states AI-assisted authoring after the defences, by authors who knew each layer, and that scenario-selection bias cannot be excluded. |
| Table VII | New row: "Blind authoring and freezing" → "AI-assisted authoring after the defences; team review and freezing" → "Possible scenario-selection bias (Section VI-J)". |

Evidence:
- **Fields unchanged from review to freeze:** a diff of `data/eval/review/scenario_review.csv` against `scenarios_v1.json`. Only the expected-outcome text (LS04, IL04, UD04, RA01, RA05) and the attack checks (RA05, AM02) differ.
- **No model run before the freeze:** the only pre-freeze model runs used pilot scenario P03 and demo scenario D01.

## 2. A1–A13 (all resolved)

| # | Section | Before → after |
|---|---|---|
| A1 | VIII | "…test, document and present AgentShield" → "…test and document AgentShield, and will present it together" |
| A2 | VI-J | See §1 |
| A3 | VI-A | "(5, 3 and 7 of 9)" → "(5 of 9, 3 of 8 and 7 of 9)" |
| A4 | Table III | "…identical in all configurations" → "…; Layer 2 appends its isolation instruction" |
| A5 | III-E | `verify_frozen()` runs "before and after each run" → "before and after each run set and each live dashboard run" |
| A6 | VI-E | "got through every configuration" → "got through the full defence" |
| A7 | IV-F, V-I | IV-F now says the 279 tests that need neither Ollama nor the detector model passed on a fresh clone of the final repository. V-I distinguishes those 279 from the 283 tests (including a real Ollama run) passed on the development machine, and says the frozen-data hashes and all 2,681 run-manifest hashes were re-verified, instead of "all frozen and recorded hashes" |
| A8 | VI-A | "…both of them answer manipulation, which Layer 3 does not inspect (4 of 26 under sampling)" |
| A9 | VI-J | "confirmed each of these limitations" → "confirmed the limitations it could test" |
| A10 | Fig. 7 | Figure captions are now kept on one block (`keepLines`, applied in the build script to all figures). Fig. 7 is placed after the VI-H paragraph, so it and its caption sit together on page 17 |
| A11 | V-H | "(61–77 s) are dominated by generation time and timeouts" → "(61–77 s, excluding timed-out runs) are dominated by generation time" |
| A12 | Table XI, V-H, VI-G | 0.502 → 0.503 (three places) and 0.652 → 0.653 (exact ties now rounded up consistently) |
| A13 | IV-A | "about 20 modules" → "about 30 modules" |

## 3. B1–B7

| # | Status | Action |
|---|---|---|
| B1 | **Resolved by disclosure** | V-F: the live log is "a demonstration record kept outside the project repository and separately from the experiment run sets". III opening: "every reported **experimental** number comes from…" (the live-run counts are not experimental results). Nothing claims the live logs or screenshots are committed. |
| B2 | **Resolved** | Covered by §1. |
| B3 | **Open (team decision)** | "All Members" kept. No individual responsibilities were invented. |
| B4 | **Resolved** (unsupported claim removed) | II opening: "Each D1 source was rechecked," deleted. There is no record of a full re-check. The DRIFT venue update and the four new sources remain. |
| B5 | **Resolved** (corrected) | The 200-run reference run (19:00 UTC, 13 Nov) predates `experiments.py` (written 20:33 UTC). Its settings were fixed in `configs/*.json`. New text: "fixed in configuration files or registered in code (`src/agentshield/experiments.py`) before the corresponding runs". |
| B6 | **Resolved** (corrected) | The deviation log holds only the first seven rows of Table VII. New text: "The first seven are recorded in the project's deviation log; the others are documented in the evaluation plans and review records, and the last was identified in the final review of this report." |
| B7 | **Checked; no change needed; one item open** | Nasr et al. [30] is listed in the USENIX Security 2026 programme, so the citation is correct. CaMeL [27] and Beurer-Kellner [29] still show only arXiv versions, so they stay as cited. FIDES [28] and MITRE ATLAS [4] (data release 2026.09) were not re-checked. |

## 4. Layout fixes made while verifying

- **Page 9:** Table VIII now precedes Fig. 1 in the text flow, so it fills the left column instead of leaving a gap. Numbering is unchanged.
- **Page 13:** Fig. 4 now follows the paragraph that introduces the Q1 results, which removes a column gap.

## 5. Not changed

- Section C cosmetic items and the D1 grammar fixes were not requested.
- The responsible-use clause (entry 62) is unchanged; the notice is not yet committed.

---

# Targeted corrections, round 2 (18 Nov 2026)

**Rebuilt report:** docx `cacebe2c…`, pdf `4feabf9f…`.
- 20 pages; the body still ends on page 19.
- References are numbered 1–33 in order of first use, all cited.
- D1 sentences kept verbatim: 136 of 200 (unchanged).

| Item | Original claim | Verified evidence | Correction |
|---|---|---|---|
| FIDES [28] | arXiv preprint arXiv:2505.23643, 2025 | arXiv page: the title and all nine authors match exactly (v1 29 May 2025, v2 3 Sep 2025; no journal reference). The NeurIPS 2026 virtual site lists the same paper and authors as a poster on 10 Dec 2026. | Venue updated to "in *Advances in Neural Information Processing Systems (NeurIPS)*, 2026, to be published", with the arXiv link (same format as DRIFT [26]). Pages are not available yet. |
| MITRE ATLAS [4] | "AML.T0051: LLM prompt injection. MITRE ATLAS, data release 2026.09" | GitHub `mitre-atlas/atlas-data`: release v2026.09 is genuine (15 Sep 2026; 120 techniques, 88 sub-techniques). In `dist/ATLAS.yaml` at tag v2026.09, AML.T0051 = LLM Prompt Injection, with sub-techniques .000 Direct, .001 Indirect and **.002 Triggered**. v2026.10 (later) keeps the same ID and name. | Reference unchanged (accurate). Section I's "with two sub-techniques: Direct … and Indirect …" → "whose sub-techniques include Direct (AML.T0051.000) and Indirect (AML.T0051.001) prompt injection" |
| Table III | Python 3.11.9; PyTorch 2.15.0 (CPU); Transformers 5.22.2; ollama client 0.6.3; pytest 9.2.0; Streamlit 1.67.0; Ollama 0.40.16 | See the next table | None needed |
| VIII, Table XVIII | "…test and document AgentShield, and will present it together"; "…documentation, and presentation." | Requested removal | "…test and document AgentShield."; "…evaluation and documentation." |

## Table III evidence: what was used during the experiments

The run logs do not record package versions. The evidence comes from the session's own install records.

| Item | Evidence |
|---|---|
| Python 3.11.9 | Recorded in every run log (`run_start.python`) and in each run-set manifest. |
| PyTorch 2.15.0+cpu, Transformers 5.22.2, ollama client 0.6.3, pytest 9.2.0 | The project `.venv` was created on 13 Nov at 12:13–12:17 UTC. pip reported "Successfully installed … torch-2.15.0+cpu … transformers-5.22.2 … ollama-0.6.3 … pytest-9.2.0". That list was frozen into `requirements.txt` the same day. |
| No later changes | Only two installs followed, and neither changed these packages: openpyxl (13 Nov, 14:27 UTC) and Streamlit with its dependencies (14 Nov, 13:23 UTC). All experiments ran on 13–14 Nov between 18:57 and 03:37 UTC, so Streamlit was installed after them. |
| Ollama 0.40.16 | Upgraded from 0.9.0 on 13 Nov at 12:32 UTC (`ollama --version`; `/api/version` 0.40.16 at 12:33). Recorded in `configs/models.lock.json`, and read again as 0.40.16 on 14 Nov at 21:40 UTC, after all runs. |
| Streamlit 1.67.0 | Dashboard only (pinned in `requirements-dashboard.txt`); not used in the experiments. |
| Current environment | Matches every Table III version. |

**Remaining uncertainty:** no run log records the PyTorch, Transformers or Ollama server version at run time. Those versions are inferred from the install records and the absence of any recorded change, not logged per run.

---

# Final adjustment: Table III (18 Nov 2026)

**Rebuilt report:** docx `01403274…`, pdf `8bfe3483…`.
- 20 pages; the body still ends on page 19.
- Table III stays on page 5, one row longer. Pages 16–20 are unchanged.

| Original | Evidence | Correction |
|---|---|---|
| Table III "Software" row ended with "Streamlit 1.67.0" | Streamlit was installed on 14 Nov at 13:23 UTC, after the last evaluation run (14 Nov, 03:37 UTC). It is used only by the dashboard (`requirements-dashboard.txt`). | Streamlit removed from the "Software" row. New row: "Dashboard only" → "Streamlit 1.67.0; installed after all evaluation runs and not used in them". |

**Kept as is, still accurate:**
- the table title "Execution Environment (All Evaluation Runs)", because the new row states that it is not part of the runs;
- III-B "Table III lists the environment used for every evaluation run";
- III-K "The dashboard added Streamlit (Table III)".

---

# Team review wording (18 Nov 2026)

**Rebuilt report:** docx `1f3b9d1e…`, pdf `6cf89e4b…`.
- 20 pages; the body still ends on page 19.
- Table VII now sits whole on page 9 instead of being split across pages 8 and 9.
- D1 sentences kept verbatim: 136 of 200 (unchanged).
- All review counts, unresolved cases, results and limitations are unchanged.

**Evidence basis:**
- `docs/D2_review_methodology.md`, `docs/D2_quality_audit_findings.md`, `docs/D2_l3_block_review.md`, `docs/scoring_quality_audit_plan.md` and the final review package generator.
- What they establish:
  - all five members are named reviewers;
  - each finalised case has two different named reviewers;
  - the reviewers saw the logged request, the tool calls with guard decisions, and the final answer;
  - the scoring-audit and attack-verdict workbooks hid the configuration and model;
  - ChatGPT assisted drafting;
  - independence between the reviewers is not recorded.

| Section | Before | After |
|---|---|---|
| I-F, contribution (iii) | "…where required, by recorded manual review" | "…where required, by the team's recorded manual review" |
| III-I, para. 1 | "Three review activities were carried out against a rubric frozen with the datasets." | "The team carried out three review activities against a rubric frozen with the datasets." |
| III-I, para. 2 | "The review process has documented limits. The team reports that ChatGPT assisted with drafting the classifications and rationales in all of these reviews, and two named team members then verified and accepted each decision. The workbooks do not record how independently each reviewer worked, so agreement figures are reported only as *recorded agreement*, not as inter-rater reliability." | "Team members were the human reviewers in all three activities. Each finalised case was labelled by two different named members, who examined its logged evidence (the user request, the proposed tool calls with the guard's decisions, and the final answer) against the frozen rubric and recorded the final label and rationale; the workbooks for the scoring audit and the attack verdicts did not show the configuration or the model. The team reports that ChatGPT assisted with drafting the classifications and rationales, which the two reviewers then verified and accepted. The workbooks do not record how independently each reviewer worked, so agreement figures are reported only as *recorded agreement*, not as inter-rater reliability." (The rest of the paragraph, including A05, is unchanged.) |
| III-L | "The use of AI assistance in preparing review rationales is disclosed in Section III-I because it affects how the review evidence can be interpreted." | "Section III-I describes the team's review of cases that required human judgement, including the AI assistance used to draft classifications and rationales." |
| V-C | "…the AM03 run, which manual review judged not successful." | "…the AM03 run, which the team's manual review judged not successful." |
| VI-J, internal validity | "The reviews were AI-assisted and are not independent human judgements." | "Cases that required human judgement were decided by two named team members, who verified AI-drafted classifications and rationales against the logs; the records do not show that the two reviewers worked independently, so their agreement is not reported as inter-rater reliability." |
| VIII | "…evaluated results and addressed technical challenges collectively." | "…evaluated results, reviewed the cases that required human judgement and addressed technical challenges collectively." |

**Deliberately unchanged:**
- The detector-label sentence ("each label was validated by a second member of the team. All 120 labels were confirmed."), which is D1 wording.
- The scenario-review description in III-E.
- Future work's "independent human review", which describes work not yet done.
- The disclosure of AI-assisted scenario authoring in III-D, VI-J and Table VII.

---

# A05 finalised (18 Nov 2026)

**Rebuilt report:** docx `0a91904b…`, pdf `3f96d93e…`.
- 20 pages; the body still ends on page 19.
- Pages 8, 14 and 17 were checked visually.

## Review record
Second reviewer Mohammed Adel, 18 Nov 2026:
- Label SUCCESS, rule B2, with the reviewer's own rationale (recorded verbatim).
- No AI assistance.
- The reviewer saw reviewer 1's judgement before deciding.
- The reviewer had approved AM03's scoring change in dataset review round 2.

The details come from the reviewer's statements in chat.

## Evidence (new folder `docs/evidence/final_review_a05_second_review/`, with `SHA256SUMS.txt`)
- **`second_review_record.json`:** the reviewer's statements, verbatim.
- **`A_attack_outcomes_review_as_saved_by_reviewer_2026-11-18.xlsx`:** the workbook exactly as the reviewer saved it (two cells edited in place).
- **`A_attack_outcomes_review_A05_finalised.xlsx`:** the committed workbook with row 6 completed. The pre-filled AI-drafted reviewer 2 text is replaced by the reviewer's own text.
- **`S1_rep02…__manual_adjudication_before.csv` / `_after.csv`:** the adjudication record before and after the change.
- **`change_log.json`:** every changed cell and field, with before and after.

## Files changed
- `docs/evidence/final_review_a05/A_attack_outcomes_review.xlsx` was restored to its committed version. Its `SHA256SUMS.txt` entry verifies again.
- `results/eval/S1_rep02_a1_20261114T032637Z/adjudication/manual_adjudication.csv` now records:
  - secondary reviewer Mohammed Adel, SUCCESS, B2;
  - final SUCCESS, resolution "agreed";
  - the disclosures in `review_item` and `ai_assistance`.
- New aggregate `results/eval/aggregates/S1_20261118T154119Z/`. The earlier `S1_20261114T131526Z` is kept.
- Run logs, frozen data and source code are unchanged.

## S1 Full: before → after (only S1 Full changed; Unprotected, R1 and Q1 unchanged)

| Measure | Before (A05 lower–upper) | After |
|---|---|---|
| Attack attempt | 0.077 – 0.085 | 0.085 [0.023, 0.177] |
| Attack success | 0.061 [0.008, 0.139] – 0.069 [0.008, 0.162] | 0.069 [0.008, 0.162] |
| Conditional ASR (4 scenarios) | 0.30 – 0.35 [0.00, 0.60] | 0.35 [0.00, 0.75] |
| Paired Δ attack vs Unprotected | −0.031 [−0.092, 0.015] | −0.023 [−0.085, 0.023] |
| Outcome reproducibility (Full) | 0.885 | 0.890 |
| Manual-review runs | 1 | 0 |

## Report passages changed
| Section | Change |
|---|---|
| III-I | The A05 sentences now say: 37 of 38 were finalised on 14 Nov; A05 got its second review on 18 Nov 2026 without AI assistance and agreed with reviewer 1 (SUCCESS, B2); the reviewer saw the first judgement and had approved AM03's scoring change, so this is a second review, not an independent one; all 38 records are final and S1 was re-aggregated from the unchanged logs. |
| V (opening) | Aggregate list S1_20261114T131526Z → S1_20261118T154119Z |
| V-D | "0.061 … to 0.069 …, the range reflecting the unresolved review A05" → "0.069 [0.008, 0.162], with the manual-review case A05 finalised as a success (Section III-I)"; reproducibility 0.885 → 0.890 (Full) |
| Table XIII | Column "Full (A05 lower – upper)" → "Full"; values as in the table above |
| Fig. 7 | S1 Full attack point redrawn at −0.023 [−0.085, 0.023] (`report_draft/work/make_report_figures.py`, S1 row and aggregate path); the caption clause "the S1 attack value is the A05 lower bound" removed |
| VI-J, internal validity | "A05 remains unresolved, so S1's Full figures are ranges." → "The second reviewer of A05 saw the first reviewer's judgement before deciding." |

III-G's general rule ("Where a manual review remained unresolved, the affected rate is reported as a lower and an upper bound") is kept, because it is the method.

## Not updated (source code, tests and repository docs were outside this change)
- **Dashboard code:** `src/agentshield/dashboard/data.py` still points at the old aggregate `S1_20261114T131526Z`.
- **Dashboard tests:** 4 tests in `tests/test_dashboard.py` assume A05 is unresolved and now fail. The other 32 pass and 1 is skipped.
- **Repository documents** still describe A05 as unresolved: `docs/D2_review_methodology.md`, `docs/D2_results_inventory.md`, `docs/D2_final_review_validation.md`, `docs/D2_dashboard*.md` and `docs/D2_implementation_notes.md`.
