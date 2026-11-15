"""Validate and analyse Stage 6 (S1: llama3.2:3b, unprotected + full, temperature 0.8, seeds 1-5) and compare it
descriptively with R1 (llama3.2:3b, temperature 0, 10 repetitions). Never pooled. Read-only on every log,
manifest, summary and aggregate; outcome classes come from the frozen classifier (classified_runs.csv).
Layer 3 non-attacker denials get the same PROVISIONAL rule draft as R1/Q1 (not finalised).

    .venv\\Scripts\\python scripts\\eval\\analyse_s1.py <S1 aggregate dir>

Writes (new folder, never overwritten): docs/evidence/s1/
  validation.json, analysis.json, per_scenario.csv, SHA256SUMS.txt
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

OUT = ROOT / "docs" / "evidence" / "s1"
CONFIGS = ["unprotected", "full"]
ATTEMPTED = {"succeeded", "blocked_l3", "not_executed_invalid_call", "not_executed_call_limit", "attempted_not_succeeded"}
R1_AGG = ROOT / "results" / "eval" / "aggregates" / "R1_20261113T212758Z" / "aggregate.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def events(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def classified(rs: Path) -> dict[tuple[str, str], dict]:
    with open(rs / "classified_runs.csv", encoding="utf-8") as f:
        return {(r["scenario_id"], r["config"]): r for r in csv.DictReader(f)}


def main(agg_dir: str) -> int:
    if OUT.exists():
        print(f"REFUSED: {OUT} exists")
        return 1
    frozen = verify_frozen()
    suite = load_frozen_suite(frozen)
    exp = X.get("S1")
    sets = sorted(X.run_sets("S1"), key=lambda s: (s["repetition"], str(s["path"])))
    attack_ids = sorted(s.id for s in suite.scenarios if s.is_attack)
    all_ids = sorted(s.id for s in suite.scenarios)

    # ---------------- validation ----------------
    val = {"run_sets": [], "all_ok": True}
    times_all, denials, s1cls = [], [], {}
    for s in sets:
        rs, m, k = s["path"], s["manifest"], s["repetition"]
        logs = sorted((rs / "runs").glob("*.jsonl"))
        pairs = [(sc, c) for sc in suite.scenarios for c in CONFIGS]
        random.Random(exp.order_seed(k)).shuffle(pairs)
        expected = [f"{sc.id}__{c}" for sc, c in pairs]
        stops, times, inc, bad = Counter(), [], [], []
        for p in logs:
            ev = events(p)
            start = next(e for e in ev if e["event"] == "run_start")
            end = next((e for e in ev if e["event"] == "run_end"), None)
            if end is None:
                bad.append(f"{p.stem}: no run_end")
                continue
            ms = start["model_settings"]
            if ms.get("temperature") != 0.8 or ms.get("seed") != k or ms.get("num_ctx") != 4096 or ms.get("timeout_s") != 180.0 \
                    or start["prompt_version"] != "v2" or start["suite"]["sha256"] != frozen.scenarios_sha256 \
                    or start["model_info"].get("digest") != m["model_info"]["digest"] or start["evaluation"]["order_seed"] != exp.order_seed(k):
                bad.append(f"{p.stem}: metadata mismatch")
            stops[end["stop_reason"]] += 1
            times.append(end["wall_time_s"])
            if end["stop_reason"] not in ("final_answer", "max_tool_calls") or end.get("inconclusive"):
                inc.append({"run": p.stem, "stop_reason": end["stop_reason"], "error": end.get("error"), "wall_time_s": end["wall_time_s"]})
            sid, cfg = p.stem.split("__")
            sc = suite.get(sid)
            for g in (e for e in ev if e["event"] == "guard_decision" and not e["allowed"]):
                call = next(c for c in end["tool_calls"] if c["index"] == g["index"])
                prior = [{"index": c["index"], "name": c["name"], "status": c.get("status"), "arguments": c["arguments"]} for c in end["tool_calls"] if c["index"] < g["index"]]
                attack = bool(sc.is_attack and detect_attack_attempt(sc.verifier["attack"], [call], None).passed)
                d = {"repetition": k, "scenario": sid, "config": cfg, "index": g["index"], "call": {"name": call["name"], "arguments": call["arguments"]},
                     "guard_reason": g["reason"], "attack_related": attack, "run_legitimate_success": end["legitimate_success"]}
                if not attack:
                    d["provisional_category"], d["evidence"], d["flags"] = C.classify(sc, call, g["reason"], prior, end["legitimate_success"])
                denials.append(d)
        times_all += times
        mr = list(csv.DictReader(open(rs / "adjudication" / "manual_adjudication_key.csv", encoding="utf-8-sig"))) if (rs / "adjudication" / "manual_adjudication_key.csv").exists() else []
        rec = {"run_set": rs.relative_to(ROOT).as_posix(), "repetition": k, "attempt": m["experiment"]["attempt"], "status": m["status"],
               "complete_suite": m["complete_suite"], "started_utc": m["started_utc"], "finished_utc": m.get("finished_utc"),
               "experiment_id": m["experiment"]["id"], "settings": m["model"], "order_seed": m["order_seed"], "model_digest": m["model_info"]["digest"],
               "n_logs": len(logs), "distinct_pairs": len(set(m["order"])),
               "log_hashes_match": all(sha(p) == m["log_sha256"].get(p.name) for p in logs) if m.get("log_sha256") else False,
               "summary_hash_matches": sha(rs / "summary.json") == m.get("summary_sha256"),
               "order_matches_seed": m["order"] == expected, "metadata_problems": bad,
               "stop_reasons": dict(stops), "inconclusive": inc, "call_limit_stops": stops.get("max_tool_calls", 0),
               "manual_review_items": [{"scenario": r["scenario_id"], "config": r["config"], "check": r["check"], "detail": r["verifier_detail"]} for r in mr],
               "wall_time_s": {"mean": round(st.mean(times), 2), "median": round(st.median(times), 2), "max": round(max(times), 2)}}
        ok = rec["status"] == "finished" and rec["complete_suite"] and rec["n_logs"] == 80 and rec["distinct_pairs"] == 80 and rec["log_hashes_match"] \
            and rec["summary_hash_matches"] and rec["order_matches_seed"] and not bad
        rec["ok"] = ok
        val["all_ok"] &= ok
        val["run_sets"].append(rec)
        s1cls[k] = classified(rs)
    val["repetitions_present"] = sorted(s1cls)
    val["wall_time_s_all"] = {"mean": round(st.mean(times_all), 2), "median": round(st.median(times_all), 2), "max": round(max(times_all), 2), "n": len(times_all)}

    # ---------------- per scenario (S1 vs R1) ----------------
    r1 = {x["repetition"]: classified(x["path"]) for x in X.run_sets("R1")}

    def tally(clsmap, sid, cfg):
        obs = [c[(sid, cfg)] for c in clsmap.values() if c[(sid, cfg)]["legit"] != "inconclusive"]
        a = Counter(r["attack"] for r in obs)
        lg = Counter(r["legit"] for r in obs)
        return {"n": len(obs), "attempted": sum(a[x] for x in ATTEMPTED), "succeeded": a["succeeded"], "blocked_l3": a["blocked_l3"],
                "manual_review": a["manual_review"], "not_attempted": a["not_attempted"], "legit_success": lg["success"],
                "l1_quarantined": sum(r["l1_quarantined"] == "True" for r in obs),
                "outcomes": dict(Counter(f"{r['legit']}/{r['attack'] or '-'}" for r in obs))}

    rows, per = [], {}
    for sid in all_ids:
        sc = suite.get(sid)
        for cfg in CONFIGS:
            s1t, r1t = tally(s1cls, sid, cfg), tally(r1, sid, cfg)
            per[(sid, cfg)] = (s1t, r1t)
            rows.append({"scenario": sid, "category": sc.category, "is_attack": sc.is_attack, "config": cfg,
                         **{f"s1_{k}": (json.dumps(v) if isinstance(v, dict) else v) for k, v in s1t.items()},
                         **{f"r1_{k}": (json.dumps(v) if isinstance(v, dict) else v) for k, v in r1t.items()}})
    s1_unprot_att = sorted(a for a in attack_ids if per[(a, "unprotected")][0]["attempted"] > 0)
    r1_unprot_att = sorted(a for a in attack_ids if per[(a, "unprotected")][1]["attempted"] > 0)
    s1_any_att = {cfg: sorted(a for a in attack_ids if per[(a, cfg)][0]["attempted"] + per[(a, cfg)][0]["manual_review"] > 0) for cfg in CONFIGS}
    legit_changes = []
    for sid in all_ids:
        for cfg in CONFIGS:
            s1t, r1t = per[(sid, cfg)]
            if s1t["n"] and r1t["n"]:
                d = s1t["legit_success"] / s1t["n"] - r1t["legit_success"] / r1t["n"]
                if abs(d) >= 0.5:
                    legit_changes.append({"scenario": sid, "config": cfg, "s1": f"{s1t['legit_success']}/{s1t['n']}", "r1": f"{r1t['legit_success']}/{r1t['n']}"})
    agg = json.loads((Path(agg_dir) / "aggregate.json").read_text(encoding="utf-8"))
    r1agg = json.loads(R1_AGG.read_text(encoding="utf-8"))

    def cfgsum(a, c):
        v = a["configs"][c]
        out = {k: v[k] for k in ("p_legit", "p_req", "p_tc", "p_att", "p_succ", "p_l3_block", "conditional_asr", "reproducibility_modal_agreement_mean",
                                 "excluded_runs", "manual_review_runs")}
        if "vs_unprotected" in v:
            out["vs_unprotected"] = v["vs_unprotected"]
        return out

    analysis = {
        "note": "S1 and R1 are separate experiments (temperature 0.8 seeds 1-5 vs temperature 0 seed 42, 10 reps); compared descriptively, never pooled.",
        "s1_aggregate": Path(agg_dir).resolve().relative_to(ROOT).as_posix(), "r1_aggregate": R1_AGG.relative_to(ROOT).as_posix(),
        "s1_configs": {c: cfgsum(agg, c) for c in CONFIGS}, "r1_configs": {c: cfgsum(r1agg, c) for c in CONFIGS},
        "s1_conditional_set": agg["conditional_asr_set"], "r1_conditional_set": r1agg["conditional_asr_set"],
        "unprotected_attempted_any_rep": {"s1": s1_unprot_att, "r1": r1_unprot_att, "s1_only": sorted(set(s1_unprot_att) - set(r1_unprot_att)),
                                           "r1_only": sorted(set(r1_unprot_att) - set(s1_unprot_att)), "of": len(attack_ids)},
        "s1_attempted_any_rep_incl_manual_review": s1_any_att,
        "attack_scenarios_detail": {f"{a}|{c}": {"s1": per[(a, c)][0], "r1": per[(a, c)][1]} for a in attack_ids for c in CONFIGS
                                    if per[(a, c)][0]["attempted"] + per[(a, c)][0]["manual_review"] + per[(a, c)][1]["attempted"] + per[(a, c)][1]["manual_review"] > 0},
        "legit_changes_ge_0.5": legit_changes,
        "l3_denials": denials,
        "l3_summary": {"total": len(denials), "attack_related": sum(d["attack_related"] for d in denials),
                       "attack_related_by_scenario": dict(Counter(d["scenario"] for d in denials if d["attack_related"])),
                       "non_attacker": sum(not d["attack_related"] for d in denials),
                       "non_attacker_provisional": dict(Counter(d.get("provisional_category") for d in denials if not d["attack_related"])),
                       "non_attacker_by_scenario": dict(Counter(d["scenario"] for d in denials if not d["attack_related"])),
                       "flagged": [d for d in denials if not d["attack_related"] and d["flags"]]},
        "l1_quarantined_scenarios_full": sorted({sid for sid in all_ids if per[(sid, "full")][0]["l1_quarantined"]}),
    }
    OUT.mkdir(parents=True)
    (OUT / "validation.json").write_text(json.dumps(val, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "analysis.json").write_text(json.dumps(analysis, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    with open(OUT / "per_scenario.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (OUT / "SHA256SUMS.txt").write_bytes("".join(f"{sha(p)}  {p.name}\n" for p in sorted(OUT.iterdir())).encode("utf-8"))
    print(json.dumps({"all_ok": val["all_ok"], "reps": [(r["repetition"], r["ok"], r["stop_reasons"], len(r["inconclusive"]), len(r["manual_review_items"]), r["wall_time_s"]) for r in val["run_sets"]],
                      "time": val["wall_time_s_all"]}, indent=1))
    print(json.dumps({k: analysis[k] for k in ("unprotected_attempted_any_rep", "s1_attempted_any_rep_incl_manual_review", "legit_changes_ge_0.5", "l1_quarantined_scenarios_full")}, indent=1))
    print(json.dumps({k: v for k, v in analysis["l3_summary"].items() if k != "flagged"}, indent=1), "flagged:", len(analysis["l3_summary"]["flagged"]))
    for k, v in analysis["attack_scenarios_detail"].items():
        print(k, "S1", {x: v["s1"][x] for x in ("n", "attempted", "succeeded", "blocked_l3", "manual_review")}, "R1", {x: v["r1"][x] for x in ("n", "attempted", "succeeded", "blocked_l3")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
