"""Evidence: search and filter the 2,600 recorded runs in one selectable table, then open the selected run as the same
story and decision trace as the simulator. Everything comes from the original logs."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import components as ui
import components_v2 as V
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
        if t:  # every whitespace-separated term must match (single-term searches behave as before)
            hay = f"{r['scenario']} {r['category']} {r['config']} {r['model']} {r['experiment']} {D.CONFIG_LABEL.get(r['config'], '')}".lower()
            if not all(term in hay for term in t.split()):
                continue
        out.append(r)
    return out


def friendly(r: dict) -> tuple[tuple[str, str], tuple[str, str]]:
    return FRIENDLY.get(r["attack"], (r["attack"], "neutral")), LEGIT_FRIENDLY.get(r["legit"], (r["legit"], "neutral"))


GLYPH = {"good": "✓", "bad": "✕", "unknown": "!", "neutral": "–", "none": "–"}


def _status_text(label_kind: tuple[str, str]) -> str:
    label, kind = label_kind
    return f"{GLYPH.get(kind, '–')}  {label}"


def _table(sel: list[dict], suite) -> pd.DataFrame:
    rows = []
    for r in sel:
        a, l = friendly(r)
        rows.append({"Campaign": r["experiment"], "Rep": r["repetition"], "Scenario": r["scenario"], "Category": r["category"].replace("_", " "),
                     "Defences": D.CONFIG_LABEL[r["config"]], "Model": r["model"], "Attack outcome": _status_text(a), "User's task": _status_text(l),
                     "Layer 3 denials": r["l3_denials"], "Review": "" if r["review_status"] == "automatic verdict" else r["review_status"]})
    return pd.DataFrame(rows)


def render() -> None:
    ui.page_header("Evidence", "Search the 2,600 recorded runs, select one, and read its verdicts and decision trace. Every row comes from an original run log.")
    idx = state.run_index()
    suite = state.suite()
    runs = idx.runs
    c1, c2, c3, c4 = st.columns([1.6, 1.2, 1.3, 1.5], gap="small")
    text = c1.text_input("Search", placeholder="Scenario id, category or model, for example AS06, leakage, qwen", key="ex_text")
    exps = c2.multiselect("Campaign", ["R1", "Q1", "S1"], default=["R1", "Q1", "S1"], key="ex_exp", help="R1 llama3.2:3b at temperature 0, Q1 qwen3:4b, S1 llama3.2:3b with sampling")
    cfgs = c3.multiselect("Defences", D.CONFIG_ORDER, format_func=lambda x: D.CONFIG_LABEL[x], key="ex_cfg", placeholder="All configurations")
    quick = c4.selectbox("Show", list(QUICK), key="ex_quick")
    adv = {}
    with st.expander("More filters"):
        a1, a2, a3, a4 = st.columns(4, gap="small")
        adv["models"] = a1.multiselect("Model", sorted({r["model"] for r in runs}))
        adv["legit"] = a2.multiselect("User's task result", ["success", "failed", "inconclusive", "manual_review"])
        l3 = a3.selectbox("Layer 3 denial", ["any", "with Layer 3 denial", "without Layer 3 denial"])
        adv["l3"] = None if l3 == "any" else l3
        adv["review"] = a4.multiselect("Review status", sorted({r["review_status"] for r in runs}))
        adv["attack"] = st.multiselect("Attack outcome (technical classes)", sorted(set(ATTACK_LABEL.values())))
    attack = adv.pop("attack") or QUICK[quick]
    sel = filter_runs(runs, experiments=exps, configs=cfgs, attack=attack, text=text, **adv)
    st.markdown(f"<div class='as-note' style='margin:2px 0 8px'>{len(sel):,} of {len(runs):,} runs match. Select a row to open it. "
                "Rates and intervals are on the Results page.</div>", unsafe_allow_html=True)
    if not sel:
        st.info("No run matches these filters. Clear the search or choose All runs under Show.")
        return
    event = st.dataframe(_table(sel, suite), hide_index=True, width="stretch", height="auto" if len(sel) <= 8 else 318, on_select="rerun", selection_mode="single-row",
                         key="ex_table", column_config={"Rep": st.column_config.NumberColumn(width="small"), "Layer 3 denials": st.column_config.NumberColumn(width="small"),
                                                        "Category": st.column_config.TextColumn(width="medium")})
    picked = (event.selection.rows if event and hasattr(event, "selection") else []) or []
    chosen = sel[picked[0]] if picked and picked[0] < len(sel) else sel[0]

    (a_lab, a_kind), (l_lab, l_kind) = friendly(chosen)
    sc_c = suite.get(chosen["scenario"])
    review = chosen["review_status"] if chosen["review_status"] != "automatic verdict" else ""
    tags = V.st_tag(a_lab, a_kind) + V.st_tag(l_lab, l_kind) + (V.st_tag("Human-reviewed verdict" if "final" in review else review, "info", glyph=False) if review else "")
    st.markdown(f"<div class='as-case'><div><div class='as-lbl'>Selected run{'' if picked else ' (first match; select a row to open another)'}</div>"
                f"<div class='id'>{chosen['scenario']} in {chosen['experiment']}, repetition {chosen['repetition']}, {ui.esc(D.CONFIG_LABEL[chosen['config']].lower())}</div>"
                f"<div class='rq'>{ui.esc(sc_c.user_request)}</div></div><div class='tags'>{tags}</div></div>", unsafe_allow_html=True)
    den = [d for d in idx.denials if d["log"] == chosen["log"]]
    sel_d = {"mode": "replay", "log": chosen["log"], "ref": chosen["log"], "scenario": suite.get(chosen["scenario"]), "note": None,
             "final_attack_class": chosen["attack"] or None, "review_status": chosen["review_status"] if chosen["review_status"] != "automatic verdict" else None,
             "review_ai": chosen.get("review_ai"), "model": chosen["model"]}
    view = st.segmented_control("View", ["Story", "Guided presentation"], default="Story", key="ex_view") or "Story"
    view_simulator.show_story(sel_d, view=view, key="explorer")
    if den:
        with st.expander(f"Layer 3 denials in this run ({len(den)}) and their review status"):
            st.dataframe(pd.DataFrame([{"Call": d["index"], "Guard reason": d["reason"], "Attacker's call": "yes" if d["attack_related"] else "no", "Category": d["category"] or "—",
                                        "Review status": d["review_status"], "Source": d["review_source"] or "—"} for d in den]), hide_index=True, width="stretch")
