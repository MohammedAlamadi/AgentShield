"""Layer 3 - deterministic tool-call authorization guard (D1 Section III-C-3, Table IV).

Security properties:
* Deny by default: a call is allowed only if a rule below explicitly permits it.
* Permissions come ONLY from the trusted TaskScope (selected by the user through an
  application control) and the trusted contact list / mailbox metadata in the environment.
  Nothing in retrieved emails, documents or model output can create or widen a permission;
  the scope object is immutable and the guard exposes no way to change it.
* The guard never consults the language model.
* At most one high-risk action (send_email or delete_file) is executed per task.

Known limitation (kept on purpose, reported in D2): the guard checks tool calls only. It
cannot detect abuse *inside* an authorised action (e.g. leaked text in a permitted reply)
and it does not check the assistant's final natural-language answer.
"""

from __future__ import annotations

from typing import Any

from .agent import GuardDecision
from .environment import Environment
from .scope import TaskScope
from .tools import HIGH_RISK_TOOLS, TOOL_NAMES

SCOPE_PERMISSIONS: dict[str, frozenset[str]] = {
    "read_summarise": frozenset({"read_inbox", "read_document"}),
    "send_email": frozenset({"read_inbox", "read_document", "send_email"}),
    "reply_email": frozenset({"read_inbox", "send_email"}),
    "delete_file": frozenset({"read_document", "delete_file"}),
}

POLICY_MESSAGE = (
    "[AgentShield] Action blocked by the user's task policy: {reason}. "
    "It was not performed. Continue the user's original task using only permitted actions."
)


class AuthorizationGuard:
    def __init__(self) -> None:
        self._high_risk_done = 0

    def start_run(self) -> None:
        """Reset per-task state. Called by the agent at the start of every run."""
        self._high_risk_done = 0

    def record_executed(self, tool_name: str, args: dict[str, Any]) -> None:
        """Called after a call was executed successfully, to enforce the one-action limit."""
        if tool_name in HIGH_RISK_TOOLS:
            self._high_risk_done += 1

    # ------------------------------------------------------------------ main check
    def check(self, tool_name: str, args: dict[str, Any], scope: TaskScope, env: Environment) -> GuardDecision:
        reason = self._deny_reason(tool_name, args, scope, env)
        if reason is None:
            return GuardDecision(allowed=True, reason=f"{tool_name} permitted by '{scope.kind}' scope")
        return GuardDecision(allowed=False, reason=reason, policy_message=POLICY_MESSAGE.format(reason=reason))

    def _deny_reason(self, tool_name: str, args: dict[str, Any], scope: TaskScope, env: Environment) -> str | None:
        if tool_name not in TOOL_NAMES:
            return f"unsupported tool '{tool_name}'"
        permitted = SCOPE_PERMISSIONS.get(scope.kind, frozenset())  # unknown scope => nothing permitted
        if tool_name not in permitted:
            return f"{tool_name} is not permitted in the '{scope.kind}' scope"
        if tool_name in HIGH_RISK_TOOLS and self._high_risk_done >= 1:
            return "only one high-risk action (send or delete) is allowed per task"

        if tool_name == "send_email":
            recipients = tuple(r.lower() for r in args.get("to", ()))
            if not recipients:
                return "no recipient"
            if scope.kind == "send_email":
                for r in recipients:
                    if r not in scope.recipients:
                        return f"recipient {r} is not listed in the user's task scope"
                    if r not in env.contacts and r not in scope.user_entered_recipients:
                        return f"recipient {r} is neither a trusted contact nor entered by the user"
                return None
            if scope.kind == "reply_email":
                original = env.get_email(scope.reply_to_email_id or "")
                if original is None:
                    return "the email selected for reply does not exist"
                # Recipient comes from trusted mailbox metadata, never from text in the email body.
                if recipients != (original.sender.lower(),):
                    return f"a reply may only go to the original sender {original.sender}"
                return None
            return "sending is not permitted in this scope"  # unreachable given SCOPE_PERMISSIONS

        if tool_name == "delete_file":
            if args.get("name") != scope.filename:
                return f"only the file named in the scope ({scope.filename}) may be deleted"
            return None

        return None  # read_inbox / read_document permitted by scope
