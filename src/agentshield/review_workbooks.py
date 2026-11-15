"""Excel workbooks for the blinded reviews, and import of the filled workbooks back into the review CSVs.

The exported CSV sheets (adjudication.export_blind) remain the authoritative merge input; the workbooks are
a reviewer-friendly view of exactly the same items and order, plus two columns that are identical across all
configurations and so do not break blinding:
  * source_content   - the scenario's synthetic emails/documents (what the assistant could read), and
  * task_requirement - the approved expected legitimate outcome (legitimate items only).
The configuration, model, run id, automatic verdict and verifier details are never written to a workbook.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .adjudication import _read_csv

FILL_COLS = ("reviewer_name", "label", "rationale", "paraphrase_note")
YELLOW = PatternFill("solid", start_color="FFF2CC")
GREY = PatternFill("solid", start_color="D9D9D9")
WIDTHS = {"item_id": 15, "question": 34, "user_request": 34, "attacker_objective": 30, "task_requirement": 34,
          "source_content": 60, "text": 60, "reviewer_name": 16, "label": 10, "rationale": 36, "paraphrase_note": 26}


def source_content(scenario) -> str:
    st = scenario.initial_state
    parts = [f"EMAIL {e['id']} from {e['from']}\nSubject: {e['subject']}\n{e['body']}" for e in st.get("inbox", [])]
    parts += [f"DOCUMENT {d['name']}\n{d['content']}" for d in st.get("files", [])]
    return "\n\n".join(parts) or "(no emails or documents)"


def build_workbooks(review_dir: str | Path, prefix: str, suite, *, labels: tuple[str, ...], instructions: list[str]) -> list[Path]:
    rdir = Path(review_dir)
    out_dir = rdir / "review_workbooks"
    targets = [out_dir / f"{prefix}_reviewer_{n}.xlsx" for n in (1, 2)]
    if any(p.exists() for p in targets):
        raise FileExistsError(f"workbooks already exist in {out_dir}; they may contain reviewer decisions")
    sheet = _read_csv(rdir / f"{prefix}_reviewer_1.csv")
    key = {r["item_id"]: r for r in _read_csv(rdir / f"{prefix}_key.csv")}
    if any(r[c] for r in sheet for c in FILL_COLS if c in r):
        raise ValueError("the blind CSV already contains reviewer input")
    cols = ["item_id", "question", "user_request", "attacker_objective", "task_requirement", "source_content", "text", *FILL_COLS]
    out_dir.mkdir(parents=True, exist_ok=True)
    for n, path in enumerate(targets, start=1):
        wb = Workbook()
        ws = wb.active
        ws.title = "Items"
        ws.append(cols)
        for r in sheet:
            sc = suite.get(key[r["item_id"]]["scenario_id"])  # used only to look up config-independent content
            req = (sc.expected_legitimate_outcome or "") if key[r["item_id"]]["check"] == "legitimate" else ""
            ws.append([r["item_id"], r["question"], r["user_request"], r["attacker_objective"], req, source_content(sc), r["text"], "", "", "", ""])
        for c_idx, col in enumerate(cols, start=1):
            ws.column_dimensions[get_column_letter(c_idx)].width = WIDTHS[col]
            for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=c_idx, max_col=c_idx):
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
                    if cell.value is not None:
                        cell.data_type = "s"
                        cell.number_format = "@"
                    if cell.row == 1:
                        cell.font, cell.fill = Font(bold=True), GREY
                    elif col in FILL_COLS:
                        cell.fill = YELLOW
        for r_idx in range(2, ws.max_row + 1):
            ws.row_dimensions[r_idx].height = 220
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{ws.max_row}"
        dv = DataValidation(type="list", formula1='"' + ",".join(labels) + '"', allow_blank=True)
        dv.error, dv.showErrorMessage = f"Choose one of {', '.join(labels)}", True
        ws.add_data_validation(dv)
        letter = get_column_letter(cols.index("label") + 1)
        dv.add(f"{letter}2:{letter}{ws.max_row}")
        info = wb.create_sheet("Instructions")
        info.column_dimensions["A"].width = 120
        for i, line in enumerate([f"Reviewer {n} workbook - fill ONLY the yellow columns; work independently; do not look at the other workbook.", ""] + instructions, start=1):
            c = info.cell(row=i, column=1, value=line)
            c.alignment = Alignment(wrap_text=True)
            if i == 1:
                c.font = Font(bold=True)
        wb.active = 0
        wb.save(path)
    return targets


def _norm_label(v: Any, labels: tuple[str, ...]) -> str:
    if isinstance(v, bool):  # Excel may turn "True"/"False" into booleans
        v = "True" if v else "False"
    s = "" if v is None else str(v).strip()
    for lab in labels:
        if s.lower() == lab.lower():
            return lab
    return s


def import_workbook(xlsx: str | Path, csv_path: str | Path, labels: tuple[str, ...]) -> int:
    """Copy reviewer_name/label/rationale/paraphrase_note from a filled workbook into the blind CSV.
    Refuses if the CSV already holds reviewer input or the item ids/order differ. Returns rows imported."""
    rows = _read_csv(Path(csv_path))
    if any(r[c] for r in rows for c in FILL_COLS):
        raise ValueError(f"{Path(csv_path).name} already contains reviewer input; not overwritten")
    ws = load_workbook(xlsx, data_only=True)["Items"]
    data = list(ws.iter_rows(values_only=True))
    head = list(data[0])
    got = [dict(zip(head, r)) for r in data[1:] if any(v not in (None, "") for v in r)]
    if [g["item_id"] for g in got] != [r["item_id"] for r in rows]:
        raise ValueError("workbook item ids/order differ from the exported CSV")
    for r, g in zip(rows, got):
        r["reviewer_name"] = str(g.get("reviewer_name") or "").strip()
        r["label"] = _norm_label(g.get("label"), labels)
        r["rationale"] = str(g.get("rationale") or "").strip()
        r["paraphrase_note"] = str(g.get("paraphrase_note") or "").strip()
        if "rule" in r and g.get("rule"):
            r["rule"] = str(g["rule"]).strip()
    with Path(csv_path).open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return len(rows)
