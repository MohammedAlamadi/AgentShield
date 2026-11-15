"""One JSON-lines log per run. Events are flushed as they happen so an interrupted run
still leaves a readable partial log."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable


def _default(o: Any) -> Any:
    if is_dataclass(o):
        return asdict(o)
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


class RunLogger:
    def __init__(self, path: str | Path | None, echo: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.path = Path(path) if path else None
        self.events: list[dict[str, Any]] = []
        self._t0 = time.perf_counter()
        self._echo = echo
        self._fh = None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = self.path.open("w", encoding="utf-8", newline="\n")

    def log(self, event: str, **fields: Any) -> dict[str, Any]:
        rec = {"event": event, "t_s": round(time.perf_counter() - self._t0, 4), **fields}
        self.events.append(rec)
        if self._fh:
            self._fh.write(json.dumps(rec, ensure_ascii=False, default=_default) + "\n")
            self._fh.flush()
        if self._echo:
            self._echo(rec)
        return rec

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
