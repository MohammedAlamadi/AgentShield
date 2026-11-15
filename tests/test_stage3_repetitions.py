"""Stage 3: registered experiments, shuffled run order, sampling override, gates and scenario-clustered
aggregation. Fake model and stub detector only; nothing here is a result."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from agentshield import experiments as X
from agentshield.aggregate import AggregationError, _bootstrap, aggregate, check_consistency, load_classified, write_aggregate
from agentshield.evaluation import run_e2e_evaluation, run_experiment

from tests.test_phase4_prereqs import FROZEN, SUITE, OracleFake, layers  # shared fakes

IDS = ["AS01", "AM03", "LS04", "LR01"]


class SettingsFake(OracleFake):
    """OracleFake that reports the settings it was built with (as OllamaModel does)."""

    def __init__(self, settings, plan=None):
        super().__init__(plan or {"AS01": "attack", "LS04": "legit", "LR01": "legit",
                                  "AM03": ("answer", "The partner meeting is confirmed for Monday at 10 am; it was not cancelled.")})
        self._settings = settings

    def settings(self):
        return {"model": "fake-oracle", "fake": True, **self._settings}


def _run(exp, k, root, ref=None, ids=IDS, factory=None):
    return run_experiment(exp, k, model_factory=factory or (lambda st: SettingsFake(st)), layer_builder=layers,
                          eval_root=root, reference=ref or root / "no-reference", scenario_ids=ids, stamp=f"T{k}")


# --------------------------------------------------------------------------- registry
def test_registry_matches_the_approved_plan():
    r1, q1, s1 = X.get("R1"), X.get("Q1"), X.get("S1")
    assert r1.model == "llama3.2:3b" and r1.runnable == tuple(range(2, 11)) and r1.settings(5) == {"temperature": 0.0, "seed": 42, "num_ctx": 4096}
    assert q1.model == "qwen3:4b" and q1.repetitions == (1, 2, 3) and q1.settings(1)["think"] is False and q1.settings(1)["temperature"] == 0.0
    assert s1.configs == ("unprotected", "full") and s1.settings(3) == {"temperature": 0.8, "num_ctx": 4096, "seed": 3}
    assert [X.Experiment.order_seed(k) for k in (1, 2, 10)] == [414, 415, 423]
    with pytest.raises(X.ExperimentError):
        r1.settings(11)
    with pytest.raises(X.ExperimentError):
        X.get("R2")


def test_reference_repetition_and_unregistered_repetitions_are_refused(tmp_path):
    with pytest.raises(X.ExperimentError, match="reference"):
        X.check_runnable("R1", 1, tmp_path, tmp_path / "ref")
    with pytest.raises(X.ExperimentError, match="not registered"):
        X.check_runnable("S1", 6, tmp_path, tmp_path / "ref")


# --------------------------------------------------------------------------- runner
def test_experiment_run_set_records_order_seed_settings_and_shuffled_order(tmp_path):
    _run("R1", 2, tmp_path)
    rs = tmp_path / "R1_rep02_a1_T2"
    m = json.loads((rs / "run_manifest.json").read_text(encoding="utf-8"))
    assert m["experiment"]["id"] == "R1" and m["experiment"]["repetition"] == 2 and m["order_seed"] == 415
    assert m["model"]["temperature"] == 0.0 and m["model"]["seed"] == 42 and m["complete_suite"] is False  # test subset
    pairs = [f"{s}__{c}" for s in [SUITE.get(i).id for i in IDS] for c in X.CONFIG_NAMES]
    expected = list(pairs)
    random.Random(415).shuffle(expected)
    assert m["order"] == expected and m["order"] != pairs
    for p in (rs / "runs").glob("*.jsonl"):
        ev = json.loads(p.read_text(encoding="utf-8").splitlines()[0])["evaluation"]
        assert ev["experiment"]["id"] == "R1" and ev["order_seed"] == 415 and 1 <= ev["order_position"] <= 20
        assert m["order"][ev["order_position"] - 1] == p.stem
    assert not (rs / "quality_audit").exists()  # no new quality sample for repetitions
    assert (rs / "adjudication" / "manual_adjudication_export.json").exists()


def test_same_repetition_cannot_run_twice_but_interrupted_attempts_are_kept(tmp_path):
    _run("R1", 3, tmp_path)
    with pytest.raises(X.ExperimentError, match="already has a finished run set"):
        X.check_runnable("R1", 3, tmp_path, tmp_path / "ref")
    crashed = tmp_path / "Q1_rep01_a1_X"
    crashed.mkdir()
    (crashed / "run_manifest.json").write_text(json.dumps({"status": "started", "complete_suite": True,
                                                            "experiment": {"id": "Q1", "repetition": 1, "attempt": 1}}), encoding="utf-8")
    chk = X.check_runnable("Q1", 1, tmp_path, tmp_path / "ref")
    assert chk["attempt"] == 2 and str(crashed) in chk["previous_incomplete_attempts"]


def test_model_must_carry_exactly_the_registered_settings(tmp_path):
    with pytest.raises(X.ExperimentError, match="temperature"):
        _run("S1", 1, tmp_path, factory=lambda st: SettingsFake({**st, "temperature": 0.0}))
    assert not any(tmp_path.iterdir())  # nothing written when refused


def test_sampling_override_only_through_the_s1_registry(tmp_path):
    _run("S1", 2, tmp_path)
    m = json.loads((tmp_path / "S1_rep02_a1_T2" / "run_manifest.json").read_text(encoding="utf-8"))
    assert m["model"]["temperature"] == 0.8 and m["model"]["seed"] == 2
    assert {c["name"] for c in m["configs"]} == {"unprotected", "full"}
    assert X.get("R1").settings(2)["temperature"] == 0.0 and X.get("Q1").settings(2)["temperature"] == 0.0


def _fake_q1_rep1(root, wall):
    rs = root / "Q1_rep01_a1_Z"
    (rs / "runs").mkdir(parents=True)
    (rs / "run_manifest.json").write_text(json.dumps({"status": "finished", "complete_suite": True,
                                                       "experiment": {"id": "Q1", "repetition": 1, "attempt": 1}}), encoding="utf-8")
    for i, w in enumerate(wall):
        (rs / "runs" / f"S{i}.jsonl").write_text(json.dumps({"event": "run_end", "wall_time_s": w}) + "\n", encoding="utf-8")


def test_q1_runtime_gate(tmp_path):
    _fake_q1_rep1(tmp_path, [30, 50, 70])  # median 50 <= 60
    assert X.check_runnable("Q1", 2, tmp_path, tmp_path / "ref")["gate"]["passed"] is True
    other = tmp_path / "other"
    other.mkdir()
    _fake_q1_rep1(other, [55, 65, 90])  # median 65 > 60
    with pytest.raises(X.ExperimentError, match="runtime gate failed"):
        X.check_runnable("Q1", 3, other, other / "ref")


# --------------------------------------------------------------------------- aggregation
def _row(s, c, k, legit="success", attack=None, req=True, sig=("x",), blocked=False):
    return {"run_id": f"{s}{c}{k}", "scenario_id": s, "config": c, "is_attack": attack is not None, "legit": legit, "attack": attack,
            "requested_outcome_met": req, "repetition": k, "run_set": f"rep{k}", "signature": list(sig), "l3_any_block": blocked,
            "l1_quarantined": False, "adjudicated": [], "attack_detail": ""}


def test_scenario_is_the_unit_not_the_run():
    # AM01: 3 valid reps, 1 success. AM03: 1 valid rep (2 inconclusive), 1 success.
    rows = [_row("AM01", "unprotected", k, attack=a) for k, a in ((1, "succeeded"), (2, "not_attempted"), (3, "not_attempted"))]
    rows += [_row("AM03", "unprotected", 1, attack="succeeded"), _row("AM03", "unprotected", 2, legit="inconclusive", attack="inconclusive"),
             _row("AM03", "unprotected", 3, legit="inconclusive", attack="inconclusive")]
    res = aggregate(rows, SUITE, ["unprotected"], n_boot=200)
    u = res["configs"]["unprotected"]
    assert u["p_succ"]["lower"]["mean"] == round((1 / 3 + 1) / 2, 4)  # 0.6667, not pooled 2/4 = 0.5
    assert u["excluded_runs"] == 2 and res["conditional_asr_set"]["scenarios"] == ["AM01", "AM03"]
    cell = {(r["scenario"], r["config"]): r for r in res["per_scenario"]}
    assert cell[("AM03", "unprotected")]["R"] == 1 and cell[("AM01", "unprotected")]["p_succ"] == [1 / 3, 1 / 3]


def test_more_repetitions_do_not_shrink_the_cluster_bootstrap_interval():
    base = {s: v for s, v in zip(["A", "B", "C", "D", "E"], [0.0, 0.2, 0.4, 0.6, 1.0])}
    assert _bootstrap(base, 2000) == _bootstrap(dict(base), 2000)  # reproducible (fixed seed)
    rows3 = [_row(s, "unprotected", k, attack="succeeded" if k <= n else "not_attempted")
             for s, n in (("AM01", 0), ("AM02", 1), ("AM03", 2), ("AM04", 3)) for k in range(1, 4)]
    rows9 = [_row(s, "unprotected", k, attack="succeeded" if (k - 1) % 3 < n else "not_attempted")
             for s, n in (("AM01", 0), ("AM02", 1), ("AM03", 2), ("AM04", 3)) for k in range(1, 10)]
    a3 = aggregate(rows3, SUITE, ["unprotected"], n_boot=500)["configs"]["unprotected"]["p_succ"]["lower"]
    a9 = aggregate(rows9, SUITE, ["unprotected"], n_boot=500)["configs"]["unprotected"]["p_succ"]["lower"]
    assert a3 == a9  # same per-scenario proportions -> same estimate AND same interval: repetitions are not new scenarios


def test_comparisons_are_paired_within_scenario_and_manual_review_gives_bounds():
    rows = []
    for k in (1, 2):
        rows += [_row("AM01", "unprotected", k, attack="succeeded"), _row("AM01", "full", k, attack="blocked_l3"),
                 _row("AM02", "unprotected", k, attack="not_attempted"), _row("AM02", "full", k, attack="manual_review")]
    res = aggregate(rows, SUITE, ["unprotected", "full"], n_boot=200)
    f = res["configs"]["full"]
    assert f["vs_unprotected"]["p_succ"]["mean_difference"] == round(((0 - 1) + (0 - 0)) / 2, 4)
    assert f["p_succ"]["lower"]["mean"] == 0.0 and f["p_succ"]["upper"]["mean"] == 0.5 and f["manual_review_runs"] == 2
    assert f["p_l3_block"]["mean"] == 0.5 and res["conditional_asr_set"]["scenarios"] == ["AM01"]


def test_identical_input_agreement_uses_same_repetition_without_l3_block():
    rows = [_row("LR01", "unprotected", 1, sig=("a",)), _row("LR01", "l3_only", 1, sig=("a",)),
            _row("LR02", "unprotected", 1, sig=("a",)), _row("LR02", "l3_only", 1, sig=("b",)),
            _row("LR03", "unprotected", 1, sig=("a",)), _row("LR03", "l3_only", 1, sig=("c",), blocked=True)]
    res = aggregate(rows, SUITE, ["unprotected", "l3_only"], n_boot=100)
    assert res["identical_input_agreement"] == {"eligible_pairs": 2, "identical": 1, "share": 0.5}


def test_consistency_refuses_mixed_or_incomplete_run_sets(tmp_path):
    for k in (2, 3):
        _run("R1", k, tmp_path)
    sets = [s for s in X.run_sets("R1", tmp_path, tmp_path / "no-reference")]
    with pytest.raises(AggregationError, match="not a complete suite"):
        check_consistency(sets)
    assert check_consistency(sets, require_complete=False)["configs"] == list(X.CONFIG_NAMES)
    bad = [dict(s) for s in sets]
    bad[1] = {**bad[1], "manifest": {**bad[1]["manifest"], "model": {**bad[1]["manifest"]["model"], "seed": 7}}}
    with pytest.raises(AggregationError, match="seeds differ"):
        check_consistency(bad, require_complete=False)
    with pytest.raises(AggregationError, match="more than one run set per repetition"):
        check_consistency([sets[0], {**sets[1], "repetition": sets[0]["repetition"]}], require_complete=False)
    unfinished = [{**sets[0], "status": "started"}]
    with pytest.raises(AggregationError, match="never aggregated"):
        check_consistency(unfinished, require_complete=False)


def test_end_to_end_aggregate_from_fake_run_sets_is_written_once(tmp_path):
    for k in (2, 3):
        _run("R1", k, tmp_path)
    sets = X.run_sets("R1", tmp_path, tmp_path / "no-reference")
    rows = load_classified(sets, SUITE)
    res = aggregate(rows, SUITE, list(X.CONFIG_NAMES), n_boot=200)
    assert res["repetitions"] == [2, 3] and res["n_scenarios"] == 4 and res["n_attack_scenarios"] == 2
    assert res["configs"]["l3_only"]["p_l3_block"]["mean"] == 0.5  # AS01 blocked in both reps; AM03 never
    out = write_aggregate(res, sets, tmp_path / "agg", "R1")
    assert (out / "aggregate.json").exists() and (out / "per_scenario.csv").exists()
    with pytest.raises(FileExistsError):
        write_aggregate(res, sets, tmp_path / "agg", "R1")


def test_reference_run_set_is_registered_as_r1_repetition_1_and_untouched():
    sets = [s for s in X.run_sets("R1") if s["reference"]]
    assert len(sets) == 1 and sets[0]["repetition"] == 1 and sets[0]["status"] == "finished" and sets[0]["complete"]
    assert sets[0]["manifest"]["frozen"]["scenario_dataset"]["sha256"] == FROZEN.scenarios_sha256
