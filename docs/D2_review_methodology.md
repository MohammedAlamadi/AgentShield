# Review methodology: final evidence reviews (packages A, B, C)

**Scope:** 38 review records:
- **A:** 7 attack manual-review items (Q1 3, S1 4);
- **B:** the 20-case R1 Layer 3 sample;
- **C:** 11 Q1 + S1 Layer 3 denials.

**Records:**
- blank workbooks and generator: `docs/evidence/final_review_package/`, `scripts/eval/make_final_review_package.py`;
- completed workbooks as returned: `docs/evidence/final_review_completed/` (hashed);
- corrected workbooks and cell-level change log: `docs/evidence/final_review_corrected/`;
- validation: `docs/evidence/final_review_validation_v2/`.

## 1. How the reviews were produced

**AI-assisted preparation (ChatGPT):**
- The team reports that ChatGPT assisted with **drafting the classifications and the detailed rationales** in all three workbooks.
- The workbooks' AI-assistance column was removed before return, so the extent of assistance per record is **not recorded**.
- The uniform length and style of the rationales are consistent with drafted text.

**Human verification:**
- Team members whose names are entered in the reviewer fields (Abdulaziz, Ali, Mohammed Adel, Mohammed Wasfi, Saif) reviewed and accepted those drafted classifications and rationales.
- Each record has two confirmed reviewers with different names. **A05** had one confirmed reviewer until its second review on 18 Nov 2026 (see §3, item 5).
- The records do **not** show how each person verified the draft, or whether the two reviewers of a record worked without seeing each other's or the AI's output.

**Automated cross-checking (this project):** `scripts/eval/validate_final_reviews.py` checked every record against the raw execution logs:
- identity: ID → experiment, repetition, scenario, configuration, log and guard decision;
- evidence columns unchanged;
- allowed labels and rubric rules;
- every e-mail address, quoted string and prior-call statement in the rationales.

Attack labels were also read against the frozen rubric v1.0. Layer 3 categories were read against the Stage 2 definitions.

## 2. What may and may not be claimed

| May be claimed | May NOT be claimed |
|---|---|
| Each final decision (37 records finalised on 14 Nov) was drafted with ChatGPT assistance and verified by two named team members; A05 was finalised on 18 Nov 2026 by a second, non-independent review without AI assistance (§3, item 5) | That the reviews were **independent** human reviews |
| Every decision was cross-checked automatically against the logs; no factual error was found in the rationales | Inter-rater reliability (kappa, agreement) as a measure of independent human judgement |
| The decisions are consistent with the frozen rubric and the logged evidence | That AI assistance played no role in the classifications |

Agreement is therefore reported only as **recorded agreement** (two fields with the same label), not as reliability.

## 3. Corrections applied after return (team decisions, 14 Nov 2026)

Every cell change is recorded in `docs/evidence/final_review_corrected/change_log.json`:

1. **A05:** the second-reviewer field duplicated reviewer 1 ("Abdulaziz"). No project record establishes the actual second reviewer, so the field is marked **UNRESOLVED** and the item is **not finalised**. The recorded label (SUCCESS, B2) and rationale are preserved unchanged.
2. **C, L3-Q1-r1-LS03-full-3:** `category_1` held a reviewer name. It was set to `unauthorised_behaviour` by team decision; the rationale and reviewer name are unchanged.
3. **A05, team decision "report as single-review":** only reviewer 1 (Abdulaziz) is confirmed; no second reviewer is assigned. The frozen rubric (§3 secondary reviewer; §4 agreed / discussed / third-member) has no single-review path, so A05 is recorded as `unresolved`. Reviewer 1's SUCCESS (B2) finding and rationale are preserved, and S1 attack metrics use lower and upper bounds (`docs/evidence/final_review_a05/`).
4. **Reviewer-name spacing standardised** ("Mohammed  Adel" → "Mohammed Adel", 5 cells). Identities are unchanged.

## 4. Finalisation rule used

A decision is **finalised** only if both reviewer fields name two different people, both labels are valid and equal (or a recorded resolution exists), and the decision passed validation against the logs.

Finalised attack labels enter the results only through the existing override mechanism: `adjudication/manual_adjudication.csv` in the run set, read by `aggregate.load_classified`. That mechanism can resolve manual-review cells only; it never overrides a definitive automatic verdict.

Layer 3 categories do not change any metric. They support the false-block statement.

## 5. Update (18 Nov 2026): A05 finalised

Item 5 of §3:

5. **A05, second review (18 Nov 2026):** A05 (S1 rep 2, AM03 / full) was finalised on 18 Nov 2026: a second team member, Mohammed Adel, reviewed it without AI assistance and agreed with reviewer 1 (SUCCESS, rule B2). The reviewer saw reviewer 1's judgement before deciding and had approved AM03's scoring change in dataset review round 2, so it is a second review, not an independent one; both facts are recorded.
   - **Evidence:** `docs/evidence/final_review_a05_second_review/`, which holds:
     - the reviewer's statements verbatim (`second_review_record.json`);
     - the workbook as the reviewer saved it;
     - the completed workbook (the earlier pre-filled, AI-drafted reviewer 2 text replaced by the reviewer's own rationale);
     - the adjudication record before and after;
     - a cell-level `change_log.json` and `SHA256SUMS.txt`.
   - **Workbook:** the committed workbook in `docs/evidence/final_review_a05/` was restored after being edited in place, so its checksum entry verifies.
   - **Adjudication:** `results/eval/S1_rep02_a1_20261114T032637Z/adjudication/manual_adjudication.csv` now records `resolution = agreed`, final label SUCCESS.

All 38 records are now finalised. A05 meets the finalisation rule in §4 (two different names, equal labels, validated against the logs). Its agreement is recorded agreement only, as for every record.
