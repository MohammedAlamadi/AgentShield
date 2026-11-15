"""Validate the three completed review workbooks (A attack outcomes, B R1 Layer 3, C Q1+S1 Layer 3) against the
raw logs, the generated evidence and the frozen rubric. Read-only: workbooks are read from the hashed snapshot
docs/evidence/final_review_completed/; nothing is labelled, merged or finalised here.

    .venv\\Scripts\\python scripts\\eval\\validate_final_reviews.py [snapshot_dir out_dir]   (folders under docs/evidence/)

Writes (new folder, never overwritten): docs/evidence/final_review_validation/validation.json + SHA256SUMS.txt
Checks per record: identity (id -> experiment/repetition/scenario/config/log, log hash), evidence columns unchanged,
allowed label values, reviewer independence (two different names), agreement, final == recorded agreement,
resolution present when needed, and factual claims in comments (e-mail addresses, quoted strings, "no prior calls",
"already executed") checked against the logged evidence. Findings are flags for the team, not corrections.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "eval"))
import openpyxl  # noqa: E402

import make_final_review_package as P  # noqa: E402
from agentshield.frozen import load_frozen_suite, verify_frozen  # noqa: E402

SNAP = ROOT / "docs" / "evidence" / (sys.argv[1] if len(sys.argv) > 1 else "final_review_completed")
OUT = ROOT / "docs" / "evidence" / (sys.argv[2] if len(sys.argv) > 2 else "final_review_validation")
PKG = ROOT / "docs" / "evidence" / "final_review_package"
R1E = ROOT / "docs" / "evidence" / "l3_block_review_r1"
CATS = {"incorrect_arguments", "unauthorised_behaviour", "false_block"}
LABELS = {"SUCCESS", "NOT SUCCESS"}
RULES = {"A1", "A2", "A3", "A4", "B1", "B2", "B3", "C1"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
QUOTE = re.compile(r"(?<![A-Za-z])\"([^\"\n]{6,160}?)[,.]?\"(?![A-Za-z])")
NO_PRIOR = re.compile(r"no (earlier|prior|previous)[^.]*?(calls?|actions?)|prior_calls field (is empty|records no|shows no|contains no)|no recorded prior|no earlier calls", re.I)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower().strip(" .,;:")


def rows(path: Path, sheet: str) -> list[dict]:
    ws = openpyxl.load_workbook(path)[sheet]
    h = [c.value for c in ws[1]]
    return [dict(zip(h, r)) for r in ws.iter_rows(min_row=2, values_only=True) if any(v is not None for v in r)], h


def claims(comment: str, evidence_text: str, prior_empty: bool) -> list[str]:
    issues = []
    ev = evidence_text.lower()
    for e in set(EMAIL.findall(comment or "")):
        if e.lower() not in ev:
            issues.append(f"address '{e}' not found in the row's evidence or scenario")
    for q in QUOTE.findall(comment or ""):
        if norm(q) not in norm(evidence_text):
            issues.append(f"quoted text \"{q[:80]}\" not found verbatim in the evidence")
    if NO_PRIOR.search(comment or "") and not prior_empty:
        issues.append("comment says there were no prior calls, but prior_calls is not empty")
    if re.search(r"already (been )?(successfully )?(sent|executed|completed|delivered)", comment or "", re.I) and prior_empty:
        issues.append("comment says the action was already executed, but prior_calls is empty")
    return issues


def reviewer_checks(r1n, r2n, c1, c2, final, resolution, allowed, pending_word="PENDING"):
    out = []
    n1, n2 = norm(r1n), norm(r2n)
    if not n1 or not n2:
        out.append("missing reviewer name")
    elif n1.startswith("unresolved") or n2.startswith("unresolved"):
        out.append("reviewer identity UNRESOLVED - not a completed two-reviewer decision")
    elif n1 == n2:
        out.append(f"SAME PERSON recorded as reviewer 1 and reviewer 2 ('{r1n}') - not two independent reviews")
    for k, v in (("reviewer 1", c1), ("reviewer 2", c2)):
        if v not in allowed:
            out.append(f"{k} label '{v}' is not an allowed value")
    if c1 in allowed and c2 in allowed and c1 != c2 and not resolution:
        out.append("reviewers disagree and no resolution is recorded")
    if final in (None, "", pending_word):
        out.append("final decision still pending")
    elif c1 in allowed and c2 in allowed and c1 == c2 and final != c1:
        out.append("final decision differs from both reviewers' agreed label")
    elif final not in allowed:
        out.append(f"final decision '{final}' is not an allowed value")
    return out


def main() -> int:
    if OUT.exists():
        print(f"REFUSED: {OUT} exists")
        return 1
    snap = {l.split("  ")[1]: l.split("  ")[0] for l in (SNAP / "SHA256SUMS.txt").read_text().splitlines() if l.strip() and l.endswith(".xlsx")}
    for name, h in snap.items():
        assert sha(SNAP / name) == h, f"snapshot {name} changed"
    suite = load_frozen_suite(verify_frozen())
    report = {"snapshot": {k: v for k, v in snap.items()}, "A": [], "B": [], "C": [], "workbook_level": []}

    # ---------------- A ----------------
    rowsA, hA = rows(SNAP / "A_attack_outcomes_review.xlsx", "Attack items (blind)")
    if "ai_assistance_disclosed" not in hA:
        report["workbook_level"].append("A: column 'ai_assistance_disclosed' was removed; AI assistance is not recorded")
    key = {r["item"]: r for r in csv.DictReader(open(PKG / "A_attack_outcomes_key.csv", encoding="utf-8"))}
    regen = P.attack_items(suite)
    by_log = {it["_key"]["log"]: it for it in regen}
    for r in rowsA:
        k = key.get(r["item"])
        rec = {"item": r["item"], "issues": []}
        if not k:
            rec["issues"].append("item not in key")
            report["A"].append(rec)
            continue
        log = ROOT / k["log"]
        rec.update(experiment=k["experiment"], repetition=k["repetition"], scenario=k["scenario_id"], config=k["config"], log=k["log"])
        if sha(log) != k["log_sha256"]:
            rec["issues"].append("log hash differs from key")
        g = by_log[k["log"]]
        for col in ("user_request", "attacker_objective", "tool_actions", "final_answer", "verifier_detail"):
            if norm(r[col]) != norm(g[col]):
                rec["issues"].append(f"evidence column '{col}' differs from the log")
        evtext = " ".join(str(r[c] or "") for c in ("user_request", "attacker_objective", "genuine_content_of_that_source", "tool_actions", "emails_sent", "final_answer"))
        evtext += " " + json.dumps(suite.get(k["scenario_id"]).initial_state)
        for n in (1, 2):
            for i in claims(r[f"reviewer_{n}_rationale"], evtext, True):
                if "prior calls" not in i and "already executed" not in i:
                    rec["issues"].append(f"reviewer {n}: {i}")
        for n in (1, 2):
            if r[f"reviewer_{n}_rule"] not in RULES:
                rec["issues"].append(f"reviewer {n} rule '{r[f'reviewer_{n}_rule']}' not a rubric rule")
        if r["reviewer_1_label"] == r["reviewer_2_label"] and r["reviewer_1_rule"] != r["reviewer_2_rule"]:
            rec["issues"].append("same label but different rules")
        rec["issues"] += reviewer_checks(r["reviewer_1_name"], r["reviewer_2_name"], r["reviewer_1_label"], r["reviewer_2_label"],
                                         r["final_label"], r["resolution_note"], LABELS)
        rec["labels"] = {"r1": [r["reviewer_1_name"], r["reviewer_1_label"], r["reviewer_1_rule"]],
                         "r2": [r["reviewer_2_name"], r["reviewer_2_label"], r["reviewer_2_rule"]], "final": r["final_label"]}
        report["A"].append(rec)

    # ---------------- B and C (Layer 3) ----------------
    r1den = {d["id"]: d for d in json.loads((R1E / "l3_denials_r1.json").read_text(encoding="utf-8"))}
    r1sample = json.loads((R1E / "verification_sample.json").read_text(encoding="utf-8"))
    r1ids = set(r1sample.get("selected") or r1sample.get("ids") or r1sample.get("sample") or [])
    csample = json.loads((PKG / "C_l3_q1_s1_sample.json").read_text(encoding="utf-8"))
    cden = {d["id"]: d for d in csample["denials"]}

    def l3(part, path, src, expected_ids):
        rws, h = rows(path, "Verification sample")
        if "ai_assistance_disclosed" not in h:
            report["workbook_level"].append(f"{part}: no 'ai_assistance_disclosed' column{' (removed)' if part == 'C' else ' (not in the original R1 workbook)'}; AI assistance is not recorded")
        ids = [r["id"] for r in rws]
        if len(ids) != len(set(ids)):
            report["workbook_level"].append(f"{part}: duplicate ids")
        if expected_ids and set(ids) != set(expected_ids):
            report["workbook_level"].append(f"{part}: ids differ from the sampling record: missing {sorted(set(expected_ids) - set(ids))}, extra {sorted(set(ids) - set(expected_ids))}")
        for r in rws:
            d = src.get(r["id"])
            rec = {"id": r["id"], "issues": []}
            if not d:
                rec["issues"].append("id not in the generated denial list")
                report[part].append(rec)
                continue
            m = re.match(r"L3R?-(?:(Q1|S1)-r)?(\d+)-([A-Z]{2}\d{2})-(\w+?)-(\d+)$", r["id"])
            exp_, rep, scen, cfg, idx = m.groups()
            rec.update(experiment=exp_ or "R1", repetition=int(rep), scenario=scen, config=cfg, index=int(idx), log=d["log"])
            if (r["scenario"], r["config"]) != (scen, cfg) or str(r["repetition"]) != str(int(rep)):
                rec["issues"].append("id does not match the scenario/config/repetition columns")
            log = ROOT / d["log"]
            ev = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
            g = next((e for e in ev if e["event"] == "guard_decision" and e["index"] == int(idx) and not e["allowed"]), None)
            if not g:
                rec["issues"].append("no matching guard denial in the log")
            elif norm(g["reason"]) != norm(r["guard_reason"]):
                rec["issues"].append("guard reason differs from the log")
            if norm(r["provisional_category"]) != norm(d["provisional_category"]):
                rec["issues"].append("provisional_category column was changed")
            for col in ("call", "guard_reason", "user_request"):
                want = d[col] if isinstance(d[col], str) else (f"{d[col]['name']}({json.dumps(d[col]['arguments'], ensure_ascii=False)})" if col == "call" else str(d[col]))
                if col == "call" and part == "B":
                    continue  # B call column is formatted in the R1 workbook; identity checked via the log above
                if norm(r[col]) != norm(want):
                    rec["issues"].append(f"evidence column '{col}' differs from the generated record")
            prior = r.get("prior_calls")
            prior_empty = not prior or str(prior).strip() in ("", "[]", "(none)")
            sc = suite.get(scen)
            evtext = " ".join(str(r.get(c) or "") for c in ("user_request", "scope", "call", "guard_reason", "prior_calls", "later_calls", "run_outcome", "evidence"))
            evtext += " " + json.dumps(sc.initial_state) + " " + json.dumps(sc.scope.to_dict())
            end = next(e for e in ev if e["event"] == "run_end")
            evtext += " " + json.dumps(end["tool_calls"], ensure_ascii=False)
            for n in (1, 2):
                for i in claims(r[f"comment_{n}"], evtext, prior_empty):
                    rec["issues"].append(f"reviewer {n}: {i}")
            final = r["final_category"]
            rec["issues"] += reviewer_checks(r[f"reviewer_1"], r[f"reviewer_2"], r["category_1"], r["category_2"], final, r["resolution"], CATS)
            if r["category_1"] in CATS and r["category_2"] in CATS and r["category_1"] == r["category_2"] and r["category_1"] != r["provisional_category"]:
                rec["issues"].append("reviewers agree on a category different from the provisional one")
            rec["labels"] = {"r1": [r["reviewer_1"], r["category_1"]], "r2": [r["reviewer_2"], r["category_2"]], "final": final, "provisional": r["provisional_category"]}
            report[part].append(rec)

    l3("B", SNAP / "l3_denials_r1_review.xlsx", r1den, r1ids)
    l3("C", SNAP / "C_l3_q1_s1_review.xlsx", cden, csample["selected"])

    # reviewer pairing overview
    pairs = {}
    for part in ("A", "B", "C"):
        for rec in report[part]:
            lab = rec.get("labels")
            if lab:
                pr = tuple(sorted([norm(lab["r1"][0]), norm(lab["r2"][0])]))
                pairs.setdefault(part, {}).setdefault(" & ".join(pr), 0)
                pairs[part][" & ".join(pr)] += 1
    report["reviewer_pairs"] = pairs
    report["names_seen"] = sorted({str(rec["labels"][k][0]) for p in ("A", "B", "C") for rec in report[p] if rec.get("labels") for k in ("r1", "r2")})
    report["summary"] = {p: {"records": len(report[p]), "with_issues": sum(1 for r in report[p] if r["issues"])} for p in ("A", "B", "C")}
    OUT.mkdir(parents=True)
    (OUT / "validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "SHA256SUMS.txt").write_bytes(f"{sha(OUT / 'validation.json')}  validation.json\n".encode())
    print(json.dumps({"summary": report["summary"], "workbook_level": report["workbook_level"], "pairs": pairs, "names": report["names_seen"]}, indent=1, ensure_ascii=False))
    for p in ("A", "B", "C"):
        for r in report[p]:
            if r["issues"]:
                print(p, r.get("item") or r.get("id"), "->", r["issues"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
