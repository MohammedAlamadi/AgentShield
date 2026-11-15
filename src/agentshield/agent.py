"""Agent execution loop with pluggable defence layers.

Runtime order per proposed tool call (D1 Fig. 1; master prompt Section 4):

    model proposes call -> [logged as proposed, BEFORE Layer 3]
      -> argument validation
      -> Layer 3 guard (if on): deny => not executed, short policy message to the model
      -> execute simulated tool
      -> Layer 1 detector (if on): flagged => whole output quarantined, notice to the model
      -> Layer 2 isolation (if on): source-tagged, escaped untrusted block
      -> back to the model
    ... until a final answer, or the model asks for a call beyond the six-call limit.

The final natural-language answer is NOT checked by Layer 3 (documented limitation).
"""

from __future__ import annotations

import json
import platform
import sys
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from . import __version__
from .config import DefenceConfig
from .environment import Environment
from .llm import ChatModel, ModelError
from .logging_jsonl import RunLogger
from .prompts import PROMPT_VERSION, PROMPTS, prompt_sha256
from .scenarios import Scenario
from .scope import TaskScope
from .tools import TOOL_SCHEMAS, ToolArgumentError, ToolOutput, execute_tool, validate_arguments
from .verifiers import detect_attack_attempt, verify_attack_success, verify_legitimate


# --------------------------------------------------------------------------- layer interfaces
@dataclass
class GuardDecision:
    allowed: bool
    reason: str
    policy_message: str = ""


class Guard(Protocol):
    def start_run(self) -> None: ...

    def check(self, tool_name: str, args: dict[str, Any], scope: TaskScope, env: Environment) -> GuardDecision: ...

    def record_executed(self, tool_name: str, args: dict[str, Any]) -> None: ...


@dataclass
class DetectorResult:
    flagged: bool
    max_score: float
    chunk_scores: list[float]
    n_chunks: int
    seconds: float
    label: str = ""


class Detector(Protocol):
    def screen(self, text: str) -> DetectorResult: ...


class Isolator(Protocol):
    system_prompt_addendum: str

    def wrap(self, output: ToolOutput, tool_name: str) -> str: ...


QUARANTINE_NOTICE = (
    "[AgentShield] The output of {tool} ({sources}) was withheld because it was flagged as "
    "possibly containing malicious instructions. Tell the user it was withheld; do not guess its content."
)


# --------------------------------------------------------------------------- result
@dataclass
class RunResult:
    run_id: str
    scenario_id: str
    config: str
    model: str
    final_answer: str | None
    stop_reason: str
    tool_calls: list[dict[str, Any]]
    final_state: dict[str, Any]
    legitimate_success: bool | None
    attack_attempted: bool | None
    attack_succeeded: bool | None
    wall_time_s: float
    error: str | None = None
    log_path: str | None = None
    verdict_details: dict[str, list[str]] = field(default_factory=dict)


def _call_key(name: str, args: Any) -> str:
    return name + ":" + json.dumps(args, sort_keys=True, default=str)


# --------------------------------------------------------------------------- main loop
def run_scenario(
    scenario: Scenario,
    model: ChatModel,
    config: DefenceConfig,
    *,
    guard: Guard | None = None,
    detector: Detector | None = None,
    isolator: Isolator | None = None,
    log_path: str | Path | None = None,
    run_id: str | None = None,
    suite_meta: dict[str, Any] | None = None,
    model_info: dict[str, Any] | None = None,
    echo: Callable[[dict[str, Any]], None] | None = None,
    prompt_version: str = PROMPT_VERSION,
    run_meta: dict[str, Any] | None = None,
) -> RunResult:
    # Layers must match the configuration exactly, so a config file can never be silently ignored.
    for flag, obj, label in ((config.guard, guard, "guard"), (config.detector, detector, "detector"), (config.isolation, isolator, "isolator")):
        if flag and obj is None:
            raise ValueError(f"config '{config.name}' enables the {label} but none was supplied")
        if not flag and obj is not None:
            raise ValueError(f"config '{config.name}' disables the {label} but one was supplied")

    run_id = run_id or uuid.uuid4().hex[:12]
    env = scenario.fresh_environment()
    if guard is not None:
        guard.start_run()  # per-task state (one high-risk action) never leaks between runs
    log = RunLogger(log_path, echo=echo)
    t0 = time.perf_counter()

    if prompt_version not in PROMPTS:
        raise ValueError(f"unknown prompt version '{prompt_version}'")
    system_prompt = PROMPTS[prompt_version] + (("\n\n" + isolator.system_prompt_addendum) if isolator else "")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": scenario.user_request},
    ]
    log.log(
        "run_start",
        run_id=run_id,
        scenario_id=scenario.id,
        category=scenario.category,
        is_attack=scenario.is_attack,
        suite=suite_meta or {},
        config=config.to_dict(),
        model_settings=model.settings(),
        model_info=model_info or {},
        detector_info=detector.info() if detector is not None and hasattr(detector, "info") else None,
        scope=scenario.scope.to_dict(),
        prompt_version=prompt_version,
        system_prompt_sha256=prompt_sha256(system_prompt),
        initial_state_id=env.initial_state_id,
        agentshield_version=__version__,
        python=sys.version.split()[0],
        platform=platform.platform(),
        started_utc=datetime.now(timezone.utc).isoformat(),
        evaluation=run_meta,  # Phase 4: frozen dataset hashes, config file hash, run-set id (None for dev runs)
    )
    for m in messages:
        log.log("message", role=m["role"], content=m["content"])

    tool_calls: list[dict[str, Any]] = []
    seen: set[str] = set()
    final_answer: str | None = None
    stop_reason = "unknown"
    error: str | None = None

    try:
        while True:
            try:
                turn = model.chat(messages, TOOL_SCHEMAS)
            except ModelError as exc:
                stop_reason, error = "model_error", str(exc)
                log.log("model_error", error=error)
                break
            log.log(
                "model_turn",
                content=turn.content,
                thinking=turn.thinking,
                proposed=[{"name": c.name, "arguments": c.arguments, "source": c.source} for c in turn.tool_calls],
                duration_s=round(turn.duration_s, 4),
                stats=turn.stats,
            )
            if not turn.tool_calls:
                final_answer = turn.content
                stop_reason = "final_answer" if turn.content.strip() else "empty_answer"
                messages.append({"role": "assistant", "content": turn.content})
                log.log("final_answer", content=final_answer)
                break

            if all(c.source == "native" for c in turn.tool_calls):
                messages.append({
                    "role": "assistant",
                    "content": turn.content,
                    "tool_calls": [{"function": {"name": c.name, "arguments": c.arguments if isinstance(c.arguments, dict) else {}}} for c in turn.tool_calls],
                })
            else:
                messages.append({"role": "assistant", "content": turn.content})

            limit_hit = False
            for call in turn.tool_calls:
                if len(tool_calls) >= config.max_tool_calls:
                    # Still logged as a proposal (an attempt is an attempt), but never executed.
                    rec = {"index": len(tool_calls) + 1, "name": call.name, "arguments": call.arguments, "source": call.source, "status": "over_limit"}
                    log.log("proposed_tool_call", **rec)
                    tool_calls.append(rec)
                    limit_hit = True
                    break

                rec: dict[str, Any] = {"index": len(tool_calls) + 1, "name": call.name, "arguments": call.arguments, "source": call.source}
                key = _call_key(call.name, call.arguments)
                rec["repeated"] = key in seen
                seen.add(key)
                log.log("proposed_tool_call", **rec)  # logged BEFORE Layer 3
                tool_calls.append(rec)

                content = _process_call(call.name, call.arguments, rec, env, scenario.scope, guard, detector, isolator, log)
                tool_msg = {"role": "tool", "content": content, "tool_name": call.name}
                messages.append(tool_msg)
                log.log("message", role="tool", tool_name=call.name, content=content)
            if limit_hit:
                stop_reason = "max_tool_calls"
                log.log("stop", reason=f"model requested more than {config.max_tool_calls} tool calls")
                break
    except Exception as exc:  # unexpected failure: record it, never hide it
        stop_reason, error = "exception", f"{type(exc).__name__}: {exc}"
        log.log("exception", error=error, traceback=traceback.format_exc())

    wall = time.perf_counter() - t0
    final_state = env.snapshot()
    proposed_for_attempt = [c for c in tool_calls]
    legit = verify_legitimate(scenario.verifier.get("legitimate", {}), final_state, final_answer)
    attack_spec = scenario.verifier.get("attack", {}) if scenario.is_attack else {}
    succ = verify_attack_success(attack_spec, final_state, final_answer)
    att = detect_attack_attempt(attack_spec, proposed_for_attempt, final_answer)

    # A run that crashed or lost the model is inconclusive, not a pass/fail.
    inconclusive = stop_reason in ("model_error", "exception")
    result = RunResult(
        run_id=run_id,
        scenario_id=scenario.id,
        config=config.name,
        model=model.name,
        final_answer=final_answer,
        stop_reason=stop_reason,
        tool_calls=tool_calls,
        final_state=final_state,
        legitimate_success=None if inconclusive else legit.passed,
        attack_attempted=None if inconclusive else att.passed,
        attack_succeeded=None if inconclusive else succ.passed,
        wall_time_s=round(wall, 3),
        error=error,
        log_path=str(log.path) if log.path else None,
        verdict_details={"legitimate": legit.details, "attack_attempt": att.details, "attack_success": succ.details,
                         # requested outcome achieved, ignoring unrequested side effects (review round 1)
                         "legitimate_requested_outcome_met": None if inconclusive else legit.requested_outcome_met},
    )
    log.log(
        "run_end",
        stop_reason=stop_reason,
        error=error,
        final_answer=final_answer,
        final_state=final_state,
        n_tool_calls=len(tool_calls),
        tool_calls=tool_calls,  # final per-call record: status, guard decision, detector result, isolation
        legitimate_success=result.legitimate_success,
        attack_attempted=result.attack_attempted,
        attack_succeeded=result.attack_succeeded,
        verdict_details=result.verdict_details,
        inconclusive=inconclusive,
        wall_time_s=result.wall_time_s,
    )
    log.close()
    return result


def _process_call(
    name: str,
    raw_args: Any,
    rec: dict[str, Any],
    env: Environment,
    scope: TaskScope,
    guard: Guard | None,
    detector: Detector | None,
    isolator: Isolator | None,
    log: RunLogger,
) -> str:
    """Run one proposed call through validation, L3, execution, L1 and L2. Returns the tool message."""
    try:
        args = validate_arguments(name, raw_args)
    except ToolArgumentError as exc:
        rec["status"] = "invalid"
        rec["reason"] = str(exc)
        log.log("invalid_tool_call", index=rec["index"], name=name, reason=str(exc))
        return f"Error: {exc}. Available tools: read_inbox, read_document, send_email, delete_file."

    # ---- Layer 3: authorization guard (before execution)
    if guard is not None:
        decision = guard.check(name, args, scope, env)
        rec["guard"] = {"allowed": decision.allowed, "reason": decision.reason}
        log.log("guard_decision", index=rec["index"], name=name, arguments=args, allowed=decision.allowed, reason=decision.reason)
        if not decision.allowed:
            rec["status"] = "blocked_l3"
            return decision.policy_message

    # ---- execute the simulated tool
    try:
        output = execute_tool(env, name, args)
    except Exception as exc:  # defensive: tools should not raise
        rec["status"] = "tool_exception"
        rec["reason"] = f"{type(exc).__name__}: {exc}"
        log.log("tool_exception", index=rec["index"], name=name, error=rec["reason"])
        return "Error: the tool failed unexpectedly."
    if guard is not None and output.ok:
        guard.record_executed(name, args)
    rec["status"] = "executed" if output.ok else "executed_error"
    rec["output_sources"] = output.sources
    log.log("tool_executed", index=rec["index"], name=name, arguments=args, ok=output.ok, sources=output.sources, output=output.text)

    # ---- Layer 1: injection detector on the whole output
    if detector is not None:
        res = detector.screen(output.text)
        rec["detector"] = {"flagged": res.flagged, "max_score": res.max_score, "n_chunks": res.n_chunks, "seconds": res.seconds}
        log.log(
            "detector_decision",
            index=rec["index"],
            name=name,
            sources=output.sources,
            flagged=res.flagged,
            max_score=res.max_score,
            chunk_scores=res.chunk_scores,
            n_chunks=res.n_chunks,
            seconds=res.seconds,
            label=res.label,
        )
        if res.flagged:
            rec["status"] = "quarantined_l1"
            return QUARANTINE_NOTICE.format(tool=name, sources=", ".join(output.sources) or "tool output")

    # ---- Layer 2: content isolation
    if isolator is not None:
        wrapped = isolator.wrap(output, name)
        escapes = getattr(isolator, "last_escapes", 0)
        rec["isolation"] = {"sources": output.sources, "escaped_tags": escapes}
        log.log("isolation_applied", index=rec["index"], name=name, sources=output.sources, escaped_tags=escapes, wrapped=wrapped)
        return wrapped
    return output.text
