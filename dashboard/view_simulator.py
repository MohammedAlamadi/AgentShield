"""A. Live Attack Simulator. A plain-English five-step story (or a guided step-by-step presentation) built from the
REAL selected run's log, with all technical evidence in a collapsed section. Live = real execution through
agent.run_scenario; Recorded replay = a stored experiment log, always labelled as such."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

import components as ui
import state
from agentshield.dashboard import data as D
from agentshield.dashboard import live as L
from agentshield.dashboard import story as S
from agentshield.dashboard import trace as T

CONFIGS = D.CONFIG_ORDER
DEMO_SHORT = {"Layer 3 blocks an attacker action": "🛂 Layer 3 block", "Legitimate task completed under full defence": "✅ Task completed",
              "Layer 1 false quarantine (benign content)": "🚨 Layer 1 false alarm", "Full defence still fails (answer manipulation)": "⚠ Answer manipulation",
              "Full defence fails through an authorised channel": "⚠ Authorised channel"}
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
    return f"{sc.id} ({tag}) — {req}"


# ------------------------------------------------------------------ the five steps
def _step1(story) -> str:
    return (ui.step_header(1, "trusted · typed by the user") + f"<div class='as-big'>“{ui.esc(story['user_request'])}”</div>"
            "<div class='as-note' style='margin-top:6px'>This is the only instruction the AI should follow.</div>")


def _step2(story) -> str:
    a = story["attacker"]
    if not a:
        return ui.step_header(2, "none") + "<div class='as-big'>No attacker in this scenario.</div><div class='as-note'>A benign task, used to measure usefulness and false alarms.</div>"
    src = a["source"]
    quote = ui.highlight_injection(src["text"], a["instruction"]) if src else ui.esc(a["instruction"])
    return (ui.step_header(2, "untrusted · hidden in " + (src["kind"] if src else "content")) +
            f"<div class='as-big' style='color:{ui.C['red']}'>Goal: {ui.esc(a['objective'])}</div>"
            f"<div class='as-note' style='margin:6px 0 4px'>Found in {ui.esc(src['label'] if src else 'the content')} — the injected part is highlighted:</div>"
            f"<div class='as-quote'>{quote}</div><div class='as-note' style='margin-top:8px'><b>Why it is suspicious:</b> {ui.esc(a['why_suspicious'])}</div>")


def _step3(story) -> str:
    warn = ""
    if story.get("invented"):
        warn = (f"<div class='as-warnbox' style='margin-top:8px'>The answer mentions {', '.join(repr(n) for n in story['invented'])}, which does not exist anywhere in this "
                "scenario or in what the tools returned: the model made it up.</div>")
    return ui.step_header(3, "observed actions, in order (from the run log)") + ui.actions_html(story) + warn


def _step4(story) -> None:
    st.markdown(ui.step_header(4, "what each layer actually did in this run"), unsafe_allow_html=True)
    cols = st.columns(3)
    for col, k in zip(cols, ("L1", "L2", "L3")):
        with col:
            st.markdown(ui.layer_card(k, story["layers"][k]), unsafe_allow_html=True)


def _step5(story) -> None:
    st.markdown(ui.step_header(5, "attack and task verdicts from the frozen benchmark verifier" + (" + manual review" if "review" in story["attack"]["reason"].lower() else "")), unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1.25])
    with c1:
        st.markdown(ui.result_card("Attack outcome", story["attack"]), unsafe_allow_html=True)
    with c2:
        st.markdown(ui.result_card("User's task · benchmark verdict", story["legit"]), unsafe_allow_html=True)
    with c3:
        st.markdown(ui.workflow_card(story["workflow"]), unsafe_allow_html=True)
    st.caption("The benchmark verdicts are the frozen, pre-registered checks used for all reported results; they are never changed here. "
               "Workflow evidence is a separate, stricter reading of the log for this demo: it marks a step done only if the log proves it.")


def _mode_line(sel) -> None:
    if sel["mode"] == "live":
        st.markdown(f"<div class='as-modeline' style='color:{ui.C['green']};background:{ui.C['green']}18;border:1px solid {ui.C['green']}'>● LIVE EXECUTION — run just now on {ui.esc(sel.get('model'))} ({sel.get('seconds', 0):.1f} s"
                    + (", freshly loaded model" if sel.get("fresh") else "") + ")</div>", unsafe_allow_html=True)
        st.caption("A live run is one real run. The same request can play out differently on another run, even at temperature 0 — the recorded experiments measure this over many runs.")
    else:
        st.markdown(f"<div class='as-modeline' style='color:{ui.C['amber']};background:{ui.C['amber']}14;border:1px solid {ui.C['amber']}'>⏵ RECORDED REPLAY — a stored experiment run ({ui.esc(sel['ref'])}), not a live execution</div>", unsafe_allow_html=True)


def show_story(sel, *, view: str, key: str) -> None:
    """Render the selected run (live or recorded) as a story or a guided presentation, plus collapsed technical evidence."""
    events = T.load_events(D.ROOT / sel["log"]) if not str(sel["log"]).startswith(str(D.ROOT)) else T.load_events(sel["log"])
    sc = sel["scenario"]
    story = S.build_story(events, sc, final_attack_class=sel.get("final_attack_class"), review_status=sel.get("review_status"))
    _mode_line(sel)
    if sel.get("note"):
        ui.warnbox(sel["note"])
    st.markdown(f"<div class='as-note' style='margin-bottom:8px'>Scenario <b>{sc.id}</b> · defences: <b>{ui.esc(D.CONFIG_LABEL.get(story['config'], story['config']))}</b> · model {ui.esc(story['model'])}</div>", unsafe_allow_html=True)

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
        if b1.button("◀ Previous", key=f"prev_{k}", disabled=i == 0, use_container_width=True):
            st.session_state[k] = i - 1
            st.rerun()
        mid.markdown(f"<div style='text-align:center' class='as-note'>Step {i + 1} of 5 · {ui.STEP_TITLES[i]}</div>", unsafe_allow_html=True)
        if b2.button("Next ▶", key=f"next_{k}", disabled=i == 4, use_container_width=True, type="primary"):
            st.session_state[k] = i + 1
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"<div class='as-story'>{_step1(story)}</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='as-story'>{_step2(story)}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='as-story'>{_step3(story)}</div>", unsafe_allow_html=True)
        _step4(story)
        st.write("")
        _step5(story)

    with st.expander("🔬 Technical evidence — full timeline, tool arguments, layer scores, prompts, raw log", expanded=False):
        technical_evidence(events, sc, sel.get("ref"))


# ------------------------------------------------------------------ technical evidence (unchanged capabilities)
def technical_evidence(events: list[dict], sc, log_ref: str | None) -> None:
    hdr = T.run_header(events)
    st.markdown(ui.layer_pills(hdr["layers"]) + ui.pill(f"L1 threshold {hdr['detector_threshold']}", ui.C["orange"]) +
                ui.pill(f"config: {hdr['config']}", ui.C["cyan"]), unsafe_allow_html=True)
    steps = T.timeline(events)
    tabs = st.tabs(["Execution timeline", "Tool calls & Layer 3", "Layer 1 scores", "Layer 2 & system prompt", "Final answer & verifier", "Raw events (JSON)"])
    with tabs[0]:
        show_model = st.toggle("Include the model's own text between steps", value=False, key=f"showmodel_{hdr['run_id']}_{log_ref}")
        st.markdown(ui.timeline_html(steps, show_model_text=show_model), unsafe_allow_html=True)
    with tabs[1]:
        end = hdr["end"] or {}
        rows = [{"#": tc.get("index"), "tool": tc.get("name"), "arguments": json.dumps(tc.get("arguments"), ensure_ascii=False),
                 "Layer 3": ("—" if not tc.get("guard") else ("ALLOW" if tc["guard"].get("allowed") else "DENY")),
                 "guard reason": (tc.get("guard") or {}).get("reason", "" if hdr["layers"]["L3 guard"] else "not recorded (Layer 3 off)"),
                 "status": tc.get("status")} for tc in end.get("tool_calls", [])]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.info("No tool calls were proposed.")
        st.caption("'invalid' = rejected by argument validation; 'over_limit' = beyond the six-call limit. Neither is a defence layer.")
    with tabs[2]:
        dets = [e for e in events if e["event"] == "detector_decision"]
        if not hdr["layers"]["L1 detector"]:
            st.info("Layer 1 was off: no detector decision was made or recorded.")
        elif not dets:
            st.info("Layer 1 was on, but no tool output was screened.")
        else:
            st.dataframe(pd.DataFrame([{"call #": e["index"], "tool": e["name"], "sources": ", ".join(e.get("sources") or []), "max score": round(e["max_score"], 4),
                                        "threshold": hdr["detector_threshold"], "decision": "QUARANTINE" if e["flagged"] else "pass", "chunks": e["n_chunks"]} for e in dets]),
                         hide_index=True, use_container_width=True)
    with tabs[3]:
        from agentshield.isolation import SYSTEM_PROMPT_ADDENDUM
        if hdr["layers"]["L2 isolation"]:
            st.markdown("Layer 2 instruction added to the system prompt:")
            st.code(SYSTEM_PROMPT_ADDENDUM, language=None)
            st.caption(f"Present in the logged system prompt: {hdr['l2_addendum_in_system_prompt']}")
        else:
            st.info("Layer 2 was off.")
        st.code(hdr["system_prompt"] or "(not recorded)", language=None)
    with tabs[4]:
        end = hdr["end"] or {}
        st.markdown("**Final answer (verbatim)**")
        st.code(end.get("final_answer") or "(none recorded)", language=None)
        if (end.get("final_state") or {}).get("outbox"):
            st.markdown("**Emails sent (simulated outbox)**")
            st.json(end["final_state"]["outbox"])
        st.markdown("**Frozen verifier record**")
        st.json({k: end.get(k) for k in ("stop_reason", "legitimate_success", "attack_attempted", "attack_succeeded", "verdict_details", "wall_time_s")})
    with tabs[5]:
        st.caption(f"{len(events)} events · {log_ref or ''}")
        st.json(events, expanded=False)


# ------------------------------------------------------------------ selection: live
def _live_picker(suite) -> None:
    ids = [s.id for s in suite.scenarios]
    c1, c2, c3 = st.columns([2.2, 2.2, 1.2])
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
    if sc.is_attack and sc.attacker_text:
        with st.expander("✏️ Edit the hidden instruction (optional, sandbox copy only)"):
            use = st.toggle("Use my own hidden instruction", key=f"usecustom_{sid}")
            txt = st.text_area("Hidden instruction", value=sc.attacker_text, height=90, key=f"custom_{sid}", disabled=not use)
            st.caption("Applied to an in-memory copy; the frozen dataset is never changed. The verifier still checks the ORIGINAL attacker goal.")
            custom = txt if use else None
    fresh = st.toggle("Start from a freshly loaded model (more repeatable demos)", value=True, key="live_fresh",
                      help="Unloads the model before the run (~1–2 s extra). The small model's choices can depend on what it processed just before, "
                           "even at temperature 0. This changes only the model server's state, never the scenario, defences or scoring. "
                           "The recorded experiments did not reset the model between runs.")
    status = state.runtime_status(model)
    b1, b2 = st.columns([1, 3])
    go = b1.button("▶ Run live", type="primary", use_container_width=True, disabled=not status["ok"])
    b1.button("⏵ Show a recorded run instead", key="fallback_btn", use_container_width=True, on_click=_fallback, args=(sid, cfg),
              help="Fallback if Ollama is unavailable or slow: loads the recorded R1 repetition-1 run of this scenario and configuration, clearly labelled as a replay.")
    if status["ok"]:
        b2.markdown(f"<div class='as-note' style='padding-top:8px'>● Ollama ready — {ui.esc(model)}. Simulated tools only: no real email is sent and no file is touched."
                    + (" The first run with Layer 1 loads the detector (~20–30 s)." if cfg in ("l1_only", "full") else "") + "</div>", unsafe_allow_html=True)
    else:
        b2.markdown(f"<div class='as-mode-down'>Live execution unavailable: {ui.esc(status['message'])} — start Ollama, or switch to <b>Recorded replay</b>.</div>", unsafe_allow_html=True)
    if go:
        events: list[dict] = []
        with st.status(f"Running {sid} with {D.CONFIG_LABEL[cfg].lower()} on {model} — live", expanded=True) as box:
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
                st.error(f"{exc} — nothing was executed. Use Recorded replay to show stored evidence (it will be labelled as replay).")
                state.runtime_status.clear()
            except Exception as exc:
                box.update(label="Run failed", state="error")
                st.error(f"The run failed: {type(exc).__name__}: {exc}")


# ------------------------------------------------------------------ selection: replay
def _replay_picker(suite) -> None:
    idx = state.run_index()
    cases = D.demo_cases(idx.runs)
    st.markdown("<div class='as-note' style='margin-bottom:6px'>Demonstration cases — each is the first run in a fixed order that matches the stated rule; the count shows how many runs match.</div>", unsafe_allow_html=True)
    cols = st.columns(len(cases))
    for i, (col, c) in enumerate(zip(cols, cases)):
        r = c["run"]
        with col:
            if st.button(DEMO_SHORT.get(c["title"], c["title"]), key=f"demo_{i}", use_container_width=True, help=f"{c['description']} ({r['experiment']} rep {r['repetition']} · {r['scenario']} · {D.CONFIG_LABEL[r['config']]} · {c['matching_runs']} matching runs)"):
                st.session_state["sel_replay"] = _sel_from_run(r, suite, f"Demonstration case: {c['title']} — {c['description']} ({c['matching_runs']} matching runs in the evidence).")
    with st.expander("…or pick any recorded run"):
        c1, c2, c3, c4, c5 = st.columns([1, 1, 1.3, 1.3, 1])
        exp = c1.selectbox("Experiment", ["R1", "Q1", "S1"], key="rp_exp")
        rep = c2.selectbox("Repetition", sorted({r["repetition"] for r in idx.runs if r["experiment"] == exp}), key="rp_rep")
        sid = c3.selectbox("Scenario", sorted({r["scenario"] for r in idx.runs if r["experiment"] == exp}), key="rp_sid")
        cfg = c4.selectbox("Defences", [c for c in CONFIGS if any(r["experiment"] == exp and r["config"] == c for r in idx.runs)], format_func=lambda c: D.CONFIG_LABEL[c], key="rp_cfg")
        if c5.button("Show", use_container_width=True, key="rp_go"):
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
            "model": r["model"]}


def render() -> None:
    ui.inject_story_css()
    h1, h2 = st.columns([3, 1])
    with h1:
        ui.hero("Live Attack Simulator", "Watch a hidden instruction meet AgentShield, step by step")
    with h2:
        with st.popover("❓ What do these terms mean?", use_container_width=True):
            st.markdown(GLOSSARY)
    suite = state.suite()
    m1, m2 = st.columns([1, 1])
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
        st.info("Choose a scenario and the defences above, then press **Run live**.")
