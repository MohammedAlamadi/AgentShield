"""Phase 4 runners. They load ONLY the frozen eval-v1 datasets and verify every recorded hash before (and
again after) running. Nothing here is executed by the test-suite against the real model or detector.

End-to-end:  40 frozen scenarios x 5 configurations -> one JSONL log per run (run_start carries the frozen
             dataset hashes, config file hash and run-set id), then outcome classes and summary, the blinded
             manual-review export and the predefined scoring-quality audit sample.
Detector:    120 frozen examples -> per-example scores and precision / recall / F1 / FPR (D1 RQ1).

Outputs are never overwritten: an existing output directory is refused.
"""

from __future__ import annotations

import csv
import json
import platform
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .adjudication import collect_manual_review_items, export_blind
from .agent import run_scenario
from .config import DefenceConfig
from .frozen import ROOT, FrozenDatasetError, FrozenInfo, load_frozen_detector_examples, load_frozen_suite, sha256_file, verify_frozen
from .outcomes import classify, load_run_records, summarize, wilson
from .prompts import PROMPT_VERSION, PROMPTS, prompt_sha256
from .quality_audit import create_audit

CONFIG_NAMES = ("unprotected", "l1_only", "l2_only", "l3_only", "full")
MANUAL_REVIEW_SEED = 413  # recorded in every export file (rubric: "fixed, recorded seed")
MANUAL_REVIEW_PREFIX = "manual_adjudication"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fresh_dir(out_dir: Path) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"{out_dir} exists and is not empty; evaluation outputs are never overwritten")
    out_dir.mkdir(parents=True, exist_ok=True)


def load_configs(names=CONFIG_NAMES, config_dir: Path = ROOT / "configs") -> list[dict[str, Any]]:
    out = []
    for n in names:
        p = config_dir / f"{n}.json"
        cfg = DefenceConfig.load(p)
        if cfg.name != n:
            raise ValueError(f"{p} declares name '{cfg.name}'")
        out.append({"config": cfg, "path": p.relative_to(ROOT).as_posix(), "sha256": sha256_file(p)})
    return out


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def postprocess(out_dir: Path, frozen: FrozenInfo, suite, *, invalid_scenarios=(), overrides=None, export=True,
                quality_sample: bool = True) -> dict[str, Any]:
    """Classify every run, summarise per configuration, export manual-review items and draw the quality-audit sample."""
    records = load_run_records(out_dir / "runs")
    classified = [classify(r, suite.get(r["scenario_id"]).verifier.get("attack") if r["is_attack"] else None,
                           invalid_scenarios=invalid_scenarios, overrides=overrides) for r in records]
    summary = summarize(classified)
    summary.update(n_runs=len(records), invalid_scenarios=sorted(invalid_scenarios),
                   adjudication_applied=bool(overrides), generated_utc=_now())
    with (out_dir / "classified_runs.csv").open("w", encoding="utf-8", newline="") as fh:
        cols = ["run_id", "scenario_id", "config", "is_attack", "legit", "attack", "attack_detail", "l1_quarantined", "requested_outcome_met", "adjudicated"]
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for c in classified:
            w.writerow({**c, "adjudicated": ",".join(c["adjudicated"])})
    _write_json(out_dir / ("summary_adjudicated.json" if overrides else "summary.json"), summary)
    if export:
        items = collect_manual_review_items(records, suite)
        export_blind(items, out_dir / "adjudication", prefix=MANUAL_REVIEW_PREFIX, seed=MANUAL_REVIEW_SEED,
                     meta={"rubric_sha256": frozen.scoring.get("docs/manual_adjudication_rubric.md (v1.0)")})
        if quality_sample:  # plan v1.0 defines ONE sample, from the reference run set; repetitions draw none
            create_audit(records, suite, out_dir / "quality_audit", plan_sha256=frozen.scoring.get("docs/scoring_quality_audit_plan.md (v1.0)"),
                         invalid_scenarios=invalid_scenarios)
    return summary


def run_e2e_evaluation(out_dir: str | Path, *, model_factory: Callable[[], Any], layer_builder: Callable[[DefenceConfig], dict[str, Any]],
                       model_info: dict[str, Any] | None = None, config_names=CONFIG_NAMES, scenario_ids=None,
                       frozen: FrozenInfo | None = None, echo=None, label: str = "", order_seed: int | None = None,
                       experiment: dict[str, Any] | None = None, quality_sample: bool = True) -> dict[str, Any]:
    frozen = frozen or verify_frozen()
    out = Path(out_dir)
    _fresh_dir(out)
    suite = load_frozen_suite(frozen)
    configs = load_configs(config_names)
    scenarios = [suite.get(i) for i in scenario_ids] if scenario_ids else list(suite.scenarios)
    model = model_factory()
    run_set_id = out.name
    lock = ROOT / "configs" / "models.lock.json"
    manifest: dict[str, Any] = {
        "run_set_id": run_set_id, "label": label, "status": "started", "started_utc": _now(),
        "frozen": frozen.as_log(),
        "configs": [{"name": c["config"].name, "path": c["path"], "sha256": c["sha256"], "flags": c["config"].to_dict()} for c in configs],
        "model": model.settings(), "model_info": model_info or {},
        "models_lock": {"path": lock.relative_to(ROOT).as_posix(), "sha256": sha256_file(lock)} if lock.exists() else None,
        "prompt": {"version": PROMPT_VERSION, "sha256": prompt_sha256(PROMPTS[PROMPT_VERSION])},
        "agentshield_version": __version__, "python": sys.version.split()[0], "platform": platform.platform(),
        # complete = all 40 frozen scenarios x every configuration the run set is registered for
        "complete_suite": not scenario_ids and tuple(config_names) == (tuple(experiment["configs"]) if experiment else CONFIG_NAMES),
        "experiment": experiment,
        "order_seed": order_seed,
    }
    pairs = [(sc, c) for sc in scenarios for c in configs]
    if order_seed is not None:  # registered experiments: shuffled, reproducible run order
        random.Random(order_seed).shuffle(pairs)
    manifest["order"] = [f"{sc.id}__{c['config'].name}" for sc, c in pairs]
    _write_json(out / "run_manifest.json", manifest)
    for position, (sc, c) in enumerate(pairs, start=1):
        cfg = c["config"]
        meta = {"run_set_id": run_set_id, "frozen": frozen.as_log(),
                "config_file": {"path": c["path"], "sha256": c["sha256"]},
                "experiment": experiment, "order_seed": order_seed, "order_position": position}
        run_scenario(sc, model, cfg, **layer_builder(cfg), log_path=out / "runs" / f"{sc.id}__{cfg.name}.jsonl",
                     suite_meta={"suite": suite.suite, "version": suite.version, "sha256": suite.sha256, "path": frozen.scenarios_path.relative_to(ROOT).as_posix()},
                     model_info=model_info, echo=echo, run_meta=meta)
    verify_frozen()  # fail loudly if anything changed while running (results would then be reported as invalid)
    summary = postprocess(out, frozen, suite, quality_sample=quality_sample)
    manifest.update(status="finished", finished_utc=_now(), n_runs=len(manifest["order"]),
                    log_sha256={p.name: sha256_file(p) for p in sorted((out / "runs").glob("*.jsonl"))},
                    summary_sha256=sha256_file(out / "summary.json"))
    _write_json(out / "run_manifest.json", manifest)
    return summary


def run_detector_evaluation(out_dir: str | Path, detector, *, frozen: FrozenInfo | None = None, label: str = "") -> dict[str, Any]:
    """RQ1 on the 120 frozen examples: flagged = any window >= threshold (same rule as Layer 1)."""
    frozen = frozen or verify_frozen()
    out = Path(out_dir)
    _fresh_dir(out)
    rows = load_frozen_detector_examples(frozen)
    info = detector.info() if hasattr(detector, "info") else {}
    _write_json(out / "run_manifest.json", {"status": "started", "started_utc": _now(), "label": label, "frozen": frozen.as_log(),
                                            "detector": info, "n_examples": len(rows)})
    per = []
    with (out / "detector_scores.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            res = detector.screen(r["text"])
            rec = {"id": r["id"], "category": r["category"], "label": r["label"], "flagged": bool(res.flagged), "max_score": res.max_score,
                   "chunk_scores": res.chunk_scores, "n_chunks": res.n_chunks, "seconds": res.seconds}
            per.append(rec)
            fh.write(json.dumps(rec) + "\n")
    tp = sum(r["label"] == 1 and r["flagged"] for r in per)
    fp = sum(r["label"] == 0 and r["flagged"] for r in per)
    fn = sum(r["label"] == 1 and not r["flagged"] for r in per)
    tn = sum(r["label"] == 0 and not r["flagged"] for r in per)
    prec = tp / (tp + fp) if tp + fp else None
    rec_ = tp / (tp + fn) if tp + fn else None
    f1 = 2 * prec * rec_ / (prec + rec_) if prec and rec_ else (0.0 if prec == 0 or rec_ == 0 else None)
    cats: dict[str, Any] = {}
    for cat in sorted({r["category"] for r in per}):
        rs = [r for r in per if r["category"] == cat]
        k = sum(r["flagged"] for r in rs)
        cats[cat] = {"n": len(rs), "flagged": k, "flag_rate": round(k / len(rs), 4), "wilson95": wilson(k, len(rs))}
    secs = [r["seconds"] for r in per]
    metrics = {"n": len(per), "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
               "precision": prec, "recall": rec_, "f1": f1, "fpr": fp / (fp + tn) if fp + tn else None,
               "recall_wilson95": wilson(tp, tp + fn), "fpr_wilson95": wilson(fp, fp + tn), "per_category": cats,
               "latency_s": {"median": statistics.median(secs), "mean": statistics.mean(secs), "max": max(secs)} if secs else None,
               "threshold": info.get("threshold"), "generated_utc": _now()}
    _write_json(out / "detector_metrics.json", metrics)
    verify_frozen()
    m = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    m.update(status="finished", finished_utc=_now(), scores_sha256=sha256_file(out / "detector_scores.jsonl"),
             metrics_sha256=sha256_file(out / "detector_metrics.json"))
    _write_json(out / "run_manifest.json", m)
    return metrics


def run_experiment(exp_id: str, k: int, *, model_factory: Callable[[dict[str, Any]], Any], layer_builder: Callable[[DefenceConfig], dict[str, Any]],
                   eval_root: Path | None = None, reference: Path | None = None, model_info: dict[str, Any] | None = None,
                   frozen: FrozenInfo | None = None, echo=None, scenario_ids=None, stamp: str | None = None) -> dict[str, Any]:
    """Run repetition k of a REGISTERED experiment (experiments.py). Model, configurations, settings and order seed
    come from the registry; ``model_factory(settings)`` must build the model with exactly those settings.
    ``scenario_ids`` exists for tests only: such a run set is marked incomplete and never counts as a repetition."""
    from . import experiments as X

    exp = X.get(exp_id)
    eval_root = eval_root or X.EVAL_ROOT
    reference = reference or X.REFERENCE_RUN_SET
    check = X.check_runnable(exp_id, k, eval_root, reference)
    frozen = frozen or verify_frozen()
    settings = exp.settings(k)
    model = model_factory(settings)
    got = model.settings()
    for key, val in settings.items():  # the built model must carry exactly the registered settings
        if got.get(key) != val:
            raise X.ExperimentError(f"model setting {key}={got.get(key)!r} differs from registered {val!r}")
    if got.get("model") != exp.model and not got.get("fake"):
        raise X.ExperimentError(f"model {got.get('model')} differs from registered {exp.model}")
    stamp = stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = eval_root / f"{exp_id}_rep{k:02d}_a{check['attempt']}_{stamp}"
    meta = {"id": exp_id, "description": exp.description, "repetition": k, "attempt": check["attempt"],
            "registered_model": exp.model, "registered_settings": settings, "configs": list(exp.configs), "previous_incomplete_attempts": check["previous_incomplete_attempts"],
            "runtime_gate": check["gate"], "plan": "docs/D2_phase4_continuation_plan.md (v2)"}
    return run_e2e_evaluation(out, model_factory=lambda: model, layer_builder=layer_builder, model_info=model_info,
                              config_names=exp.configs, scenario_ids=scenario_ids, frozen=frozen, echo=echo,
                              label=f"{exp_id} repetition {k} attempt {check['attempt']}", order_seed=exp.order_seed(k),
                              experiment=meta, quality_sample=False) | {"_run_set": str(out)}


__all__ = ["run_experiment", "CONFIG_NAMES", "FrozenDatasetError", "load_configs", "postprocess", "run_detector_evaluation", "run_e2e_evaluation"]
