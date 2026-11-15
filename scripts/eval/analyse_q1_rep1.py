"""Validate and analyse Q1 repetition 1 (qwen3:4b), and compare it descriptively with llama3.2:3b R1.
Read-only on every run log, manifest and summary. Nothing is re-classified with new rules: outcome classes come
from the frozen classifier (classified_runs.csv written by postprocess); Layer 3 denials are listed with the same
provisional rule draft used for R1 (scripts/eval/classify_l3_denials_r1.py), NOT finalised.

    .venv\\Scripts\\python scripts\\eval\\analyse_q1_rep1.py

Writes (new folder, never overwritten):
  docs/evidence/q1_rep1/validation.json   completeness, integrity, stop reasons, timing, runtime gate
  docs/evidence/q1_rep1/analysis.json     per-config counts, per-scenario outcomes, L1/L3 detail, Llama comparison
  docs/evidence/q1_rep1/per_scenario.csv  scenario x config outcome table (Qwen rep 1) with Llama R1 attempt counts
  docs/evidence/q1_rep1/SHA256SUMS.txt
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "eval"))

import classify_l3_denials_r1 as C  # noqa: E402
from agentshield import experiments as X  # noqa: E402
from agentshield.frozen import load_frozen_suite, verify_frozen  # noqa: E402
from agentshield.verifiers import detect_attack_attempt  # noqa: E402

OUT = ROOT / "docs" / "evidence" / "q1_rep1"
CONFIGS = list(X.CONFIG_NAMES)
ATTEMPTED = {"succeeded", "blocked_l3", "not_executed_invalid_call", "not_executed_call_limit", "attempted_not_succeeded"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def events(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def classified(run_set: Path) -> dict[tuple[str, str], dict]:
    with open(run_set / "classified_runs.csv", encoding="utf-8") as f:
        return {(r["scenario_id"], r["config"]): r for r in csv.DictReader(f)}


def main() -> int:
    if OUT.exists():
        print(f"REFUSED: {OUT} exists")
        return 1
    frozen = verify_frozen()
    suite = load_frozen_suite(frozen)
    q_sets = X.run_sets("Q1")
    rep1 = [s for s in q_sets if s["repetition"] == 1]
    assert len(rep1) == 1, rep1
    s = rep1[0]
    rs: Path = s["path"]
    m = s["manifest"]

    # ---------------- validation ----------------
    logs = sorted((rs / "runs").glob("*.jsonl"))
    hash_ok = {p.name: sha(p) == m["log_sha256"].get(p.name) for p in logs}
    pairs = [(sc, c) for sc in suite.scenarios for c in CONFIGS]
    random.Random(414).shuffle(pairs)
    expected_order = [f"{sc.id}__{c}" for sc, c in pairs]
    exp = X.get("Q1")
    runs = {}
    bad_meta = []
    for p in logs:
        ev = events(p)
        start = next(e for e in ev if e["event"] == "run_start")
        end = next((e for e in ev if e["event"] == "run_end"), None)
        runs[p.stem] = (start, end, ev)
        if start["model_settings"] != m["model"] or start["model_info"].get("digest") != m["model_info"]["digest"] \
                or start["suite"]["sha256"] != frozen.scenarios_sha256 or start.get("evaluation", {}).get("order_seed") != 414:
            bad_meta.append(p.stem)
    pos = {k: i + 1 for i, k in enumerate(m["order"])}
    stops = Counter(r[1]["stop_reason"] for r in runs.values())
    times = {k: r[1]["wall_time_s"] for k, r in runs.items()}
    tv = list(times.values())
    by_cfg_time = {c: round(st.median([t for k, t in times.items() if k.endswith("__" + c)]), 1) for c in CONFIGS}
    inconclusive = []
    for k, (start, end, ev) in sorted(runs.items(), key=lambda kv: pos[kv[0]]):
        if end["stop_reason"] != "final_answer" or end.get("inconclusive"):
            sid, cfg = k.split("__")
            n_model_calls = sum(1 for e in ev if e["event"] == "model_turn")
            inconclusive.append({"run": k, "order_position": pos[k], "is_attack": suite.get(sid).is_attack,
                                 "stop_reason": end["stop_reason"], "error": end.get("error"), "wall_time_s": end["wall_time_s"],
                                 "n_tool_calls_before_stop": end["n_tool_calls"], "model_turns_completed_before_stop": n_model_calls})
    cls = classified(rs)
    med = X.median_wall_time(rs)
    validation = {
        "run_set": rs.relative_to(ROOT).as_posix(),
        "status": m["status"], "complete_suite": m["complete_suite"], "attempt": m["experiment"]["attempt"],
        "started_utc": m["started_utc"], "finished_utc": m["finished_utc"],
        "n_logs": len(logs), "n_order": len(m["order"]), "distinct_pairs": len(set(m["order"])),
        "all_logs_have_run_end": all(r[1] is not None for r in runs.values()),
        "log_hashes_match_manifest": all(hash_ok.values()), "summary_hash_matches": sha(rs / "summary.json") == m["summary_sha256"],
        "order_equals_seed_414_shuffle": m["order"] == expected_order,
        "settings": m["model"], "registered_settings": exp.settings(1),
        "model_digest": m["model_info"]["digest"], "prompt": m["prompt"], "frozen_manifest_sha256": m["frozen"]["manifest_sha256"],
        "runs_with_mismatched_metadata": bad_meta,
        "frozen_verified_now": True,
        "stop_reasons": dict(stops),
        "inconclusive_runs": inconclusive,
        "n_inconclusive": len(inconclusive),
        "invalid_scenarios": [],
        "call_limit_stops": stops.get("max_tool_calls", 0),
        "manual_review_items": [r for r in csv.DictReader(open(rs / "adjudication" / "manual_adjudication_key.csv", encoding="utf-8-sig"))],
        "wall_time_s": {"mean": round(st.mean(tv), 1), "median": round(st.median(tv), 1), "p90": round(sorted(tv)[int(0.9 * len(tv)) - 1], 1),
                        "max": round(max(tv), 1), "min": round(min(tv), 1), "total_h": round(sum(tv) / 3600, 2),
                        "median_by_config": by_cfg_time,
                        "median_excluding_inconclusive": round(st.median([t for k, t in times.items() if runs[k][1]["stop_reason"] == "final_answer"]), 1)},
        "runtime_gate": {"rule": f"repetitions 2-3 only if repetition 1 is finished, complete and its median wall time per run <= {X.Q1_GATE_MEDIAN_S} s",
                         "median_s": round(med, 3), "passed": med <= X.Q1_GATE_MEDIAN_S},
    }

    # ---------------- analysis ----------------
    summ = json.loads((rs / "summary.json").read_text(encoding="utf-8"))
    per_cfg = {}
    for c in CONFIGS:
        cs = summ["configs"][c]
        per_cfg[c] = {"legit_classes": cs["legit_classes"], "attack_classes": cs["attack_classes"],
                      "legit_success": cs["legit_success_rate"]["lower"], "task_completion_without_recorded_attack_success": cs["task_completion_without_recorded_attack_success"],
                      "requested_outcome_met": cs["requested_outcome_met"],
                      "asr_bounds": {"lower": cs["asr"]["lower"], "upper": cs["asr"]["upper"]},
                      "conditional_asr_bounds": {"lower": cs["conditional_asr"]["lower"], "upper": cs["conditional_asr"]["upper"]},
                      "attempted_attack_runs": sum(cs["attack_classes"][k] for k in ATTEMPTED),
                      "prevented_by_l3": cs["prevented_by_l3"], "not_attempted_with_l1_quarantine": cs["not_attempted_with_l1_quarantine"],
                      "l1_quarantined_runs": sum(1 for (sid, cc), r in cls.items() if cc == c and r["l1_quarantined"] == "True"),
                      "l1_quarantined_scenarios": sorted(sid for (sid, cc), r in cls.items() if cc == c and r["l1_quarantined"] == "True")}
    attack_ids = [sc.id for sc in suite.scenarios if sc.is_attack]
    unprot_attempted = sorted(a for a in attack_ids if cls[(a, "unprotected")]["attack"] in ATTEMPTED)
    unprot_manual = sorted(a for a in attack_ids if cls[(a, "unprotected")]["attack"] == "manual_review")
    unprot_inconcl = sorted(a for a in attack_ids if cls[(a, "unprotected")]["attack"] == "inconclusive")
    any_attempted = sorted(a for a in attack_ids if any(cls[(a, c)]["attack"] in ATTEMPTED for c in CONFIGS))

    # Layer 3 denials (same extraction as R1; provisional rule draft only for non-attacker denials)
    denials = []
    for k, (start, end, ev) in runs.items():
        sid, cfg = k.split("__")
        sc = suite.get(sid)
        for g in (e for e in ev if e["event"] == "guard_decision" and not e["allowed"]):
            call = next(c for c in end["tool_calls"] if c["index"] == g["index"])
            prior = [{"index": c["index"], "name": c["name"], "status": c.get("status"), "arguments": c["arguments"]} for c in end["tool_calls"] if c["index"] < g["index"]]
            attack = bool(sc.is_attack and detect_attack_attempt(sc.verifier["attack"], [call], None).passed)
            d = {"scenario": sid, "config": cfg, "index": g["index"], "call": {"name": call["name"], "arguments": call["arguments"]},
                 "guard_reason": g["reason"], "attack_related": attack, "run_legitimate_success": end["legitimate_success"],
                 "run_attack_outcome": cls[(sid, cfg)]["attack"] if sc.is_attack else None}
            if not attack:
                d["provisional_category"], d["evidence"], d["flags"] = C.classify(sc, call, g["reason"], prior, end["legitimate_success"])
            denials.append(d)

    # Llama R1 (10 repetitions) per scenario x config, for descriptive comparison only (never pooled)
    r1 = sorted(X.run_sets("R1"), key=lambda x: x["repetition"])
    llama = defaultdict(lambda: {"attempted": 0, "succeeded": 0, "legit_success": 0, "n": 0})
    for x in r1:
        for key, r in classified(x["path"]).items():
            L = llama[key]
            L["n"] += 1
            L["attempted"] += r["attack"] in ATTEMPTED
            L["succeeded"] += r["attack"] == "succeeded"
            L["legit_success"] += r["legit"] == "success"
    llama_unprot = sorted(a for a in attack_ids if llama[(a, "unprotected")]["attempted"] > 0)

    rows = []
    for sc in suite.scenarios:
        row = {"scenario": sc.id, "category": sc.category, "is_attack": sc.is_attack}
        for c in CONFIGS:
            r = cls[(sc.id, c)]
            row[f"q_{c}_legit"] = r["legit"]
            row[f"q_{c}_attack"] = r["attack"] if sc.is_attack else ""
            row[f"q_{c}_l1"] = r["l1_quarantined"] == "True"
            L = llama[(sc.id, c)]
            row[f"llama_{c}_attempted_of_10"] = L["attempted"] if sc.is_attack else ""
            row[f"llama_{c}_succeeded_of_10"] = L["succeeded"] if sc.is_attack else ""
            row[f"llama_{c}_legit_of_10"] = L["legit_success"]
        rows.append(row)

    attack_table = {a: {c: cls[(a, c)]["attack"] for c in CONFIGS} for a in any_attempted + [x for x in unprot_manual + unprot_inconcl if x not in any_attempted]}
    succeeded_by_cfg = {c: sorted(a for a in attack_ids if cls[(a, c)]["attack"] == "succeeded") for c in CONFIGS}
    manual_by_cfg = {c: sorted(a for a in attack_ids if cls[(a, c)]["attack"] == "manual_review") for c in CONFIGS}
    cat = {sc.id: sc.category for sc in suite.scenarios}
    analysis = {
        "run_set": validation["run_set"],
        "unit_note": "One repetition only: each cell is a single run. Rates are descriptive; Wilson intervals treat runs as independent and are shown only as rough width indicators.",
        "per_config": per_cfg,
        "unprotected_attempted_attack_scenarios": unprot_attempted,
        "unprotected_manual_review_attack_scenarios": unprot_manual,
        "unprotected_inconclusive_attack_scenarios": unprot_inconcl,
        "attack_scenarios_attempted_in_any_config": any_attempted,
        "attack_outcomes_for_relevant_scenarios": attack_table,
        "attack_succeeded_by_config": succeeded_by_cfg,
        "attack_manual_review_by_config": manual_by_cfg,
        "scenario_categories": {a: cat[a] for a in attack_table},
        "l3_denials": denials,
        "l3_denials_summary": {"total": len(denials), "attack_related": sum(d["attack_related"] for d in denials),
                               "non_attacker": sum(not d["attack_related"] for d in denials),
                               "by_config": dict(Counter(d["config"] for d in denials)),
                               "non_attacker_provisional_categories": dict(Counter(d.get("provisional_category") for d in denials if not d["attack_related"])),
                               "non_attacker_flagged": [d for d in denials if not d["attack_related"] and d["flags"]]},
        "llama_r1": {"unprotected_attempted_attack_scenarios_any_rep": llama_unprot, "n_repetitions": len(r1)},
        "comparison": {"qwen_unprotected_attempted": len(unprot_attempted), "llama_unprotected_attempted": len(llama_unprot), "of": len(attack_ids),
                       "overlap": sorted(set(unprot_attempted) & set(llama_unprot)),
                       "qwen_only": sorted(set(unprot_attempted) - set(llama_unprot)), "llama_only": sorted(set(llama_unprot) - set(unprot_attempted))},
    }

    OUT.mkdir(parents=True)
    (OUT / "validation.json").write_text(json.dumps(validation, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "analysis.json").write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(OUT / "per_scenario.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (OUT / "SHA256SUMS.txt").write_bytes(("".join(f"{sha(p)}  {p.name}\n" for p in sorted(OUT.iterdir()) if p.name != "SHA256SUMS.txt")).encode("utf-8"))
    print(json.dumps({k: validation[k] for k in ("status", "complete_suite", "n_logs", "distinct_pairs", "log_hashes_match_manifest", "summary_hash_matches",
                                                  "order_equals_seed_414_shuffle", "runs_with_mismatched_metadata", "stop_reasons", "n_inconclusive",
                                                  "call_limit_stops", "wall_time_s", "runtime_gate")}, indent=1))
    print("manual review:", [(r["scenario_id"], r["config"]) for r in validation["manual_review_items"]])
    print(json.dumps({k: analysis[k] for k in ("unprotected_attempted_attack_scenarios", "unprotected_manual_review_attack_scenarios",
                                                "unprotected_inconclusive_attack_scenarios", "attack_scenarios_attempted_in_any_config",
                                                "attack_succeeded_by_config", "attack_manual_review_by_config", "comparison")}, indent=1))
    print(json.dumps(analysis["l3_denials_summary"], indent=1, default=str)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
