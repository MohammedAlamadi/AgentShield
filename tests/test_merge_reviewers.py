"""D1 (Stage 1 decision): reviewer independence is validated PER ITEM, so several people may share a sheet
(rotating pairs), but the same person may never give both labels of an item."""

import csv

import pytest

from agentshield.adjudication import MergeError, _read_csv, export_blind, merge

PAIRS = [("Mohammed Adel", "Saif"), ("Saif", "Mohammed Wasfi"), ("Ali", "Abdulaziz"), ("Abdulaziz", "Ali"), ("Mohammed Wasfi", "Mohammed Adel")]
LABELS = ("True", "False")


def _items(n):
    return [{"item_id": f"QA-{i:03d}", "run_id": f"r{i}", "scenario_id": "LR01", "config": "unprotected", "model": "m", "check": "legitimate",
             "question": "q?", "user_request": "req", "attacker_objective": "", "text": f"t{i}", "automatic_verdict": "True",
             "verifier_detail": "", "stratum": "s"} for i in range(n)]


def _write(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def _fill(d, names1, names2, labels1, labels2):
    for n, names, labels in ((1, names1, labels1), (2, names2, labels2)):
        p = d / f"p_reviewer_{n}.csv"
        rows = _read_csv(p)
        for r, name, lab in zip(rows, names, labels):
            r.update(reviewer_name=name, label=lab, rationale="because")
        _write(p, rows)


def _setup(tmp_path, n=40):
    d = tmp_path / "qa"
    export_blind(_items(n), d, prefix="p", seed=413)
    return d


def _rotating(n=40):
    first = [PAIRS[i // 8][0] for i in range(n)]
    second = [PAIRS[i // 8][1] for i in range(n)]
    return first, second


def test_rotating_pairs_with_different_people_per_item_merge(tmp_path):
    d = _setup(tmp_path)
    n1, n2 = _rotating()
    _fill(d, n1, n2, ["True"] * 40, ["True"] * 40)
    res = merge(d, prefix="p", labels=LABELS, require_rule=False)
    st = res["stats"]
    assert st["n_items"] == 40 and st["raw_agreement"] == 1.0 and len(st["reviewer_pairs"]) == 5
    assert all(r["primary_reviewer"] != r["secondary_reviewer"] for r in res["rows"])


def test_same_person_on_one_item_is_rejected_and_named(tmp_path):
    d = _setup(tmp_path)
    n1, n2 = _rotating()
    n2[5] = n1[5]  # one item labelled twice by the same person
    n2[30] = n1[30].upper()  # case differences do not make two people
    _fill(d, n1, n2, ["True"] * 40, ["True"] * 40)
    with pytest.raises(MergeError) as e:
        merge(d, prefix="p", labels=LABELS, require_rule=False)
    same = [p for p in e.value.args[0] if "same person" in p]
    assert len(same) == 2
    order = [r["item_id"] for r in _read_csv(d / "p_reviewer_1.csv")]
    assert order[5] in same[0] or order[5] in same[1]


def test_missing_reviewer_names_are_rejected(tmp_path):
    d = _setup(tmp_path, n=6)
    n1, n2 = _rotating(6)
    n1[2] = ""
    n2[4] = "  "
    _fill(d, n1, n2, ["True"] * 6, ["True"] * 6)
    with pytest.raises(MergeError) as e:
        merge(d, prefix="p", labels=LABELS, require_rule=False)
    assert sum("missing reviewer name" in p for p in e.value.args[0]) == 2


def test_incomplete_cases_are_rejected(tmp_path):
    d = _setup(tmp_path, n=6)
    n1, n2 = _rotating(6)
    _fill(d, n1, n2, ["True", "", "False", "True", "maybe", "True"], ["True"] * 6)
    with pytest.raises(MergeError) as e:
        merge(d, prefix="p", labels=LABELS, require_rule=False)
    msgs = e.value.args[0]
    assert any("missing label" in p for p in msgs) and any("'maybe' not in" in p for p in msgs)
    assert not (d / "p.csv").exists()


def test_third_member_must_differ_from_that_items_reviewers(tmp_path):
    d = _setup(tmp_path, n=16)
    n1, n2 = _rotating(16)  # items 0-7: Mohammed Adel / Saif; items 8-15: Saif / Mohammed Wasfi
    l1 = ["True"] * 16
    l2 = ["True"] * 16
    l2[0] = "False"
    _fill(d, n1, n2, l1, l2)
    order = [r["item_id"] for r in _read_csv(d / "p_reviewer_1.csv")]
    res = d / "p_resolutions.csv"
    _write(res, [{"item_id": order[0], "final_label": "True", "resolution": "third-member", "decider": "Saif", "rationale": "x"}])
    with pytest.raises(MergeError, match="neither reviewer"):
        merge(d, prefix="p", labels=LABELS, require_rule=False)
    # Mohammed Wasfi reviewed other items, but not this one: allowed as the third member here
    _write(res, [{"item_id": order[0], "final_label": "True", "resolution": "third-member", "decider": "Mohammed Wasfi", "rationale": "x"}])
    out = merge(d, prefix="p", labels=LABELS, require_rule=False)
    assert out["stats"]["resolutions"] == {"third-member": 1, "agreed": 15}
