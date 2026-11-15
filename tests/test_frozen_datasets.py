"""Guards for the FROZEN evaluation datasets (frozen 13 Nov 2026 after review rounds 1-3, before any
evaluation run). A failure here means a frozen artefact or the frozen scoring logic changed: that must be
recorded in docs/implementation_deviations.md and every affected run repeated - never "fixed" here."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "data" / "eval"
MANIFEST = EVAL / "FROZEN_MANIFEST.json"

FROZEN_DETECTOR_SHA256 = "cb3b7afb07dad35bc885ddb3105e5df68085ebebe2bde394546175dc7033a82d"
FROZEN_SCENARIOS_SHA256 = "d08a2dd7b71f4ce289e3212679a2ebb7fcb94d7c52253ceeb57d215fbf7b1f89"
FROZEN_MANIFEST_SHA256 = "744c62736c8fe5f67a582c8ffa41e6c1459ebc79dc1a555e25617aebb5b01102"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_frozen_files_match_recorded_hashes():
    assert sha(EVAL / "detector_examples_v1.jsonl") == FROZEN_DETECTOR_SHA256
    assert sha(EVAL / "scenarios_v1.json") == FROZEN_SCENARIOS_SHA256
    assert sha(MANIFEST) == FROZEN_MANIFEST_SHA256
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["status"] == "FROZEN" and m["version"] == "eval-v1"
    assert m["datasets"]["detector"]["sha256"] == FROZEN_DETECTOR_SHA256
    assert m["datasets"]["scenarios"]["sha256"] == FROZEN_SCENARIOS_SHA256


def test_frozen_contents_and_status():
    scn = json.loads((EVAL / "scenarios_v1.json").read_text(encoding="utf-8"))
    assert scn["version"] == "eval-v1" and scn["status"].startswith("FROZEN")
    assert len(scn["scenarios"]) == 40 and sum(s["is_attack"] for s in scn["scenarios"]) == 26
    det = [json.loads(l) for l in (EVAL / "detector_examples_v1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(det) == 120 and sum(r["label"] for r in det) == 60


def test_scoring_logic_and_procedures_are_frozen():
    """The verifier code, rubric and quality-audit plan the datasets were reviewed against."""
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key, digest in m["scoring"].items():
        path = ROOT / key.split(" ")[0]
        assert sha(path) == digest, f"{key} changed after the freeze"


def test_review_evidence_preserved():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))["review_evidence"]
    for k in ("round1_detector_labels", "round1_scenarios", "round2_scenarios"):
        assert sha(ROOT / m[k]["path"]) == m[k]["sha256"], k
    for path, digest in m["evidence_copies"].items():
        assert sha(ROOT / path) == digest, path
    for path, digest in m["round1_sheets_as_reviewed_csv"].items():
        assert sha(ROOT / path) == digest, path


def test_frozen_files_are_read_only():
    for name in ("detector_examples_v1.jsonl", "scenarios_v1.json", "FROZEN_MANIFEST.json"):
        assert not os.access(EVAL / name, os.W_OK), f"{name} is writable"


def test_freeze_script_refuses_to_overwrite():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "dataset" / "freeze_datasets.py")], capture_output=True, text=True)
    assert r.returncode == 1 and "REFUSED" in r.stdout
    assert sha(EVAL / "scenarios_v1.json") == FROZEN_SCENARIOS_SHA256


def test_frozen_scenarios_equal_approved_drafts_except_metadata():
    frozen = json.loads((EVAL / "scenarios_v1.json").read_text(encoding="utf-8"))
    draft = json.loads((EVAL / "scenarios_v1_draft.json").read_text(encoding="utf-8"))
    assert frozen["scenarios"] == draft["scenarios"]
