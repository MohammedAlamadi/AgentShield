"""Iteration-2 visual components: text tiers, icons, verdict banner, attack flow, layer strip, tiles and finding rows.
Imported by components.py (kept separate so the first-generation helpers stay readable)."""

from __future__ import annotations

import streamlit as st

from components import LAYER_STATUS, STATUS, esc

# Text tiers: values and headings in primary ink; body copy recedes to secondary; labels muted; evidence in mono.
CSS2 = """
<style>
[data-testid="stMain"] .stMarkdown p, [data-testid="stMain"] .stMarkdown li { color: var(--tx2); }
[data-testid="stMain"] .stMarkdown strong { color: var(--tx); font-weight: 600; }
.as-ph p { color: var(--tx3) !important; }
.as-ico { display: inline-flex; width: 16px; height: 16px; flex: none; }
.as-ico svg { width: 100%; height: 100%; }
.as-ibox { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 6px; flex: none;
           background: var(--s2); border: 1px solid var(--line); color: var(--tx2); }
.as-ibox.good { color: var(--good); border-color: rgba(79,167,122,.35); background: rgba(79,167,122,.08); }
.as-ibox.bad { color: var(--crit); border-color: rgba(208,96,90,.35); background: rgba(208,96,90,.08); }
.as-ibox.warn { color: var(--warn); border-color: rgba(201,154,62,.35); background: rgba(201,154,62,.08); }
.as-ibox.info { color: var(--accent); border-color: rgba(79,163,191,.35); background: rgba(79,163,191,.08); }
.as-lbl { font-size: 12px; color: var(--tx3); letter-spacing: .01em; }
.as-val { font-size: 26px; font-weight: 600; color: var(--tx); font-variant-numeric: tabular-nums; line-height: 1.15; }
.as-sm { font-size: 12.5px; color: var(--tx3); line-height: 1.45; }

.as-tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 4px 0 8px; }
.as-tile { background: var(--s1); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; display: grid; grid-template-columns: 1fr auto; gap: 2px 10px; }
.as-tile .as-lbl { grid-column: 1; }
.as-tile .as-ibox { grid-row: 1 / span 2; grid-column: 2; }
.as-tile .as-val { grid-column: 1; margin-top: 4px; }
.as-tile .as-sm { grid-column: 1 / span 2; margin-top: 6px; }

.as-st { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 500; padding: 2px 9px 2px 7px; border-radius: 999px; white-space: normal; line-height: 1.45; }
.as-st .as-ico { width: 12px; height: 12px; }
.as-st.good { color: #8FD1AE; background: rgba(79,167,122,.14); }
.as-st.bad { color: #EBA29D; background: rgba(208,96,90,.15); }
.as-st.warn { color: #E2C27E; background: rgba(201,154,62,.15); }
.as-st.neutral { color: var(--tx2); background: rgba(138,146,157,.14); }
.as-st.info { color: #9CCBDB; background: rgba(79,163,191,.14); }

.as-frow { display: grid; grid-template-columns: 30px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 11px 0; border-top: 1px solid var(--line); }
.as-frow:first-of-type { border-top: none; padding-top: 4px; }
.as-frow .t { font-size: 14px; color: var(--tx); font-weight: 500; }
.as-frow .d { font-size: 12.5px; color: var(--tx3); margin-top: 2px; }
.as-card2 { background: var(--s1); border: 1px solid var(--line); border-radius: 8px; padding: 14px 18px; height: 100%; }
.as-card2 h3 { font-size: 13px; font-weight: 600; color: var(--tx2); margin: 0 0 8px 0; }

.as-verdict { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 16px; align-items: center; background: var(--s1);
              border: 1px solid var(--line); border-left: 3px solid var(--vc); border-radius: 8px; padding: 16px 18px; margin: 6px 0 14px; }
.as-verdict .vi { width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--vc);
                  background: color-mix(in srgb, var(--vc) 13%, transparent); }
.as-verdict .vi .as-ico { width: 22px; height: 22px; }
.as-verdict .vh { font-size: 20px; font-weight: 600; color: var(--tx); line-height: 1.25; }
.as-verdict .vr { font-size: 13.5px; color: var(--tx2); margin-top: 4px; line-height: 1.5; max-width: 90ch; }
.as-verdict .vm { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
.as-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; align-items: center; }
.as-mchip { font-size: 12px; color: var(--tx2); border: 1px solid var(--line2); border-radius: 4px; padding: 1px 7px; }
.as-mchip b { color: var(--tx3); font-weight: 400; margin-right: 4px; }

.as-flow2 { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0; align-items: stretch; margin: 0 0 14px; }
.as-fn { position: relative; background: var(--s1); border: 1px solid var(--line); border-top: 2px solid var(--fc, var(--line2)); border-radius: 8px;
         padding: 12px; margin-right: 22px; min-width: 0; }
.as-fn:last-child { margin-right: 0; }
.as-fn:not(:last-child)::after { content: ''; position: absolute; right: -17px; top: 26px; width: 10px; height: 10px; border-top: 1.5px solid var(--tx3);
                                 border-right: 1.5px solid var(--tx3); transform: rotate(45deg); }
.as-fn .h { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.as-fn .h .k { font-size: 12px; color: var(--tx3); }
.as-fn .h .n { font-size: 13px; font-weight: 600; color: var(--tx); }
.as-fn .b { font-size: 12.5px; color: var(--tx2); line-height: 1.45; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; }
.as-fn .row { display: grid; grid-template-columns: 14px minmax(0, 1fr); gap: 6px; align-items: start; font-size: 12.5px; color: var(--tx2); margin: 3px 0; }
.as-fn .row .g { font-weight: 700; text-align: center; }
.as-fn .row code { font-family: 'IBM Plex Mono', ui-monospace, monospace; font-size: 11.5px; color: var(--tx); background: none; padding: 0; }
.as-fn .row .s { color: var(--tx3); }

.as-layers { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 0 0 14px; }
.as-lc { display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 4px 10px; background: var(--s1); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; }
.as-lc .n { font-size: 12px; color: var(--tx3); }
.as-lc .s { font-size: 14px; font-weight: 600; color: var(--tx); }
.as-lc .d { grid-column: 1 / span 2; font-size: 12.5px; color: var(--tx2); line-height: 1.45; margin-top: 4px; }
.as-lc.off { opacity: .55; }

.as-status { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--tx2); padding-top: 9px; }

.as-case { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px 16px; align-items: start; background: var(--s1); border: 1px solid var(--line);
           border-radius: 8px; padding: 14px 18px; margin: 10px 0 12px; }
.as-case .id { font-size: 18px; font-weight: 600; color: var(--tx); }
.as-case .rq { font-size: 13.5px; color: var(--tx2); margin-top: 3px; }
.as-case .tags { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }

.as-cmp { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 4px 0 10px; }
.as-cc { background: var(--s1); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; }
.as-cc .top { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.as-cc .nm { font-size: 14px; font-weight: 600; color: var(--tx); }
.as-cc .md { font-size: 12px; color: var(--tx3); }
.as-cc .fig { display: flex; align-items: baseline; gap: 8px; margin: 12px 0 2px; font-variant-numeric: tabular-nums; }
.as-cc .fig .a { font-size: 22px; font-weight: 600; color: var(--tx3); }
.as-cc .fig .b { font-size: 26px; font-weight: 600; color: var(--tx); }
.as-cc .fig .ar { color: var(--tx3); }

.as-bk { background: var(--s1); border: 1px solid var(--line); border-radius: 8px; padding: 14px 18px; margin: 2px 0 8px; }
.as-bk-leg { display: flex; flex-wrap: wrap; gap: 6px 16px; margin-bottom: 12px; }
.as-bk-l { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--tx2); }
.as-bk-l i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.as-bk-r { display: grid; grid-template-columns: 110px minmax(0, 1fr) 220px; gap: 14px; align-items: center; padding: 6px 0; }
.as-bk-r .k { font-size: 13px; font-weight: 600; color: var(--tx); }
.as-bk-r .bar { display: flex; height: 16px; border-radius: 3px; overflow: hidden; background: var(--s2); gap: 2px; }
.as-bk-r .seg { display: block; height: 100%; min-width: 3px; }
.as-bk-r .n { font-size: 12.5px; color: var(--tx3); font-variant-numeric: tabular-nums; text-align: right; }
.as-db-r { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 14px; align-items: center; padding: 11px 56px 11px 0; }
.as-db-r .k { font-size: 13px; font-weight: 600; color: var(--tx); line-height: 1.25; }
.as-db-r .k span { display: block; font-size: 11.5px; font-weight: 400; color: var(--tx3); }
.as-db-r .trk { position: relative; height: 12px; margin: 0 6px; background: linear-gradient(var(--line), var(--line)) center / 100% 1px no-repeat; }
.as-db-r .seg { position: absolute; top: 5px; height: 2px; background: var(--line2); }
.as-db-r .dot { position: absolute; top: 0; width: 12px; height: 12px; margin-left: -6px; border-radius: 50%; box-shadow: 0 0 0 2px var(--s1); }
.as-db-r .dot em { position: absolute; top: -3px; font-style: normal; font-size: 12px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.as-db-ax { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 14px; padding-right: 56px; }
.as-db-ax .t { position: relative; height: 16px; margin: 4px 6px 0; border-top: 1px solid var(--line); }
.as-db-ax .t span { position: absolute; top: 3px; transform: translateX(-50%); font-size: 11px; color: var(--tx3); }
.as-db-ft { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; font-size: 12px; color: var(--tx3); }
@media (max-width: 1100px) {
  .as-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .as-flow2 { grid-template-columns: repeat(2, minmax(0, 1fr)); row-gap: 12px; }
  .as-fn::after { display: none; }
  .as-fn { margin-right: 12px; }
  .as-cmp { grid-template-columns: minmax(0, 1fr); }
}
</style>
"""

_P = {  # 24x24 line icons, stroke = currentColor
    "user": '<circle cx="12" cy="8" r="3.6"/><path d="M4.5 20c.6-3.6 3.6-5.6 7.5-5.6s6.9 2 7.5 5.6"/>',
    "inject": '<path d="M14 3H6.5A1.5 1.5 0 0 0 5 4.5v15A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3v5h5"/><path d="M12 11v4.2"/><path d="M12 18h.01"/>',
    "ai": '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9.5 2.5v3M14.5 2.5v3M9.5 18.5v3M14.5 18.5v3M2.5 9.5h3M2.5 14.5h3M18.5 9.5h3M18.5 14.5h3"/>',
    "shield": '<path d="M12 3l7 3v5.5c0 4.6-3 8-7 9.5-4-1.5-7-4.9-7-9.5V6z"/>',
    "shieldok": '<path d="M12 3l7 3v5.5c0 4.6-3 8-7 9.5-4-1.5-7-4.9-7-9.5V6z"/><path d="M8.8 12.2l2.3 2.3 4.2-4.6"/>',
    "target": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r=".8"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "x": '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    "alert": '<path d="M12 3.8l9 15.7H3z"/><path d="M12 10v4.2"/><path d="M12 17h.01"/>',
    "minus": '<path d="M6.5 12h11"/>',
    "scan": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.6-4.6"/>',
    "brackets": '<path d="M8.5 6.5L4 12l4.5 5.5M15.5 6.5L20 12l-4.5 5.5"/>',
    "lock": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
    "db": '<ellipse cx="12" cy="6" rx="7" ry="2.8"/><path d="M5 6v12c0 1.5 3.1 2.8 7 2.8s7-1.3 7-2.8V6M5 12c0 1.5 3.1 2.8 7 2.8s7-1.3 7-2.8"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "review": '<circle cx="9" cy="8" r="3.2"/><path d="M3.5 19c.5-3 2.7-4.8 5.5-4.8 1.3 0 2.4.4 3.3 1"/><path d="M14 17.5l2 2 4.5-5"/>',
    "flow": '<circle cx="5.5" cy="12" r="2.2"/><circle cx="18.5" cy="6" r="2.2"/><circle cx="18.5" cy="18" r="2.2"/><path d="M7.6 11l8.7-4M7.6 13l8.7 4"/>',
    "play": '<path d="M8 5.5v13l10-6.5z"/>',
    "replay": '<path d="M4 12a8 8 0 1 0 2.4-5.7"/><path d="M4 4.5v4h4"/>',
}
KIND_ICON = {"good": "check", "bad": "x", "critical": "x", "warn": "alert", "unknown": "alert", "neutral": "minus", "none": "minus"}
KIND_VAR = {"good": "var(--good)", "bad": "var(--crit)", "critical": "var(--crit)", "warn": "var(--warn)", "unknown": "var(--warn)",
            "neutral": "var(--neu)", "none": "var(--neu)"}
KIND_CLASS = {"good": "good", "bad": "bad", "critical": "bad", "warn": "warn", "unknown": "warn", "neutral": "neutral", "none": "neutral", "info": "info"}


def inject_css2() -> None:
    st.markdown(CSS2, unsafe_allow_html=True)


def icon(name: str) -> str:
    return (f"<span class='as-ico'><svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.75' "
            f"stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'>{_P[name]}</svg></span>")


def ibox(name: str, kind: str = "") -> str:
    return f"<span class='as-ibox {KIND_CLASS.get(kind, '') if kind else ''}'>{icon(name)}</span>"


def st_tag(label: str, kind: str = "neutral", glyph: bool = True) -> str:
    k = KIND_CLASS.get(kind, "neutral")
    g = icon(KIND_ICON[kind]) if glyph and kind in KIND_ICON else ""
    return f"<span class='as-st {k}'>{g}{esc(label)}</span>"


def tile(label: str, value: str, sub: str, icon_name: str, kind: str = "") -> str:
    return (f"<div class='as-tile'><div class='as-lbl'>{esc(label)}</div>{ibox(icon_name, kind)}<div class='as-val'>{esc(value)}</div>"
            f"<div class='as-sm'>{sub}</div></div>")


def frow(icon_name: str, kind: str, title: str, detail: str, right: str = "") -> str:
    return (f"<div class='as-frow'>{ibox(icon_name, kind)}<div><div class='t'>{esc(title)}</div><div class='d'>{esc(detail)}</div></div>"
            f"<div>{right}</div></div>")


def first_sentence(text: str, limit: int = 220) -> str:
    t = (text or "").strip()
    i = t.find(". ")
    if 0 < i < limit:
        return t[: i + 1]
    return t if len(t) <= limit else t[: limit - 1].rstrip() + "…"


def task_label(headline: str) -> str:
    t = headline.replace("Benchmark: ", "").strip()
    return t[:1].upper() + t[1:] if t else t


def verdict_banner(story: dict, meta: list[tuple[str, str]], mode_tag: str) -> str:
    a, l = story["attack"], story["legit"]
    kind = a["status"]
    col = KIND_VAR.get(kind, "var(--neu)")
    ic = {"good": "shieldok", "bad": "x", "unknown": "alert"}.get(kind, "minus")
    # human-reviewed verdicts keep their full reason: it carries the reviewers' recorded AI-assistance disclosure
    reason = a["reason"] if "review" in a["reason"].lower() else first_sentence(a["reason"], 260)
    chips = "".join(f"<span class='as-mchip'><b>{esc(k)}</b>{esc(v)}</span>" for k, v in meta)
    return (f"<div class='as-verdict' style='--vc:{col}'><div class='vi'>{icon(ic)}</div>"
            f"<div><div class='vh'>{esc(a['headline'])}</div><div class='vr'>{esc(reason)}</div><div class='as-meta'>{mode_tag}{chips}</div></div>"
            f"<div class='vm'><span class='as-lbl'>User's task</span>{st_tag(task_label(l['headline']), l['status'])}</div></div>")


_CALL = {"executed": ("ok", "ran"), "executed_error": ("warn", "tool error"), "blocked_l3": ("deny", "denied by Layer 3"),
         "quarantined_l1": ("deny", "output withheld by Layer 1"), "invalid": ("warn", "malformed, rejected"), "over_limit": ("warn", "beyond call limit")}


def flow_html(story: dict, calls: list[dict], attacker_calls: set, layer_on: dict) -> str:
    """Trusted request -> injected content -> AI actions -> layer decisions -> outcome."""
    a, l = story["attack"], story["legit"]
    att = story["attacker"]
    n1 = (f"<div class='as-fn'><div class='h'>{ibox('user')}<div><div class='k'>Trusted</div><div class='n'>User request</div></div></div>"
          f"<div class='b'>{esc(story['user_request'])}</div></div>")
    if att:
        kind = esc((att.get("source") or {}).get("kind", "content"))
        n2 = (f"<div class='as-fn' style='--fc:var(--crit)'><div class='h'>{ibox('inject', 'bad')}<div><div class='k'>Untrusted, in {kind}</div>"
              f"<div class='n'>Injected instruction</div></div></div><div class='b'>{esc(att['objective'])}</div></div>")
    else:
        n2 = (f"<div class='as-fn'><div class='h'>{ibox('inject')}<div><div class='k'>Untrusted content</div><div class='n'>No injection</div></div></div>"
              f"<div class='b'>Benign task: measures usefulness and false alarms.</div></div>")
    rows = []
    for c in calls[:5]:
        k, lab = _CALL.get(c.get("status"), ("ok", c.get("status") or ""))
        is_att = c.get("index") in attacker_calls
        g, col = {"ok": ("✓", "var(--tx3)"), "warn": ("!", "var(--warn)"),
                  "deny": ("✕", "var(--good)" if is_att else "var(--tx)")}.get(k, ("•", "var(--tx3)"))
        if k == "ok" and is_att:
            g, col = "!", "var(--crit)"
        goal = " <span style='color:var(--crit)'>attacker's goal</span>" if is_att else ""
        rows.append(f"<div class='row'><span class='g' style='color:{col}'>{g}</span><span><code>{esc(c.get('name'))}</code> "
                    f"<span class='s'>{esc(lab)}</span>{goal}</span></div>")
    if len(calls) > 5:
        rows.append(f"<div class='row'><span class='g'>…</span><span class='s'>{len(calls) - 5} more in the trace</span></div>")
    if not rows:
        rows.append("<div class='row'><span class='g'>–</span><span class='s'>No tool call; answered directly</span></div>")
    n3 = (f"<div class='as-fn'><div class='h'>{ibox('ai')}<div><div class='k'>{len(calls)} tool call{'s' if len(calls) != 1 else ''}</div>"
          f"<div class='n'>AI actions</div></div></div>{''.join(rows)}</div>")
    lrows = []
    for key, short in (("L1", "Detector"), ("L2", "Isolation"), ("L3", "Guard")):
        lay = story["layers"][key]
        label, kind = LAYER_STATUS.get(lay["status"], (lay["status"], "neutral"))
        g, col = STATUS.get(kind, STATUS["neutral"])
        lrows.append(f"<div class='row'><span class='g' style='color:{col}'>{g}</span><span><span style='color:var(--tx)'>{short}</span> "
                     f"<span class='s'>{esc(label.lower())}</span></span></div>")
    n4 = (f"<div class='as-fn'><div class='h'>{ibox('shield')}<div><div class='k'>{sum(layer_on.values())} of 3 switched on</div>"
          f"<div class='n'>Defence layers</div></div></div>{''.join(lrows)}</div>")
    ak, lk = a["status"], l["status"]
    n5 = (f"<div class='as-fn' style='--fc:{KIND_VAR.get(ak, 'var(--neu)')}'><div class='h'>{ibox('target', ak)}<div><div class='k'>Verdict</div>"
          f"<div class='n'>Outcome</div></div></div>"
          f"<div class='row'><span class='g' style='color:{KIND_VAR.get(ak, 'var(--neu)')}'>{STATUS.get(ak, STATUS['neutral'])[0]}</span>"
          f"<span style='color:var(--tx)'>{esc(a['headline'])}</span></div>"
          f"<div class='row'><span class='g' style='color:{KIND_VAR.get(lk, 'var(--neu)')}'>{STATUS.get(lk, STATUS['neutral'])[0]}</span>"
          f"<span>{esc(task_label(l['headline']))}</span></div></div>")
    return f"<div class='as-flow2'>{n1}{n2}{n3}{n4}{n5}</div>"


_LAYER_ICON = {"L1": "scan", "L2": "brackets", "L3": "lock"}


def layer_strip(story: dict) -> str:
    out = []
    for key, name in (("L1", "Layer 1, injection detector"), ("L2", "Layer 2, content isolation"), ("L3", "Layer 3, action guard")):
        lay = story["layers"][key]
        label, kind = LAYER_STATUS.get(lay["status"], (lay["status"], "neutral"))
        off = " off" if lay["status"] == "off" else ""
        out.append(f"<div class='as-lc{off}'>{ibox(_LAYER_ICON[key], kind if kind != 'neutral' else '')}<div><div class='n'>{esc(name)}</div>"
                   f"<div class='s'>{esc(label)}</div></div><div class='d'>{esc(first_sentence(lay['summary'], 180))}</div></div>")
    return f"<div class='as-layers'>{''.join(out)}</div>"
