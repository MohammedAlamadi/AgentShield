"""Shared visual components: theme CSS, badges, KPI cards and the execution timeline. All dynamic text is HTML-escaped
(logs contain attacker-controlled text, including HTML comments)."""

from __future__ import annotations

import html
import json
from typing import Any

import streamlit as st

C = {
    "bg": "#0A0F1E", "panel": "#111A2E", "panel2": "#16213A", "line": "#24314F", "text": "#E6EAF2", "muted": "#8A97B2",
    "cyan": "#22D3EE", "green": "#34D399", "red": "#F87171", "amber": "#FBBF24", "violet": "#A78BFA", "orange": "#FB923C", "blue": "#60A5FA",
}
LAYER_COLOR = {"Layer 1 detector": C["orange"], "Layer 2 isolation": C["violet"], "Layer 3 guard": C["cyan"], "Trusted input": C["blue"],
               "Model": "#CBD5E1", "Agent": "#CBD5E1", "Tool (simulated)": C["muted"], "Argument validation": C["amber"],
               "AgentShield": C["amber"], "Runtime": C["red"], "Frozen verifier": C["green"]}
STATUS_COLOR = {"allow": C["green"], "ok": C["green"], "block": C["red"], "fail": C["red"], "warn": C["amber"], "info": C["muted"]}
CONFIG_COLOR = {"unprotected": "#64748B", "l1_only": C["orange"], "l2_only": C["violet"], "l3_only": C["cyan"], "full": C["green"]}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, [class*="css"], .stMarkdown, .stText {{ font-family: 'Inter', system-ui, sans-serif; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1500px; }}
section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #0D1427 0%, #0A0F1E 100%); border-right: 1px solid {C['line']}; }}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
.as-hero {{ display:flex; align-items:center; gap:14px; margin-bottom:6px; }}
.as-hero .logo {{ width:40px; height:40px; border-radius:10px; background: radial-gradient(circle at 30% 30%, {C['cyan']}, #0E7490);
   display:flex; align-items:center; justify-content:center; font-weight:800; color:#04121A; font-size:18px; box-shadow: 0 0 24px rgba(34,211,238,.35); }}
.as-hero .t {{ font-size:26px; font-weight:800; }}
.as-hero .s {{ color:{C['muted']}; font-size:13px; margin-top:-2px; }}
.as-card {{ background:{C['panel']}; border:1px solid {C['line']}; border-radius:14px; padding:14px 16px; margin-bottom:12px; }}
.as-card h4 {{ margin:0 0 6px 0; font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:{C['muted']}; font-weight:700; }}
.as-card .v {{ font-size:15px; line-height:1.45; white-space:pre-wrap; word-break:break-word; }}
.as-trusted {{ border-left:4px solid {C['blue']}; }}
.as-untrusted {{ border-left:4px solid {C['red']}; background: linear-gradient(90deg, rgba(248,113,113,.07), {C['panel']} 40%); }}
.as-objective {{ border-left:4px solid {C['amber']}; }}
.as-inject {{ background: rgba(248,113,113,.18); border:1px dashed {C['red']}; border-radius:6px; padding:1px 4px; }}
.as-kpi {{ background:{C['panel']}; border:1px solid {C['line']}; border-radius:14px; padding:12px 14px; height:100%; }}
.as-kpi .l {{ color:{C['muted']}; font-size:11px; text-transform:uppercase; letter-spacing:.08em; font-weight:700; }}
.as-kpi .n {{ font-size:26px; font-weight:800; margin-top:2px; }}
.as-kpi .d {{ color:{C['muted']}; font-size:12px; margin-top:2px; line-height:1.35; }}
.as-pill {{ display:inline-block; padding:3px 10px; border-radius:999px; font-size:12px; font-weight:700; margin:2px 4px 2px 0; border:1px solid; }}
.as-mode-live {{ background: rgba(52,211,153,.12); border:1px solid {C['green']}; color:{C['green']}; padding:10px 14px; border-radius:12px; font-weight:700; }}
.as-mode-replay {{ background: rgba(251,191,36,.10); border:1px solid {C['amber']}; color:{C['amber']}; padding:10px 14px; border-radius:12px; font-weight:700; }}
.as-mode-down {{ background: rgba(248,113,113,.10); border:1px solid {C['red']}; color:{C['red']}; padding:10px 14px; border-radius:12px; font-weight:600; }}
.as-tl {{ position:relative; margin-left:8px; padding-left:22px; border-left:2px solid {C['line']}; }}
.as-step {{ position:relative; background:{C['panel']}; border:1px solid {C['line']}; border-radius:12px; padding:9px 12px; margin:0 0 9px 0; }}
.as-step::before {{ content:''; position:absolute; left:-31px; top:12px; width:14px; height:14px; border-radius:50%; background: var(--dot); box-shadow:0 0 0 4px {C['bg']}, 0 0 12px var(--dot); }}
.as-step .hd {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
.as-step .layer {{ font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:.06em; color: var(--lc); }}
.as-step .title {{ font-weight:700; font-size:14px; }}
.as-step .ts {{ margin-left:auto; color:{C['muted']}; font-size:11px; font-family:'JetBrains Mono', monospace; }}
.as-step .body {{ margin-top:5px; color:#C9D2E3; font-size:12.5px; font-family:'JetBrains Mono', monospace; white-space:pre-wrap; word-break:break-word; max-height:220px; overflow:auto; }}
.as-outcome {{ border-radius:14px; padding:12px 16px; font-weight:700; font-size:15px; margin-bottom:8px; border:1px solid; }}
.as-note {{ color:{C['muted']}; font-size:12.5px; line-height:1.45; }}
.as-explain {{ background:{C['panel2']}; border-left:3px solid {C['cyan']}; border-radius:8px; padding:8px 12px; color:#C9D2E3; font-size:13px; margin:4px 0 10px 0; }}
.as-warnbox {{ background: rgba(251,191,36,.08); border-left:3px solid {C['amber']}; border-radius:8px; padding:8px 12px; color:#F3E3B5; font-size:13px; margin:4px 0 10px 0; }}
div[data-testid="stMetricValue"] {{ font-weight:800; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(x: Any) -> str:
    return html.escape("" if x is None else (x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)))


def hero(title: str, subtitle: str) -> None:
    st.markdown(f"<div class='as-hero'><div class='logo'>AS</div><div><div class='t'>{esc(title)}</div><div class='s'>{esc(subtitle)}</div></div></div>", unsafe_allow_html=True)


def card(label: str, value: str, kind: str = "", raw_html: bool = False) -> None:
    v = value if raw_html else esc(value)
    st.markdown(f"<div class='as-card {kind}'><h4>{esc(label)}</h4><div class='v'>{v}</div></div>", unsafe_allow_html=True)


def kpi(label: str, number: str, desc: str = "", color: str | None = None) -> None:
    col = f"color:{color};" if color else ""
    st.markdown(f"<div class='as-kpi'><div class='l'>{esc(label)}</div><div class='n' style='{col}'>{esc(number)}</div><div class='d'>{esc(desc)}</div></div>", unsafe_allow_html=True)


def pill(text: str, color: str, filled: bool = False) -> str:
    bg = f"background:{color}22;" if filled else "background:transparent;"
    return f"<span class='as-pill' style='border-color:{color};color:{color};{bg}'>{esc(text)}</span>"


def explain(text: str) -> None:
    st.markdown(f"<div class='as-explain'>{esc(text)}</div>", unsafe_allow_html=True)


def warnbox(text: str) -> None:
    st.markdown(f"<div class='as-warnbox'>{esc(text)}</div>", unsafe_allow_html=True)


def layer_pills(layers: dict[str, bool]) -> str:
    colors = {"L1 detector": C["orange"], "L2 isolation": C["violet"], "L3 guard": C["cyan"]}
    return "".join(pill(f"{k}: {'ON' if v else 'off'}", colors[k] if v else C["muted"], filled=v) for k, v in layers.items())


def highlight_injection(full_text: str, injected: str | None) -> str:
    t = esc(full_text)
    if injected:
        i = esc(injected)
        t = t.replace(i, f"<span class='as-inject'>{i}</span>")
    return t


def outcome_banner(text: str, kind: str) -> None:
    col = {"good": C["green"], "bad": C["red"], "warn": C["amber"], "neutral": C["muted"]}[kind]
    st.markdown(f"<div class='as-outcome' style='border-color:{col};color:{col};background:{col}14'>{esc(text)}</div>", unsafe_allow_html=True)


def timeline_html(steps: list[dict[str, Any]], show_model_text: bool = True) -> str:
    out = ["<div class='as-tl'>"]
    for s in steps:
        if s["kind"] == "model" and not show_model_text:
            continue
        dot = STATUS_COLOR.get(s["status"], C["muted"])
        lc = LAYER_COLOR.get(s["layer"], C["muted"])
        ts = f"t+{s['t_s']:.2f}s" if isinstance(s.get("t_s"), (int, float)) else ""
        body = f"<div class='body'>{esc(s['body'])}</div>" if s.get("body") else ""
        out.append(f"<div class='as-step' style='--dot:{dot};--lc:{lc}'><div class='hd'><span class='layer'>{esc(s['layer'])}</span>"
                   f"<span class='title'>{esc(s['title'])}</span><span class='ts'>{ts}</span></div>{body}</div>")
    out.append("</div>")
    return "".join(out)


def outcome_kind(badges: dict[str, str]) -> str:
    a = badges.get("attack", "")
    if "SUCCEEDED" in a:
        return "bad"
    if "not determined" in a or "MANUAL" in a or "inconclusive" in badges.get("run", ""):
        return "warn"
    return "good" if ("did not succeed" in a or "benign" in a) and "NOT completed" not in badges.get("legit", "") else "neutral"


# ------------------------------------------------------------------ story (plain-English) components
STORY_CSS = f"""
<style>
.block-container {{ padding-left: 2rem; padding-right: 2rem; }}
p, li, .stMarkdown {{ font-size: 15.5px; }}
.as-note {{ font-size: 14px !important; }}
.as-step-h {{ display:flex; align-items:center; gap:10px; margin: 2px 0 8px 0; }}
.as-num {{ width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:15px; color:#04121A; flex:none; }}
.as-step-t {{ font-size:17px; font-weight:800; letter-spacing:-.01em; }}
.as-step-s {{ color:{C['muted']}; font-size:13.5px; margin-left:auto; }}
.as-story {{ background:{C['panel']}; border:1px solid {C['line']}; border-radius:16px; padding:16px 18px; margin-bottom:14px; height:100%; }}
.as-big {{ font-size:19px; line-height:1.5; font-weight:600; }}
.as-quote {{ font-size:16px; line-height:1.55; background:{C['bg']}; border:1px solid {C['line']}; border-radius:10px; padding:10px 12px; white-space:pre-wrap; word-break:break-word; }}
.as-act {{ display:flex; gap:10px; align-items:flex-start; padding:9px 10px; border-radius:10px; margin-bottom:6px; background:{C['bg']}; border:1px solid {C['line']}; font-size:15.5px; line-height:1.45; }}
.as-act .ic {{ font-size:18px; width:24px; text-align:center; flex:none; }}
.as-tag {{ display:inline-block; font-size:12px; font-weight:800; padding:1px 8px; border-radius:999px; margin-left:6px; vertical-align:1px; }}
.as-layer {{ border-radius:14px; padding:13px 14px; border:1px solid {C['line']}; background:{C['panel']}; height:100%; }}
.as-layer .ln {{ font-size:12.5px; font-weight:800; text-transform:uppercase; letter-spacing:.07em; }}
.as-layer .ls {{ font-size:13px; font-weight:800; margin:4px 0 6px 0; }}
.as-layer .lt {{ font-size:15px; line-height:1.5; }}
.as-layer .ld {{ font-size:13.5px; color:#C9D2E3; margin-top:6px; line-height:1.45; }}
.as-res {{ border-radius:16px; padding:14px 18px; border:2px solid; height:100%; }}
.as-res .rl {{ font-size:12.5px; font-weight:800; text-transform:uppercase; letter-spacing:.08em; opacity:.9; }}
.as-res .rh {{ font-size:23px; font-weight:800; margin:2px 0 4px 0; }}
.as-res .rr {{ font-size:15px; line-height:1.5; color:#E6EAF2; }}
.as-progress {{ display:flex; gap:8px; margin: 4px 0 12px 0; }}
.as-progress div {{ flex:1; height:6px; border-radius:6px; background:{C['line']}; }}
.as-progress div.on {{ background:{C['cyan']}; }}
.as-guide {{ background:{C['panel']}; border:1px solid {C['line']}; border-radius:18px; padding:22px 26px; min-height:330px; }}
.as-guide .as-big {{ font-size:22px; }}
.as-modeline {{ font-size:14px; font-weight:700; padding:7px 12px; border-radius:10px; display:inline-block; margin-bottom:10px; }}
</style>
"""

OUTCOME_COLOR = {"good": C["green"], "bad": C["red"], "unknown": C["amber"], "neutral": "#94A3B8", "none": "#94A3B8"}
LAYER_STATUS = {  # status -> (label, color)
    "acted": ("Stopped it", C["green"]), "bypassed": ("Partly bypassed", C["amber"]), "missed": ("Missed it", C["amber"]),
    "false_alarm": ("False alarm", C["amber"]), "influenced": ("Labelled, model still influenced", C["amber"]),
    "labelled": ("Labelled as untrusted", C["violet"]), "passed": ("Nothing flagged", "#94A3B8"), "allowed": ("Allowed all actions", "#94A3B8"),
    "denied_other": ("Denied agent mistakes", C["cyan"]), "idle": ("Nothing to do", "#64748B"), "off": ("Off", "#475569"),
}
LAYER_ACCENT = {"L1": C["orange"], "L2": C["violet"], "L3": C["cyan"]}
STEP_COLORS = [C["blue"], C["red"], "#CBD5E1", C["cyan"], C["green"]]
STEP_TITLES = ["The user's request", "The attacker's hidden instruction", "What the AI did", "How AgentShield responded", "The outcome"]


def inject_story_css() -> None:
    st.markdown(STORY_CSS, unsafe_allow_html=True)


def step_header(n: int, sub: str = "") -> str:
    return (f"<div class='as-step-h'><div class='as-num' style='background:{STEP_COLORS[n - 1]}'>{n}</div>"
            f"<div class='as-step-t'>{esc(STEP_TITLES[n - 1])}</div><div class='as-step-s'>{esc(sub)}</div></div>")


def result_card(label: str, outcome: dict, big: bool = False) -> str:
    col = OUTCOME_COLOR.get(outcome["status"], "#94A3B8")
    return (f"<div class='as-res' style='border-color:{col};background:{col}12'><div class='rl' style='color:{col}'>{esc(label)}</div>"
            f"<div class='rh' style='color:{col}'>{esc(outcome['headline'])}</div><div class='rr'>{esc(outcome['reason'])}</div></div>")


def layer_card(key: str, layer: dict) -> str:
    label, col = LAYER_STATUS.get(layer["status"], (layer["status"], "#94A3B8"))
    from agentshield.dashboard.story import LAYER_NAMES
    det = "".join(f"<div class='ld'>• {esc(d)}</div>" for d in layer["details"][:4])
    op = "opacity:.55;" if layer["status"] == "off" else ""
    return (f"<div class='as-layer' style='border-top:3px solid {LAYER_ACCENT[key]};{op}'><div class='ln' style='color:{LAYER_ACCENT[key]}'>{esc(LAYER_NAMES[key])}</div>"
            f"<div class='ls' style='color:{col}'>● {esc(label)}</div><div class='lt'>{esc(layer['summary'])}</div>{det}</div>")


ACT_ICON = {"done": ("✓", "#94A3B8"), "blocked": ("⛔", C["green"]), "quarantined": ("🛡", C["orange"]), "failed": ("⚠", C["amber"]), "other": ("•", "#94A3B8")}


def actions_html(story: dict) -> str:
    rows = []
    for a in story["actions"]:
        ic, col = ACT_ICON.get(a["kind"], ("•", "#94A3B8"))
        tags = ""
        if a["attacker_goal"]:
            tags += f"<span class='as-tag' style='background:{C['red']}22;color:{C['red']};border:1px solid {C['red']}'>attacker's goal</span>"
        if a["read_injection"]:
            tags += f"<span class='as-tag' style='background:{C['amber']}18;color:{C['amber']};border:1px solid {C['amber']}'>contained the injection</span>"
        rows.append(f"<div class='as-act'><div class='ic' style='color:{col}'>{ic}</div><div>{esc(a['text'])}{tags}</div></div>")
    if not rows:
        rows.append("<div class='as-act'><div class='ic'>•</div><div>The AI did not use any tool; it only wrote an answer.</div></div>")
    fa = story.get("final_answer")
    if fa:
        short = fa if len(fa) <= 420 else fa[:417] + "…"
        rows.append(f"<div class='as-act'><div class='ic'>💬</div><div><b>Answered the user:</b> “{esc(short)}”</div></div>")
    return "".join(rows)


def question_header(n: int, title: str, sub: str = "") -> str:
    col = [C["cyan"], C["violet"], C["red"]][(n - 1) % 3]
    return (f"<div class='as-step-h' style='margin-top:10px'><div class='as-num' style='background:{col}'>Q{n}</div>"
            f"<div class='as-step-t' style='font-size:20px'>{esc(title)}</div><div class='as-step-s'>{esc(sub)}</div></div>")


WF_STYLE = {"completed": ("✓", C["green"], "done"), "not_done": ("✗", C["red"], "not done"), "failed": ("⚠", C["amber"], "tried, did not happen"),
            "unverified": ("?", "#94A3B8", "cannot be proven from the log")}
WF_OVERALL = {"complete": ("Every requested step is shown in the log", C["green"]), "incomplete": ("Not every requested step happened", C["amber"]),
              "partly unverified": ("Some steps cannot be proven from the log", "#94A3B8"), "unverified": ("Nothing to assess", "#94A3B8")}


def workflow_card(wf: dict) -> str:
    title, col = WF_OVERALL.get(wf["overall"], (wf["overall"], "#94A3B8"))
    rows = []
    for s in wf["steps"]:
        ic, c, lab = WF_STYLE.get(s["status"], ("•", "#94A3B8", s["status"]))
        rows.append(f"<div style='display:flex;gap:8px;margin:5px 0'><div style='color:{c};font-weight:800;width:16px'>{ic}</div>"
                    f"<div><b>{esc(s['step'])}</b> <span style='color:{c};font-size:12.5px;font-weight:700'>({lab})</span><br>"
                    f"<span style='color:#C9D2E3;font-size:13.5px'>{esc(s['evidence'])}</span></div></div>")
    return (f"<div class='as-res' style='border-color:{col};background:{col}10'><div class='rl' style='color:{col}'>Workflow evidence · live-demo check, not the benchmark</div>"
            f"<div class='rh' style='color:{col};font-size:19px'>{esc(title)}</div>{''.join(rows) or '<div class=rr>No steps to check.</div>'}</div>")
