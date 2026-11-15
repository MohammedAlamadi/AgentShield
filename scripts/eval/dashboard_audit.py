"""Final validation audit of the dashboard presentation layer (read-only; writes only its own report folder).

    .venv\\Scripts\\python scripts\\eval\\dashboard_audit.py

For all 40 frozen scenarios and all 2,600 recorded runs it rebuilds the Story (the same build_story the Story and
Guided views render) and checks it against the raw log, event by event. Writes docs/evidence/dashboard_audit/.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agentshield.dashboard import data as D  # noqa: E402
from agentshield.dashboard import live as L  # noqa: E402
from agentshield.dashboard import story as S  # noqa: E402
from agentshield.dashboard import trace as T  # noqa: E402
from agentshield.frozen import load_frozen_suite, verify_frozen  # noqa: E402
from agentshield.verifiers import detect_attack_attempt  # noqa: E402

OUT = ROOT / "docs" / "evidence" / "dashboard_audit"
KIND_OF_STATUS = {"executed": "done", "blocked_l3": "blocked", "quarantined_l1": "quarantined", "invalid": "failed", "over_limit": "failed", "executed_error": "failed"}
ATTACK_EXPECT = {"succeeded": "bad", "blocked_l3": "good", "manual_review": "unknown", "": "none"}
LEGIT_EXPECT = {"success": "good", "failed": "bad", "inconclusive": "unknown", "manual_review": "unknown"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_run(r: dict, ev: list[dict], sc) -> tuple[list[str], dict]:
    """Return (failures, story) for one recorded run."""
    f: list[str] = []
    rs = r["review_status"] if r["review_status"] != "automatic verdict" else None
    s = S.build_story(ev, sc, final_attack_class=r["attack"] or None, review_status=rs)
    start = ev[0]
    end = next((e for e in reversed(ev) if e["event"] == "run_end"), None)
    cfg = start["config"]
    calls = (end or {}).get("tool_calls") or []
    spec = sc.verifier.get("attack") if sc.is_attack else None

    # 1 actions: same calls, same order, kind matches status, attacker-goal tag matches the frozen detector
    if [a["index"] for a in s["actions"]] != [c["index"] for c in calls]:
        f.append("actions: order/count differs from tool_calls")
    for a, c in zip(s["actions"], calls):
        want = KIND_OF_STATUS.get(c.get("status"), "other")
        if a["kind"] != want:
            f.append(f"action #{c['index']}: kind {a['kind']} != status {c.get('status')}")
        att = bool(spec and detect_attack_attempt(spec, [c], None).passed)
        if a["attacker_goal"] != att:
            f.append(f"action #{c['index']}: attacker tag mismatch")
        if c.get("status") == "executed" and a["text"].startswith("Tried"):
            f.append(f"action #{c['index']}: executed call described as only tried")
        if c.get("status") in ("blocked_l3", "invalid", "over_limit") and not a["text"].startswith("Tried"):
            f.append(f"action #{c['index']}: non-executed call described as done")
    # 2 layers vs config and events
    on = {"L1": bool(cfg.get("detector")), "L2": bool(cfg.get("isolation")), "L3": bool(cfg.get("guard"))}
    for k in ("L1", "L2", "L3"):
        if (s["layers"][k]["status"] == "off") != (not on[k]):
            f.append(f"{k}: on/off mismatch with config")
    flagged = [e for e in ev if e["event"] == "detector_decision" and e["flagged"]]
    if s["layers"]["L1"]["status"] in ("acted", "false_alarm") and not flagged:
        f.append("L1 credited with a quarantine that is not in the log")
    if flagged and s["layers"]["L1"]["status"] in ("passed", "missed", "idle", "off"):
        f.append("L1 quarantine in the log not shown")
    for e in ev:
        if e["event"] == "detector_decision" and e.get("sources"):
            txt = " ".join(s["layers"]["L1"]["details"])
            if f"{e['max_score']:.3f}" not in txt and f"{e['max_score']:.4f}" not in txt:
                f.append(f"L1 score {e['max_score']} not shown")
    denied_att = [c for c in calls if c.get("status") == "blocked_l3" and spec and detect_attack_attempt(spec, [c], None).passed]
    if s["layers"]["L3"]["status"] == "acted" and not denied_att:
        f.append("L3 credited with stopping the attack without a logged denial of the attacker's call")
    if denied_att and s["layers"]["L3"]["status"] not in ("acted", "bypassed"):
        f.append("logged L3 denial of the attacker's call not shown as acted/bypassed")
    if not on["L3"] and any(e["event"] == "guard_decision" for e in ev):
        f.append("guard events in a run with L3 off")
    if s["layers"]["L2"]["status"] not in ("off",) and on["L2"] and s["layers"]["L2"]["status"] == "acted":
        f.append("L2 credited as stopping an attack")
    # 3 outcomes vs final classification
    if r["legit"] == "inconclusive":
        if not (s["attack"]["status"] == s["legit"]["status"] == "unknown"):
            f.append("inconclusive run not shown as undetermined")
    else:
        ea = ATTACK_EXPECT.get(r["attack"], "neutral")
        if s["attack"]["status"] != ea:
            f.append(f"attack status {s['attack']['status']} != expected {ea} for class {r['attack']}")
        if s["legit"]["status"] != LEGIT_EXPECT[r["legit"]]:
            f.append(f"legit status {s['legit']['status']} != {r['legit']}")
        if r["attack"] == "not_attempted" and "prevention" in s["attack"]["reason"] and "not counted as a prevention" not in s["attack"]["reason"]:
            f.append("non-attempt presented as prevention")
    # 4 benchmark vs workflow separation
    if not s["legit"]["headline"].startswith("Benchmark") and r["legit"] != "inconclusive":
        f.append("task verdict not labelled as the benchmark verdict")
    if "workflow" not in s or not isinstance(s["workflow"].get("steps"), list):
        f.append("workflow evidence missing")
    if s["legit"]["status"] == "good" and s["workflow"]["overall"] != "complete" and "does not show every step" not in s["legit"]["reason"]:
        f.append("benchmark success not qualified despite incomplete workflow evidence")
    for st in s["workflow"]["steps"]:
        if st["status"] == "completed" and st["step"].startswith("Open and read"):
            name = st["step"].split("'")[1]
            if not any(c.get("name") == "read_document" and (c.get("arguments") or {}).get("name") == name and c.get("status") == "executed" for c in calls):
                f.append(f"workflow claims '{name}' was read without an executed read_document")
        if st["status"] == "completed" and st["step"].startswith("Delete"):
            if not any(c.get("name") == "delete_file" and c.get("status") == "executed" for c in calls):
                f.append("workflow claims a deletion that was not executed")
    # 5 final answer quoted verbatim (truncated) and invented names really absent
    fa = (end or {}).get("final_answer")
    for n in s["invented"]:
        if n in json.dumps(sc.initial_state) or any(n in str(e.get("output", "")) for e in ev if e["event"] == "tool_executed"):
            f.append(f"'{n}' flagged as invented but it exists")
    if fa and s["final_answer"] != fa:
        f.append("final answer altered")
    return f, s


def edge(r: dict, s: dict) -> list[str]:
    tags = []
    if r["attack"] == "blocked_l3":
        tags.append("blocked attack")
    if r["attack"] == "succeeded":
        tags.append("successful attack")
    if r["attack"] == "not_attempted":
        tags.append("no attack attempt")
    if s["layers"]["L1"]["status"] == "false_alarm":
        tags.append("false positive (L1)")
    if r["legit"] == "failed":
        tags.append("legitimate-task failure")
    if r["legit"] == "inconclusive":
        tags.append("timeout / inconclusive")
    if r["attack"] == "manual_review":
        tags.append("unresolved review (A05)")
    if r["review_status"].startswith("manual review - final"):
        tags.append("adjudicated attack verdict")
    if s["workflow"]["overall"] in ("incomplete", "partly unverified") and r["legit"] == "success":
        tags.append("incomplete evidence behind a benchmark success")
    if s["layers"]["L3"]["status"] == "bypassed":
        tags.append("authorised-channel bypass")
    if any(a["kind"] == "failed" for a in s["actions"]):
        tags.append("malformed / non-existent tool call")
    if s["invented"]:
        tags.append("invented file name in answer")
    return tags


def main() -> int:
    if OUT.exists():
        print(f"REFUSED: {OUT} exists")
        return 1
    frozen = verify_frozen()
    suite = load_frozen_suite(frozen)
    report: dict = {"frozen": {"scenarios": frozen.scenarios_sha256, "manifest": frozen.manifest_sha256}}

    # A. all 40 frozen scenarios: the pieces the UI needs exist and render
    scen = []
    for sc in suite.scenarios:
        problems = []
        if sc.is_attack:
            src = L.injection_source(sc)
            if not src:
                problems.append("injected passage not located (no highlight)")
            try:
                cp, note = L.scenario_with_payload(sc, sc.attacker_text + " [audit]")
                if not note or sc.attacker_text in json.dumps(cp.initial_state) and "[audit]" not in json.dumps(cp.initial_state):
                    problems.append("custom payload copy failed")
            except Exception as exc:
                problems.append(f"custom payload: {exc}")
        if not S.benchmark_checks(sc) or S.benchmark_checks(sc) == "the scenario's end result":
            problems.append("benchmark check not described")
        scen.append({"scenario": sc.id, "is_attack": sc.is_attack, "category": sc.category, "scope": sc.scope.kind, "problems": problems})
    report["scenarios"] = {"n": len(scen), "with_problems": [x for x in scen if x["problems"]]}

    # B. all recorded runs
    idx = D.build_run_index()
    fails, coverage, edges, examples = [], Counter(), Counter(), defaultdict(list)
    for r in idx.runs:
        ev = T.load_events(ROOT / r["log"])
        f, s = check_run(r, ev, suite.get(r["scenario"]))
        coverage[(r["experiment"], r["model"], r["config"])] += 1
        if f:
            fails.append({"run": r["log"], "failures": f})
        for t in edge(r, s):
            edges[t] += 1
            if len(examples[t]) < 3:
                examples[t].append(f"{r['experiment']} rep {r['repetition']} {r['scenario']}/{r['config']}")
    report["runs"] = {"checked": len(idx.runs), "failed": len(fails), "failures": fails[:50],
                      "coverage": {f"{e}|{m}|{c}": n for (e, m, c), n in sorted(coverage.items())},
                      "edge_cases": {t: {"runs": n, "examples": examples[t]} for t, n in edges.items()}}
    # C. live-demo logs in the sandbox (same checks, outcome taken from the log)
    live = []
    for p in sorted(L.SANDBOX.glob("*.jsonl")):
        ev = T.load_events(p)
        if not ev or ev[-1]["event"] != "run_end":
            continue
        sc = suite.get(ev[0]["scenario_id"])
        if (ev[0].get("evaluation") or {}).get("custom_payload"):
            continue
        end = ev[-1]
        cls = "" if not sc.is_attack else ("inconclusive" if end.get("inconclusive") else ("manual_review" if end["attack_succeeded"] is None else
              ("succeeded" if end["attack_succeeded"] else ("blocked_l3" if any(c.get("status") == "blocked_l3" and detect_attack_attempt(sc.verifier["attack"], [c], None).passed for c in end["tool_calls"])
               else ("not_attempted" if not end["attack_attempted"] else "attempted_not_succeeded")))))
        legit = "inconclusive" if end.get("inconclusive") else {True: "success", False: "failed", None: "manual_review"}[end["legitimate_success"]]
        r = {"attack": cls, "legit": legit, "review_status": "automatic verdict", "experiment": "live", "repetition": 0, "scenario": sc.id, "config": ev[0]["config"]["name"]}
        f, s = check_run(r, ev, sc)
        live.append({"log": D.rel(p), "scenario": sc.id, "config": r["config"], "failures": f, "attack": s["attack"]["headline"], "legit": s["legit"]["headline"], "workflow": s["workflow"]["overall"]})
    report["live_logs"] = {"checked": len(live), "failed": sum(1 for x in live if x["failures"]), "items": live}
    OUT.mkdir(parents=True)
    (OUT / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "SHA256SUMS.txt").write_bytes(f"{sha(OUT / 'audit.json')}  audit.json\n".encode())
    print(json.dumps({"scenarios_with_problems": report["scenarios"]["with_problems"], "runs_checked": len(idx.runs), "runs_failed": len(fails),
                      "first_failures": fails[:8], "coverage_cells": len(coverage), "edge_cases": {t: v["runs"] for t, v in report["runs"]["edge_cases"].items()},
                      "live_checked": len(live), "live_failed": report["live_logs"]["failed"]}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
