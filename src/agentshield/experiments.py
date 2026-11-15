"""Registered Phase 4 continuation experiments (docs/D2_phase4_continuation_plan.md v2, Stage 3).

Every repeated run set belongs to exactly one registered experiment and repetition. The model, configurations,
inference settings and run-order seed come from this registry, never from free command-line values, so no run
can be started with tuned or ad-hoc settings. Frozen datasets, prompt, verifier, detector threshold and config
files are never changed; the only predefined differences are the model (Q1) and sampling (S1).

  R1  llama3.2:3b, all 5 configs, temperature 0 / seed 42 (frozen settings), repetitions 1-10.
      Repetition 1 IS the reference run set (results/eval/20261113T190040Z); only 2-10 are run.
  Q1  qwen3:4b (think=False), all 5 configs, temperature 0 / seed 42, repetitions 1-3.
      Runtime gate: repetitions 2-3 only if repetition 1 finished complete with median wall time <= 60 s per run.
  S1  llama3.2:3b, configs unprotected + full, temperature 0.8, seed = repetition (1-5). Stability check only.

Run order: the (scenario, configuration) pairs of repetition k are shuffled with random.Random(order_seed(k)).
Interruptions: an unfinished run set is kept and marked incomplete; the repetition is repeated in full in a NEW
run set (attempt n+1). A repetition that already has a finished run set can never be run again.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .frozen import ROOT

CONFIG_NAMES = ("unprotected", "l1_only", "l2_only", "l3_only", "full")
EVAL_ROOT = ROOT / "results" / "eval"
REFERENCE_RUN_SET = EVAL_ROOT / "20261113T190040Z"
FROZEN_SETTINGS = {"temperature": 0.0, "seed": 42, "num_ctx": 4096}
Q1_GATE_MEDIAN_S = 60.0


class ExperimentError(RuntimeError):
    pass


@dataclass(frozen=True)
class Experiment:
    id: str
    description: str
    model: str
    configs: tuple[str, ...]
    repetitions: tuple[int, ...]
    runnable: tuple[int, ...]
    base_settings: dict[str, Any] = field(default_factory=dict)
    sampling: bool = False

    def settings(self, k: int) -> dict[str, Any]:
        if k not in self.repetitions:
            raise ExperimentError(f"{self.id}: repetition {k} is not registered (allowed {self.repetitions})")
        s = dict(self.base_settings)
        if self.sampling:
            s["seed"] = k  # S1: seeds 1-5, one per repetition
        return s

    @staticmethod
    def order_seed(k: int) -> int:
        return 413 + k


EXPERIMENTS: dict[str, Experiment] = {
    "R1": Experiment("R1", "llama3.2:3b repetitions at the frozen settings (variance and attempt probability)",
                     "llama3.2:3b", CONFIG_NAMES, tuple(range(1, 11)), tuple(range(2, 11)), dict(FROZEN_SETTINGS)),
    "Q1": Experiment("Q1", "qwen3:4b as a separate model under D1's inconclusive rule",
                     "qwen3:4b", CONFIG_NAMES, (1, 2, 3), (1, 2, 3), {**FROZEN_SETTINGS, "think": False}),
    "S1": Experiment("S1", "sampling-on stability check (D1: no-defence and full, sampling on)",
                     "llama3.2:3b", ("unprotected", "full"), (1, 2, 3, 4, 5), (1, 2, 3, 4, 5),
                     {"temperature": 0.8, "num_ctx": 4096}, sampling=True),
}


def get(exp_id: str) -> Experiment:
    if exp_id not in EXPERIMENTS:
        raise ExperimentError(f"unknown experiment '{exp_id}'; registered: {sorted(EXPERIMENTS)}")
    return EXPERIMENTS[exp_id]


def _manifest(p: Path) -> dict[str, Any] | None:
    f = p / "run_manifest.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def run_sets(exp_id: str, eval_root: Path = EVAL_ROOT, reference: Path = REFERENCE_RUN_SET) -> list[dict[str, Any]]:
    """All run sets of an experiment (finished or not), including the reference as R1 repetition 1."""
    out = []
    if exp_id == "R1" and reference.exists():
        m = _manifest(reference)
        if m:
            out.append({"path": reference, "repetition": 1, "attempt": 1, "status": m.get("status"),
                        "complete": bool(m.get("complete_suite")), "manifest": m, "reference": True})
    if eval_root.exists():
        for p in sorted(eval_root.iterdir()):
            m = _manifest(p) if p.is_dir() else None
            if m and (m.get("experiment") or {}).get("id") == exp_id:
                e = m["experiment"]
                out.append({"path": p, "repetition": e["repetition"], "attempt": e["attempt"], "status": m.get("status"),
                            "complete": bool(m.get("complete_suite")), "manifest": m, "reference": False})
    return out


def median_wall_time(run_set: Path) -> float:
    times = []
    for p in sorted((run_set / "runs").glob("*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            if '"run_end"' in line:
                times.append(json.loads(line)["wall_time_s"])
    if not times:
        raise ExperimentError(f"{run_set}: no finished runs")
    return statistics.median(times)


def check_runnable(exp_id: str, k: int, eval_root: Path = EVAL_ROOT, reference: Path = REFERENCE_RUN_SET) -> dict[str, Any]:
    """Raise ExperimentError unless repetition k may be started now. Returns {"attempt": n, "gate": {...}|None}."""
    exp = get(exp_id)
    exp.settings(k)  # registered repetition?
    if k not in exp.runnable:
        raise ExperimentError(f"{exp_id}: repetition {k} is not runnable (R1 repetition 1 is the preserved reference run set)")
    sets = run_sets(exp_id, eval_root, reference)
    same = [s for s in sets if s["repetition"] == k]
    if any(s["status"] == "finished" for s in same):
        raise ExperimentError(f"{exp_id}: repetition {k} already has a finished run set; repetitions are never re-run")
    gate = None
    if exp_id == "Q1" and k >= 2:
        first = [s for s in sets if s["repetition"] == 1 and s["status"] == "finished" and s["complete"]]
        if not first:
            raise ExperimentError("Q1: repetitions 2-3 need a finished, complete repetition 1 (runtime gate)")
        med = median_wall_time(first[0]["path"])
        gate = {"rule": f"median wall time per run in repetition 1 <= {Q1_GATE_MEDIAN_S} s", "median_s": round(med, 3),
                "passed": med <= Q1_GATE_MEDIAN_S}
        if not gate["passed"]:
            raise ExperimentError(f"Q1 runtime gate failed: repetition 1 median {med:.1f} s > {Q1_GATE_MEDIAN_S} s; stop after repetition 1")
    return {"attempt": len(same) + 1, "previous_incomplete_attempts": [str(s["path"]) for s in same], "gate": gate}
