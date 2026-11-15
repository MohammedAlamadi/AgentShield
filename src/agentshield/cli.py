"""Command-line interface.

    python -m agentshield check
    python -m agentshield run   --scenarios FILE --id P01 --config configs/unprotected.json --model llama3.2:3b
    python -m agentshield pilot --models llama3.2:3b qwen3:4b
    python -m agentshield evaluate --model llama3.2:3b --confirm-real-evaluation      (Phase 4, frozen eval-v1 only)
    python -m agentshield evaluate-detector --confirm-real-evaluation                 (Phase 4, frozen eval-v1 only)
    python -m agentshield adjudicate RUN_DIR         merge blinded manual-review labels, re-summarise
    python -m agentshield quality-report RUN_DIR     merge the scoring-quality audit, write its report

The trusted task scope comes from the scenario file (the "application control"); it is
never derived from the conversation.
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import statistics
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent import RunResult, run_scenario
from .config import DefenceConfig
from .llm import ModelError, ModelUnavailableError, OllamaModel
from .scenarios import load_suite

ROOT = Path(__file__).resolve().parents[2]
OLLAMA_URL = "http://127.0.0.1:11434"


def model_defaults(name: str) -> dict[str, Any]:
    """Main-run inference settings. Qwen3 'thinking' is switched off to keep latency/context small."""
    d: dict[str, Any] = {"temperature": 0.0, "seed": 42, "num_ctx": 4096}
    if name.startswith("qwen3"):
        d["think"] = False
    return d


def make_model(name: str) -> OllamaModel:
    return OllamaModel(name, **model_defaults(name))


_DETECTOR_CACHE: dict[float, Any] = {}


def get_detector(threshold: float):
    """Load the detector once per process (about 25 s cold) and reuse it across runs."""
    if threshold not in _DETECTOR_CACHE:
        from .detector import InjectionDetector

        _DETECTOR_CACHE[threshold] = InjectionDetector(threshold=threshold)
    return _DETECTOR_CACHE[threshold]


def build_layers(config: DefenceConfig) -> dict[str, Any]:
    """Instantiate exactly the layers the configuration file switches on."""
    from .guard import AuthorizationGuard
    from .isolation import ContentIsolator

    layers: dict[str, Any] = {}
    if config.guard:
        layers["guard"] = AuthorizationGuard()
    if config.detector:
        layers["detector"] = get_detector(config.detector_threshold)
    if config.isolation:
        layers["isolator"] = ContentIsolator()
    return layers


# --------------------------------------------------------------------------- terminal trace
def _short(s: Any, n: int = 300) -> str:
    s = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False)
    s = s.replace("\n", " | ")
    return s if len(s) <= n else s[: n - 3] + "..."


def echo_event(e: dict[str, Any]) -> None:
    ev = e["event"]
    if ev == "run_start":
        print(f"\n=== Run {e['run_id']}  scenario={e['scenario_id']}  config={e['config']['name']}  model={e['model_settings'].get('model')}")
        print(f"    trusted scope: {e['scope']}")
    elif ev == "message" and e["role"] == "user":
        print(f"[USER]       {_short(e['content'])}")
    elif ev == "proposed_tool_call":
        print(f"[PROPOSED #{e['index']}] {e['name']}({_short(e['arguments'], 200)})  source={e['source']}{'  REPEATED' if e.get('repeated') else ''}{'  OVER LIMIT' if e.get('status') == 'over_limit' else ''}")
    elif ev == "invalid_tool_call":
        print(f"[INVALID]    {e['reason']}")
    elif ev == "guard_decision":
        print(f"[L3 GUARD]   {'ALLOW' if e['allowed'] else 'BLOCK'}: {e['reason']}")
    elif ev == "tool_executed":
        print(f"[EXECUTED]   {e['name']} -> {_short(e['output'], 220)}")
    elif ev == "detector_decision":
        print(f"[L1 DETECT]  {'QUARANTINE' if e['flagged'] else 'pass'}  max_score={e['max_score']:.4f}  chunks={e['n_chunks']}  {e['seconds']*1000:.0f} ms")
    elif ev == "isolation_applied":
        print(f"[L2 ISOLATE] wrapped sources {e['sources']}  escaped_tags={e.get('escaped_tags', 0)}")
        print(f"             {_short(e.get('wrapped', ''), 400)}")
    elif ev == "final_answer":
        print(f"[ANSWER]     {_short(e['content'], 600)}")
    elif ev in ("model_error", "exception"):
        print(f"[ERROR]      {e['error']}")
    elif ev == "run_end":
        print(f"[RESULT]     stop={e['stop_reason']}  legit_success={e['legitimate_success']}  attack_attempted={e['attack_attempted']}  "
              f"attack_succeeded={e['attack_succeeded']}  time={e['wall_time_s']}s")
        print(f"             outbox={e['final_state']['outbox']}  deleted={e['final_state']['deleted_files']}")


# --------------------------------------------------------------------------- commands
def cmd_check(_: argparse.Namespace) -> int:
    ok = True
    print(f"Python {sys.version.split()[0]} {'OK' if sys.version_info[:2] == (3, 11) else '(D1 specifies 3.11)'}")
    for pkg in ("ollama", "torch", "transformers", "pytest", "pandas", "matplotlib"):
        try:
            print(f"  {pkg:<13}{md.version(pkg)}")
        except md.PackageNotFoundError:
            print(f"  {pkg:<13}MISSING - run: python -m pip install -r requirements.txt")
            ok = False
    lock = json.loads((ROOT / "configs" / "models.lock.json").read_text(encoding="utf-8"))
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/version", timeout=5) as r:
            print(f"Ollama server {json.load(r)['version']} (locked: {lock['ollama_version']})")
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as r:
            pulled = {m["name"]: m["digest"] for m in json.load(r)["models"]}
        for name, info in lock["llm_models"].items():
            dg = pulled.get(name)
            status = "MISSING - run: ollama pull " + name if dg is None else ("digest OK" if dg == info["digest"] else f"DIGEST DIFFERS ({dg[:12]})")
            ok &= dg is not None
            print(f"  {name:<13}{status}")
    except OSError as exc:
        print(f"Ollama server not reachable at {OLLAMA_URL}: {exc}. Start the Ollama app.")
        ok = False
    print("CHECK PASSED" if ok else "CHECK FAILED")
    return 0 if ok else 1


def cmd_run(a: argparse.Namespace) -> int:
    suite = load_suite(a.scenarios)
    configs = [DefenceConfig.load(c) for c in (a.config or [str(ROOT / "configs" / "unprotected.json")])]
    model = make_model(a.model)
    info = model.model_info()
    ids = a.id or [s.id for s in suite.scenarios]
    out = Path(a.out) if a.out else ROOT / "results" / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for sid, config in [(s, c) for s in ids for c in configs]:
        sc = suite.get(sid)
        run_scenario(sc, model, config, **build_layers(config),
                     log_path=out / f"{sc.id}__{config.name}__{a.model.replace(':', '-')}.jsonl",
                     suite_meta={"suite": suite.suite, "version": suite.version, "sha256": suite.sha256, "path": suite.path},
                     model_info=info, echo=echo_event)
    print(f"\nLogs written to {out}")
    return 0


def _ollama_ps() -> list[dict[str, Any]]:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/ps", timeout=5) as r:
            return [{"name": m["name"], "size": m["size"], "size_vram": m.get("size_vram")} for m in json.load(r).get("models", [])]
    except OSError:
        return []


def cmd_pilot(a: argparse.Namespace) -> int:
    suite = load_suite(a.scenarios)
    config = DefenceConfig.load(ROOT / "configs" / "unprotected.json")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "results" / "pilot" / stamp
    from .prompts import PROMPT_VERSION

    pv = a.prompt_version or PROMPT_VERSION
    summary: dict[str, Any] = {"label": a.label, "prompt_version": pv, "suite": suite.suite, "version": suite.version, "suite_sha256": suite.sha256, "config": config.name, "started_utc": stamp, "models": {}}
    for name in a.models:
        model = make_model(name)
        info = model.model_info()
        # Warm-up: load the model once so per-scenario times measure inference, not disk loading.
        warm = model.chat([{"role": "user", "content": "Reply with the word ready."}], [])
        ps = _ollama_ps()
        print(f"\n##### {name}  warm-up {warm.duration_s:.1f}s  loaded: {ps}")
        results: list[RunResult] = []
        for sc in suite.scenarios:
            results.append(run_scenario(sc, model, config, prompt_version=pv, log_path=out / name.replace(":", "-") / f"{sc.id}.jsonl",
                                        suite_meta={"suite": suite.suite, "version": suite.version, "sha256": suite.sha256},
                                        model_info=info, echo=echo_event))
        calls = [c for r in results for c in r.tool_calls]
        times = [r.wall_time_s for r in results]
        summary["models"][name] = {
            "model_info": info,
            "settings": model.settings(),
            "warmup_s": round(warm.duration_s, 2),
            "ollama_ps_after_load": ps,
            "n_scenarios": len(results),
            "legitimate_success": sum(bool(r.legitimate_success) for r in results),
            "inconclusive_runs": sum(r.legitimate_success is None for r in results),
            "proposed_calls": len(calls),
            "native_calls": sum(c["source"] == "native" for c in calls),
            "recovered_from_text": sum(c["source"] == "content_json" for c in calls),
            "invalid_calls": sum(c.get("status") == "invalid" for c in calls),
            "executed_error_calls": sum(c.get("status") == "executed_error" for c in calls),
            "repeated_calls": sum(bool(c.get("repeated")) for c in calls),
            "median_wall_s": round(statistics.median(times), 2),
            "mean_wall_s": round(statistics.mean(times), 2),
            "max_wall_s": round(max(times), 2),
            "per_scenario": [
                {"id": r.scenario_id, "legit": r.legitimate_success, "stop": r.stop_reason, "calls": [f"{c['name']}:{c.get('status')}:{c['source']}" for c in r.tool_calls],
                 "wall_s": r.wall_time_s, "details": r.verdict_details["legitimate"], "answer": r.final_answer}
                for r in results
            ],
        }
    out.mkdir(parents=True, exist_ok=True)
    (out / "pilot_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n===== PILOT SUMMARY =====")
    for name, s in summary["models"].items():
        print(f"{name:<13} legit {s['legitimate_success']}/{s['n_scenarios']}  calls {s['proposed_calls']} (native {s['native_calls']}, from-text {s['recovered_from_text']}, invalid {s['invalid_calls']})  "
              f"median {s['median_wall_s']}s  max {s['max_wall_s']}s  vram {s['ollama_ps_after_load']}")
    print(f"Saved: {out / 'pilot_summary.json'}")
    return 0


# --------------------------------------------------------------------------- Phase 4 (frozen eval-v1 only)
def _stamp_dir(base: str, out: str | None) -> Path:
    return Path(out) if out else ROOT / "results" / base / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def cmd_evaluate(a: argparse.Namespace) -> int:
    from .evaluation import CONFIG_NAMES, run_e2e_evaluation
    from .frozen import verify_frozen

    frozen = verify_frozen()  # fail closed before anything is loaded
    print(f"Frozen {frozen.version} verified: scenarios {frozen.scenarios_sha256[:12]}..., manifest {frozen.manifest_sha256[:12]}...")
    if not a.confirm_real_evaluation:
        print("Refusing to start: pass --confirm-real-evaluation once the team has approved the real evaluation.")
        return 4
    model = make_model(a.model)
    info = model.model_info()
    out = _stamp_dir("eval", a.out)
    summary = run_e2e_evaluation(out, model_factory=lambda: model, layer_builder=build_layers, model_info=info,
                                 config_names=tuple(a.config) if a.config else CONFIG_NAMES,
                                 scenario_ids=a.id, frozen=frozen, echo=echo_event if a.trace else None, label=a.label)
    print(json.dumps(summary["configs"], indent=1))
    print(f"Run set written to {out}")
    return 0


def cmd_evaluate_detector(a: argparse.Namespace) -> int:
    from .evaluation import run_detector_evaluation
    from .frozen import verify_frozen

    frozen = verify_frozen()
    print(f"Frozen {frozen.version} verified: detector set {frozen.detector_sha256[:12]}...")
    if not a.confirm_real_evaluation:
        print("Refusing to start: pass --confirm-real-evaluation once the team has approved the real evaluation.")
        return 4
    out = _stamp_dir("detector_eval", a.out)
    metrics = run_detector_evaluation(out, get_detector(a.threshold), frozen=frozen, label=a.label)
    print(json.dumps({k: metrics[k] for k in ("confusion", "precision", "recall", "f1", "fpr")}, indent=1))
    print(f"Written to {out}")
    return 0


def cmd_adjudicate(a: argparse.Namespace) -> int:
    from .adjudication import MergeError, merge, overrides_from_final
    from .evaluation import MANUAL_REVIEW_PREFIX, postprocess
    from .frozen import load_frozen_suite, verify_frozen

    frozen = verify_frozen()
    run_dir = Path(a.run_dir)
    try:
        res = merge(run_dir / "adjudication", prefix=MANUAL_REVIEW_PREFIX, labels=("PASS", "FAIL", "SUCCESS", "NOT SUCCESS"))
    except MergeError as exc:
        print("ADJUDICATION INCOMPLETE OR INVALID:")
        for problem in exc.args[0]:
            print("  -", problem)
        return 5
    overrides = overrides_from_final(res["path"])
    postprocess(run_dir, frozen, load_frozen_suite(frozen), invalid_scenarios=a.invalid or (), overrides=overrides, export=False)
    print(json.dumps(res["stats"], indent=1))
    print(f"Wrote {res['path']} and {run_dir / 'summary_adjudicated.json'}")
    return 0


def cmd_quality_report(a: argparse.Namespace) -> int:
    from .adjudication import MergeError, merge
    from .quality_audit import PREFIX, report

    qdir = Path(a.run_dir) / "quality_audit"
    try:
        res = merge(qdir, prefix=PREFIX, labels=("True", "False"), require_rule=False)
    except MergeError as exc:
        print("QUALITY AUDIT INCOMPLETE OR INVALID:")
        for problem in exc.args[0]:
            print("  -", problem)
        return 5
    rep = report(res["path"])
    (qdir / f"{PREFIX}_report.json").write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rep["overall"], indent=1))
    return 0


def cmd_import_reviews(a: argparse.Namespace) -> int:
    """Copy filled reviewer workbooks (review_workbooks/*.xlsx) into the blind CSVs used by the merge."""
    from .review_workbooks import import_workbook

    kinds = {"quality": ("quality_audit", "scoring_quality_audit", ("True", "False")),
             "manual": ("adjudication", "manual_adjudication", ("PASS", "FAIL", "SUCCESS", "NOT SUCCESS"))}
    sub, prefix, labels = kinds[a.kind]
    d = Path(a.run_dir) / sub
    for n in (1, 2):
        k = import_workbook(d / "review_workbooks" / f"{prefix}_reviewer_{n}.xlsx", d / f"{prefix}_reviewer_{n}.csv", labels)
        print(f"imported reviewer {n}: {k} rows")
    return 0


def cmd_experiment_run(a: argparse.Namespace) -> int:
    """Run ONE repetition of a registered continuation experiment (R1, Q1, S1)."""
    from . import experiments as X
    from .evaluation import run_experiment
    from .frozen import verify_frozen

    frozen = verify_frozen()
    exp = X.get(a.experiment)
    try:
        check = X.check_runnable(a.experiment, a.repetition)
    except X.ExperimentError as exc:
        print(f"REFUSED: {exc}")
        return 6
    print(f"Frozen {frozen.version} verified. {exp.id} repetition {a.repetition} (attempt {check['attempt']}): model {exp.model}, "
          f"configs {list(exp.configs)}, settings {exp.settings(a.repetition)}, order seed {exp.order_seed(a.repetition)}"
          + (f", runtime gate {check['gate']}" if check["gate"] else ""))
    if not a.confirm_real_evaluation:
        print("Refusing to start: pass --confirm-real-evaluation once this stage is approved.")
        return 4
    info = OllamaModel(exp.model, **exp.settings(a.repetition)).model_info()
    res = run_experiment(a.experiment, a.repetition, model_factory=lambda st: OllamaModel(exp.model, **st), layer_builder=build_layers,
                         model_info=info, frozen=frozen, echo=echo_event if a.trace else None)
    print(f"Run set written to {res['_run_set']}")
    return 0


def cmd_aggregate(a: argparse.Namespace) -> int:
    """Aggregate all finished, complete run sets of ONE experiment (scenario-clustered; never pooled)."""
    from . import experiments as X
    from .aggregate import AggregationError, aggregate, check_consistency, load_classified, write_aggregate
    from .frozen import load_frozen_suite, verify_frozen

    frozen = verify_frozen()
    suite = load_frozen_suite(frozen)
    sets = [s for s in X.run_sets(a.experiment) if s["status"] == "finished" and s["complete"]]
    skipped = [str(s["path"]) for s in X.run_sets(a.experiment) if s not in sets]
    try:
        info = check_consistency(sets)
    except AggregationError as exc:
        print("CANNOT AGGREGATE:")
        for problem in exc.args[0]:
            print("  -", problem)
        return 7
    res = aggregate(load_classified(sets, suite, invalid_scenarios=a.invalid or ()), suite, info["configs"])
    res["skipped_incomplete_run_sets"] = skipped
    out = write_aggregate(res, sets, ROOT / "results" / "eval" / "aggregates" / f"{a.experiment}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}", a.experiment)
    print(f"{a.experiment}: {len(sets)} repetition(s) {res['repetitions']}; written to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agentshield", description="AgentShield D2 prototype")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="verify Python packages, Ollama server and pinned models")
    r = sub.add_parser("run", help="run scenario(s) with one configuration and print a trace")
    r.add_argument("--scenarios", required=True)
    r.add_argument("--id", action="append", help="scenario id (repeatable); default all")
    r.add_argument("--config", action="append", help="config file (repeatable); default configs/unprotected.json")
    r.add_argument("--model", default="llama3.2:3b")
    r.add_argument("--out")
    pl = sub.add_parser("pilot", help="D1 model pilot: five scenarios per candidate model")
    pl.add_argument("--models", nargs="+", default=["llama3.2:3b", "qwen3:4b"])
    pl.add_argument("--scenarios", default=str(ROOT / "data" / "pilot" / "pilot_scenarios.json"))
    pl.add_argument("--label", default="", help="free-text label stored in pilot_summary.json")
    pl.add_argument("--prompt-version", default=None, help="system prompt version (default: frozen PROMPT_VERSION)")
    ev = sub.add_parser("evaluate", help="Phase 4 end-to-end evaluation on the FROZEN eval-v1 suite")
    ev.add_argument("--model", default="llama3.2:3b")
    ev.add_argument("--config", action="append", help="config name (repeatable); default all five")
    ev.add_argument("--id", action="append", help="scenario id (repeatable); default all 40")
    ev.add_argument("--out")
    ev.add_argument("--label", default="")
    ev.add_argument("--trace", action="store_true", help="print the per-run trace")
    ev.add_argument("--confirm-real-evaluation", action="store_true", help="required: guards against accidental runs")
    ed = sub.add_parser("evaluate-detector", help="Phase 4 detector evaluation on the FROZEN 120 examples")
    ed.add_argument("--threshold", type=float, default=0.5)
    ed.add_argument("--out")
    ed.add_argument("--label", default="")
    ed.add_argument("--confirm-real-evaluation", action="store_true", help="required: guards against accidental runs")
    ad = sub.add_parser("adjudicate", help="merge blinded manual-review labels and re-summarise")
    ad.add_argument("run_dir")
    ad.add_argument("--invalid", action="append", help="scenario id reported as invalid (repeatable; document the reason)")
    qr = sub.add_parser("quality-report", help="merge the scoring-quality audit labels and write the report")
    qr.add_argument("run_dir")
    ir = sub.add_parser("import-reviews", help="import filled reviewer workbooks into the blind review CSVs")
    ir.add_argument("run_dir")
    ir.add_argument("--kind", choices=["quality", "manual"], required=True)
    xr = sub.add_parser("experiment-run", help="run one repetition of a registered experiment (R1, Q1, S1)")
    xr.add_argument("experiment", choices=["R1", "Q1", "S1"])
    xr.add_argument("--repetition", type=int, required=True)
    xr.add_argument("--trace", action="store_true")
    xr.add_argument("--confirm-real-evaluation", action="store_true", help="required: guards against accidental runs")
    ag = sub.add_parser("aggregate", help="aggregate the finished run sets of one experiment (scenario-clustered)")
    ag.add_argument("experiment", choices=["R1", "Q1", "S1"])
    ag.add_argument("--invalid", action="append", help="scenario id reported as invalid (repeatable; document the reason)")
    a = p.parse_args(argv)
    try:
        return {"check": cmd_check, "run": cmd_run, "pilot": cmd_pilot, "evaluate": cmd_evaluate, "evaluate-detector": cmd_evaluate_detector,
                "adjudicate": cmd_adjudicate, "quality-report": cmd_quality_report,
                "import-reviews": cmd_import_reviews, "experiment-run": cmd_experiment_run, "aggregate": cmd_aggregate}[a.cmd](a)
    except ModelUnavailableError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ModelError as exc:
        print(f"MODEL ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
