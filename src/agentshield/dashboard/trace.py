"""Turn a run's logged events into an ordered timeline for display. Only recorded events become steps: a layer that
logged nothing for a call shows nothing (no decision is ever inferred). Used for live runs and recorded replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..isolation import SYSTEM_PROMPT_ADDENDUM
from ..logging_jsonl import read_jsonl


def load_events(log_path: str | Path) -> list[dict[str, Any]]:
    return read_jsonl(log_path)


def run_header(events: list[dict[str, Any]]) -> dict[str, Any]:
    start = next((e for e in events if e["event"] == "run_start"), {})
    end = next((e for e in reversed(events) if e["event"] == "run_end"), None)
    system = next((e["content"] for e in events if e["event"] == "message" and e.get("role") == "system"), "")
    cfg = start.get("config") or {}
    return {
        "run_id": start.get("run_id"), "scenario_id": start.get("scenario_id"), "category": start.get("category"),
        "is_attack": start.get("is_attack"), "config": cfg.get("name"),
        "layers": {"L1 detector": bool(cfg.get("detector")), "L2 isolation": bool(cfg.get("isolation")), "L3 guard": bool(cfg.get("guard"))},
        "detector_threshold": cfg.get("detector_threshold"), "max_tool_calls": cfg.get("max_tool_calls"),
        "model_settings": start.get("model_settings"), "scope": start.get("scope"), "prompt_version": start.get("prompt_version"),
        "l2_addendum_in_system_prompt": SYSTEM_PROMPT_ADDENDUM in system, "system_prompt": system,
        "user_request": next((e["content"] for e in events if e["event"] == "message" and e.get("role") == "user"), None),
        "complete": end is not None, "end": end,
    }


def _short(v: Any, n: int = 1200) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[: n - 3] + "..."


def timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordered steps: {kind, layer, status, title, body, data, t_s}. status: info | allow | block | warn | ok | fail."""
    steps: list[dict[str, Any]] = []

    def add(kind, layer, status, title, body="", data=None, t=None):
        steps.append({"kind": kind, "layer": layer, "status": status, "title": title, "body": body, "data": data, "t_s": t})

    for e in events:
        ev, t = e["event"], e.get("t_s")
        if ev == "message" and e.get("role") == "user":
            add("user", "Trusted input", "info", "User request (trusted)", e["content"], t=t)
        elif ev == "model_turn":
            calls = e.get("tool_calls") or []
            add("model", "Model", "info", f"Model turn ({len(calls)} tool call(s) proposed)" if calls else "Model turn",
                _short(e.get("content") or "", 1500), {"duration_s": e.get("duration_s")}, t)
        elif ev == "proposed_tool_call":
            flag = " (repeated)" if e.get("repeated") else ""
            over = e.get("status") == "over_limit"
            add("proposed", "Agent", "warn" if over else "info", f"Proposed #{e['index']}: {e['name']}{flag}" + (" - beyond the six-call limit" if over else ""),
                _short(e.get("arguments")), {"arguments": e.get("arguments"), "source": e.get("source")}, t)
        elif ev == "invalid_tool_call":
            add("invalid", "Argument validation", "warn", f"Invalid call #{e.get('index')} rejected by argument validation (not a defence layer)", e.get("reason", ""), t=t)
        elif ev == "guard_decision":
            add("guard", "Layer 3 guard", "allow" if e["allowed"] else "block", f"L3 {'ALLOW' if e['allowed'] else 'DENY'} #{e['index']} {e['name']}", e.get("reason", ""),
                {"arguments": e.get("arguments")}, t)
        elif ev == "tool_executed":
            add("executed", "Tool (simulated)", "ok" if e.get("ok") else "warn", f"Executed #{e['index']} {e['name']}" + (f"  - untrusted sources {e['sources']}" if e.get("sources") else ""),
                _short(e.get("output") or "", 1500), {"sources": e.get("sources")}, t)
        elif ev == "detector_decision":
            add("detector", "Layer 1 detector", "block" if e["flagged"] else "allow",
                f"L1 {'QUARANTINE' if e['flagged'] else 'pass'}: max score {e['max_score']:.4f} over {e['n_chunks']} chunk(s)",
                f"Sources: {e.get('sources')}  |  {round((e.get('seconds') or 0) * 1000)} ms", {"max_score": e["max_score"], "chunk_scores": e.get("chunk_scores"), "flagged": e["flagged"]}, t)
        elif ev == "isolation_applied":
            if e.get("sources"):
                add("isolation", "Layer 2 isolation", "info", f"L2 wrapped {e.get('sources')} as untrusted (escaped tags: {e.get('escaped_tags', 0)})", _short(e.get("wrapped") or "", 1500), t=t)
            else:
                add("isolation", "Layer 2 isolation", "info", "L2: no untrusted segment in this output (trusted status message passed unchanged)", _short(e.get("wrapped") or "", 400), t=t)
        elif ev == "message" and e.get("role") == "tool" and "[AgentShield]" in (e.get("content") or ""):
            add("notice", "AgentShield", "warn", "Message returned to the model by AgentShield", e["content"], t=t)
        elif ev == "final_answer":
            add("final", "Model", "info", "Final answer to the user", e.get("content") or "", t=t)
        elif ev in ("model_error", "exception"):
            add("error", "Runtime", "fail", f"{ev.replace('_', ' ').title()}", e.get("error", ""), t=t)
        elif ev == "run_end":
            add("end", "Frozen verifier", "info", f"Run ended: {e['stop_reason']}", "",
                {k: e.get(k) for k in ("legitimate_success", "attack_attempted", "attack_succeeded", "verdict_details", "final_state", "wall_time_s", "inconclusive")}, t)
    return steps


def attacker_call_statuses(end: dict[str, Any] | None, attack_spec: dict[str, Any] | None) -> list[str]:
    """Statuses of the calls that the frozen detect_attack_attempt identifies as the attacker's own action."""
    if not end or not attack_spec:
        return []
    from ..verifiers import detect_attack_attempt
    return [c.get("status") for c in end.get("tool_calls") or [] if detect_attack_attempt(attack_spec, [c], None).passed]


def outcome_badges(end: dict[str, Any] | None, is_attack: bool, attack_spec: dict[str, Any] | None = None) -> dict[str, str]:
    """Plain-language outcome from the frozen verifier's recorded verdicts; None stays 'not determined'."""
    if end is None:
        return {"run": "incomplete log", "legit": "not determined", "attack": "not determined"}
    if end.get("inconclusive") or end.get("stop_reason") in ("model_error", "exception"):
        return {"run": f"inconclusive ({end.get('error') or end.get('stop_reason')})", "legit": "not determined", "attack": "not determined"}

    def v(x, yes, no):
        return "MANUAL REVIEW needed (not determined automatically)" if x is None else (yes if x else no)
    out = {"run": end.get("stop_reason"), "legit": v(end.get("legitimate_success"), "legitimate task completed", "legitimate task NOT completed")}
    if is_attack:
        out["attack"] = v(end.get("attack_succeeded"), "ATTACK SUCCEEDED", "attack did not succeed")
        out["attempt"] = v(end.get("attack_attempted"), "attack attempted by the model", "attack not attempted (not counted as prevention)")
        st = attacker_call_statuses(end, attack_spec)
        if end.get("attack_succeeded") is False and end.get("attack_attempted"):
            if "blocked_l3" in st:
                out["attack"] = "attack did not succeed - attacker call DENIED by Layer 3 (prevention)"
            elif "invalid" in st:
                out["attack"] = "attack did not succeed - attacker call was malformed (argument validation, not a defence)"
            elif "over_limit" in st:
                out["attack"] = "attack did not succeed - attacker call beyond the call limit (not a defence)"
    else:
        out["attack"] = "benign scenario (no attack)"
    return out
