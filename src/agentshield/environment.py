"""Synthetic, in-memory environment: inbox, file store, outbox and trusted contacts.

Nothing here touches the real file system or any real mail service. Each run builds a
fresh Environment from a scenario's initial state, so every scenario x configuration
starts from an identical state (verified via ``initial_state_id``).
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Email:
    id: str
    sender: str  # trusted mailbox metadata (the "From" header), never parsed from the body
    subject: str
    body: str


@dataclass(frozen=True)
class Document:
    name: str
    content: str
    confidential: bool = False


@dataclass(frozen=True)
class SentEmail:
    to: tuple[str, ...]
    subject: str
    body: str


@dataclass
class Environment:
    inbox: list[Email]
    files: dict[str, Document]
    contacts: tuple[str, ...]
    outbox: list[SentEmail] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    initial_state_id: str = ""

    # ------------------------------------------------------------------ construction
    @classmethod
    def from_initial_state(cls, state: dict[str, Any]) -> "Environment":
        """Build a fresh environment from a scenario's ``initial_state`` dictionary."""
        state = copy.deepcopy(state)
        inbox = [
            Email(id=e["id"], sender=e["from"], subject=e.get("subject", ""), body=e.get("body", ""))
            for e in state.get("inbox", [])
        ]
        files = {
            d["name"]: Document(name=d["name"], content=d.get("content", ""), confidential=bool(d.get("confidential", False)))
            for d in state.get("files", [])
        }
        ids = [e.id for e in inbox]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate email ids in initial state: {ids}")
        if len(files) != len(state.get("files", [])):
            raise ValueError("duplicate document names in initial state")
        contacts = tuple(c.lower() for c in state.get("contacts", []))
        return cls(inbox=inbox, files=files, contacts=contacts, initial_state_id=state_id(state))

    # ------------------------------------------------------------------ queries
    def get_email(self, email_id: str) -> Email | None:
        return next((e for e in self.inbox if e.id == email_id), None)

    def snapshot(self) -> dict[str, Any]:
        """JSON-serialisable view of the current state (for logs and verifiers)."""
        return {
            "inbox_ids": [e.id for e in self.inbox],
            "files": sorted(self.files),
            "deleted_files": list(self.deleted_files),
            "outbox": [asdict(m) | {"to": list(m.to)} for m in self.outbox],
        }


def state_id(state: dict[str, Any]) -> str:
    """Deterministic identifier (sha256 of canonical JSON) for an initial state."""
    canonical = json.dumps(state, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
