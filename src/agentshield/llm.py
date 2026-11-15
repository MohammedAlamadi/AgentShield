"""Model interface: a thin wrapper over the local Ollama server, plus a scripted fake for tests.

Tool calls are taken from Ollama's native ``tool_calls`` field. Small models sometimes
write the call as JSON text in ``content`` instead; such calls are recovered and marked
``source="content_json"`` so the pilot can report native vs recovered calls honestly.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class ModelError(RuntimeError):
    """Model call failed (server down, timeout, invalid response...)."""


class ModelUnavailableError(ModelError):
    """The requested model is not pulled, or the Ollama server is not reachable."""


@dataclass
class ProposedCall:
    name: str
    arguments: Any  # raw, unvalidated arguments as produced by the model
    source: str = "native"  # "native" | "content_json"


@dataclass
class ModelTurn:
    content: str
    tool_calls: list[ProposedCall] = field(default_factory=list)
    thinking: str | None = None
    duration_s: float = 0.0
    stats: dict[str, Any] = field(default_factory=dict)


class ChatModel(Protocol):
    name: str

    def settings(self) -> dict[str, Any]: ...

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn: ...


# --------------------------------------------------------------------------- JSON fallback parsing
_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def parse_content_tool_calls(content: str) -> list[ProposedCall]:
    """Recover tool calls that a model wrote as JSON text instead of native tool calls.

    Accepts a JSON object (or list of objects) of the form
    ``{"name": ..., "parameters"|"arguments": {...}}``, optionally inside a ```json fence.
    Anything else is treated as a normal natural-language answer.
    """
    text = (content or "").strip()
    m = _FENCE_RE.match(text)
    if m:
        text = m.group(1).strip()
    if not text or text[0] not in "[{":
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    items = data if isinstance(data, list) else [data]
    calls: list[ProposedCall] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            return []
        args = item.get("parameters", item.get("arguments", {}))
        if not ("parameters" in item or "arguments" in item):
            return []
        calls.append(ProposedCall(name=item["name"], arguments=args, source="content_json"))
    return calls


def _coerce_arguments(args: Any) -> Any:
    if isinstance(args, str):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return args
    return args


# --------------------------------------------------------------------------- Ollama
class OllamaModel:
    def __init__(
        self,
        name: str,
        temperature: float = 0.0,
        seed: int = 42,
        num_ctx: int = 4096,
        think: bool | None = None,
        timeout_s: float = 180.0,
        host: str | None = None,
        keep_alive: str = "10m",
    ) -> None:
        try:
            import ollama  # noqa: F401
        except ImportError as exc:  # pragma: no cover - environment problem
            raise ModelUnavailableError("The 'ollama' Python package is missing. Run: python -m pip install -r requirements.txt") from exc
        import ollama

        self.name = name
        self.temperature = temperature
        self.seed = seed
        self.num_ctx = num_ctx
        self.think = think
        self.timeout_s = timeout_s
        self.keep_alive = keep_alive
        self._client = ollama.Client(host=host, timeout=timeout_s)

    def settings(self) -> dict[str, Any]:
        return {
            "model": self.name,
            "temperature": self.temperature,
            "seed": self.seed,
            "num_ctx": self.num_ctx,
            "think": self.think,
            "timeout_s": self.timeout_s,
        }

    def model_info(self) -> dict[str, Any]:
        """Return digest/details of the pulled model, or raise ModelUnavailableError."""
        try:
            listing = self._client.list()
        except Exception as exc:
            raise ModelUnavailableError(f"Cannot reach the Ollama server ({exc}). Start Ollama and retry.") from exc
        for m in listing.models:
            if m.model == self.name:
                details = m.details.model_dump() if m.details else {}
                return {"model": m.model, "digest": m.digest, "size": m.size, "details": details}
        raise ModelUnavailableError(f"Model '{self.name}' is not pulled. Run: ollama pull {self.name}")

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
        kwargs: dict[str, Any] = {
            "model": self.name,
            "messages": messages,
            "tools": tools or None,
            "options": {"temperature": self.temperature, "seed": self.seed, "num_ctx": self.num_ctx},
            "keep_alive": self.keep_alive,
        }
        if self.think is not None:
            kwargs["think"] = self.think
        start = time.perf_counter()
        try:
            resp = self._client.chat(**kwargs)
        except Exception as exc:
            raise ModelError(f"{type(exc).__name__}: {exc}") from exc
        elapsed = time.perf_counter() - start

        msg = resp.message
        content = msg.content or ""
        calls = [
            ProposedCall(name=tc.function.name, arguments=_coerce_arguments(tc.function.arguments), source="native")
            for tc in (msg.tool_calls or [])
        ]
        if not calls:
            calls = parse_content_tool_calls(content)
        stats = {
            "total_duration_ns": resp.total_duration,
            "load_duration_ns": resp.load_duration,
            "prompt_eval_count": resp.prompt_eval_count,
            "eval_count": resp.eval_count,
            "eval_duration_ns": resp.eval_duration,
        }
        return ModelTurn(content=content, tool_calls=calls, thinking=getattr(msg, "thinking", None), duration_s=elapsed, stats=stats)


# --------------------------------------------------------------------------- fake model (unit tests only)
class FakeModel:
    """Scripted model for unit tests. Never used for experiments.

    ``script`` items are ModelTurn objects or callables ``(messages) -> ModelTurn``.
    When the script is exhausted the fake returns a fixed final answer.
    """

    def __init__(self, script: list[ModelTurn | Callable[[list[dict[str, Any]]], ModelTurn]], name: str = "fake-model") -> None:
        self.name = name
        self._script = list(script)
        self.calls: list[list[dict[str, Any]]] = []

    def settings(self) -> dict[str, Any]:
        return {"model": self.name, "fake": True}

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
        self.calls.append([dict(m) for m in messages])
        if not self._script:
            return ModelTurn(content="(fake) done")
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item(messages) if callable(item) else item
