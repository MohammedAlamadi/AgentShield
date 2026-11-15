"""Convert the CSV review sheets to Excel workbooks for the team's label review, and verify them.

    .venv\\Scripts\\python scripts\\dataset\\make_review_xlsx.py

Reads (never modifies):  data/eval/review/detector_label_review.csv, data/eval/review/scenario_review.csv
Writes:                  data/eval/review/detector_label_review.xlsx, data/eval/review/scenario_review.xlsx

Every cell is stored as an explicit TEXT cell (never number/date/formula), so values such as
"=...", "-...", IDs and dates cannot be reinterpreted by Excel. After writing, each workbook is
re-opened and compared cell-by-cell with its CSV; the script exits non-zero on any difference.
"""

from __future__ import annotations

import csv
import hashlib
import math
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "data" / "eval" / "review"

# column widths (Excel character units); anything not listed gets DEFAULT_WIDTH
WIDTHS = {
    "id": 8, "category": 26, "proposed_label": 12, "text": 70, "explanation": 45, "author": 22,
    "is_attack": 9, "attack_style": 18, "user_request": 45, "trusted_scope": 30, "attacker_text": 55,
    "attacker_objective": 35, "expected_legitimate_outcome": 35, "security_success_condition": 35,
    "legit_check": 40, "attack_check": 35,
    "second_reviewer_name": 20, "agrees_with_label (Y/N)": 14, "realistic_and_correct (Y/N)": 14, "comment": 40,
}
DEFAULT_WIDTH = 20
REVIEWER_COLS = {"second_reviewer_name", "agrees_with_label (Y/N)", "realistic_and_correct (Y/N)", "comment"}
DECISION_COLS = {"agrees_with_label (Y/N)", "realistic_and_correct (Y/N)"}

HEADER_FILL = PatternFill("solid", start_color="D9D9D9")
REVIEWER_FILL = PatternFill("solid", start_color="FFF2CC")  # light yellow: columns for reviewers to fill
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def read_csv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [row for row in csv.reader(fh)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def estimated_lines(value: str, width: float) -> int:
    chars_per_line = max(1, int(width * 1.1))
    return sum(max(1, math.ceil(len(part) / chars_per_line)) for part in value.split("\n"))


def build(csv_path: Path, xlsx_path: Path, sheet_title: str, item_word: str, instructions: list[str]) -> None:
    rows = read_csv(csv_path)
    header, data = rows[0], rows[1:]

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title

    for r_idx, row in enumerate([header] + data, start=1):
        if len(row) != len(header):
            raise ValueError(f"{csv_path.name}: row {r_idx} has {len(row)} fields, header has {len(header)}")
        for c_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.value = value
            cell.data_type = "s"  # force text: no formulas, numbers or dates
            cell.number_format = "@"
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = BORDER
            col = header[c_idx - 1]
            if r_idx == 1:
                cell.font = Font(bold=True)
                cell.fill = HEADER_FILL
            elif col in REVIEWER_COLS:
                cell.fill = REVIEWER_FILL

    for c_idx, col in enumerate(header, start=1):
        ws.column_dimensions[get_column_letter(c_idx)].width = WIDTHS.get(col, DEFAULT_WIDTH)
    # row heights estimated from wrapped content (openpyxl cannot auto-fit)
    ws.row_dimensions[1].height = 32
    for r_idx, row in enumerate(data, start=2):
        lines = max(estimated_lines(v, WIDTHS.get(header[i], DEFAULT_WIDTH)) for i, v in enumerate(row))
        ws.row_dimensions[r_idx].height = min(409, max(18, 15 * lines))

    last_col = get_column_letter(len(header))
    last_row = len(data) + 1
    ws.freeze_panes = "B2"  # header row and id column stay visible
    ws.auto_filter.ref = f"A1:{last_col}{last_row}"

    for col in DECISION_COLS & set(header):
        letter = get_column_letter(header.index(col) + 1)
        dv = DataValidation(type="list", formula1='"Y,N"', allow_blank=True, showDropDown=False,
                            errorTitle="Y or N", error="Please choose Y (agree) or N (disagree).",
                            promptTitle="Reviewer decision", prompt="Choose Y or N; explain any N in the comment column.")
        dv.showErrorMessage = True
        dv.showInputMessage = True
        ws.add_data_validation(dv)
        dv.add(f"{letter}2:{letter}{last_row}")

    info = wb.create_sheet("Instructions")
    info.column_dimensions["A"].width = 110
    lines = [f"AgentShield D2 - {sheet_title}", "",
             f"Source: {csv_path.relative_to(ROOT).as_posix()} (sha256 {sha256(csv_path)})",
             f"Rows: {len(data)} {item_word}. Status: DRAFT v1 - not frozen.", ""] + instructions + [
             "", "Yellow columns are for reviewers. Do not edit the grey/white data columns here;",
             "report any requested change in the comment column so it can be applied to the source and re-audited."]
    for i, text in enumerate(lines, start=1):
        c = info.cell(row=i, column=1, value=text)
        c.data_type = "s"
        c.alignment = Alignment(wrap_text=True)
        if i == 1:
            c.font = Font(bold=True, size=13)
    wb.active = 0
    wb.save(xlsx_path)


def verify(csv_path: Path, xlsx_path: Path, sheet_title: str, expected_items: int, decision_col: str) -> list[str]:
    problems = []
    rows = read_csv(csv_path)
    wb = load_workbook(xlsx_path)  # values as stored (no formula evaluation needed: all text)
    ws = wb[sheet_title]
    got = [[("" if c.value is None else c.value) for c in r] for r in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column)]
    if ws.max_column != len(rows[0]):
        problems.append(f"column count {ws.max_column} != {len(rows[0])}")
    if len(got) != len(rows):
        problems.append(f"row count {len(got)} != CSV {len(rows)}")
    for i, (a, b) in enumerate(zip(rows, got), start=1):
        if a != b:
            diff = [rows[0][j] for j in range(len(a)) if j >= len(b) or a[j] != b[j]]
            problems.append(f"row {i} differs in {diff}")
    n_items = len(got) - 1
    if n_items != expected_items:
        problems.append(f"{n_items} data rows, expected {expected_items}")
    ids = [r[0] for r in got[1:]]
    if len(set(ids)) != len(ids):
        problems.append("duplicate ids")
    non_text = [c.coordinate for r in ws.iter_rows() for c in r if c.value is not None and c.data_type != "s"]
    if non_text:
        problems.append(f"non-text cells: {non_text[:5]}")
    if ws.freeze_panes != "B2" or not ws.auto_filter.ref:
        problems.append("freeze panes / filter missing")
    letter = get_column_letter(rows[0].index(decision_col) + 1)
    if not any(f"{letter}2:{letter}{len(rows)}" in str(dv.sqref) and dv.formula1 == '"Y,N"' for dv in ws.data_validations.dataValidation):
        problems.append("Y/N dropdown missing")
    return problems


def main() -> int:
    jobs = [
        ("detector_label_review", "Detector labels", "examples", 120, "agrees_with_label (Y/N)", [
            "Task (D1): every label must be checked by a second team member.",
            "For each row: read the text, decide whether the proposed label (benign / malicious) is correct,",
            "enter your name, choose Y or N from the dropdown, and explain any N in the comment column.",
            "Malicious = an instruction aimed at an AI assistant that tries to make it act against its user.",
            "Open questions for the team: BC02, BC08 and BC15 are labelled benign (see docs/D2_dataset_review_notes.md, Q3).",
        ]),
        ("scenario_review", "Scenarios", "scenarios", 40, "realistic_and_correct (Y/N)", [
            "Task: a second team member checks each scenario before the suite is frozen.",
            "Check that the request is realistic, the trusted scope is what a genuine user would choose,",
            "the attacker text and objective match the category, and the checks measure the stated outcomes.",
            "Do NOT judge scenarios by how a particular model might behave; scenarios are not tuned to models.",
            "Open questions: Q1 (AM02), Q2 (AM03), Q4, Q5 in docs/D2_dataset_review_notes.md.",
        ]),
    ]
    all_ok = True
    for stem, title, word, n, decision, instr in jobs:
        csv_path, xlsx_path = REVIEW / f"{stem}.csv", REVIEW / f"{stem}.xlsx"
        if xlsx_path.exists() and "--force" not in sys.argv:
            # The completed human-review workbooks are evidence (copies + sha256 in docs/evidence/dataset_review/).
            print(f"REFUSED: {xlsx_path.relative_to(ROOT).as_posix()} exists (completed review evidence). Use --force only for a NEW blank review round.")
            all_ok = False
            continue
        before = sha256(csv_path)
        build(csv_path, xlsx_path, title, word, instr)
        problems = verify(csv_path, xlsx_path, title, n, decision)
        after = sha256(csv_path)
        if before != after:
            problems.append("CSV CHANGED during conversion")
        all_ok &= not problems
        print(f"{xlsx_path.relative_to(ROOT).as_posix()}: {n if not problems else '?'} {word}; csv sha256 unchanged={before == after}; "
              f"{'VERIFIED: cell-for-cell identical to CSV' if not problems else problems}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
