"""How AgentShield works (visual pipeline + plain-English layers) and honest limitations (expandable)."""

from __future__ import annotations

import streamlit as st

import components as ui
import state
from agentshield.dashboard import data as D

FLOW_CSS = f"""
<style>
.as-flow {{ display:flex; align-items:stretch; gap:6px; flex-wrap:wrap; margin: 6px 0 4px 0; }}
.as-node {{ flex:1 1 130px; min-width:120px; max-width:210px; background:{ui.C['panel']}; border:1px solid {ui.C['line']}; border-radius:14px; padding:12px; text-align:center; }}
.as-node .t {{ font-weight:800; font-size:15px; margin-top:4px; }}
.as-node .d {{ color:{ui.C['muted']}; font-size:13px; margin-top:4px; line-height:1.35; }}
.as-node .i {{ font-size:24px; }}
.as-arrow {{ display:flex; align-items:center; color:#64748B; font-size:22px; padding:0 2px; }}
.as-deny {{ margin-top:6px; font-size:12.5px; font-weight:700; color:{ui.C['red']}; }}
</style>
"""


def _node(icon, title, desc, color, extra=""):
    return f"<div class='as-node' style='border-top:3px solid {color}'><div class='i'>{icon}</div><div class='t' style='color:{color}'>{title}</div><div class='d'>{desc}</div>{extra}</div>"


def render() -> None:
    ui.inject_story_css()
    st.markdown(FLOW_CSS, unsafe_allow_html=True)
    ui.hero("How AgentShield works", "One action at a time, every step checked")
    st.markdown("#### The path of every action the AI proposes")
    arrow = "<div class='as-arrow'>➜</div>"
    flow = "".join([
        _node("🧑", "User request", "The trusted instruction. It defines what is allowed.", ui.C["blue"]), arrow,
        _node("🤖", "AI proposes an action", "e.g. read a document, send an email, delete a file", "#CBD5E1"), arrow,
        _node("🛂", "Layer 3 · Action guard", "Is this action within the user's request?", ui.C["cyan"], "<div class='as-deny'>No → blocked, never runs</div>"), arrow,
        _node("🧰", "Simulated tool runs", "Safe sandbox: no real email, no real files", "#94A3B8"), arrow,
        _node("🔎", "Layer 1 · Detector", "Does the returned text look like an injection?", ui.C["orange"], "<div class='as-deny'>Yes → content withheld</div>"), arrow,
        _node("🏷️", "Layer 2 · Isolation", "Wrap outside text as untrusted before the AI reads it", ui.C["violet"]), arrow,
        _node("🔁", "Back to the AI", "…until it writes its final answer", "#CBD5E1"),
    ])
    st.markdown(f"<div class='as-flow'>{flow}</div>", unsafe_allow_html=True)
    st.caption("The final written answer goes straight to the user: no layer checks it. That is why answer-manipulation attacks are a known gap.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='as-layer' style='border-top:3px solid {ui.C['orange']}'><div class='ln' style='color:{ui.C['orange']}'>Layer 1 · Injection detector</div><div class='lt'>"
                    "A trained classifier reads every email or document the AI opens and gives it a score. If the score reaches 0.5, the whole text is withheld from the AI. "
                    "It can miss well-disguised injections and can wrongly flag harmless text.</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='as-layer' style='border-top:3px solid {ui.C['violet']}'><div class='ln' style='color:{ui.C['violet']}'>Layer 2 · Untrusted-content isolation</div><div class='lt'>"
                    "Outside text is wrapped in clear 'untrusted' tags, and the AI is told never to follow instructions inside them. "
                    "This is advice to the model, not a hard barrier: a model can still be persuaded.</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='as-layer' style='border-top:3px solid {ui.C['cyan']}'><div class='ln' style='color:{ui.C['cyan']}'>Layer 3 · Action guard</div><div class='lt'>"
                    "Before any action runs, it is checked against the user's request: allowed tool, allowed recipient (replies only to the original sender), the named file, and at most one send or delete. "
                    "Everything else is denied. It checks who and what, not the content of a message.</div></div>", unsafe_allow_html=True)

    st.markdown("#### Honest limitations")
    ov = state.overview()
    idx = state.run_index()
    cs = {e: state.conditional_set(e) for e in ("R1", "Q1", "S1")}
    q1_obs = len({r["scenario"] for r in idx.runs if r["experiment"] == "Q1" and r["config"] == "unprotected" and r["is_attack"] and r["legit"] != "inconclusive"})
    l3 = D.l3_summary(idx.denials)
    reviewed, fb = sum(x["human_reviewed"] for x in l3), sum(x["reviewed_false_blocks"] for x in l3)

    def l1diff(e):
        v = next(r for r in state.metric_table(e) if r["config"] == "l1_only")["vs_unprotected"]["p_legit"]["mean_difference"]
        return f"{v * 100:+.0f} percentage points"
    with st.expander("The small models rarely attacked, which limits what can be concluded"):
        st.markdown(f"llama3.2:3b attempted only **{len(cs['R1'])} of 26** attack scenarios at temperature 0 and **{len(cs['S1'])} of 26** with sampling on, so the main effectiveness questions stay inconclusive for it. "
                    f"qwen3:4b attempted **{len(cs['Q1'])} of {q1_obs}** observed scenarios, but it ran only **one repetition**, and {ov['experiments']['Q1']['inconclusive']} of its runs timed out and are excluded. "
                    "A low attack rate is not the same as a defence working.")
    with st.expander("Answer manipulation gets through every configuration"):
        st.markdown("When the attacker only wants the AI to *say* something false (e.g. 'the meeting was cancelled'), no tool action is needed, so Layer 3 has nothing to block, and Layers 1–2 can be missed or ignored. "
                    "See the Evaluation Results page, question 3, for every such case.")
    with st.expander("Attacks can travel through allowed actions"):
        st.markdown("After Layer 3 blocks a wrong recipient, the AI can send the same harmful content to the permitted recipient (IL04 in R1, IL06 in Q1, RA05 in S1). Layer 3 checks who receives a message, not what it says.")
    with st.expander("Layer 1 false alarms cost usefulness"):
        st.markdown(f"Harmless documents (LD02, LR04) are withheld, so those tasks fail. Layer 1 alone changed legitimate success by **{l1diff('R1')}** in R1 and **{l1diff('Q1')}** in Q1.")
    with st.expander("Layer 3 false blocks: reviewed sample, not a full audit"):
        st.markdown(f"**{fb}** false blocks were found in the **{reviewed}** human-reviewed non-attacker denials. The remaining denials have rule-based, provisional classifications. "
                    "Reviews were drafted with ChatGPT assistance and verified by named team members; they are not independent reviews.")
    with st.expander("One review remains unresolved (A05)"):
        st.markdown("One S1 item has a single confirmed reviewer; the frozen rubric requires two. It is shown as a range (lower and upper bound) everywhere, never as a success or failure.")
    with st.expander("Scope"):
        st.markdown("40 synthetic scenarios, small local models, a simulated tool environment, keyword-based task checks. Results are indicative, not statistically conclusive; no significance tests were run.")

    with st.expander("📐 Full technical methodology"):
        st.markdown("""
- **Frozen before any run:** 40 scenarios (26 attack, 14 benign), 120 detector examples, verifiers, prompt v2, rubric v1.0 (hash-checked).
- **Experiments:** R1 llama3.2:3b, T=0, 10 repetitions (repetition 1 = the reference evaluation); Q1 qwen3:4b, 1 repetition (runtime gate); S1 llama3.2:3b, T=0.8, seeds 1–5, unprotected and full only.
- **Statistics:** the scenario is the unit (repetitions are repeated measures); 95% scenario-cluster bootstrap, 10,000 resamples, seed 413; paired comparisons within scenario; no significance tests.
- **Outcome classes:** only `blocked_l3` is prevention; not attempted, Layer 1 quarantine before a non-attempt, malformed calls and call-limit stops are not.
- **Pipeline per call:** model proposes → argument validation → Layer 3 guard → simulated tool → Layer 1 detector (quarantine on score ≥ 0.5) → Layer 2 wrapping → back to the model; six-call limit.
- **Live simulator:** the same `run_scenario` loop and layer classes as the experiments, an in-memory environment, logs in `dashboard_runs/`, frozen data verified before and after each run; live runs never enter the statistics.
- Details: `docs/D2_dashboard.md`, `docs/D2_results_inventory.md`, `docs/D2_review_methodology.md`.
""")
