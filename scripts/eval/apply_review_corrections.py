"""Apply the team-approved corrections to the completed review workbooks (14 Nov 2026), with a cell-level change log.

    .venv\\Scripts\\python scripts\\eval\\apply_review_corrections.py

Approved corrections:
  * A05: the second reviewer field duplicated reviewer 1 ('Abdulaziz'). No project record establishes the actual
    second reviewer, so the field is marked UNRESOLVED (no identity invented) and the item is flagged; the recorded
    label, rule and rationale are preserved unchanged.
  * C, L3-Q1-r1-LS03-full-3: category_1 held a reviewer name; set to 'unauthorised_behaviour' (team decision);
    the rationale is unchanged and the name stays in reviewer_1.
  * Reviewer-name spacing standardised (e.g. 'Mohammed  Adel' -> 'Mohammed Adel'); identities unchanged.
The pre-correction completed workbooks stay hashed in docs/evidence/final_review_completed/. Corrected copies go to
docs/evidence/final_review_corrected/ (with change_log.json and SHA256SUMS.txt) and replace the working copies.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "docs" / "evidence" / "final_review_completed"
OUT = ROOT / "docs" / "evidence" / "final_review_corrected"
WORK = {
    "A_attack_outcomes_review.xlsx": (ROOT / "docs/evidence/final_review_package/A_attack_outcomes_review.xlsx", "Attack items (blind)",
                                      ["reviewer_1_name", "reviewer_2_name"]),
    "C_l3_q1_s1_review.xlsx": (ROOT / "docs/evidence/final_review_package/C_l3_q1_s1_review.xlsx", "Verification sample", ["reviewer_1", "reviewer_2"]),
    "l3_denials_r1_review.xlsx": (ROOT / "docs/evidence/l3_block_review_r1/l3_denials_r1_review.xlsx", "Verification sample", ["reviewer_1", "reviewer_2"]),
}
A05_R2 = "UNRESOLVED - second reviewer not established (field duplicated reviewer 1 'Abdulaziz')"
A05_NOTE = (" | NOT FINALISED (14 Nov 2026): the second-reviewer field duplicated reviewer 1; no project record establishes a "
            "second independent review. Label, rule and rationale preserved as recorded; needs team confirmation.")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    if OUT.exists():
        print(f"REFUSED: {OUT} exists")
        return 1
    snap = dict(reversed(l.split("  ")) for l in (SNAP / "SHA256SUMS.txt").read_text().splitlines() if l.strip())
    for name, (path, _, _) in WORK.items():
        if sha(path) != snap[name]:
            raise SystemExit(f"{path} differs from the completed snapshot; stop")
    OUT.mkdir(parents=True)
    log = []
    for name, (path, sheet, name_cols) in WORK.items():
        wb = openpyxl.load_workbook(path)
        ws = wb[sheet]
        h = [c.value for c in ws[1]]
        col = {c: h.index(c) + 1 for c in h if c}
        for r in range(2, ws.max_row + 1):
            rid = ws.cell(r, col.get("item") or col["id"]).value

            def setv(c, new, why):
                cell = ws.cell(r, col[c])
                if cell.value != new:
                    log.append({"workbook": name, "record": rid, "column": c, "before": cell.value, "after": new, "reason": why})
                    cell.value = new
            for c in name_cols:
                v = ws.cell(r, col[c]).value
                if isinstance(v, str) and re.sub(r"\s+", " ", v).strip() != v:
                    setv(c, re.sub(r"\s+", " ", v).strip(), "reviewer-name spacing standardised (identity unchanged)")
            if name.startswith("A_") and rid == "A05":
                setv("reviewer_2_name", A05_R2, "duplicate reviewer; actual second reviewer not established in project records (team decision: do not invent)")
                note = ws.cell(r, col["resolution_note"]).value or ""
                if "NOT FINALISED" not in note:
                    setv("resolution_note", note + A05_NOTE, "flag A05 as not finalised")
            if name.startswith("C_") and rid == "L3-Q1-r1-LS03-full-3":
                setv("category_1", "unauthorised_behaviour", "category_1 held a reviewer name; corrected per team decision (rationale unchanged)")
        wb.save(OUT / name)
        shutil.copy2(OUT / name, path)
    (OUT / "change_log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "SHA256SUMS.txt").write_bytes("".join(f"{sha(p)}  {p.name}\n" for p in sorted(OUT.iterdir()) if p.name != "SHA256SUMS.txt").encode())
    for e in log:
        print(e["workbook"], e["record"], e["column"], repr(e["before"])[:60], "->", repr(e["after"])[:70])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
