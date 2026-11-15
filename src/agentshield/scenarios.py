"""Scenario loading. A scenario file is JSON: {"suite": ..., "version": ..., "scenarios": [...]}.

Each scenario carries its own initial state, trusted scope and declarative verifier spec,
so every run rebuilds an identical environment from the file.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .environment import Environment, state_id
from .scope import TaskScope

REQUIRED_KEYS = ("id", "category", "user_request", "scope", "initial_state", "verifier")


@dataclass(frozen=True)
class Scenario:
    id: str
    category: str
    user_request: str
    scope: TaskScope
    initial_state: dict[str, Any]
    verifier: dict[str, Any]
    is_attack: bool = False
    attacker_text: str | None = None
    attacker_objective: str | None = None
    expected_legitimate_outcome: str | None = None
    notes: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def fresh_environment(self) -> Environment:
        return Environment.from_initial_state(self.initial_state)

    @property
    def initial_state_id(self) -> str:
        return state_id(self.initial_state)


@dataclass(frozen=True)
class ScenarioSuite:
    suite: str
    version: str
    scenarios: tuple[Scenario, ...]
    path: str
    sha256: str

    def get(self, scenario_id: str) -> Scenario:
        for s in self.scenarios:
            if s.id == scenario_id:
                return s
        raise KeyError(f"scenario '{scenario_id}' not found in {self.path}")


def _parse(d: dict[str, Any]) -> Scenario:
    missing = [k for k in REQUIRED_KEYS if k not in d]
    if missing:
        raise ValueError(f"scenario {d.get('id', '?')} missing keys: {missing}")
    return Scenario(
        id=d["id"],
        category=d["category"],
        user_request=d["user_request"],
        scope=TaskScope.from_dict(d["scope"]),
        initial_state=d["initial_state"],
        verifier=d["verifier"],
        is_attack=bool(d.get("is_attack", False)),
        attacker_text=d.get("attacker_text"),
        attacker_objective=d.get("attacker_objective"),
        expected_legitimate_outcome=d.get("expected_legitimate_outcome"),
        notes=d.get("notes"),
        raw=d,
    )


def load_suite(path: str | Path) -> ScenarioSuite:
    p = Path(path)
    raw_bytes = p.read_bytes()
    data = json.loads(raw_bytes.decode("utf-8"))
    scenarios = tuple(_parse(d) for d in data["scenarios"])
    ids = [s.id for s in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate scenario ids in {p}")
    for s in scenarios:  # fail early on broken initial states
        s.fresh_environment()
    return ScenarioSuite(
        suite=data.get("suite", p.stem),
        version=str(data.get("version", "unversioned")),
        scenarios=scenarios,
        path=p.as_posix(),
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )
