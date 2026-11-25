"""Shared visual components for the AgentShield dashboard (design system: dashboard/DESIGN_SYSTEM.md).

Most styling comes from the native Streamlit theme in .streamlit/config.toml; the CSS below covers only the few
components Streamlit has no primitive for (decision trace, status tags, key/value rows, run story panels).
All dynamic text is HTML-escaped: logs contain attacker-controlled text, including HTML comments.
"""

from __future__ import annotations

import html
import json
from typing import Any

import streamlit as st

# ------------------------------------------------------------------ tokens
T = {
    "page": "#121418", "s1": "#181B20", "s2": "#1E2228", "line": "#2A2F36", "line2": "#363C45",
    "tx": "#E4E7EB", "tx2": "#A9B1BC", "tx3": "#7C8591", "accent": "#4FA3BF",
    "good": "#4FA77A", "critical": "#D0605A", "warning": "#C99A3E", "neutral": "#8A929D",
}
# Backwards-compatible names used by older callers; every value maps onto the token set above.
C = {"bg": T["page"], "panel": T["s1"], "panel2": T["s2"], "line": T["line"], "text": T["tx"], "muted": T["tx3"],
     "cyan": T["accent"], "green": T["good"], "red": T["critical"], "amber": T["warning"], "violet": T["tx2"], "orange": T["tx2"], "blue": T["tx2"]}
# Chart series colours, used only where a chart needs configuration identity (dataviz reference dark order,
# validated on #181B20: CVD worst adjacent dE 8.4, normal-vision 19.3, contrast >= 3:1).
SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"]
CONFIG_COLOR = dict(zip(["unprotected", "l1_only", "l2_only", "l3_only", "full"], SERIES))
STATUS = {"good": ("✓", T["good"]), "bad": ("✕", T["critical"]), "critical": ("✕", T["critical"]), "warn": ("!", T["warning"]),
          "unknown": ("!", T["warning"]), "neutral": ("–", T["neutral"]), "none": ("–", T["neutral"])}
OUTCOME_COLOR = {"good": T["good"], "bad": T["critical"], "unknown": T["warning"], "neutral": T["neutral"], "none": T["neutral"]}

CSS = f"""
<style>
:root {{ --page:{T['page']}; --s1:{T['s1']}; --s2:{T['s2']}; --line:{T['line']}; --line2:{T['line2']}; --tx:{T['tx']}; --tx2:{T['tx2']};
         --tx3:{T['tx3']}; --accent:{T['accent']}; --good:{T['good']}; --crit:{T['critical']}; --warn:{T['warning']}; --neu:{T['neutral']}; }}
.block-container {{ max-width: 1320px; padding-top: 3.6rem; padding-bottom: 3rem; }}
[data-testid="stMain"] p, [data-testid="stMain"] li {{ line-height: 1.55; }}
[data-testid="stCaptionContainer"] p {{ color: var(--tx3); }}
[data-testid="stExpander"] details {{ border-color: var(--line); background: var(--s1); }}
[data-testid="stExpander"] summary p {{ font-weight: 500; }}
:focus-visible {{ outline: 2px solid var(--accent) !important; outline-offset: 2px; }}

/* page header */
.as-ph {{ margin: 0 0 6px 0; padding-bottom: 14px; border-bottom: 1px solid var(--line); }}
.as-ph h1 {{ font-size: 22px; font-weight: 600; margin: 0; padding: 0; letter-spacing: -0.005em; color: var(--tx); }}
.as-ph p {{ color: var(--tx2); margin: 4px 0 0 0; font-size: 14px; max-width: 78ch; }}
.as-ph [data-testid="stHeaderActionElements"], .as-ph h1 a {{ display: none !important; }}
.as-fig {{ display: flex; align-items: baseline; gap: 10px; font-size: 24px; font-weight: 600; color: var(--tx); font-variant-numeric: tabular-nums; margin: 4px 0 2px; }}
.as-fig .to {{ font-size: 13px; font-weight: 400; color: var(--tx3); }}
.as-h2 {{ font-size: 16px; font-weight: 600; color: var(--tx); margin: 22px 0 4px 0; }}
.as-sub {{ color: var(--tx3); font-size: 13px; margin: 0 0 10px 0; max-width: 90ch; }}

/* panels */
.as-panel {{ background: var(--s1); border: 1px solid var(--line); border-radius: 6px; padding: 14px 16px; margin-bottom: 12px; }}
.as-panel.fill {{ height: 100%; }}
.as-panel h3 {{ font-size: 14px; font-weight: 600; margin: 0 0 8px 0; color: var(--tx); }}
.as-note {{ color: var(--tx3); font-size: 13px; line-height: 1.5; }}
.as-explain {{ color: var(--tx2); font-size: 13.5px; line-height: 1.55; margin: 0 0 12px 0; max-width: 95ch; }}
.as-warnbox {{ border: 1px solid var(--line); border-left: 3px solid var(--warn); background: var(--s1); border-radius: 4px;
               padding: 9px 12px; color: var(--tx2); font-size: 13.5px; line-height: 1.5; margin: 0 0 12px 0; }}

/* key / value rows */
.as-kv {{ display: grid; grid-template-columns: max-content 1fr; gap: 4px 18px; font-size: 13.5px; margin: 0; }}
.as-kv dt {{ color: var(--tx3); }}
.as-kv dd {{ color: var(--tx); margin: 0; }}

.as-kvi {{ display: flex; flex-wrap: wrap; gap: 6px 22px; font-size: 13.5px; color: var(--tx); margin: 0 0 12px 2px; }}
.as-kvi .k {{ color: var(--tx3); margin-right: 4px; }}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primary"] p {{ color: #0F1A1F !important; font-weight: 600; }}

/* stats */
.as-stat {{ background: var(--s1); border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; height: 100%; }}
.as-stat .l {{ color: var(--tx2); font-size: 13px; }}
.as-stat .n {{ font-size: 21px; font-weight: 600; margin: 4px 0 2px; font-variant-numeric: tabular-nums; color: var(--tx); }}
.as-stat .d {{ color: var(--tx3); font-size: 12.5px; line-height: 1.45; }}

/* status tags: glyph + label, never colour alone */
.as-tag {{ display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 500; padding: 2px 8px; border-radius: 4px;
           border: 1px solid var(--line2); background: var(--s2); color: var(--tx); margin: 2px 6px 2px 0; white-space: nowrap; }}
.as-tag .g {{ font-weight: 700; width: 10px; text-align: center; }}
.as-chip {{ display: inline-block; font-size: 12px; padding: 1px 7px; border-radius: 4px; border: 1px solid var(--line2); color: var(--tx2); margin: 2px 6px 2px 0; }}
.as-chip.on {{ color: var(--tx); border-color: var(--accent); }}

/* mode line (live vs recorded) */
.as-mode {{ display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; border: 1px solid var(--line); background: var(--s1); border-radius: 6px;
            padding: 9px 12px; margin: 4px 0 12px 0; font-size: 13.5px; color: var(--tx2); }}
.as-mode b {{ color: var(--tx); font-weight: 600; }}
.as-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 2px; }}

/* decision trace */
.as-trace {{ border: 1px solid var(--line); border-radius: 6px; overflow: hidden; background: var(--s1); }}
.as-tr {{ display: grid; grid-template-columns: 64px 150px minmax(0, 1fr) 128px; gap: 0 12px; padding: 8px 12px; border-top: 1px solid var(--line); align-items: start; }}
.as-tr:first-child {{ border-top: none; }}
.as-tr.hd {{ background: var(--s2); color: var(--tx3); font-size: 12.5px; padding-top: 6px; padding-bottom: 6px; }}
.as-tr .t {{ color: var(--tx3); font-size: 12px; font-variant-numeric: tabular-nums; padding-top: 1px; }}
.as-tr .a {{ color: var(--tx2); font-size: 13px; }}
.as-tr .e {{ font-size: 13.5px; color: var(--tx); min-width: 0; }}
.as-tr .b {{ margin-top: 4px; font-family: 'IBM Plex Mono', ui-monospace, monospace; font-size: 12px; color: var(--tx2); white-space: pre-wrap;
             word-break: break-word; max-height: 168px; overflow: auto; background: var(--page); border: 1px solid var(--line); border-radius: 4px; padding: 6px 8px; }}
.as-tr .v {{ font-size: 12.5px; color: var(--tx3); }}
.as-tr .v.strong {{ color: var(--tx); font-weight: 600; }}
.as-tr.deny {{ background: rgba(201, 154, 62, 0.06); }}

/* run story */
.as-step-h {{ display: flex; align-items: baseline; gap: 10px; margin: 2px 0 8px 0; }}
.as-num {{ width: 22px; height: 22px; border-radius: 50%; border: 1px solid var(--line2); color: var(--tx2); font-size: 12px; font-weight: 600;
           display: inline-flex; align-items: center; justify-content: center; flex: none; position: relative; top: -1px; }}
.as-step-t {{ font-size: 15px; font-weight: 600; color: var(--tx); }}
.as-step-s {{ color: var(--tx3); font-size: 13px; margin-left: auto; }}
.as-big {{ font-size: 16px; line-height: 1.5; color: var(--tx); }}
.as-quote {{ font-family: 'IBM Plex Mono', ui-monospace, monospace; font-size: 12.5px; line-height: 1.55; background: var(--page); border: 1px solid var(--line);
             border-radius: 4px; padding: 9px 11px; white-space: pre-wrap; word-break: break-word; color: var(--tx2); }}
.as-inject {{ color: var(--tx); background: rgba(208, 96, 90, 0.16); border-bottom: 1px solid var(--crit); padding: 0 2px; }}
.as-act {{ display: grid; grid-template-columns: 22px minmax(0, 1fr); gap: 8px; padding: 8px 2px; border-top: 1px solid var(--line); font-size: 14px; line-height: 1.5; }}
.as-act:first-of-type {{ border-top: none; }}
.as-act .ic {{ color: var(--tx3); font-weight: 700; text-align: center; }}
.as-act .ic.deny {{ color: var(--tx); }}
.as-flag {{ display: inline-block; font-size: 12px; padding: 0 6px; border-radius: 4px; margin-left: 6px; border: 1px solid var(--line2); color: var(--tx2); }}
.as-flag.goal {{ border-color: rgba(208, 96, 90, 0.6); color: #E3A29D; }}
.as-layer {{ background: var(--s1); border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; height: 100%; }}
.as-layer .ln {{ font-size: 13px; color: var(--tx2); }}
.as-layer .ls {{ margin: 6px 0 6px 0; }}
.as-layer .lt {{ font-size: 13.5px; line-height: 1.5; color: var(--tx); }}
.as-layer .ld {{ font-size: 12.5px; color: var(--tx3); margin-top: 6px; line-height: 1.45; }}
.as-layer.off {{ opacity: .6; }}
.as-res {{ background: var(--s1); border: 1px solid var(--line); border-left: 3px solid var(--stc); border-radius: 6px; padding: 12px 14px; height: 100%; }}
.as-res .rl {{ font-size: 13px; color: var(--tx3); }}
.as-res .rh {{ font-size: 17px; font-weight: 600; margin: 4px 0 6px 0; color: var(--tx); display: flex; gap: 8px; align-items: baseline; }}
.as-res .rh .g {{ color: var(--stc); font-weight: 700; }}
.as-res .rr {{ font-size: 13.5px; line-height: 1.5; color: var(--tx2); }}
.as-wf {{ display: grid; grid-template-columns: 16px minmax(0, 1fr); gap: 8px; margin: 7px 0; font-size: 13.5px; }}
.as-progress {{ display: flex; gap: 6px; margin: 4px 0 12px 0; }}
.as-progress div {{ flex: 1; height: 3px; border-radius: 2px; background: var(--line); }}
.as-progress div.on {{ background: var(--accent); }}
.as-guide {{ background: var(--s1); border: 1px solid var(--line); border-radius: 6px; padding: 20px 24px; min-height: 300px; }}

/* overview */
.as-finding {{ border-top: 1px solid var(--line); padding: 10px 0; font-size: 14px; line-height: 1.55; color: var(--tx); }}
.as-finding:first-of-type {{ border-top: none; padding-top: 2px; }}
.as-finding .src {{ color: var(--tx3); font-size: 12.5px; margin-top: 2px; }}

/* methodology pipeline */
.as-flow {{ display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; background: var(--s1); }}
.as-node {{ padding: 12px 12px; border-left: 1px solid var(--line); }}
.as-node:first-child {{ border-left: none; }}
.as-node .k {{ font-size: 12px; color: var(--tx3); }}
.as-node .t {{ font-size: 13.5px; font-weight: 600; margin-top: 2px; color: var(--tx); }}
.as-node .d {{ font-size: 12.5px; color: var(--tx2); margin-top: 4px; line-height: 1.45; }}
.as-node .x {{ font-size: 12.5px; color: var(--tx); margin-top: 6px; }}
.as-node.layer {{ background: var(--s2); }}
@media (max-width: 1100px) {{ .as-flow {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .as-node {{ border-top: 1px solid var(--line); }} }}
@media (max-width: 900px) {{ .as-tr {{ grid-template-columns: 54px minmax(0, 1fr) 110px; }} .as-tr .a {{ display: none; }} }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def inject_story_css() -> None:  # kept for callers; the story styles are part of the single stylesheet
    return None


def pct(x: Any, signed: bool = False) -> str:
    """Percent with one decimal, rounded half-up on the stored 4-decimal value (the report's rounding)."""
    if x is None:
        return "—"
    from decimal import ROUND_HALF_UP, Decimal
    v = (Decimal(str(x)) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)  # Decimal first: 0.5025 * 100 is 50.2499… in float
    return (f"{v:+}" if signed else f"{v}") + "%"


def ci(c: Any) -> str:
    return "" if not c else f"[{pct(c[0])[:-1]}, {pct(c[1])[:-1]}]"


def esc(x: Any) -> str:
    return html.escape("" if x is None else (x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)))


# ------------------------------------------------------------------ page structure
def page_header(title: str, subtitle: str) -> None:
    st.markdown(f"<div class='as-ph'><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>", unsafe_allow_html=True)


hero = page_header


def section(title: str, subtitle: str = "") -> None:
    st.markdown(f"<div class='as-h2'>{esc(title)}</div>" + (f"<div class='as-sub'>{esc(subtitle)}</div>" if subtitle else ""), unsafe_allow_html=True)


def kv(rows: list[tuple[str, str]], raw: bool = False) -> str:
    return "<dl class='as-kv'>" + "".join(f"<dt>{esc(k)}</dt><dd>{v if raw else esc(v)}</dd>" for k, v in rows) + "</dl>"


def kv_inline(rows: list[tuple[str, str]]) -> str:
    return "<div class='as-kvi'>" + "".join(f"<span><span class='k'>{esc(k)}</span> {esc(v)}</span>" for k, v in rows) + "</div>"


def card(label: str, value: str, kind: str = "", raw_html: bool = False) -> None:
    v = value if raw_html else esc(value)
    st.markdown(f"<div class='as-panel {kind}'><h3>{esc(label)}</h3><div>{v}</div></div>", unsafe_allow_html=True)


def kpi(label: str, number: str, desc: str = "", color: str | None = None) -> None:  # colour is ignored: figures stay in text ink
    st.markdown(f"<div class='as-stat'><div class='l'>{esc(label)}</div><div class='n'>{esc(number)}</div><div class='d'>{esc(desc)}</div></div>", unsafe_allow_html=True)


def tag(label: str, kind: str = "neutral") -> str:
    g, col = STATUS.get(kind, STATUS["neutral"])
    return f"<span class='as-tag'><span class='g' style='color:{col}'>{g}</span>{esc(label)}</span>"


def pill(text: str, color: str | None = None, filled: bool = False) -> str:
    return f"<span class='as-chip{' on' if filled and color == T['accent'] else ''}'>{esc(text)}</span>"


def explain(text: str) -> None:
    st.markdown(f"<div class='as-explain'>{esc(text)}</div>", unsafe_allow_html=True)


def warnbox(text: str) -> None:
    st.markdown(f"<div class='as-warnbox'>{esc(text)}</div>", unsafe_allow_html=True)


def layer_pills(layers: dict[str, bool]) -> str:
    names = {"L1 detector": "Layer 1 detector", "L2 isolation": "Layer 2 isolation", "L3 guard": "Layer 3 guard"}
    return "".join(f"<span class='as-chip{' on' if v else ''}'>{esc(names.get(k, k))}: {'on' if v else 'off'}</span>" for k, v in layers.items())


def highlight_injection(full_text: str, injected: str | None) -> str:
    t = esc(full_text)
    if injected:
        i = esc(injected)
        t = t.replace(i, f"<span class='as-inject'>{i}</span>")
    return t


def outcome_banner(text: str, kind: str) -> None:
    st.markdown(tag(text, {"good": "good", "bad": "bad", "warn": "warn"}.get(kind, "neutral")), unsafe_allow_html=True)


# ------------------------------------------------------------------ decision trace
_ACTOR = {"Trusted input": "User", "Model": "Model", "Agent": "Model proposal", "Tool (simulated)": "Simulated tool",
          "Argument validation": "Argument check", "Layer 1 detector": "Layer 1 detector", "Layer 2 isolation": "Layer 2 isolation",
          "Layer 3 guard": "Layer 3 guard", "AgentShield": "AgentShield", "Runtime": "Runtime", "Frozen verifier": "Verifier"}


def _verdict(s: dict[str, Any]) -> tuple[str, bool]:
    k, st_ = s["kind"], s["status"]
    if k == "guard":
        return ("Denied", True) if st_ == "block" else ("Allowed", False)
    if k == "detector":
        return ("Withheld", True) if st_ == "block" else ("Passed", False)
    if k == "invalid":
        return ("Rejected", True)
    if k == "executed":
        return ("Executed", False) if st_ == "ok" else ("Tool error", False)
    if k == "proposed":
        return ("Over limit", True) if st_ == "warn" else ("Proposed", False)
    if k == "isolation":
        return ("Wrapped", False)
    if k == "error":
        return ("Error", True)
    if k == "final":
        return ("Answer", False)
    if k == "end":
        return ("Ended", False)
    return ("", False)


def timeline_html(steps: list[dict[str, Any]], show_model_text: bool = True) -> str:
    out = ["<div class='as-trace'><div class='as-tr hd'><div>Time</div><div>Component</div><div>Event</div><div>Decision</div></div>"]
    for s in steps:
        if s["kind"] == "model" and not show_model_text:
            continue
        ts = f"+{s['t_s']:.2f}s" if isinstance(s.get("t_s"), (int, float)) else ""
        verdict, strong = _verdict(s)
        body = f"<div class='b'>{esc(s['body'])}</div>" if s.get("body") else ""
        deny = " deny" if strong and s["kind"] in ("guard", "detector") else ""
        out.append(f"<div class='as-tr{deny}'><div class='t'>{ts}</div><div class='a'>{esc(_ACTOR.get(s['layer'], s['layer']))}</div>"
                   f"<div class='e'>{esc(s['title'])}{body}</div><div class='v{' strong' if strong else ''}'>{esc(verdict)}</div></div>")
    out.append("</div>")
    return "".join(out)


def outcome_kind(badges: dict[str, str]) -> str:
    a = badges.get("attack", "")
    if "SUCCEEDED" in a:
        return "bad"
    if "not determined" in a or "MANUAL" in a or "inconclusive" in badges.get("run", ""):
        return "warn"
    return "good" if ("did not succeed" in a or "benign" in a) and "NOT completed" not in badges.get("legit", "") else "neutral"


# ------------------------------------------------------------------ run story
LAYER_TITLE = {"L1": "Layer 1, injection detector", "L2": "Layer 2, content isolation", "L3": "Layer 3, action guard"}
LAYER_STATUS = {  # status -> (label, status kind)
    "acted": ("Stopped the attacker's action", "good"), "bypassed": ("Partly bypassed", "warn"), "missed": ("Missed the injection", "warn"),
    "false_alarm": ("False alarm", "warn"), "influenced": ("Labelled, model still influenced", "warn"), "labelled": ("Labelled as untrusted", "neutral"),
    "passed": ("Nothing flagged", "neutral"), "allowed": ("Allowed all actions", "neutral"), "denied_other": ("Denied agent mistakes", "neutral"),
    "idle": ("Nothing to do", "neutral"), "off": ("Switched off", "neutral"),
}
STEP_TITLES = ["The user's request", "The attacker's hidden instruction", "What the AI did", "How each layer responded", "Outcome"]


def step_header(n: int, sub: str = "") -> str:
    return (f"<div class='as-step-h'><span class='as-num'>{n}</span><span class='as-step-t'>{esc(STEP_TITLES[n - 1])}</span>"
            f"<span class='as-step-s'>{esc(sub)}</span></div>")


def result_card(label: str, outcome: dict, big: bool = False) -> str:
    g, col = STATUS.get(outcome["status"], STATUS["neutral"])
    return (f"<div class='as-res' style='--stc:{col}'><div class='rl'>{esc(label)}</div>"
            f"<div class='rh'><span class='g'>{g}</span><span>{esc(outcome['headline'])}</span></div><div class='rr'>{esc(outcome['reason'])}</div></div>")


def layer_card(key: str, layer: dict) -> str:
    label, kind = LAYER_STATUS.get(layer["status"], (layer["status"], "neutral"))
    det = "".join(f"<div class='ld'>{esc(d)}</div>" for d in layer["details"][:4])
    off = " off" if layer["status"] == "off" else ""
    return (f"<div class='as-layer{off}'><div class='ln'>{esc(LAYER_TITLE[key])}</div><div class='ls'>{tag(label, kind)}</div>"
            f"<div class='lt'>{esc(layer['summary'])}</div>{det}</div>")


ACT_ICON = {"done": "✓", "blocked": "✕", "quarantined": "■", "failed": "!", "other": "•"}


def actions_html(story: dict) -> str:
    rows = []
    for a in story["actions"]:
        ic = ACT_ICON.get(a["kind"], "•")
        flags = ""
        if a["attacker_goal"]:
            flags += "<span class='as-flag goal'>attacker's goal</span>"
        if a["read_injection"]:
            flags += "<span class='as-flag'>contained the injection</span>"
        cls = " deny" if a["kind"] in ("blocked", "quarantined") else ""
        rows.append(f"<div class='as-act'><div class='ic{cls}'>{ic}</div><div>{esc(a['text'])}{flags}</div></div>")
    if not rows:
        rows.append("<div class='as-act'><div class='ic'>•</div><div>The AI did not use any tool; it only wrote an answer.</div></div>")
    fa = story.get("final_answer")
    if fa:
        short = fa if len(fa) <= 420 else fa[:417] + "…"
        rows.append(f"<div class='as-act'><div class='ic'>&gt;</div><div><span style='color:var(--tx3)'>Answer to the user</span><br>“{esc(short)}”</div></div>")
    return "".join(rows)


def question_header(n: int, title: str, sub: str = "") -> str:  # kept for compatibility; questions are not a sequence
    return f"<div class='as-h2'>{esc(title)}</div>" + (f"<div class='as-sub'>{esc(sub)}</div>" if sub else "")


WF_STYLE = {"completed": ("good", "done"), "not_done": ("bad", "not done"), "failed": ("warn", "tried, did not happen"),
            "unverified": ("neutral", "not provable from the log")}
WF_OVERALL = {"complete": ("Every requested step is in the log", "good"), "incomplete": ("Not every requested step happened", "warn"),
              "partly unverified": ("Some steps cannot be proven from the log", "neutral"), "unverified": ("Nothing to assess", "neutral")}


def workflow_card(wf: dict) -> str:
    title, kind = WF_OVERALL.get(wf["overall"], (wf["overall"], "neutral"))
    g, col = STATUS[kind]
    rows = []
    for s in wf["steps"]:
        k, lab = WF_STYLE.get(s["status"], ("neutral", s["status"]))
        sg, sc = STATUS[k]
        rows.append(f"<div class='as-wf'><div style='color:{sc};font-weight:700'>{sg}</div><div><span style='color:var(--tx)'>{esc(s['step'])}</span>"
                    f" <span style='color:var(--tx3)'>({lab})</span><br><span style='color:var(--tx2);font-size:13px'>{esc(s['evidence'])}</span></div></div>")
    return (f"<div class='as-res' style='--stc:{col}'><div class='rl'>Workflow evidence (demo check, not the benchmark)</div>"
            f"<div class='rh'><span class='g'>{g}</span><span>{esc(title)}</span></div>{''.join(rows) or '<div class=rr>No steps to check.</div>'}</div>")


# ------------------------------------------------------------------ charts (Altair) — dataviz mark specs
CHART_AXIS = {"labelColor": T["tx2"], "titleColor": T["tx3"], "gridColor": "#252930", "domainColor": T["line2"], "tickColor": T["line2"],
              "labelFont": "IBM Plex Sans", "titleFont": "IBM Plex Sans", "labelFontSize": 12, "titleFontSize": 12, "titleFontWeight": 500}


def chart(c):
    """Apply the shared chart chrome: recessive grid and axes, text-token ink, transparent background."""
    return (c.configure_view(strokeWidth=0).configure_axis(**CHART_AXIS)
            .configure_legend(labelColor=T["tx2"], titleColor=T["tx3"], labelFont="IBM Plex Sans", titleFont="IBM Plex Sans", labelFontSize=12, titleFontSize=12, orient="top")
            .configure_header(labelColor=T["tx"], labelFont="IBM Plex Sans", labelFontSize=13, labelFontWeight=600, titleColor=T["tx3"])
            .configure_text(font="IBM Plex Sans")
            .configure(background="transparent", font="IBM Plex Sans", padding={"left": 12, "right": 8, "top": 4, "bottom": 4}))
