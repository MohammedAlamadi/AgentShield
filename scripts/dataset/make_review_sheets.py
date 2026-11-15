"""Create CSV review sheets for the team's label review (D1: each label checked by a second member).

    .venv\\Scripts\\python scripts\\dataset\\make_review_sheets.py

Writes data/eval/review/detector_label_review.csv and data/eval/review/scenario_review.csv.
Open them in Excel; fill reviewer columns; return them before the datasets are frozen.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "eval" / "review"
OUT.mkdir(parents=True, exist_ok=True)
if any((OUT / n).exists() for n in ("detector_label_review.csv", "scenario_review.csv")) and "--force" not in sys.argv:
    # The CSVs are the exact content the team reviewed (round 1); never overwrite them silently.
    sys.exit("REFUSED: review CSVs already exist (round-1 review evidence). Use --force only for a NEW review round.")

det = [json.loads(l) for l in (ROOT / "data" / "eval" / "detector_examples_v1_draft.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
with (OUT / "detector_label_review.csv").open("w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "category", "proposed_label", "text", "explanation", "author", "second_reviewer_name", "agrees_with_label (Y/N)", "comment"])
    for r in det:
        w.writerow([r["id"], r["category"], r["label_name"], r["text"], r["explanation"], "draft: Claude Code (AI-assisted)", "", "", ""])

scn = json.loads((ROOT / "data" / "eval" / "scenarios_v1_draft.json").read_text(encoding="utf-8"))["scenarios"]
with (OUT / "scenario_review.csv").open("w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "category", "is_attack", "attack_style", "user_request", "trusted_scope", "attacker_text", "attacker_objective",
                "expected_legitimate_outcome", "security_success_condition", "legit_check", "attack_check",
                "second_reviewer_name", "realistic_and_correct (Y/N)", "comment"])
    for s in scn:
        w.writerow([s["id"], s["category"], s["is_attack"], s.get("attack_style", ""), s["user_request"], json.dumps(s["scope"]),
                    s.get("attacker_text", ""), s.get("attacker_objective", ""), s["expected_legitimate_outcome"], s.get("security_success_condition", ""),
                    json.dumps(s["verifier"]["legitimate"]), json.dumps(s["verifier"].get("attack", {})), "", "", ""])
print(f"wrote {OUT}")
