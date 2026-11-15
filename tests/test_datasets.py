"""Structural tests of the evaluation datasets (counts per D1, schema, loadability).
They do not run any model and say nothing about detection or attack results."""

import json
from collections import Counter
from pathlib import Path

import pytest

from agentshield.scenarios import load_suite

ROOT = Path(__file__).resolve().parents[1]
DET = ROOT / "data" / "eval" / "detector_examples_v1.jsonl"  # frozen
SCN = ROOT / "data" / "eval" / "scenarios_v1.json"  # frozen

pytestmark = pytest.mark.skipif(not DET.exists() or not SCN.exists(), reason="evaluation datasets not built")


def test_detector_counts_match_d1():
    rows = [json.loads(l) for l in DET.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert Counter(r["category"] for r in rows) == {
        "benign_ordinary": 40, "benign_challenging": 20,
        "malicious_direct_override": 12, "malicious_authority_framing": 12, "malicious_hidden_footer_markup": 12,
        "malicious_polite_paraphrased": 12, "malicious_fragmented_obfuscated": 12,
    }
    assert len({r["id"] for r in rows}) == 120
    assert all({"id", "text", "label", "category", "provenance", "explanation"} <= set(r) for r in rows)


def test_scenario_counts_match_d1_table_v():
    suite = load_suite(SCN)
    assert Counter(s.category for s in suite.scenarios) == {
        "legit_read_summarise": 6, "legit_send_reply": 5, "legit_delete": 3, "unauthorised_send": 6,
        "information_leakage": 6, "unauthorised_delete": 4, "attack_requested_action": 6, "answer_manipulation": 4,
    }
    assert sum(s.is_attack for s in suite.scenarios) == 26
    for s in suite.scenarios:
        if s.is_attack:
            assert s.attacker_text and s.attacker_objective and s.verifier.get("attack")
        assert s.verifier.get("legitimate")


def test_every_run_rebuilds_identical_state():
    suite = load_suite(SCN)
    for s in suite.scenarios:
        a, b = s.fresh_environment(), s.fresh_environment()
        assert a.snapshot() == b.snapshot() and a.initial_state_id == b.initial_state_id == s.initial_state_id
