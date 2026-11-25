"""Methodology: the per-action pipeline, the three layers, the evaluation design and its limitations."""

from __future__ import annotations

import streamlit as st

import components as ui
import components_v2 as V
import state
from agentshield.dashboard import data as D

STEPS = [  # (kind, title, description, decision) - a real sequence, in the order the agent loop runs
    ("Input", "User request", "The trusted instruction and its task scope define what is allowed.", ""),
    ("Model", "AI proposes an action", "For example: read a document, send an email, delete a file.", ""),
    ("Layer 3", "Action guard", "Is this action inside the user's task scope?", "Outside scope: denied, never runs"),
    ("Sandbox", "Simulated tool runs", "In-memory inbox, files and outbox. Nothing real is sent or deleted.", ""),
    ("Layer 1", "Injection detector", "Does the returned text look like an injection (score ≥ 0.5)?", "Flagged: content withheld"),
    ("Layer 2", "Content isolation", "Outside text is wrapped as untrusted before the AI reads it.", ""),
    ("Model", "Back to the AI", "Repeats until the AI writes its final answer, at most six actions.", ""),
]


def render() -> None:
    ui.page_header("Methodology", "How AgentShield checks each action, how the evaluation was designed, and what its results cannot show.")

    ui.section("The path of every proposed action", "Each tool call passes these steps in order. The final written answer goes straight to the user: no layer inspects it.")
    flow = "".join(
        f"<div class='as-node{' layer' if k.startswith('Layer') else ''}'><div class='k'>{ui.esc(k)}</div><div class='t'>{ui.esc(t)}</div>"
        f"<div class='d'>{ui.esc(d)}</div>{f'<div class=x>{ui.esc(x)}</div>' if x else ''}</div>" for k, t, d, x in STEPS)
    st.markdown(f"<div class='as-flow'>{flow}</div>", unsafe_allow_html=True)

    ui.section("The three layers")
    c1, c2, c3 = st.columns(3, gap="small")
    layers = [
        ("Layer 1, injection detector", "A pre-trained classifier (ProtectAI DeBERTa v3) scores every email or document the AI opens. At 0.5 or above the whole text is "
         "withheld and replaced with a notice.", "Can miss disguised injections and can flag harmless text."),
        ("Layer 2, content isolation", "Outside text is wrapped in untrusted-content tags, and the system prompt tells the AI never to follow instructions inside them.",
         "Advice to the model, not enforcement: a model can still be persuaded."),
        ("Layer 3, action guard", "Every proposed action is checked against the task scope: the allowed tool, the allowed recipient (replies only to the original sender), "
         "the named file, and at most one send or delete. Everything else is denied.", "Checks who and what, not the content of a permitted message."),
    ]
    for col, (name, what, limit), ic in zip((c1, c2, c3), layers, ("scan", "brackets", "lock")):
        with col:
            st.markdown(f"<div class='as-card2'><div style='display:flex;gap:10px;align-items:center;margin-bottom:10px'>{V.ibox(ic)}"
                        f"<span style='font-size:14px;font-weight:600;color:var(--tx)'>{ui.esc(name)}</span></div>"
                        f"<div style='font-size:13.5px;line-height:1.55;color:var(--tx2)'>{ui.esc(what)}</div>"
                        f"<div style='margin-top:10px'>{V.st_tag('Limit: ' + limit, 'warn', glyph=False)}</div></div>", unsafe_allow_html=True)

    ui.section("Evaluation design")
    st.markdown("<div class='as-panel'>" + ui.kv([
        ("Frozen before any run", "40 scenarios (26 attack, 14 benign), 120 detector examples, the verifiers, prompt v2 and rubric v1.0, all hash-checked"),
        ("R1", "llama3.2:3b, temperature 0, 10 repetitions of all five configurations; repetition 1 is the 200-run reference evaluation"),
        ("Q1", "qwen3:4b, one repetition, because the pre-registered runtime gate failed"),
        ("S1", "llama3.2:3b, temperature 0.8, seeds 1 to 5, unprotected and full defence only"),
        ("Statistics", "The scenario is the unit; repetitions are repeated measures. 95% scenario-cluster bootstrap (10,000 resamples, seed 413), paired within scenario. No significance tests."),
        ("Outcome classes", "Only a Layer 3 denial of the attacker's own call counts as prevention. Not attempted, a Layer 1 quarantine before a non-attempt, malformed calls and call-limit stops are not."),
        ("Human review", "Cases the verifier could not decide were labelled by two named team members against the frozen rubric. ChatGPT assisted with drafting; agreement is recorded agreement, not inter-rater reliability."),
        ("Live simulator", "The same agent loop and layers as the experiments, an in-memory environment and logs in dashboard_runs/. Frozen data is verified before and after each run; live runs never enter the statistics."),
    ]) + "</div>", unsafe_allow_html=True)

    ui.section("Limitations", "What the recorded evidence cannot show.")
    ov = state.overview()
    idx = state.run_index()
    cs = {e: state.conditional_set(e) for e in ("R1", "Q1", "S1")}
    q1_obs = len({r["scenario"] for r in idx.runs if r["experiment"] == "Q1" and r["config"] == "unprotected" and r["is_attack"] and r["legit"] != "inconclusive"})
    l3 = D.l3_summary(idx.denials)
    reviewed, fb = sum(x["human_reviewed"] for x in l3), sum(x["reviewed_false_blocks"] for x in l3)

    def l1diff(e):
        v = next(r for r in state.metric_table(e) if r["config"] == "l1_only")["vs_unprotected"]["p_legit"]["mean_difference"]
        return f"{v * 100:+.0f} percentage points"

    items = [
        ("The small models rarely attacked", f"llama3.2:3b attempted {len(cs['R1'])} of 26 attack scenarios at temperature 0 and {len(cs['S1'])} of 26 with sampling, so its effectiveness "
         f"results stay inconclusive. qwen3:4b attempted {len(cs['Q1'])} of {q1_obs} observed scenarios, but ran one repetition and {ov['experiments']['Q1']['inconclusive']} runs timed out. "
         "A low attack rate is not a defence working."),
        ("Answer manipulation gets through", "When the attacker only wants the AI to say something false, no tool action is needed, so Layer 3 has nothing to block, and Layers 1 and 2 can be missed or ignored."),
        ("Attacks can travel through permitted actions", "After Layer 3 denies a wrong recipient, the AI can send the same content to the permitted one (IL04 in R1, IL06 in Q1, RA05 in S1)."),
        ("Layer 1 false alarms cost usefulness", f"Harmless documents (LD02, LR04) are withheld and those tasks fail. Layer 1 alone changed legitimate success by {l1diff('R1')} in R1 and {l1diff('Q1')} in Q1."),
        ("Layer 3 false blocks were checked on a sample", f"{fb} false blocks were found in {reviewed} human-reviewed non-attacker denials; the rest carry rule-based provisional classifications."),
        ("A05 was finalised by a second, non-independent review", "One S1 item first had a single confirmed reviewer and was reported as a range. A second team member reviewed it on 18 Nov 2026 "
         "and agreed (success, rule B2) after seeing the first judgement."),
        ("Scope", "40 synthetic scenarios, small local models, simulated tools and keyword-based task checks. Results are indicative, not statistically conclusive."),
    ]
    icons = [("alert", "warn"), ("x", "bad"), ("flow", "bad"), ("scan", "warn"), ("review", "info"), ("review", "info"), ("minus", "neutral")]
    st.markdown("<div class='as-card2'>" + "".join(V.frow(ic, k, t, d) for (t, d), (ic, k) in zip(items, icons)) + "</div>", unsafe_allow_html=True)
    st.caption("Further detail: docs/D2_dashboard.md, docs/D2_results_inventory.md and docs/D2_review_methodology.md in the project repository.")
