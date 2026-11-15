# Final evidence-review package (before Phase 5)

Prepared 14 Nov 2026 by `scripts/eval/make_final_review_package.py` (read-only on all logs; nothing labelled).
Read `REVIEWER_CHECKLIST.md` first. All labels are **PENDING**. Two different team members review each file independently. Disclose any AI assistance.

## Files to review

| Part | File | Rows | Question per row | Status |
|---|---|---|---|---|
| **A** | `A_attack_outcomes_review.xlsx` (sheet "Attack items (blind)") | 7 = Q1 3 + S1 4 | Attack SUCCESS / NOT SUCCESS + one rubric rule (A1–C1) | pending |
| **B** | `docs/evidence/l3_block_review_r1/l3_denials_r1_review.xlsx` (sheet "Verification sample"), **existing file, not copied** | 20 (R1) | Layer 3 category: incorrect_arguments / unauthorised_behaviour / false_block | pending |
| **C** | `C_l3_q1_s1_review.xlsx` (sheet "Verification sample") | 11 of 25 = all 3 Q1 + 8 stratified S1; includes both flagged UD04 rows | same as B | pending |

**Reference material inside the files:**
- the frozen rubric v1.0 (sheet "Rubric v1.0 (frozen)" in A);
- the instructions sheet in each workbook;
- "Flagged possible false blocks" and "All 25 (provisional)" in C.

**Keys — open only after both reviewers have finished:**
- `A_attack_outcomes_key.csv` maps each item to its experiment, repetition, scenario, configuration and log.
- B and C show the configuration openly; Layer 3 categories do not depend on blinding.

**Sampling record for C:** `C_l3_q1_s1_sample.json`.
- Seed 413; quotas incorrect_arguments 6 and unauthorised_behaviour 2.
- All 25 denials are included with their evidence.

## Steps for the team

1. **Reviewer 1** fills the `reviewer_1_*` columns (A) or `reviewer_1` / `category_1` / `comment_1` (B, C) and the AI-assistance column.
2. **Reviewer 2**, a different person who has not seen reviewer 1's answers, fills the `reviewer_2_*` / `category_2` columns.
3. Leave `final_label` / `final_category` as PENDING. Then return the completed workbooks unchanged in structure (do not rename sheets or columns).
4. **After you return them**, I validate and import them, compute agreement and list disagreements for you to resolve. Only then are final labels applied, through the existing override mechanism, without changing raw logs or frozen scoring. Resolve disagreements by discussion and record the reason in `resolution_note` / `resolution`.

## What changes when the reviews are done

- **A:** the manual-review ranges collapse to single values:
  - Q1 l2_only and full attack figures, and the conditional ASR (Q1 full 0.22–0.33);
  - S1 unprotected and full attack figures (attempted unprotected scenarios 4–5 of 26).
- **B and C:** the provisional Layer 3 categories (R1 106, Q1 3, S1 22) are either confirmed or show false blocks, which feed the C3 false-block statement.

## Superseded, kept unchanged (do not fill)

- `docs/evidence/q1_rep1_adjudication/q1_manual_review_workbook.xlsx`: the same 3 Q1 runs are now items in A.
- The run sets' blinded CSV exports (`adjudication/manual_adjudication_reviewer_*.csv`): they are kept as generated records, and A replaces them for labelling.

## Not covered by this package (already complete)

- Dataset review rounds 1–2 (`docs/evidence/dataset_review/`).
- The Stage 1 scoring-quality audit (`docs/evidence/quality_audit/`).
- The Stage 2 review of the 12 reference Layer 3 blocks (`docs/evidence/l3_block_review/`).
