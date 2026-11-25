"""Reproduce the official R1, Q1 and S1 aggregates from the saved run logs and adjudication records.

Read-only with respect to the repository: it verifies the frozen datasets, re-aggregates each experiment
with exactly the same code path as `python -m agentshield aggregate <EXP>` (cli.cmd_aggregate), writes
the result to a temporary directory, and compares it with the official aggregate:

* aggregate.json: every value must be equal (only the volatile `generated_utc` timestamp is ignored);
* per_scenario.csv: must be byte-identical.

Nothing under results/ is created or changed, no model is called and no experiment is re-run.

Run from the repository root (after `pip install -e . --no-deps`):
    python scripts/eval/verify_reproduction.py
Exit code 0 = all official aggregates reproduced exactly; 1 = at least one difference.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

from agentshield import experiments as X
from agentshield.aggregate import aggregate, check_consistency, load_classified, write_aggregate
from agentshield.frozen import ROOT, load_frozen_suite, verify_frozen

# Official aggregates cited in the D2 report and docs/D2_results_inventory.md (sections 6 and 7).
OFFICIAL = {
    "R1": "R1_20261113T212758Z",
    "Q1": "Q1_20261114T131523Z",
    "S1": "S1_20261118T154119Z",
}
VOLATILE = {"generated_utc"}


def _diff(a, b, path: str, out: list[str]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in VOLATILE:
                continue
            if k not in a or k not in b:
                out.append(f"{path}/{k}: present only in {'reproduced' if k in a else 'official'}")
            else:
                _diff(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} != {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                _diff(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append(f"{path}: reproduced {a!r} != official {b!r}")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reproduce(exp_id: str, suite, tmp: Path) -> Path:
    """Same steps as cli.cmd_aggregate, but written to a temporary directory."""
    sets = [s for s in X.run_sets(exp_id) if s["status"] == "finished" and s["complete"]]
    info = check_consistency(sets)
    res = aggregate(load_classified(sets, suite), suite, info["configs"])
    res["skipped_incomplete_run_sets"] = [str(s["path"]) for s in X.run_sets(exp_id) if s not in sets]
    return write_aggregate(res, sets, tmp / exp_id, exp_id)


def main() -> int:
    frozen = verify_frozen()
    print("Frozen datasets: manifest and dataset hashes verified")
    suite = load_frozen_suite(frozen)
    ok = True
    with tempfile.TemporaryDirectory(prefix="agentshield_repro_") as t:
        for exp_id, official_name in OFFICIAL.items():
            official = ROOT / "results" / "eval" / "aggregates" / official_name
            if not (official / "aggregate.json").exists():
                print(f"{exp_id}: MISSING official aggregate {official.relative_to(ROOT)}")
                ok = False
                continue
            new = reproduce(exp_id, suite, Path(t))
            diffs: list[str] = []
            _diff(json.loads((new / "aggregate.json").read_text(encoding="utf-8")),
                  json.loads((official / "aggregate.json").read_text(encoding="utf-8")), "", diffs)
            csv_same = _sha(new / "per_scenario.csv") == _sha(official / "per_scenario.csv")
            status = "REPRODUCED EXACTLY" if not diffs and csv_same else "DIFFERS"
            ok &= status == "REPRODUCED EXACTLY"
            print(f"{exp_id}: {status} vs {official_name} (aggregate.json differences: {len(diffs)}; "
                  f"per_scenario.csv identical: {csv_same})")
            for d in diffs[:20]:
                print("    ", d)
    print("ALL OFFICIAL AGGREGATES REPRODUCED" if ok else "REPRODUCTION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
