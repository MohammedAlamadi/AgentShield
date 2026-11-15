"""Freeze the team-approved evaluation datasets (one-time operation).

    .venv\\Scripts\\python scripts\\dataset\\freeze_datasets.py

Copies the approved drafts to the FROZEN files, records hashes, versions, approvals and evidence in
data/eval/FROZEN_MANIFEST.json, and marks the frozen files read-only.

Safety: this script REFUSES to run if any frozen file or the manifest already exists. There is no
--force. Changing a frozen dataset requires deliberately deleting the frozen files, recording a
deviation in docs/implementation_deviations.md and repeating every affected run.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "data" / "eval"
DET_DRAFT, SCN_DRAFT = EVAL / "detector_examples_v1_draft.jsonl", EVAL / "scenarios_v1_draft.json"
DET_FROZEN, SCN_FROZEN = EVAL / "detector_examples_v1.jsonl", EVAL / "scenarios_v1.json"
MANIFEST = EVAL / "FROZEN_MANIFEST.json"
VERSION = "eval-v1"
STATUS = "FROZEN 2026-11-13 - team-approved after review rounds 1-3; do not edit (see FROZEN_MANIFEST.json)"

# Hashes the team approved (detector: unchanged since review; scenarios: round-2 corrected content,
# whose only later change is the suite-level description text, verified before freezing).
APPROVED_DETECTOR_SHA256 = "cb3b7afb07dad35bc885ddb3105e5df68085ebebe2bde394546175dc7033a82d"
APPROVED_SCENARIO_CONTENT_SHA256 = "cc3455e4782cfea226ae4c0f7e101979fbeeb602d6089a6c6245972455441699"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def main() -> int:
    existing = [rel(p) for p in (DET_FROZEN, SCN_FROZEN, MANIFEST) if p.exists()]
    if existing:
        print(f"REFUSED: already frozen ({existing}). Frozen datasets are never overwritten by this script.")
        return 1

    # detector: byte-identical to the approved draft
    if sha(DET_DRAFT) != APPROVED_DETECTOR_SHA256:
        print("REFUSED: detector draft differs from the approved version")
        return 1
    det_rows = [json.loads(l) for l in DET_DRAFT.read_text(encoding="utf-8").splitlines() if l.strip()]

    # scenarios: approved content; prove that only the description differs from the approved round-2 file
    scn = json.loads(SCN_DRAFT.read_text(encoding="utf-8"))
    old_desc = ("40 end-to-end scenarios (D1 Table V). Synthetic. Independent of pilot/demo cases. "
                "Legitimate-task checks for attack scenarios measure only the user's requested outcome; harm is measured by the attack checks.")
    probe = dict(scn, description=old_desc)
    if hashlib.sha256((json.dumps(probe, indent=2, ensure_ascii=False) + "\n").encode()).hexdigest() != APPROVED_SCENARIO_CONTENT_SHA256:
        print("REFUSED: scenario draft content differs from the approved round-2 version")
        return 1

    DET_FROZEN.write_bytes(DET_DRAFT.read_bytes())
    frozen_scn = dict(scn, version=VERSION, status=STATUS)
    SCN_FROZEN.write_text(json.dumps(frozen_scn, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    review = ROOT / "data" / "eval" / "review"
    evidence = ROOT / "docs" / "evidence" / "dataset_review"
    audit = ROOT / "results" / "dataset_audit" / "audit_v1_draft.json"
    audit_data = json.loads(audit.read_text(encoding="utf-8"))
    manifest = {
        "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": VERSION,
        "status": "FROZEN",
        "datasets": {
            "detector": {"path": rel(DET_FROZEN), "sha256": sha(DET_FROZEN), "n": len(det_rows),
                         "labels": dict(Counter(r["label_name"] for r in det_rows)),
                         "categories": dict(Counter(r["category"] for r in det_rows)),
                         "frozen_from": {"path": rel(DET_DRAFT), "sha256": sha(DET_DRAFT)}},
            "scenarios": {"path": rel(SCN_FROZEN), "sha256": sha(SCN_FROZEN), "n": len(scn["scenarios"]),
                          "n_attack": sum(s["is_attack"] for s in scn["scenarios"]),
                          "categories": dict(Counter(s["category"] for s in scn["scenarios"])),
                          "initial_state_ids": audit_data["scenarios"]["initial_state_ids"],
                          "frozen_from": {"path": rel(SCN_DRAFT), "sha256": sha(SCN_DRAFT),
                                          "approved_round2_content_sha256": APPROVED_SCENARIO_CONTENT_SHA256,
                                          "only_difference": "suite-level 'description' updated to the reviewed legitimate-check policy; "
                                                             "'version' and 'status' set at freeze"}},
        },
        "scoring": {  # the verdict logic and adjudication procedures the datasets were reviewed against
            "src/agentshield/verifiers.py": sha(ROOT / "src" / "agentshield" / "verifiers.py"),
            "docs/manual_adjudication_rubric.md (v1.0)": sha(ROOT / "docs" / "manual_adjudication_rubric.md"),
            "docs/scoring_quality_audit_plan.md (v1.0)": sha(ROOT / "docs" / "scoring_quality_audit_plan.md"),
        },
        "final_audit": {"path": rel(audit), "sha256": sha(audit),
                        "invalid_scenarios": sum(not r["valid"] for r in audit_data["scenarios"]["rows"]),
                        "detector_issues": audit_data["detector"]["issues"],
                        "l3_blocks_reference_attack_by_design": sum(1 for r in audit_data["scenarios"]["rows"] if r["attack"] and r["attack"]["l3_blocks_by_design"])},
        "review_evidence": {
            "round1_detector_labels": {"path": rel(review / "detector_label_review.xlsx"), "sha256": sha(review / "detector_label_review.xlsx"),
                                       "note": "120/120 Y (MF12 completed after round 1; pre-completion copy kept in evidence)"},
            "round1_scenarios": {"path": rel(review / "scenario_review.xlsx"), "sha256": sha(review / "scenario_review.xlsx"), "note": "23 Y / 17 N"},
            "round1_sheets_as_reviewed_csv": {rel(review / n): sha(review / n) for n in ("detector_label_review.csv", "scenario_review.csv")},
            "round2_scenarios": {"path": rel(review / "scenario_review_round2.xlsx"), "sha256": sha(review / "scenario_review_round2.xlsx"),
                                 "note": "32 changed scenarios: 28 Y / 4 N (LS04, IL04, UD04, RA01)"},
            "round3_approval": "13 Nov 2026: project lead approved the corrected LS04/IL04/UD04/RA01 checks and rubric v1.0 in chat "
                               "(\"I approve the four corrected scenario checks (LS04, IL04, UD04, RA01) and manual-adjudication rubric v1.0.\")",
            "evidence_copies": {rel(p): sha(p) for p in sorted(evidence.glob("*.xlsx"))},
            "resolution_log": rel(ROOT / "docs" / "D2_dataset_review_resolution.md"),
        },
        "rules": "Frozen files are never edited. Defects found later are reported, not fixed. Any change requires a deviation entry and re-running every affected run.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for p in (DET_FROZEN, SCN_FROZEN, MANIFEST):
        os.chmod(p, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)  # read-only (Windows: read-only attribute)
    print(f"FROZEN {VERSION}: detector {manifest['datasets']['detector']['sha256']}  scenarios {manifest['datasets']['scenarios']['sha256']}")
    print(f"manifest: {rel(MANIFEST)} (read-only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
