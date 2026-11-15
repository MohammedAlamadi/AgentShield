"""Reviewer workbooks: blinding, round trip into the blind CSVs, and refusal to overwrite reviewer input."""

import pytest
from openpyxl import load_workbook

from agentshield.adjudication import _read_csv, export_blind, merge
from agentshield.frozen import load_frozen_suite, verify_frozen
from agentshield.review_workbooks import build_workbooks, import_workbook

SUITE = load_frozen_suite(verify_frozen())


def _items():
    return [{"item_id": f"QA-{i:03d}", "run_id": f"r{i}", "scenario_id": sid, "config": cfg, "model": "llama3.2:3b",
             "check": chk, "question": "q?", "user_request": SUITE.get(sid).user_request, "attacker_objective": "",
             "text": f"answer {i}", "automatic_verdict": "True", "verifier_detail": "SECRET-DETAIL", "stratum": "s"}
            for i, (sid, cfg, chk) in enumerate([("LR01", "unprotected", "legitimate"), ("AM01", "l3_only", "attack"), ("LS04", "full", "legitimate")])]


def _fill(path, name, labels):
    wb = load_workbook(path)
    ws = wb["Items"]
    head = [c.value for c in ws[1]]
    for r, lab in zip(range(2, ws.max_row + 1), labels):
        ws.cell(row=r, column=head.index("reviewer_name") + 1, value=name)
        ws.cell(row=r, column=head.index("label") + 1, value=lab)
        ws.cell(row=r, column=head.index("rationale") + 1, value="because")
    wb.save(path)


def test_workbooks_are_blind_and_round_trip(tmp_path):
    d = tmp_path / "qa"
    export_blind(_items(), d, prefix="p", seed=413)
    w1, w2 = build_workbooks(d, "p", SUITE, labels=("True", "False"), instructions=["x"])
    blob = " ".join(str(c.value) for r in load_workbook(w1)["Items"].iter_rows() for c in r if c.value)
    for hidden in ("unprotected", "l3_only", "llama3.2", "SECRET-DETAIL", "r0", "automatic"):
        assert hidden not in blob
    assert "Tuesday 9 December" in blob  # LR01 source email is shown
    with pytest.raises(FileExistsError):
        build_workbooks(d, "p", SUITE, labels=("True", "False"), instructions=["x"])
    _fill(w1, "Ali", [True, "false", "TRUE"])  # Excel booleans and case are normalised
    _fill(w2, "Saif", ["True", "False", "True"])
    assert import_workbook(w1, d / "p_reviewer_1.csv", ("True", "False")) == 3
    assert import_workbook(w2, d / "p_reviewer_2.csv", ("True", "False")) == 3
    order = [r["item_id"] for r in _read_csv(d / "p_reviewer_1.csv")]
    assert [r["label"] for r in _read_csv(d / "p_reviewer_1.csv")] == ["True", "False", "True"]
    res = merge(d, prefix="p", labels=("True", "False"), require_rule=False)
    assert res["stats"]["raw_agreement"] == 1.0 and [r["item_id"] for r in res["rows"]] == order
    with pytest.raises(ValueError, match="already contains"):
        import_workbook(w1, d / "p_reviewer_1.csv", ("True", "False"))


def test_import_rejects_reordered_items(tmp_path):
    d = tmp_path / "qa"
    export_blind(_items(), d, prefix="p", seed=413)
    w1, _ = build_workbooks(d, "p", SUITE, labels=("True", "False"), instructions=["x"])
    wb = load_workbook(w1)
    ws = wb["Items"]
    ws.move_range("A2:A2", rows=10)  # break the item order
    wb.save(w1)
    with pytest.raises(ValueError, match="differ"):
        import_workbook(w1, d / "p_reviewer_1.csv", ("True", "False"))
