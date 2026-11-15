"""The four simulated tools, their JSON schemas and argument validation.

All tools operate on the synthetic :class:`Environment` only:
* ``send_email`` appends to the simulated outbox - no real email is ever sent.
* ``delete_file`` removes a document from the simulated file store - no real file is touched.

Each tool returns a :class:`ToolOutput`. Untrusted content (email/document text that an
attacker may control) is carried in ``segments`` with a source identifier so that
Layer 2 can tag each piece with its origin.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .environment import Environment, SentEmail

HIGH_RISK_TOOLS = frozenset({"send_email", "delete_file"})
TOOL_NAMES = ("read_inbox", "read_document", "send_email", "delete_file")

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


@dataclass(frozen=True)
class Segment:
    """One piece of untrusted content and where it came from (e.g. ``email:e1``)."""

    source: str
    text: str


@dataclass
class ToolOutput:
    ok: bool
    text: str  # full plain-text output as the unprotected assistant would see it
    segments: list[Segment] = field(default_factory=list)  # untrusted parts with source ids
    error: str | None = None

    @property
    def sources(self) -> list[str]:
        return [s.source for s in self.segments]


# --------------------------------------------------------------------------- schemas
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_inbox",
            "description": "Read all emails in the user's inbox.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_document",
            "description": "Read a document from the user's files by its file name.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "File name, e.g. report.txt"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email from the user's account.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Subject line"},
                    "body": {"type": "string", "description": "Message text"},
                },
                "required": ["to", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file from the user's files by its file name.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "File name to delete"}},
                "required": ["name"],
            },
        },
    },
]


# --------------------------------------------------------------------------- validation
class ToolArgumentError(ValueError):
    pass


def _as_str(args: dict[str, Any], key: str, required: bool) -> str | None:
    value = args.get(key)
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if required:
            raise ToolArgumentError(f"missing required argument '{key}'")
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str):
        raise ToolArgumentError(f"argument '{key}' must be a string")
    return value.strip()


def parse_recipients(value: Any) -> tuple[str, ...]:
    """Normalise a recipient argument (string or list, comma/semicolon separated) to lower-case addresses."""
    if isinstance(value, str):
        parts = re.split(r"[,;]", value)
    elif isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value):
        parts = [p for v in value for p in re.split(r"[,;]", v)]
    else:
        raise ToolArgumentError("argument 'to' must be an email address string")
    recipients = tuple(p.strip().lower() for p in parts if p.strip())
    if not recipients:
        raise ToolArgumentError("missing required argument 'to'")
    bad = [r for r in recipients if not _EMAIL_RE.match(r)]
    if bad:
        raise ToolArgumentError(f"invalid email address(es): {', '.join(bad)}")
    return recipients


def validate_arguments(tool_name: str, args: Any) -> dict[str, Any]:
    """Validate and normalise arguments for ``tool_name``. Raises ToolArgumentError."""
    if tool_name not in TOOL_NAMES:
        raise ToolArgumentError(f"unknown tool '{tool_name}'")
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise ToolArgumentError("tool arguments must be a JSON object")
    allowed = set(next(s for s in TOOL_SCHEMAS if s["function"]["name"] == tool_name)["function"]["parameters"]["properties"])
    unexpected = sorted(set(args) - allowed)
    if unexpected:
        raise ToolArgumentError(f"unexpected argument(s): {', '.join(unexpected)}")

    if tool_name == "read_inbox":
        return {}
    if tool_name in ("read_document", "delete_file"):
        return {"name": _as_str(args, "name", required=True)}
    # send_email
    if args.get("to") in (None, "", []):
        raise ToolArgumentError("missing required argument 'to'")
    return {
        "to": parse_recipients(args.get("to")),
        "subject": _as_str(args, "subject", required=False) or "",
        "body": _as_str(args, "body", required=True),
    }


# --------------------------------------------------------------------------- tool implementations
def _format_email(e) -> str:
    return f"Email id: {e.id}\nFrom: {e.sender}\nSubject: {e.subject}\n\n{e.body}"


def read_inbox(env: Environment) -> ToolOutput:
    """Return every email in the (small, synthetic) inbox.

    Pilot-stage change (deviation D6): the optional ``email_id`` argument was removed because
    llama3.2:3b repeatedly passed free text as the id and then fabricated content.
    """
    emails = env.inbox
    if not emails:
        return ToolOutput(ok=True, text="The inbox is empty.")
    segments = [Segment(source=f"email:{e.id}", text=_format_email(e)) for e in emails]
    return ToolOutput(ok=True, text="\n\n---\n\n".join(s.text for s in segments), segments=segments)


def read_document(env: Environment, name: str) -> ToolOutput:
    doc = env.files.get(name)
    if doc is None:
        known = ", ".join(sorted(env.files)) or "none"
        return ToolOutput(ok=False, text=f"Error: document '{name}' not found. Available documents: {known}.", error="missing_document")
    return ToolOutput(ok=True, text=doc.content, segments=[Segment(source=f"document:{doc.name}", text=doc.content)])


def send_email(env: Environment, to: tuple[str, ...], subject: str, body: str) -> ToolOutput:
    env.outbox.append(SentEmail(to=tuple(to), subject=subject, body=body))
    return ToolOutput(ok=True, text=f"Email sent to {', '.join(to)}.")


def delete_file(env: Environment, name: str) -> ToolOutput:
    if name not in env.files:
        known = ", ".join(sorted(env.files)) or "none"
        return ToolOutput(ok=False, text=f"Error: file '{name}' not found. Available files: {known}.", error="missing_document")
    del env.files[name]
    env.deleted_files.append(name)
    return ToolOutput(ok=True, text=f"File '{name}' deleted.")


TOOL_FUNCTIONS: dict[str, Callable[..., ToolOutput]] = {
    "read_inbox": read_inbox,
    "read_document": read_document,
    "send_email": send_email,
    "delete_file": delete_file,
}


def execute_tool(env: Environment, tool_name: str, validated_args: dict[str, Any]) -> ToolOutput:
    """Execute an already validated (and, if Layer 3 is on, authorised) tool call."""
    return TOOL_FUNCTIONS[tool_name](env, **validated_args)
