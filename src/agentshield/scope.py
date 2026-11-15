"""Trusted task scope chosen by the user through an application control (CLI flag / menu).

The scope is passed to the guard separately from the conversation. It is never inferred
from the request wording, emails, documents or model output, and nothing retrieved
during a task can change it (D1, Section III-C-3 and Table IV).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCOPE_KINDS = ("read_summarise", "send_email", "reply_email", "delete_file")


@dataclass(frozen=True)
class TaskScope:
    kind: str
    # send_email: recipients the user listed in the scope
    recipients: tuple[str, ...] = ()
    # send_email: subset of ``recipients`` typed in by the user (allowed even if not a trusted contact)
    user_entered_recipients: tuple[str, ...] = ()
    # reply_email: id of the email the user chose to reply to (recipient comes from its mailbox metadata)
    reply_to_email_id: str | None = None
    # delete_file: the single file the user authorised for deletion
    filename: str | None = None
    extra: dict[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if self.kind not in SCOPE_KINDS:
            raise ValueError(f"unknown scope kind '{self.kind}'; expected one of {SCOPE_KINDS}")
        if self.kind == "send_email" and not self.recipients:
            raise ValueError("send_email scope needs at least one recipient")
        if self.kind == "reply_email" and not self.reply_to_email_id:
            raise ValueError("reply_email scope needs reply_to_email_id")
        if self.kind == "delete_file" and not self.filename:
            raise ValueError("delete_file scope needs filename")
        if not set(self.user_entered_recipients) <= set(self.recipients):
            raise ValueError("user_entered_recipients must be a subset of recipients")

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TaskScope":
        return cls(
            kind=d["kind"],
            recipients=tuple(r.lower() for r in d.get("recipients", [])),
            user_entered_recipients=tuple(r.lower() for r in d.get("user_entered_recipients", [])),
            reply_to_email_id=d.get("reply_to_email_id"),
            filename=d.get("filename"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "recipients": list(self.recipients),
            "user_entered_recipients": list(self.user_entered_recipients),
            "reply_to_email_id": self.reply_to_email_id,
            "filename": self.filename,
        }
