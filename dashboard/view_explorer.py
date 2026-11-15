"""C. Security Evidence Explorer: simple search -> readable run cards -> the same plain-English story as the simulator,
with the full 2,600-row table and all filters as an advanced option. Everything comes from the original logs."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import components as ui
import state
import view_simulator
from agentshield.dashboard import data as D

ATTACK_LABEL = {"succeeded": "attack succeeded", "blocked_l3": "blocked by Layer 3", "not_attempted": "not attempted", "attempted_not_succeeded": "attempted, not succeeded",
                "not_executed_invalid_call": "malformed attacker call", "not_executed_call_limit": "beyond call limit", "manual_review": "manual review (unresolved)",
                "inconclusive": "inconclusive (timeout)", "": "benign (no attack)"}
FRIENDLY = {"succeeded": ("Attack succeeded", "bad"), "blocked_l3": ("Stopped by Layer 3", "good"), "not_attempted": ("Attack not attempted", "neutral"),
            "attempted_not_succeeded": ("Attempted, did not succeed", "neutral"), "not_executed_invalid_call": ("Attacker call malformed (no defence)", "neutral"),
            "not_executed_call_limit": ("Over the action limit (no defence)", "neutral"), "manual_review": ("Undetermined — review unresolved", "unknown"),
            "inconclusive": ("Timed out — no result", "unknown"), "": ("Benign task (no attack)", "none")}
LEGIT_FRIENDLY = {"success": ("Task completed", "good"), "failed": ("Task not completed", "bad"), "inconclusive": ("Timed out", "unknown"), "manual_review": ("Task undetermined", "unknown")}
QUICK = {"All runs": None, "Attacks that succeeded": ["attack succeeded"], "Stopped by Layer 3": ["blocked by Layer 3"],
         "Unresolved or timed out": ["manual review (unresolved)", "inconclusive (timeout)"], "Benign tasks": ["benign (no attack)"]}


def filter_runs(runs: list[dict], *, experiments=None, models=None, scenarios=None, configs=None, attack=None, legit=None, l3=None, review=None, text=None) -> list[dict]:
    """Pure filter used by the UI and the tests."""
    out = []
    t = (text or "").strip().lower()
    for r in runs:
        if experiments and r["experiment"] not in experiments:
            continue
        if models and r["model"] not in models:
            continue
        if scenarios and r["scenario"] not in scenarios:
            continue
        if configs and r["config"] not in configs:
            continue
        if attack and ATTACK_LABEL.get(r["attack"], r["attack"]) not in attack:
            continue
        if legit and r["legit"] not in legit:
            continue
        if l3 == "with Layer 3 denial" and r["l3_denials"] == 0:
            continue
        if l3 == "without Layer 3 denial" and r["l3_denials"] > 0:
            continue
        if review and r["review_status"] not in review:
            continue
        if t and t not in f"{r['scenario']} {r['category']} {r['config']} {r['model']} {r['experiment']}".lower():
            continue
        out.append(r)
    return out


def friendly(r: dict) -> tuple[tuple[str, str], tuple[str, str]]:
    return FRIENDLY.get(r["attack"], (r["attack"], "neutral")), LEGIT_FRIENDLY.get(r["legit"], (r["legit"], "neutral"))


def _card(r: dict, suite) -> str:
    (a, ak), (l, lk) = friendly(r)
    sc = suite.get(r["scenario"])
    req = sc.user_request if len(sc.user_request) < 95 else sc.user_request[:92] + "…"
    ac, lc = ui.OUTCOME_COLOR[ak], ui.OUTCOME_COLOR[lk]
    return (f"<div class='as-story' style='padding:12px 14px;margin-bottom:6px'><div class='as-note'>{r['experiment']} · rep {r['repetition']} · {r['model']} · "
            f"<b>{ui.esc(D.CONFIG_LABEL[r['config']])}</b></div><div style='font-size:16px;font-weight:700;margin:3px 0'>{r['scenario']} — {ui.esc(req)}</div>"
            f"{ui.pill(a, ac, True)}{ui.pill(l, lc, True)}</div>")


def render() -> None:
    ui.inject_story_css()
    ui.hero("Security Evidence Explorer", "Find any of the 2,600 recorded runs and see what happened, in plain English")
    idx = state.run_index()
    suite = state.suite()
    runs = idx.runs
    c1, c2, c3, c4 = st.columns([1.6, 1.2, 1.3, 1.6])
    text = c1.text_input("Search", placeholder="scenario id, category, model… e.g. AS06, leakage, qwen", key="ex_text")
    exps = c2.multiselect("Experiment", ["R1", "Q1", "S1"], default=["R1", "Q1", "S1"], key="ex_exp", help="R1 llama T=0 ×10 · Q1 qwen ×1 · S1 llama T=0.8 ×5")
    cfgs = c3.multiselect("Defences", D.CONFIG_ORDER, format_func=lambda x: D.CONFIG_LABEL[x], key="ex_cfg")
    quick = c4.selectbox("Show", list(QUICK), key="ex_quick")
    adv = {}
    with st.expander("Advanced filters"):
        a1, a2, a3, a4 = st.columns(4)
        adv["models"] = a1.multiselect("Model", sorted({r["model"] for r in runs}))
        adv["legit"] = a2.multiselect("User's task result", ["success", "failed", "inconclusive", "manual_review"])
        l3 = a3.selectbox("Layer 3 denial", ["any", "with Layer 3 denial", "without Layer 3 denial"])
        adv["l3"] = None if l3 == "any" else l3
        adv["review"] = a4.multiselect("Review / adjudication status", sorted({r["review_status"] for r in runs}))
        adv["attack"] = st.multiselect("Attack outcome (technical classes)", sorted(set(ATTACK_LABEL.values())))
    attack = adv.pop("attack") or QUICK[quick]
    sel = filter_runs(runs, experiments=exps, configs=cfgs, attack=attack, text=text, **adv)
    st.markdown(f"<div class='as-note'>{len(sel):,} of {len(runs):,} runs match. These are individual runs — the Evaluation Results page has the statistics.</div>", unsafe_allow_html=True)
    if not sel:
        st.info("No run matches. Try clearing the search or the filters.")
        return
    left, right = st.columns([0.72, 1.9], gap="medium")
    with left:
        page_n = 8
        pages = (len(sel) - 1) // page_n + 1
        p = st.number_input("Page", 1, pages, 1, key="ex_page", help=f"{pages} pages of {page_n}") if pages > 1 else 1
        for i, r in enumerate(sel[(p - 1) * page_n: p * page_n]):
            st.markdown(_card(r, suite), unsafe_allow_html=True)
            if st.button("Open this run", key=f"open_{r['log']}", use_container_width=True):
                st.session_state["ex_sel"] = r["log"]
    with right:
        chosen = next((r for r in sel if r["log"] == st.session_state.get("ex_sel")), None) or sel[0]
        st.markdown(f"#### {chosen['experiment']} · rep {chosen['repetition']} · {chosen['scenario']} · {D.CONFIG_LABEL[chosen['config']]}")
        if chosen["review_status"] not in ("automatic verdict",):
            ui.warnbox(f"Review status: {chosen['review_status']}.")
        den = [d for d in idx.denials if d["log"] == chosen["log"]]
        sel_d = {"mode": "replay", "log": chosen["log"], "ref": chosen["log"], "scenario": suite.get(chosen["scenario"]), "note": None,
                 "final_attack_class": chosen["attack"] or None, "review_status": chosen["review_status"] if chosen["review_status"] != "automatic verdict" else None, "model": chosen["model"]}
        view = st.segmented_control("View", ["Story", "Guided presentation"], default="Story", key="ex_view") or "Story"
        view_simulator.show_story(sel_d, view=view, key="explorer")
        if den:
            with st.expander(f"Layer 3 denials in this run ({len(den)}) and their review status"):
                st.dataframe(pd.DataFrame([{"call #": d["index"], "guard reason": d["reason"], "attacker call": d["attack_related"], "category": d["category"] or "—",
                                            "review status": d["review_status"], "source": d["review_source"] or "—"} for d in den]), hide_index=True, use_container_width=True)
    with st.expander("📋 Advanced: full searchable table of the matching runs"):
        df = pd.DataFrame([{"Experiment": r["experiment"], "Rep": r["repetition"], "Scenario": r["scenario"], "Category": r["category"].replace("_", " "),
                            "Defences": D.CONFIG_LABEL[r["config"]], "Model": r["model"], "Attack": ATTACK_LABEL.get(r["attack"], r["attack"]), "User task": r["legit"],
                            "L1 quarantine": "yes" if r["l1_quarantined"] else "", "L3 denials": r["l3_denials"], "Review status": r["review_status"],
                            "Stop": r["stop_reason"], "Log": r["log"]} for r in sel])
        st.dataframe(df, hide_index=True, use_container_width=True, height=360)
