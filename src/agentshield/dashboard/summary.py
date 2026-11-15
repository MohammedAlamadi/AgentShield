"""Plain-language answers to the three viva questions, computed only from the validated aggregates and the run index.

Q1  Did AgentShield reduce successful attacks?   (unprotected vs full, per experiment, with HOW it happened)
Q2  Did it interfere with legitimate tasks?      (legitimate success per configuration, per experiment)
Q3  Did any attacks still succeed?               (residual successes under full defence, grouped by kind)
No experiment is pooled; ranges stay ranges; non-attempts are never called prevention.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..frozen import load_frozen_suite, verify_frozen
from ..verifiers import detect_attack_attempt
from . import data as D
from .trace import load_events


def _pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{x * 100:.1f}%" if 0 < x < 0.1 else f"{x * 100:.0f}%"


def rng(lo: float, hi: float) -> str:
    return _pct(lo) if round(lo, 4) == round(hi, 4) else f"{_pct(lo)}–{_pct(hi)}"


def q1_reduction(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for exp in ("R1", "Q1", "S1"):
        mt = {r["config"]: r for r in D.metric_table(exp)}
        u, f = mt["unprotected"], mt["full"]
        allc = {c["config"]: c for c in D.counts_with_denominators(runs, exp)}
        cnt, cu = allc["full"], allc["unprotected"]
        reps = len({r["repetition"] for r in runs if r["experiment"] == exp})
        denom = (f"Counted over {cu['attack_n']} valid attack runs without defences and {cnt['attack_n']} with all layers "
                 f"(26 attack scenarios × {reps} repetition{'s' if reps > 1 else ''}"
                 + (f"; {cu['inconclusive'] + cnt['inconclusive']} timed-out runs excluded" if cu["inconclusive"] + cnt["inconclusive"] else "") + ").")
        cs = D.conditional_set(exp)
        stopped_l3 = cnt["blocked_l3"]
        after_l1 = cnt["not_attempted_after_l1"]
        plain_na = cnt["not_attempted"] - after_l1
        sentence = (f"Overall attack success: {rng(u['attack_success_lower'], u['attack_success_upper'])} without defences vs "
                    f"{rng(f['attack_success_lower'], f['attack_success_upper'])} with all layers. "
                    f"On the {len(cs)} attack scenario(s) the unprotected model actually attempted: {rng(u['conditional_asr_lower'], u['conditional_asr_upper'])} → "
                    f"{rng(f['conditional_asr_lower'], f['conditional_asr_upper'])}.")
        how = (f"Under full defence, Layer 3 blocked the attacker's action in {stopped_l3} run(s). In {after_l1} run(s) the attack was not attempted after Layer 1 "
               f"withheld the content, and in {plain_na} run(s) it was simply not attempted; neither counts as a proven block.")
        out.append({"experiment": exp, "unprotected": u, "full": f, "conditional_n": len(cs), "sentence": sentence, "how": how, "denominator": denom,
                    "blocked_l3_full": stopped_l3, "not_attempted_after_l1_full": after_l1, "not_attempted_plain_full": plain_na,
                    "full_attack_runs": cnt["attack_n"], "is_range": f["is_range"]})
    return out


def q2_utility() -> list[dict[str, Any]]:
    out = []
    for exp in ("R1", "Q1", "S1"):
        for r in D.metric_table(exp):
            diff = (r["vs_unprotected"] or {}).get("p_legit")
            out.append({"experiment": exp, "config": r["config"], "config_label": r["config_label"], "legit": r["legit_success"], "ci": r["legit_ci"],
                        "diff": diff["mean_difference"] if diff else None, "diff_ci": diff["ci95"] if diff else None})
    return out


def q3_residual(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attack scenarios that still succeeded under full defence (final classes only; unresolved items listed separately)."""
    suite = load_frozen_suite(verify_frozen())
    cells: dict[tuple, dict[str, Any]] = {}
    totals = defaultdict(int)
    for r in runs:
        if r["config"] == "full" and r["is_attack"] and r["legit"] != "inconclusive":
            totals[(r["experiment"], r["scenario"])] += 1
    for r in runs:
        if r["config"] != "full" or r["attack"] not in ("succeeded", "manual_review"):
            continue
        sc = suite.get(r["scenario"])
        key = (r["experiment"], r["scenario"])
        c = cells.setdefault(key, {"experiment": r["experiment"], "scenario": r["scenario"], "category": sc.category, "objective": sc.attacker_objective,
                                   "succeeded": 0, "unresolved": 0, "runs": totals[key], "kind": None, "example_log": r["log"]})
        if r["attack"] == "succeeded":
            c["succeeded"] += 1
            if c["kind"] is None:
                if sc.category == "answer_manipulation":
                    c["kind"] = "Answer manipulation — the planted claim appears in the AI's written answer, which no layer inspects"
                else:
                    ev = load_events(D.ROOT / r["log"])
                    end = next((e for e in reversed(ev) if e["event"] == "run_end"), {})
                    allowed_att = [tc for tc in end.get("tool_calls", []) if tc.get("status") == "executed" and detect_attack_attempt(sc.verifier["attack"], [tc], None).passed]
                    c["kind"] = ("Authorised channel — the attacker's content travelled in an action the user's task permits (Layer 3 checks who and what, not the message)"
                                 if allowed_att else "Other — see the run evidence")
        else:
            c["unresolved"] += 1
            c["kind"] = c["kind"] or "Undetermined — unresolved review (shown as a range)"
    return sorted(cells.values(), key=lambda c: ("RQS".index(c["experiment"][0]) if c["experiment"][0] in "RQS" else 9, -c["succeeded"], c["scenario"]))
