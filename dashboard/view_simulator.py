"""A. Live Attack Simulator. A plain-English five-step story (or a guided step-by-step presentation) built from the
REAL selected run's log, with all technical evidence in a collapsed section. Live = real execution through
agent.run_scenario; Recorded replay = a stored experiment log, always labelled as such."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

import components as ui
import components_v2 as V
import state
from agentshield.dashboard import data as D
from agentshield.dashboard import live as L
from agentshield.dashboard import story as S
from agentshield.dashboard import trace as T

CONFIGS = D.CONFIG_ORDER
DEMO_SHORT = {"Layer 3 blocks an attacker action": "Layer 3 blocks an action", "Legitimate task completed under full defence": "Task completed, full defence",
              "Layer 1 false quarantine (benign content)": "Layer 1 false alarm", "Full defence still fails (answer manipulation)": "Answer manipulation",
              "Full defence fails through an authorised channel": "Authorised channel"}
SHORT = {"unprotected": "None", "l1_only": "L1", "l2_only": "L2", "l3_only": "L3", "full": "All"}
GLOSSARY = """
**Prompt injection** — instructions hidden in an email or document that try to steer the AI.
**Layer 1 · Injection detector** — a classifier scores everything the AI reads; at 0.5 or above, the content is withheld ("quarantine").
**Layer 2 · Isolation** — outside text is wrapped in `<untrusted_content>` tags and the AI is told not to obey it. It is advice, not enforcement.
**Layer 3 · Action guard** — checks every tool action against what the user actually asked (who, which file, how many sensitive actions) and blocks the rest. It does not read the AI's final answer.
**Not attempted** — the AI never tried the attacker's action. This is *not* counted as the defence stopping it.
**Benchmark verdict** — the frozen, pre-registered automatic check used for every reported result. It checks the *end result* (e.g. "the file ended up deleted"), not every step.
**Workflow evidence** — a stricter reading of the run log for this demo: a step counts as done only if the log proves it (e.g. the file was actually opened *before* it was deleted).
**Recorded replay** — a stored run from the experiments. **Live** — executed now on the local model.
"""


def _scenario_label(sc) -> str:
    tag = "attack" if sc.is_attack else "benign"
    req = sc.user_request if len(sc.user_request) < 64 else sc.user_request[:61] + "…"
    return f"{sc.id}  {req}  ({tag})"


# ------------------------------------------------------------------ the five steps
def _step1(story) -> str:
    return (ui.step_header(1, "Trusted, typed by the user") + f"<div class='as-big'>“{ui.esc(story['user_request'])}”</div>"
            "<div class='as-note' style='margin-top:6px'>This is the only instruction the AI should follow.</div>")


def _step2(story) -> str:
    a = story["attacker"]
    if not a:
        return ui.step_header(2, "None") + "<div class='as-big'>No attacker in this scenario.</div><div class='as-note'>A benign task, used to measure usefulness and false alarms.</div>"
    src = a["source"]
    quote = ui.highlight_injection(src["text"], a["instruction"]) if src else ui.esc(a["instruction"])
    return (ui.step_header(2, "Untrusted, hidden in " + (src["kind"] if src else "content")) +
            f"<div class='as-big'>{ui.esc(a['objective'])}</div>"
            f"<div class='as-note' style='margin:8px 0 6px'>Found in {ui.esc(src['label'] if src else 'the content')}. The injected text is underlined.</div>"
            f"<div class='as-quote'>{quote}</div><div class='as-note' style='margin-top:8px'><b>Why it is suspicious:</b> {ui.esc(a['why_suspicious'])}</div>")


def _step3(story) -> str:
    warn = ""
    if story.get("invented"):
        warn = (f"<div class='as-warnbox' style='margin-top:8px'>The answer mentions {', '.join(repr(n) for n in story['invented'])}, which does not exist anywhere in this "
                "scenario or in what the tools returned: the model made it up.</div>")
    return ui.step_header(3, "Observed actions in order, from the run log") + ui.actions_html(story) + warn


def _step4(story) -> None:
    st.markdown(ui.step_header(4, "What each layer did in this run"), unsafe_allow_html=True)
    cols = st.columns(3, gap="small")
    for col, k in zip(cols, ("L1", "L2", "L3")):
        with col:
            st.markdown(ui.layer_card(k, story["layers"][k]), unsafe_allow_html=True)


def _step5(story) -> None:
    st.markdown(ui.step_header(5, "Verdicts from the frozen benchmark verifier" + (" and human review" if "review" in story["attack"]["reason"].lower() else "")), unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1.25], gap="small")
    with c1:
        st.markdown(ui.result_card("Attack outcome", story["attack"]), unsafe_allow_html=True)
    with c2:
        st.markdown(ui.result_card("User's task, benchmark verdict", story["legit"]), unsafe_allow_html=True)
    with c3:
        st.markdown(ui.workflow_card(story["workflow"]), unsafe_allow_html=True)
    st.caption("Benchmark verdicts are the frozen, pre-registered checks behind every reported result and are never changed here. "
               "Workflow evidence is a stricter reading of the log for demonstrations: a step counts as done only if the log proves it.")


def _mode_line(sel) -> None:
    if sel["mode"] == "live":
        st.markdown(f"<div class='as-mode'><span><span class='as-dot' style='background:{ui.T['good']}'></span> <b>Live run</b></span>"
                    f"<span>Executed just now on {ui.esc(sel.get('model'))} in {sel.get('seconds', 0):.1f} s" + (", from a freshly loaded model" if sel.get("fresh") else "")
                    + ". One run: the same request can play out differently next time, even at temperature 0.</span></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='as-mode'><span><span class='as-dot' style='background:{ui.T['neutral']}'></span> <b>Recorded replay</b></span>"
                    f"<span>A stored experiment run, not a live execution: <code>{ui.esc(sel['ref'])}</code></span></div>", unsafe_allow_html=True)


def show_story(sel, *, view: str, key: str) -> None:
    """Render the selected run (live or recorded) as a story or a guided presentation, plus collapsed technical evidence."""
    events = T.load_events(D.ROOT / sel["log"]) if not str(sel["log"]).startswith(str(D.ROOT)) else T.load_events(sel["log"])
    sc = sel["scenario"]
    story = S.build_story(events, sc, final_attack_class=sel.get("final_attack_class"), review_status=sel.get("review_status"),
                          review_ai=sel.get("review_ai"))
    hdr = T.run_header(events)
    end = hdr["end"] or {}
    calls = end.get("tool_calls") or []
    spec = sc.verifier.get("attack") if sc.is_attack else None
    att_idx = set()
    if spec:
        from agentshield.verifiers import detect_attack_attempt
        att_idx = {c.get("index") for c in calls if detect_attack_attempt(spec, [c], None).passed}
    layer_on = {"L1": hdr["layers"]["L1 detector"], "L2": hdr["layers"]["L2 isolation"], "L3": hdr["layers"]["L3 guard"]}
    if sel["mode"] == "live":
        mode_tag = V.st_tag(f"Live run, {sel.get('seconds', 0):.1f} s", "info", glyph=False)
    else:
        mode_tag = V.st_tag("Recorded replay", "neutral", glyph=False)
    meta = [("Scenario", f"{sc.id}, {sc.category.replace('_', ' ')}"), ("Defences", D.CONFIG_LABEL.get(story["config"], story["config"])), ("Model", story["model"])]
    st.markdown(V.verdict_banner(story, meta, mode_tag), unsafe_allow_html=True)
    if sel["mode"] == "live":
        st.markdown(f"<div class='as-sm'><b>Live run</b> executed just now on {ui.esc(sel.get('model'))}" + (" from a freshly loaded model" if sel.get("fresh") else "")
                    + ". One run: the same request can play out differently next time, even at temperature 0.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='as-sm'>Recorded replay of a stored experiment run, not a live execution: <code>{ui.esc(sel['ref'])}</code></div>", unsafe_allow_html=True)
    if sel.get("note"):
        ui.warnbox(sel["note"])
    st.write("")

    if view == "Guided presentation":
        k = f"guide_{key}_{sel['log']}"
        i = st.session_state.get(k, 0)
        st.markdown("<div class='as-progress'>" + "".join(f"<div class='{'on' if j <= i else ''}'></div>" for j in range(5)) + "</div>", unsafe_allow_html=True)
        with st.container():
            if i == 0:
                st.markdown(f"<div class='as-guide'>{_step1(story)}</div>", unsafe_allow_html=True)
            elif i == 1:
                st.markdown(f"<div class='as-guide'>{_step2(story)}</div>", unsafe_allow_html=True)
            elif i == 2:
                st.markdown(f"<div class='as-guide'>{_step3(story)}</div>", unsafe_allow_html=True)
            elif i == 3:
                _step4(story)
            else:
                _step5(story)
        b1, mid, b2 = st.columns([1, 3, 1])
        if b1.button("Previous", key=f"prev_{k}", disabled=i == 0, width="stretch"):
            st.session_state[k] = i - 1
            st.rerun()
        mid.markdown(f"<div style='text-align:center' class='as-note'>Step {i + 1} of 5: {ui.STEP_TITLES[i]}</div>", unsafe_allow_html=True)
        if b2.button("Next", key=f"next_{k}", disabled=i == 4, width="stretch", type="primary"):
            st.session_state[k] = i + 1
            st.rerun()
    else:
        st.markdown(V.flow_html(story, calls, att_idx, layer_on), unsafe_allow_html=True)
        st.markdown(V.layer_strip(story), unsafe_allow_html=True)
        if story.get("invented"):
            ui.warnbox("The answer mentions " + ", ".join(repr(n) for n in story["invented"]) + ", which does not exist in this scenario: the model made it up.")
        with st.expander("Request and injected content"):
            c1, c2 = st.columns(2, gap="small")
            c1.markdown(f"<div class='as-panel fill'>{_step1(story)}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='as-panel fill'>{_step2(story)}</div>", unsafe_allow_html=True)
        with st.expander("What the AI did, step by step"):
            st.markdown(f"<div class='as-panel'>{_step3(story)}</div>", unsafe_allow_html=True)
        with st.expander("Benchmark verdicts and workflow evidence"):
            _step5(story)

    with st.expander("Decision trace: every event and decision, read from the run log"):
        show_model = st.toggle("Include the model's text between steps", value=False, key=f"showmodel_{key}_{hdr['run_id']}_{sel.get('ref')}")
        st.markdown(ui.timeline_html(T.timeline(events), show_model_text=show_model), unsafe_allow_html=True)
    with st.expander("Technical evidence: tool calls, layer scores, prompts, verifier record and the raw log", expanded=False):
        technical_evidence(events, sc, sel.get("ref"))


# ------------------------------------------------------------------ technical evidence (unchanged capabilities)
def technical_evidence(events: list[dict], sc, log_ref: str | None) -> None:
    hdr = T.run_header(events)
    st.markdown(ui.layer_pills(hdr["layers"]) + ui.pill(f"Layer 1 threshold {hdr['detector_threshold']}") + ui.pill(f"Configuration {hdr['config']}"), unsafe_allow_html=True)
    tabs = st.tabs(["Tool calls and Layer 3", "Layer 1 scores", "Layer 2 and system prompt", "Final answer and verifier", "Raw events"])
    with tabs[0]:
        end = hdr["end"] or {}
        rows = [{"Call": tc.get("index"), "Tool": tc.get("name"), "Arguments": json.dumps(tc.get("arguments"), ensure_ascii=False),
                 "Layer 3": ("—" if not tc.get("guard") else ("Allowed" if tc["guard"].get("allowed") else "Denied")),
                 "Guard reason": (tc.get("guard") or {}).get("reason", "" if hdr["layers"]["L3 guard"] else "Not recorded (Layer 3 off)"),
                 "Status": tc.get("status")} for tc in end.get("tool_calls", [])]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        else:
            st.info("No tool calls were proposed.")
        st.caption("Status 'invalid' means rejected by argument validation and 'over_limit' means beyond the six-call limit. Neither is a defence layer.")
    with tabs[1]:
        dets = [e for e in events if e["event"] == "detector_decision"]
        if not hdr["layers"]["L1 detector"]:
            st.info("Layer 1 was off: no detector decision was made or recorded.")
        elif not dets:
            st.info("Layer 1 was on, but no tool output was screened.")
        else:
            st.dataframe(pd.DataFrame([{"Call": e["index"], "Tool": e["name"], "Sources": ", ".join(e.get("sources") or []), "Max score": round(e["max_score"], 4),
                                        "Threshold": hdr["detector_threshold"], "Decision": "Withheld" if e["flagged"] else "Passed", "Chunks": e["n_chunks"]} for e in dets]),
                         hide_index=True, width="stretch")
    with tabs[2]:
        from agentshield.isolation import SYSTEM_PROMPT_ADDENDUM
        if hdr["layers"]["L2 isolation"]:
            st.markdown("Layer 2 instruction added to the system prompt:")
            st.code(SYSTEM_PROMPT_ADDENDUM, language=None)
            st.caption(f"Present in the logged system prompt: {hdr['l2_addendum_in_system_prompt']}")
        else:
            st.info("Layer 2 was off.")
        st.code(hdr["system_prompt"] or "(not recorded)", language=None)
    with tabs[3]:
        end = hdr["end"] or {}
        st.markdown("Final answer, verbatim")
        st.code(end.get("final_answer") or "(none recorded)", language=None)
        if (end.get("final_state") or {}).get("outbox"):
            st.markdown("Emails sent to the simulated outbox")
            st.json(end["final_state"]["outbox"])
        st.markdown("Frozen verifier record")
        st.json({k: end.get(k) for k in ("stop_reason", "legitimate_success", "attack_attempted", "attack_succeeded", "verdict_details", "wall_time_s")})
    with tabs[4]:
        st.caption(f"{len(events)} events in {log_ref or 'the log'}")
        st.json(events, expanded=False)


# ------------------------------------------------------------------ selection: live
def _live_picker(suite) -> None:
    ids = [s.id for s in suite.scenarios]
    c1, c2, c3 = st.columns([2.6, 1.7, 1], gap="small")
    with c1:
        sid = st.selectbox("Scenario", ids, index=ids.index("AS06"), format_func=lambda i: _scenario_label(suite.get(i)), key="live_sid",
                           help="Each scenario pairs one user task with one hidden attack (or none, for benign tasks).")
    with c2:
        cfg = st.segmented_control("Defences", CONFIGS, default="full", format_func=lambda c: SHORT[c], key="live_cfg",
                                   help="Which AgentShield layers are switched on: None, only Layer 1 (detector), only Layer 2 (isolation), only Layer 3 (action guard), or All three.") or "full"
    with c3:
        model = st.selectbox("Model", list(L.MODELS), key="live_model", help="llama3.2:3b runs in seconds; qwen3:4b takes about a minute or more.")
    sc = suite.get(sid)
    custom = None
    b1, b2, b4, b3 = st.columns([1, 1.2, 1, 2.6], gap="small", vertical_alignment="center")
    with b4:
        with st.popover("Run options", width="stretch"):
            fresh = st.toggle("Start from a freshly loaded model", value=True, key="live_fresh",
                              help="Unloads the model before the run (about 1 to 2 s extra). Changes only the model server's state, never the scenario, defences or scoring.")
            if sc.is_attack and sc.attacker_text:
                use = st.toggle("Use my own hidden instruction", key=f"usecustom_{sid}")
                txt = st.text_area("Hidden instruction", value=sc.attacker_text, height=90, key=f"custom_{sid}", disabled=not use)
                st.caption("Applied to an in-memory copy; the frozen dataset is never changed. The verifier still checks the original attacker goal.")
                custom = txt if use else None
    status = state.runtime_status(model)
    go = b1.button("Run live", type="primary", width="stretch", disabled=not status["ok"])
    b2.button("Show recorded run", key="fallback_btn", width="stretch", on_click=_fallback, args=(sid, cfg),
              help="Fallback if Ollama is unavailable or slow: loads the recorded R1 repetition-1 run of this scenario and configuration, clearly labelled as a replay.")
    if status["ok"]:
        b3.markdown(f"<div class='as-status'><span class='as-dot' style='background:{ui.T['good']}'></span> Ollama ready with {ui.esc(model)}. Tools are simulated.</div>", unsafe_allow_html=True)
    else:
        b3.markdown(f"<div class='as-status'><span class='as-dot' style='background:{ui.T['warning']}'></span> Live execution is unavailable: {ui.esc(status['message'])}. Start Ollama, or use Show recorded run.</div>", unsafe_allow_html=True)
    if go:
        events: list[dict] = []
        with st.status(f"Running {sid} with {D.CONFIG_LABEL[cfg].lower()} on {model}", expanded=True) as box:
            ph = st.empty()

            def echo(e):
                events.append(e)
                ph.markdown(ui.timeline_html(T.timeline(events)[-4:], show_model_text=False), unsafe_allow_html=True)
            try:
                res = L.run_live(sid, cfg, model, custom_text=custom, echo=echo, fresh_model=fresh)
                box.update(label=f"Finished in {res['seconds']:.1f} s", state="complete", expanded=False)
                st.session_state["sel_live"] = {"mode": "live", "log": res["log_path"], "ref": D.rel(res["log_path"]), "scenario": res["scenario"],
                                                "note": res["custom_note"], "seconds": res["seconds"], "model": model, "fresh": res["fresh_model"]}
            except L.LiveUnavailable as exc:
                box.update(label="Live execution unavailable", state="error")
                st.error(f"{exc}. Nothing was executed. Use Show recorded run to present stored evidence, labelled as a replay.")
                state.runtime_status.clear()
            except Exception as exc:
                box.update(label="Run failed", state="error")
                st.error(f"The run failed: {type(exc).__name__}: {exc}")


# ------------------------------------------------------------------ selection: replay
def _replay_picker(suite) -> None:
    idx = state.run_index()
    cases = D.demo_cases(idx.runs)
    st.markdown("<div class='as-note' style='margin-bottom:8px'>Demonstration cases. Each is the first recorded run, in a fixed order, that matches the case; hover for how many runs match.</div>", unsafe_allow_html=True)
    cols = st.columns(len(cases), gap="small")
    for i, (col, c) in enumerate(zip(cols, cases)):
        r = c["run"]
        with col:
            if st.button(DEMO_SHORT.get(c["title"], c["title"]), key=f"demo_{i}", width="stretch", help=f"{c['description']} ({r['experiment']} rep {r['repetition']} · {r['scenario']} · {D.CONFIG_LABEL[r['config']]} · {c['matching_runs']} matching runs)"):
                st.session_state["sel_replay"] = _sel_from_run(r, suite, f"Demonstration case: {c['title']} — {c['description']} ({c['matching_runs']} matching runs in the evidence).")
    with st.expander("Choose any recorded run"):
        c1, c2, c3, c4, c5 = st.columns([1, 1, 1.3, 1.3, 1])
        exp = c1.selectbox("Experiment", ["R1", "Q1", "S1"], key="rp_exp")
        rep = c2.selectbox("Repetition", sorted({r["repetition"] for r in idx.runs if r["experiment"] == exp}), key="rp_rep")
        sid = c3.selectbox("Scenario", sorted({r["scenario"] for r in idx.runs if r["experiment"] == exp}), key="rp_sid")
        cfg = c4.selectbox("Defences", [c for c in CONFIGS if any(r["experiment"] == exp and r["config"] == c for r in idx.runs)], format_func=lambda c: D.CONFIG_LABEL[c], key="rp_cfg")
        if c5.button("Show", width="stretch", key="rp_go"):
            r = next(r for r in idx.runs if (r["experiment"], r["repetition"], r["scenario"], r["config"]) == (exp, rep, sid, cfg))
            st.session_state["sel_replay"] = _sel_from_run(r, suite, None)
    if "sel_replay" not in st.session_state and cases:
        st.session_state["sel_replay"] = _sel_from_run(cases[0]["run"], suite, f"Demonstration case: {cases[0]['title']} — {cases[0]['description']} ({cases[0]['matching_runs']} matching runs in the evidence).")


def _fallback(sid: str, cfg: str) -> None:
    """Button callback (runs before the page is drawn, so it may switch the mode widget)."""
    r = next((r for r in state.run_index().runs if (r["experiment"], r["repetition"], r["scenario"], r["config"]) == ("R1", 1, sid, cfg)), None)
    if r:
        st.session_state["sel_replay"] = _sel_from_run(r, state.suite(), f"Recorded fallback for {sid} with {D.CONFIG_LABEL[cfg].lower()} (R1 repetition 1). This is NOT a live run.")
        st.session_state["sim_mode"] = "Recorded replay"


def _sel_from_run(r, suite, note) -> dict:
    return {"mode": "replay", "log": r["log"], "ref": r["log"], "scenario": suite.get(r["scenario"]), "note": note,
            "final_attack_class": r["attack"] or None, "review_status": r["review_status"] if r["review_status"] != "automatic verdict" else None,
            "review_ai": r.get("review_ai"), "model": r["model"]}


def render() -> None:
    ui.inject_story_css()
    ui.page_header("Simulator", "Run one scenario on the local model, or replay a recorded run, and follow what the AI did and how each layer responded.")
    suite = state.suite()
    m1, m2, m3 = st.columns([1, 1, 0.42], gap="small", vertical_alignment="bottom")
    with m3:
        with st.popover("Terms used", width="stretch"):
            st.markdown(GLOSSARY)
    mode = m1.segmented_control("Source", ["Live execution", "Recorded replay"], default="Live execution", key="sim_mode",
                                help="Live runs the real system now on the local model. Recorded replay shows a stored run from the experiments.") or "Live execution"
    view = m2.segmented_control("View", ["Story", "Guided presentation"], default="Story", key="sim_view",
                                help="Story shows all five steps at once; Guided presentation shows one step at a time with Next/Previous.") or "Story"
    with st.container(border=True):
        if mode == "Live execution":
            _live_picker(suite)
        else:
            _replay_picker(suite)
    sel = st.session_state.get("sel_live" if mode == "Live execution" else "sel_replay")
    if sel:
        show_story(sel, view=view, key=mode)
    elif mode == "Live execution":
        st.info("Choose a scenario and the defences, then select Run live.")
