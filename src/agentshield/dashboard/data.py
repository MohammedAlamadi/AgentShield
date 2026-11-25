"""Read-only loading of the validated AgentShield D2 artifacts for the dashboard.

Nothing here writes to the repository. Final metrics come from the VALIDATED aggregates listed in
``VALIDATED_AGGREGATES`` (documented in docs/D2_results_inventory.md section 6), and per-run evidence comes from the
original JSONL logs, classified with the frozen outcome classifier plus the finalised review overrides
(``adjudication/manual_adjudication.csv``) exactly as ``aggregate.load_classified`` does.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import experiments as X
from ..adjudication import overrides_from_final
from ..frozen import ROOT, load_frozen_suite, verify_frozen
from ..outcomes import classify, read_jsonl
from ..verifiers import detect_attack_attempt

# Validated aggregates (results inventory section 6). R1 has no manual-review items, so its original aggregate is final.
VALIDATED_AGGREGATES = {"R1": "R1_20261113T212758Z", "Q1": "Q1_20261114T131523Z", "S1": "S1_20261118T154119Z"}
AGG_ROOT = ROOT / "results" / "eval" / "aggregates"
DETECTOR_RUN = ROOT / "results" / "detector_eval" / "20261113T185711Z"
EVIDENCE = ROOT / "docs" / "evidence"
CONFIG_ORDER = ["unprotected", "l1_only", "l2_only", "l3_only", "full"]
CONFIG_LABEL = {"unprotected": "Unprotected", "l1_only": "Layer 1 only", "l2_only": "Layer 2 only", "l3_only": "Layer 3 only", "full": "Full defence"}
ATTEMPTED = {"succeeded", "blocked_l3", "not_executed_invalid_call", "not_executed_call_limit", "attempted_not_succeeded"}

EXPERIMENT_TEXT = {
    "R1": "llama3.2:3b, temperature 0, seed 42, all 5 configurations, 10 repetitions. Repetition 1 is the reference evaluation (not counted twice).",
    "Q1": "qwen3:4b (think off), temperature 0, seed 42, all 5 configurations, ONE repetition (runtime gate failed). Runs whose model call exceeded the 180 s timeout are inconclusive: excluded from every denominator (counts shown per configuration).",
    "S1": "llama3.2:3b, temperature 0.8, seeds 1-5, unprotected and full only. Sampling-on stability check. The one manual-review item, A05 (AM03, seed 2, full), was finalised as SUCCESS after a second review on 18 Nov 2026, so no S1 figure is a range.",
}


def rel(p: str | Path) -> str:
    p = Path(p)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


# --------------------------------------------------------------------------- aggregates
def load_aggregate(exp: str) -> dict[str, Any]:
    p = AGG_ROOT / VALIDATED_AGGREGATES[exp] / "aggregate.json"
    return json.loads(p.read_text(encoding="utf-8"))


def metric_table(exp: str) -> list[dict[str, Any]]:
    """One row per configuration with lower/upper bounds kept separate (never collapsed)."""
    agg = load_aggregate(exp)
    rows = []
    for c in [c for c in CONFIG_ORDER if c in agg["configs"]]:
        v = agg["configs"][c]

        def lu(key):
            d = v[key]
            return (d["lower"]["mean"], d["upper"]["mean"], d["lower"]["ci95"], d["upper"]["ci95"]) if "lower" in d else (d["mean"], d["mean"], d["ci95"], d["ci95"])
        att, succ, leg = lu("p_att"), lu("p_succ"), lu("p_legit")
        ca = v["conditional_asr"]
        rows.append({
            "experiment": exp, "config": c, "config_label": CONFIG_LABEL[c],
            "attack_attempt_lower": att[0], "attack_attempt_upper": att[1], "attack_attempt_ci": att[2],
            "attack_success_lower": succ[0], "attack_success_upper": succ[1], "attack_success_ci_lower": succ[2], "attack_success_ci_upper": succ[3],
            "legit_success": leg[0], "legit_ci": leg[2],
            "task_completion_without_attack": v["p_tc"]["mean"], "requested_outcome_met": v["p_req"]["mean"],
            "l3_attack_block": v["p_l3_block"]["mean"],
            "conditional_asr_lower": ca["lower_mean"], "conditional_asr_upper": ca["upper_mean"], "conditional_asr_ci": ca["ci95"],
            "reproducibility": v.get("reproducibility_modal_agreement_mean"),
            "excluded_runs": v["excluded_runs"], "manual_review_runs": v["manual_review_runs"],
            "is_range": succ[0] != succ[1] or att[0] != att[1],
            "vs_unprotected": v.get("vs_unprotected"),
        })
    return rows


def conditional_set(exp: str) -> list[str]:
    return load_aggregate(exp)["conditional_asr_set"]["scenarios"]


def per_scenario(exp: str) -> list[dict[str, Any]]:
    return load_aggregate(exp)["per_scenario"]


def detector_metrics() -> dict[str, Any]:
    return json.loads((DETECTOR_RUN / "detector_metrics.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- run index (all 2,600 runs)
@dataclass
class RunIndex:
    runs: list[dict[str, Any]]
    denials: list[dict[str, Any]]


def _denial_reviews() -> dict[tuple, dict[str, Any]]:
    """(experiment, repetition, scenario, config, call index) -> review status of a non-attacker Layer 3 denial."""
    import openpyxl

    out: dict[tuple, dict[str, Any]] = {}
    # provisional rule drafts (R1 reps 2-10; Q1 + S1)
    for d in json.loads((EVIDENCE / "l3_block_review_r1" / "l3_denials_r1.json").read_text(encoding="utf-8")):
        if not d.get("attack_related"):
            idx = int(d["id"].rsplit("-", 1)[1])
            out[("R1", d["repetition"], d["scenario"], d["config"], idx)] = {"status": "provisional (rule draft, not human-reviewed)", "category": d.get("provisional_category"), "source": "docs/evidence/l3_block_review_r1/l3_denials_r1.json"}
    for d in json.loads((EVIDENCE / "final_review_package" / "C_l3_q1_s1_sample.json").read_text(encoding="utf-8"))["denials"]:
        idx = int(d["id"].rsplit("-", 1)[1])
        out[(d["experiment"], d["repetition"], d["scenario"], d["config"], idx)] = {"status": "provisional (rule draft, not human-reviewed)", "category": d["provisional_category"], "source": "docs/evidence/final_review_package/C_l3_q1_s1_sample.json"}
    # Stage 2: the 12 reference (R1 rep 1) denials, human-reviewed
    blocks = {b["block_id"]: b for b in json.loads((EVIDENCE / "l3_block_review" / "l3_blocks_20261113T190040Z.json").read_text(encoding="utf-8"))}
    ws = openpyxl.load_workbook(EVIDENCE / "l3_block_review" / "l3_block_review.xlsx", read_only=True)["Blocks"]
    rows = list(ws.iter_rows(values_only=True))
    h = list(rows[0])
    for r in rows[1:]:
        d = dict(zip(h, r))
        b = blocks.get(d["block_id"])
        if b and d.get("final_category"):
            out[("R1", 1, b["scenario"], b["config"], int(b["blocked_call"]["index"]))] = {"status": "human-reviewed (final, Stage 2)", "category": d["final_category"], "source": "docs/evidence/l3_block_review/l3_block_review.xlsx"}
    # final review packages B and C (corrected copies)
    for name in ("l3_denials_r1_review.xlsx", "C_l3_q1_s1_review.xlsx"):
        ws = openpyxl.load_workbook(EVIDENCE / "final_review_corrected" / name, read_only=True)["Verification sample"]
        rows = list(ws.iter_rows(values_only=True))
        h = list(rows[0])
        for r in rows[1:]:
            d = dict(zip(h, r))
            if not d.get("id"):
                continue
            parts = d["id"].split("-")
            idx = int(parts[-1])
            exp = "R1" if d["id"].startswith("L3R-") else parts[1]
            final = d.get("final_category")
            if final in ("incorrect_arguments", "unauthorised_behaviour", "false_block"):
                out[(exp, int(d["repetition"]), d["scenario"], d["config"], idx)] = {"status": "human-reviewed (final; ChatGPT-assisted, two named reviewers)", "category": final, "source": f"docs/evidence/final_review_corrected/{name}"}
    return out


def build_run_index() -> RunIndex:
    """Classify every run of R1, Q1 and S1 with the frozen classifier + finalised overrides (read-only)."""
    suite = load_frozen_suite(verify_frozen())
    reviews = _denial_reviews()
    runs, denials = [], []
    for exp in ("R1", "Q1", "S1"):
        for rs in sorted(X.run_sets(exp), key=lambda s: s["repetition"]):
            p = Path(rs["path"])
            final = p / "adjudication" / "manual_adjudication.csv"
            overrides = overrides_from_final(final) if final.exists() else {}
            unresolved, final_rows = set(), {}
            if final.exists():
                import csv
                final_rows = {r["run_id"]: r for r in csv.DictReader(open(final, encoding="utf-8"))}
                unresolved = {rid for rid, r in final_rows.items() if r.get("resolution") == "unresolved"}
            for log in sorted((p / "runs").glob("*.jsonl")):
                ev = read_jsonl(log)
                start = next(e for e in ev if e["event"] == "run_start")
                end = next((e for e in reversed(ev) if e["event"] == "run_end"), None)
                rec = {"log_path": str(log), "run_id": start["run_id"], "scenario_id": start["scenario_id"], "config": start["config"]["name"],
                       "is_attack": bool(start.get("is_attack")), "model": start["model_settings"].get("model")}
                if end is None:
                    rec.update(stop_reason="incomplete_log", inconclusive=True, legitimate_success=None, attack_attempted=None, attack_succeeded=None,
                               verdict_details={}, tool_calls=[], final_answer=None, final_state=None, wall_time_s=None)
                else:
                    from ..outcomes import INCONCLUSIVE_STOPS
                    rec.update(stop_reason=end["stop_reason"], inconclusive=bool(end.get("inconclusive")) or end["stop_reason"] in INCONCLUSIVE_STOPS,
                               legitimate_success=end["legitimate_success"], attack_attempted=end["attack_attempted"], attack_succeeded=end["attack_succeeded"],
                               verdict_details=end.get("verdict_details") or {}, tool_calls=end.get("tool_calls") or [],
                               final_answer=end.get("final_answer"), final_state=end.get("final_state"), wall_time_s=end.get("wall_time_s"))
                rec["l1_quarantined"] = any((c.get("detector") or {}).get("flagged") for c in rec["tool_calls"])
                sc = suite.get(rec["scenario_id"])
                c = classify(rec, sc.verifier.get("attack") if sc.is_attack else None, overrides=overrides)
                if "attack" in c["adjudicated"]:
                    review = "manual review - final (adjudicated)"
                elif c["attack"] == "manual_review":
                    review = "manual review - UNRESOLVED (shown as a range)" if rec["run_id"] in unresolved else "manual review - pending"
                elif c["legit"] == "inconclusive":
                    review = "inconclusive (timeout) - excluded"
                else:
                    review = "automatic verdict"
                n_den = 0
                for g in (e for e in ev if e["event"] == "guard_decision" and not e["allowed"]):
                    n_den += 1
                    call = next((tc for tc in rec["tool_calls"] if tc["index"] == g["index"]), {"name": g["name"], "arguments": g.get("arguments")})
                    attack_call = bool(sc.is_attack and detect_attack_attempt(sc.verifier["attack"], [call], None).passed)
                    key = (exp, rs["repetition"], rec["scenario_id"], rec["config"], g["index"])
                    rv = {"status": "attacker call (counts as prevention: blocked_l3)", "category": "attack_related", "source": "run log"} if attack_call else \
                        reviews.get(key, {"status": "not reviewed", "category": None, "source": None})
                    denials.append({"experiment": exp, "repetition": rs["repetition"], "scenario": rec["scenario_id"], "config": rec["config"],
                                    "model": rec["model"], "index": g["index"], "tool": g["name"], "reason": g["reason"], "attack_related": attack_call,
                                    "review_status": rv["status"], "category": rv["category"], "review_source": rv["source"], "log": rel(log)})
                runs.append({"experiment": exp, "repetition": rs["repetition"], "run_set": p.name, "run_id": rec["run_id"],
                             "scenario": rec["scenario_id"], "category": sc.category, "is_attack": sc.is_attack, "config": rec["config"],
                             "model": rec["model"], "legit": c["legit"], "attack": c["attack"] or "", "attack_detail": c.get("attack_detail", ""),
                             "l1_quarantined": rec["l1_quarantined"], "stop_reason": rec["stop_reason"], "wall_time_s": rec["wall_time_s"],
                             "n_tool_calls": len(rec["tool_calls"]), "l3_denials": n_den, "review_status": review,
                             "review_ai": (final_rows.get(rec["run_id"]) or {}).get("ai_assistance") or None, "log": rel(log)})
    return RunIndex(runs=runs, denials=denials)


# --------------------------------------------------------------------------- summaries derived from the run index
def overview(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by = defaultdict(list)
    for r in runs:
        by[r["experiment"]].append(r)
    out = {"total_runs": len(runs), "experiments": {}}
    for exp, rr in by.items():
        out["experiments"][exp] = {
            "runs": len(rr), "repetitions": len({r["repetition"] for r in rr}), "configs": sorted({r["config"] for r in rr}, key=CONFIG_ORDER.index),
            "model": sorted({r["model"] for r in rr}), "scenarios": len({r["scenario"] for r in rr}),
            "inconclusive": sum(r["legit"] == "inconclusive" for r in rr),
            "call_limit_stops": sum(r["stop_reason"] == "max_tool_calls" for r in rr),
            "manual_review_unresolved": sum(r["attack"] == "manual_review" for r in rr),
            "adjudicated": sum(r["review_status"].startswith("manual review - final") for r in rr),
            "median_wall_time_s": sorted(r["wall_time_s"] for r in rr if r["wall_time_s"] is not None)[len(rr) // 2] if rr else None,
        }
    return out


def timeouts_by_config(runs: list[dict[str, Any]], exp: str) -> dict[str, int]:
    return {c: sum(1 for r in runs if r["experiment"] == exp and r["config"] == c and r["legit"] == "inconclusive") for c in CONFIG_ORDER
            if any(r["experiment"] == exp and r["config"] == c for r in runs)}


def counts_with_denominators(runs: list[dict[str, Any]], exp: str) -> list[dict[str, Any]]:
    """Run-level counts per configuration with explicit denominators (inconclusive excluded)."""
    out = []
    for c in CONFIG_ORDER:
        rr = [r for r in runs if r["experiment"] == exp and r["config"] == c]
        if not rr:
            continue
        valid = [r for r in rr if r["legit"] != "inconclusive"]
        atk = [r for r in valid if r["is_attack"]]
        mr = sum(r["attack"] == "manual_review" for r in atk)
        out.append({"config": c, "runs": len(rr), "inconclusive": len(rr) - len(valid),
                    "legit_success": sum(r["legit"] == "success" for r in valid), "legit_n": len(valid),
                    "attack_n": len(atk), "attempted_lower": sum(r["attack"] in ATTEMPTED for r in atk), "manual_review": mr,
                    "succeeded_lower": sum(r["attack"] == "succeeded" for r in atk), "blocked_l3": sum(r["attack"] == "blocked_l3" for r in atk),
                    "not_attempted": sum(r["attack"] == "not_attempted" for r in atk),
                    "not_attempted_after_l1": sum(r["attack"] == "not_attempted" and r["l1_quarantined"] for r in atk),
                    "invalid_call": sum(r["attack"] == "not_executed_invalid_call" for r in atk),
                    "l1_quarantined_runs": sum(r["l1_quarantined"] for r in rr)})
    return out


def per_repetition_rates(runs: list[dict[str, Any]], exp: str) -> list[dict[str, Any]]:
    """Attack success and legitimate success per repetition and configuration (lower bound for manual review)."""
    cells = defaultdict(list)
    for r in runs:
        if r["experiment"] == exp and r["legit"] != "inconclusive":
            cells[(r["repetition"], r["config"])].append(r)
    out = []
    for (rep, c), rr in sorted(cells.items()):
        atk = [r for r in rr if r["is_attack"]]
        out.append({"repetition": rep, "config": c, "attack_success": sum(r["attack"] == "succeeded" for r in atk) / len(atk) if atk else None,
                    "legit_success": sum(r["legit"] == "success" for r in rr) / len(rr)})
    return out


def l3_summary(denials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for exp in ("R1", "Q1", "S1"):
        dd = [d for d in denials if d["experiment"] == exp]
        non = [d for d in dd if not d["attack_related"]]
        reviewed = [d for d in non if d["review_status"].startswith("human-reviewed")]
        out.append({"experiment": exp, "denials": len(dd), "attack_related": len(dd) - len(non), "non_attacker": len(non),
                    "human_reviewed": len(reviewed), "reviewed_false_blocks": sum(d["category"] == "false_block" for d in reviewed),
                    "provisional": sum(d["review_status"].startswith("provisional") for d in non),
                    "not_reviewed": sum(d["review_status"] == "not reviewed" for d in non),
                    "categories_reviewed": dict(Counter(d["category"] for d in reviewed))})
    return out


# --------------------------------------------------------------------------- demonstration cases (deterministic, evidence-based)
DEMO_RULES = [
    ("Layer 3 blocks an attacker action", "Attacker's send_email in a delete-only task is denied by the guard; the requested deletion still completes.",
     lambda r: r["attack"] == "blocked_l3" and r["legit"] == "success"),
    ("Legitimate task completed under full defence", "A benign request completed with all three layers switched on.",
     lambda r: r["config"] == "full" and not r["is_attack"] and r["legit"] == "success" and r["l3_denials"] == 0 and not r["l1_quarantined"]),
    ("Layer 1 false quarantine (benign content)", "The detector withholds a harmless document, so the legitimate task fails. A real utility cost.",
     lambda r: not r["is_attack"] and r["l1_quarantined"] and r["legit"] == "failed"),
    ("Full defence still fails (answer manipulation)", "The planted claim reaches the user's answer; no layer is designed to stop answer manipulation.",
     lambda r: r["config"] == "full" and r["attack"] == "succeeded" and r["category"] == "answer_manipulation"),
    ("Full defence fails through an authorised channel", "After a guard denial the model replies to the genuine sender, carrying the attacker's claim.",
     lambda r: r["config"] == "full" and r["attack"] == "succeeded" and r["category"] != "answer_manipulation" and r["l3_denials"] > 0),
]


def demo_cases(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """First matching run per rule, in a fixed order (experiment R1 > Q1 > S1, then repetition, scenario, config).
    The rule, not a hand-picked run, decides; the matching count is shown so the case is not presented as typical."""
    order = {"R1": 0, "Q1": 1, "S1": 2}
    ranked = sorted(runs, key=lambda r: (order[r["experiment"]], r["repetition"], r["scenario"], CONFIG_ORDER.index(r["config"])))
    out = []
    for title, desc, rule in DEMO_RULES:
        hits = [r for r in ranked if rule(r)]
        if hits:
            out.append({"title": title, "description": desc, "run": hits[0], "matching_runs": len(hits)})
    return out
