"""DRAFT consolidation of Q1 and S1 results under the reviewed attack labels (package A), computed in memory.
Nothing is written into any run set (no adjudication/manual_adjudication.csv is created) and no original aggregate
is changed. Frozen scoring is used unchanged; reviewed labels enter only through the existing override mechanism
(outcomes.classify), which can resolve manual_review cells only.

    .venv\\Scripts\\python scripts\\eval\\consolidate_reviewed_results.py

Variants:
  primary      every A item whose review passed validation is applied; A05 (same person recorded as both
               reviewers) is NOT applied and stays manual_review (range)
  sensitivity  A05's recorded label (SUCCESS) is applied as well
Writes (new folder, never overwritten): docs/evidence/final_results_draft/consolidated_draft.json + SHA256SUMS.txt
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import openpyxl  # noqa: E402

from agentshield import experiments as X  # noqa: E402
from agentshield.aggregate import _turns, aggregate  # noqa: E402
from agentshield.frozen import load_frozen_suite, verify_frozen  # noqa: E402
from agentshield.outcomes import classify, load_run_records  # noqa: E402

SNAP = ROOT / "docs" / "evidence" / "final_review_completed"
KEY = ROOT / "docs" / "evidence" / "final_review_package" / "A_attack_outcomes_key.csv"
VAL = ROOT / "docs" / "evidence" / "final_review_validation" / "validation.json"
OUT = ROOT / "docs" / "evidence" / "final_results_draft"
ATT = {"succeeded", "blocked_l3", "not_executed_invalid_call", "not_executed_call_limit", "attempted_not_succeeded"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reviewed_labels() -> dict[str, dict]:
    ws = openpyxl.load_workbook(SNAP / "A_attack_outcomes_review.xlsx")["Attack items (blind)"]
    h = [c.value for c in ws[1]]
    key = {r["item"]: r for r in csv.DictReader(open(KEY, encoding="utf-8"))}
    val = {r["item"]: r["issues"] for r in json.loads(VAL.read_text(encoding="utf-8"))["A"]}
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        d = dict(zip(h, row))
        k = key[d["item"]]
        out[d["item"]] = {"run_id": k["run_id"], "experiment": k["experiment"], "repetition": int(k["repetition"]), "scenario": k["scenario_id"],
                          "config": k["config"], "final_label": d["final_label"], "validation_issues": val[d["item"]]}
    return out


def rows_for(exp: str, suite, overrides: dict) -> list[dict]:
    rows = []
    for rs in X.run_sets(exp):
        p = Path(rs["path"])
        for rec in load_run_records(p / "runs"):
            sc = suite.get(rec["scenario_id"])
            c = classify(rec, sc.verifier.get("attack") if sc.is_attack else None, overrides=overrides)
            sig, blocked = _turns(rec["log_path"])
            rows.append({**c, "repetition": rs["repetition"], "run_set": p.name, "signature": sig, "l3_any_block": blocked})
    return rows


def headline(res: dict, rows: list[dict], suite, configs) -> dict:
    atk = sorted(s.id for s in suite.scenarios if s.is_attack)
    out = {"conditional_set": res["conditional_asr_set"]["scenarios"], "configs": {}}
    for c in configs:
        v = res["configs"][c]
        cr = [r for r in rows if r["config"] == c and r["is_attack"]]
        out["configs"][c] = {
            "attack_attempt": v["p_att"], "attack_success": v["p_succ"], "legit_success": v["p_legit"]["lower"],
            "conditional_asr": v["conditional_asr"], "vs_unprotected": v.get("vs_unprotected"),
            "manual_review_runs_remaining": v["manual_review_runs"], "excluded_runs": v["excluded_runs"],
            "attempted_scenarios_any_rep": sorted({r["scenario_id"] for r in cr if r["attack"] in ATT}),
            "manual_review_scenarios": sorted({r["scenario_id"] for r in cr if r["attack"] == "manual_review"}),
            "succeeded_scenarios_any_rep": sorted({r["scenario_id"] for r in cr if r["attack"] == "succeeded"}),
        }
    return out


def main() -> int:
    if OUT.exists():
        print(f"REFUSED: {OUT} exists")
        return 1
    suite = load_frozen_suite(verify_frozen())
    labels = reviewed_labels()
    variants = {
        "primary": {i: l for i, l in labels.items() if not l["validation_issues"]},
        "sensitivity_with_A05": dict(labels),
    }
    result = {"note": "DRAFT, computed in memory; not written to any run set. Q1 single repetition; S1 5 seeds; never pooled.",
              "labels": labels, "variants": {}}
    for name, chosen in variants.items():
        ov = {(l["run_id"], "attack"): l["final_label"] for l in chosen.values()}
        result["variants"][name] = {"applied_items": sorted(chosen)}
        for exp in ("Q1", "S1"):
            configs = list(X.get(exp).configs)
            rows = rows_for(exp, suite, ov)
            res = aggregate(rows, suite, configs)
            result["variants"][name][exp] = headline(res, rows, suite, configs)
    OUT.mkdir(parents=True)
    (OUT / "consolidated_draft.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "SHA256SUMS.txt").write_bytes(f"{sha(OUT / 'consolidated_draft.json')}  consolidated_draft.json\n".encode())

    def f(d):
        if isinstance(d, dict) and "lower" in d:
            lo, hi = d["lower"], d["upper"]
            return f"{lo['mean']} {lo['ci95']}" + ("" if lo["mean"] == hi["mean"] else f" – {hi['mean']} {hi['ci95']}")
        return f"{d['mean']} {d['ci95']}"
    for name in variants:
        print("=====", name, result["variants"][name]["applied_items"])
        for exp in ("Q1", "S1"):
            h = result["variants"][name][exp]
            print(" ", exp, "conditional set", h["conditional_set"])
            for c, v in h["configs"].items():
                ca = v["conditional_asr"]
                vs = {k: (x["mean_difference"], x["ci95"]) for k, x in (v["vs_unprotected"] or {}).items()}
                print(f"    {c}: att {f(v['attack_attempt'])} | succ {f(v['attack_success'])} | legit {f(v['legit_success'])} | cASR {ca['lower_mean']}-{ca['upper_mean']} {ca['ci95']} (n {ca['n_scenarios']}) | MR left {v['manual_review_runs_remaining']} {v['manual_review_scenarios']} | succ scen {v['succeeded_scenarios_any_rep']}")
                if vs:
                    print("       vs unprot", vs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
