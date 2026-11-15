"""Experiment configuration: which defence layers are switched on.

The same code produces all five D1 configurations; only these flags differ.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MAX_TOOL_CALLS = 6  # D1: loop stops after a final answer or six tool calls


@dataclass(frozen=True)
class DefenceConfig:
    name: str
    detector: bool = False  # Layer 1
    isolation: bool = False  # Layer 2
    guard: bool = False  # Layer 3
    detector_threshold: float = 0.5
    max_tool_calls: int = MAX_TOOL_CALLS

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DefenceConfig":
        layers = d.get("layers", {})
        return cls(
            name=d["name"],
            detector=bool(layers.get("detector", False)),
            isolation=bool(layers.get("isolation", False)),
            guard=bool(layers.get("guard", False)),
            detector_threshold=float(d.get("detector_threshold", 0.5)),
            max_tool_calls=int(d.get("max_tool_calls", MAX_TOOL_CALLS)),
        )

    @classmethod
    def load(cls, path: str | Path) -> "DefenceConfig":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


UNPROTECTED = DefenceConfig(name="unprotected")
