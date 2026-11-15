"""Live execution for the dashboard: the REAL AgentShield runner (agent.run_scenario) with the REAL layers
(cli.build_layers: AuthorizationGuard, InjectionDetector, ContentIsolator) and the local Ollama model.

Safety:
  * tools are simulated against an in-memory Environment built fresh from the scenario (no real e-mail, no files);
  * logs go only to the sandbox directory ``dashboard_runs/`` (never results/, data/ or docs/);
  * an optional custom injected text is applied to an in-memory COPY of the scenario; the frozen dataset is never
    written, and verify_frozen() is checked before and after every run.
"""

from __future__ import annotations

import dataclasses
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..frozen import ROOT, load_frozen_suite, verify_frozen

SANDBOX = ROOT / "dashboard_runs"
PROTECTED = [ROOT / "data", ROOT / "results", ROOT / "docs", ROOT / "configs", ROOT / "src"]
MODELS = ("llama3.2:3b", "qwen3:4b")


class LiveUnavailable(RuntimeError):
    """The live runner cannot run (Ollama down, model missing, detector missing)."""


def check_runtime(model_name: str) -> dict[str, Any]:
    """Return {'ok': bool, 'message': str, 'info': {...}} without raising."""
    from ..llm import ModelUnavailableError
    from ..cli import make_model
    try:
        info = make_model(model_name).model_info()
    except ModelUnavailableError as exc:
        return {"ok": False, "message": str(exc), "info": {}}
    except Exception as exc:  # unexpected client problem
        return {"ok": False, "message": f"{type(exc).__name__}: {exc}", "info": {}}
    lock = json.loads((ROOT / "configs" / "models.lock.json").read_text(encoding="utf-8"))
    pinned = json.dumps(lock)
    return {"ok": True, "message": f"{model_name} available (digest {info['digest'][:12]}…)", "info": info,
            "digest_matches_lock": info["digest"] in pinned}


def sandbox_log_path(scenario_id: str, config: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p = SANDBOX / f"{stamp}_{scenario_id}_{config}_{uuid.uuid4().hex[:6]}.jsonl"
    assert_sandboxed(p)
    return p


def assert_sandboxed(p: Path) -> None:
    rp = p.resolve()
    if SANDBOX.resolve() not in rp.parents:
        raise PermissionError(f"live logs may only be written under {SANDBOX}")
    for prot in PROTECTED:
        if prot.resolve() in rp.parents:
            raise PermissionError(f"refusing to write inside protected path {prot}")


def scenario_with_payload(scenario, custom_text: str | None):
    """Return (scenario, note). With custom_text, the scenario's injected passage is replaced in an in-memory copy."""
    if custom_text is None or custom_text == (scenario.attacker_text or ""):
        return scenario, None
    if not scenario.attacker_text:
        raise ValueError(f"{scenario.id} has no injected passage to replace")
    state = json.loads(json.dumps(scenario.initial_state))
    hits = 0
    for e in state.get("inbox", []):
        if scenario.attacker_text in e.get("body", ""):
            e["body"] = e["body"].replace(scenario.attacker_text, custom_text)
            hits += 1
    for d in state.get("files", []):
        if scenario.attacker_text in d.get("content", ""):
            d["content"] = d["content"].replace(scenario.attacker_text, custom_text)
            hits += 1
    if hits == 0:
        raise ValueError(f"{scenario.id}: injected passage not found in the initial state")
    copy = dataclasses.replace(scenario, initial_state=state, attacker_text=custom_text, raw={**scenario.raw, "custom_payload": True})
    note = ("CUSTOM PAYLOAD (sandbox copy). The frozen verifier still measures the scenario's ORIGINAL attacker objective, "
            "so the attack verdict is only meaningful if the custom text pursues that same objective.")
    return copy, note


def injection_source(scenario) -> dict[str, Any] | None:
    """Where the injected passage sits in the scenario (untrusted input)."""
    if not scenario.attacker_text:
        return None
    for e in scenario.initial_state.get("inbox", []):
        if scenario.attacker_text in e.get("body", ""):
            return {"kind": "email", "id": e["id"], "label": f"Email {e['id']} from {e['from']} - '{e.get('subject', '')}'", "full_text": e["body"]}
    for d in scenario.initial_state.get("files", []):
        if scenario.attacker_text in d.get("content", ""):
            return {"kind": "document", "id": d["name"], "label": f"Document {d['name']}", "full_text": d["content"]}
    return None


def unload_model(model_name: str) -> bool:
    """Ask Ollama to unload the model so the next run starts from a freshly loaded model (runtime state only).
    Observed on this laptop: AS06/full behaves differently depending on what the server processed before
    (read-first after a fresh load, delete-first after other scenarios). Resetting makes live demos repeatable;
    it does not change prompts, payloads, defences or scoring. The evaluation runs did NOT reset between runs."""
    try:
        import ollama
        ollama.Client(timeout=30).generate(model=model_name, prompt="", keep_alive=0)
        return True
    except Exception:
        return False


def run_live(scenario_id: str, config_name: str, model_name: str, custom_text: str | None = None,
             echo: Callable[[dict[str, Any]], None] | None = None, fresh_model: bool = False) -> dict[str, Any]:
    """Execute one scenario for real. Raises LiveUnavailable if Ollama or the model is unavailable."""
    from ..cli import build_layers, make_model
    from ..evaluation import load_configs
    from ..agent import run_scenario
    from ..llm import ModelUnavailableError

    if model_name not in MODELS:
        raise ValueError(f"unknown model {model_name}")
    frozen = verify_frozen()
    suite = load_frozen_suite(frozen)
    base = suite.get(scenario_id)
    scenario, note = scenario_with_payload(base, custom_text)
    cfg = load_configs([config_name])[0]["config"]
    model = make_model(model_name)
    try:
        info = model.model_info()
    except ModelUnavailableError as exc:
        raise LiveUnavailable(str(exc)) from exc
    try:
        layers = build_layers(cfg)
    except Exception as exc:  # e.g. detector weights not downloaded
        raise LiveUnavailable(f"Could not load the defence layers for {config_name}: {type(exc).__name__}: {exc}") from exc
    fresh_ok = unload_model(model_name) if fresh_model else False
    log_path = sandbox_log_path(scenario_id, config_name)
    t0 = time.perf_counter()
    res = run_scenario(scenario, model, cfg, **layers, log_path=log_path, model_info=info, echo=echo,
                       suite_meta={"suite": suite.suite, "version": suite.version, "sha256": suite.sha256, "path": "data/eval/scenarios_v1.json"},
                       run_meta={"dashboard_live": True, "custom_payload": note is not None, "fresh_model_state": fresh_ok})
    verify_frozen()  # the frozen dataset and scoring files must be unchanged after a live run
    return {"result": res, "log_path": str(log_path), "custom_note": note, "fresh_model": fresh_ok, "model_info": info, "seconds": round(time.perf_counter() - t0, 2),
            "scenario": scenario, "base_scenario": base, "config": cfg}
