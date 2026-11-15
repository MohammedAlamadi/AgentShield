"""Access to the FROZEN eval-v1 datasets. Every evaluation entry point calls ``verify_frozen()`` first.

Verification is fail-closed: the manifest's own hash must equal the value recorded at the freeze, and
every dataset, scoring file, rubric and audit plan listed in it must still have its recorded hash.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "data" / "eval"
MANIFEST_PATH = EVAL_DIR / "FROZEN_MANIFEST.json"
FROZEN_VERSION = "eval-v1"
# Recorded at the freeze (13 Nov 2026); also asserted in tests/test_frozen_datasets.py.
FROZEN_MANIFEST_SHA256 = "744c62736c8fe5f67a582c8ffa41e6c1459ebc79dc1a555e25617aebb5b01102"


class FrozenDatasetError(RuntimeError):
    """A frozen artefact is missing or differs from the freeze record. Never run an evaluation then."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class FrozenInfo:
    version: str
    manifest_path: Path
    manifest_sha256: str
    detector_path: Path
    detector_sha256: str
    scenarios_path: Path
    scenarios_sha256: str
    scoring: dict[str, str]
    manifest: dict[str, Any]

    def as_log(self) -> dict[str, Any]:
        """Compact record written into every run log and run manifest."""
        return {"version": self.version, "manifest_sha256": self.manifest_sha256,
                "detector_dataset": {"path": self.detector_path.relative_to(ROOT).as_posix(), "sha256": self.detector_sha256},
                "scenario_dataset": {"path": self.scenarios_path.relative_to(ROOT).as_posix(), "sha256": self.scenarios_sha256},
                "scoring": self.scoring}


def verify_frozen(root: Path = ROOT, expected_manifest_sha256: str = FROZEN_MANIFEST_SHA256) -> FrozenInfo:
    manifest_path = root / "data" / "eval" / "FROZEN_MANIFEST.json"
    if not manifest_path.exists():
        raise FrozenDatasetError(f"{manifest_path} not found: datasets are not frozen")
    msha = sha256_file(manifest_path)
    if msha != expected_manifest_sha256:
        raise FrozenDatasetError(f"FROZEN_MANIFEST.json hash {msha} != recorded {expected_manifest_sha256}")
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    if m.get("status") != "FROZEN" or m.get("version") != FROZEN_VERSION:
        raise FrozenDatasetError(f"manifest status/version is {m.get('status')}/{m.get('version')}, expected FROZEN/{FROZEN_VERSION}")
    problems = []
    paths = {}
    for key in ("detector", "scenarios"):
        d = m["datasets"][key]
        p = root / d["path"]
        paths[key] = p
        if not p.exists():
            problems.append(f"{d['path']} missing")
        elif sha256_file(p) != d["sha256"]:
            problems.append(f"{d['path']} hash differs from the freeze record")
    for key, digest in m["scoring"].items():
        p = root / key.split(" ")[0]
        if not p.exists() or sha256_file(p) != digest:
            problems.append(f"{key} differs from the freeze record")
    if problems:
        raise FrozenDatasetError("; ".join(problems))
    return FrozenInfo(version=m["version"], manifest_path=manifest_path, manifest_sha256=msha,
                      detector_path=paths["detector"], detector_sha256=m["datasets"]["detector"]["sha256"],
                      scenarios_path=paths["scenarios"], scenarios_sha256=m["datasets"]["scenarios"]["sha256"],
                      scoring=dict(m["scoring"]), manifest=m)


def load_frozen_detector_examples(info: FrozenInfo) -> list[dict[str, Any]]:
    raw = info.detector_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != info.detector_sha256:  # re-check at read time
        raise FrozenDatasetError("detector dataset changed after verification")
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def load_frozen_suite(info: FrozenInfo):
    from .scenarios import load_suite

    suite = load_suite(info.scenarios_path)
    if suite.sha256 != info.scenarios_sha256:  # re-check at read time
        raise FrozenDatasetError("scenario dataset changed after verification")
    return suite
