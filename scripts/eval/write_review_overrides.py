"""Write the review override files for FINALISED attack decisions (package A) via the existing mechanism:
<run set>/adjudication/manual_adjudication.csv, read by aggregate.load_classified -> outcomes.classify, which can
resolve manual_review cells only (never a definitive automatic verdict). Logs, manifests, summary.json and
classified_runs.csv of every run set stay unchanged; an existing override file is never overwritten.

    .venv\\Scripts\\python scripts\\eval\\write_review_overrides.py

Only items with no validation issue in docs/evidence/final_review_validation_v2/validation.json are written.
A copy of every override file + hashes goes to docs/evidence/final_review_overrides/.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import openpyxl  # noqa: E402

from agentshield import experiments as X  # noqa: E402
from agentshield.adjudication import KEY_COLS  # noqa: E402

CORR = ROOT / "docs" / "evidence" / "final_review_corrected" / "A_attack_outcomes_review.xlsx"
KEY = ROOT / "docs" / "evidence" / "final_review_package" / "A_attack_outcomes_key.csv"
VAL = ROOT / "docs" / "evidence" / "final_review_validation_v2" / "validation.json"
EVID = ROOT / "docs" / "evidence" / "final_review_overrides"
COLS = list(KEY_COLS) + ["primary_reviewer", "primary_label", "primary_rule", "primary_rationale", "secondary_reviewer", "secondary_label",
                         "secondary_rule", "secondary_rationale", "final_label", "resolution", "decider", "paraphrase_note", "rubric_issue",
                         "review_item", "ai_assistance"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    if EVID.exists():
        print(f"REFUSED: {EVID} exists")
        return 1
    val = {r["item"]: r["issues"] for r in json.loads(VAL.read_text(encoding="utf-8"))["A"]}
    key = {r["item"]: r for r in csv.DictReader(open(KEY, encoding="utf-8"))}
    ws = openpyxl.load_workbook(CORR)["Attack items (blind)"]
    h = [c.value for c in ws[1]]
    by_set, skipped = defaultdict(list), {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        d = dict(zip(h, row))
        it = d["item"]
        if val[it]:
            skipped[it] = val[it]
            continue
        k = key[it]
        rs = next(s for s in X.run_sets(k["experiment"]) if s["repetition"] == int(k["repetition"]))
        src = {r["item_id"]: r for r in csv.DictReader(open(rs["path"] / "adjudication" / "manual_adjudication_key.csv", encoding="utf-8-sig"))}[k["source_item_id"]]
        assert src["run_id"] == k["run_id"]
        assert d["reviewer_1_label"] == d["reviewer_2_label"] == d["final_label"]
        by_set[rs["path"]].append({**{c: src.get(c, "") for c in KEY_COLS},
                                   "primary_reviewer": d["reviewer_1_name"], "primary_label": d["reviewer_1_label"], "primary_rule": d["reviewer_1_rule"],
                                   "primary_rationale": d["reviewer_1_rationale"], "secondary_reviewer": d["reviewer_2_name"],
                                   "secondary_label": d["reviewer_2_label"], "secondary_rule": d["reviewer_2_rule"], "secondary_rationale": d["reviewer_2_rationale"],
                                   "final_label": d["final_label"], "resolution": "agreed", "decider": "", "paraphrase_note": "", "rubric_issue": "",
                                   "review_item": f"final_review_package {it}", "ai_assistance": "ChatGPT-assisted drafting; verified by the named reviewers (docs/D2_review_methodology.md)"})
    targets = [p / "adjudication" / "manual_adjudication.csv" for p in by_set]
    if any(t.exists() for t in targets):
        raise SystemExit(f"override file already exists: {[str(t) for t in targets if t.exists()]}")
    EVID.mkdir(parents=True)
    record = {"written": [], "skipped_not_finalised": skipped}
    for p, rows in by_set.items():
        t = p / "adjudication" / "manual_adjudication.csv"
        with open(t, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLS)
            w.writeheader()
            w.writerows(rows)
        copy = EVID / f"{p.name}__manual_adjudication.csv"
        shutil.copy2(t, copy)
        record["written"].append({"run_set": p.relative_to(ROOT).as_posix(), "file": t.relative_to(ROOT).as_posix(), "sha256": sha(t),
                                  "items": [(r["review_item"].split()[-1], r["scenario_id"], r["config"], r["final_label"]) for r in rows]})
    (EVID / "overrides_record.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    (EVID / "SHA256SUMS.txt").write_bytes("".join(f"{sha(x)}  {x.name}\n" for x in sorted(EVID.iterdir())).encode())
    print(json.dumps(record, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
