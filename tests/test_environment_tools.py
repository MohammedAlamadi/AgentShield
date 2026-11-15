"""Component tests for the synthetic environment and the four simulated tools."""

import pytest

from agentshield.environment import Environment, state_id
from agentshield.tools import ToolArgumentError, execute_tool, parse_recipients, validate_arguments

from .conftest import BASE_STATE


def env() -> Environment:
    return Environment.from_initial_state(BASE_STATE)


def test_reset_gives_identical_state_and_id():
    a, b = env(), env()
    execute_tool(a, "send_email", validate_arguments("send_email", {"to": "bob@company.example", "body": "hi"}))
    execute_tool(a, "delete_file", {"name": "notes.txt"})
    assert a.snapshot() != b.snapshot()
    c = env()  # a fresh environment is unaffected by the previous run
    assert c.snapshot() == b.snapshot()
    assert c.initial_state_id == b.initial_state_id == state_id(BASE_STATE)
    assert "notes.txt" in c.files and c.outbox == []


def test_state_id_changes_with_content():
    changed = {**BASE_STATE, "contacts": ["someone@else.example"]}
    assert state_id(changed) != state_id(BASE_STATE)


def test_read_inbox_returns_all_emails_with_source_segments():
    e = env()
    out = execute_tool(e, "read_inbox", validate_arguments("read_inbox", {}))
    assert out.ok and out.sources == ["email:e1", "email:e2"]
    assert "From: sara.khan@company.example" in out.text and "evil@attacker.example" in out.text


def test_read_inbox_takes_no_arguments():
    # D6: email_id was removed; any argument is now rejected by validation.
    with pytest.raises(ToolArgumentError, match="unexpected argument"):
        validate_arguments("read_inbox", {"email_id": "e1"})


def test_read_inbox_empty():
    e = Environment.from_initial_state({"inbox": [], "files": [], "contacts": []})
    out = execute_tool(e, "read_inbox", {})
    assert out.ok and out.text == "The inbox is empty." and out.segments == []


def test_read_document_and_missing_document():
    e = env()
    out = execute_tool(e, "read_document", {"name": "notes.txt"})
    assert out.ok and out.text == "Team notes." and out.sources == ["document:notes.txt"]
    missing = execute_tool(e, "read_document", {"name": "nope.txt"})
    assert not missing.ok and missing.error == "missing_document"


def test_send_email_only_touches_simulated_outbox():
    e = env()
    args = validate_arguments("send_email", {"to": "Bob@Company.example", "subject": "s", "body": "b"})
    out = execute_tool(e, "send_email", args)
    assert out.ok and e.outbox[0].to == ("bob@company.example",)


def test_delete_file_only_touches_simulated_store(tmp_path):
    real = tmp_path / "notes.txt"
    real.write_text("real file")
    e = env()
    out = execute_tool(e, "delete_file", {"name": "notes.txt"})
    assert out.ok and "notes.txt" not in e.files and e.deleted_files == ["notes.txt"]
    assert real.exists()  # nothing on disk is touched
    again = execute_tool(e, "delete_file", {"name": "notes.txt"})
    assert not again.ok


@pytest.mark.parametrize(
    "tool,args,msg",
    [
        ("format_disk", {}, "unknown tool"),
        ("read_document", {}, "missing required argument 'name'"),
        ("read_document", {"name": ""}, "missing required argument 'name'"),
        ("read_document", {"name": ["a"]}, "must be a string"),
        ("read_document", {"name": "a", "extra": 1}, "unexpected argument"),
        ("send_email", {"body": "x"}, "missing required argument 'to'"),
        ("send_email", {"to": "not-an-address", "body": "x"}, "invalid email"),
        ("send_email", {"to": "a@b.example"}, "missing required argument 'body'"),
        ("delete_file", "notes.txt", "must be a JSON object"),
    ],
)
def test_argument_validation_rejects_bad_calls(tool, args, msg):
    with pytest.raises(ToolArgumentError, match=msg):
        validate_arguments(tool, args)


def test_recipient_parsing_lists_and_separators():
    assert parse_recipients("A@x.example; b@y.example") == ("a@x.example", "b@y.example")
    assert parse_recipients(["a@x.example", "b@y.example,c@z.example"]) == ("a@x.example", "b@y.example", "c@z.example")


def test_duplicate_ids_rejected():
    bad = {**BASE_STATE, "inbox": BASE_STATE["inbox"] + [BASE_STATE["inbox"][0]]}
    with pytest.raises(ValueError):
        Environment.from_initial_state(bad)
