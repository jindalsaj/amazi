from __future__ import annotations

from datetime import datetime, date, time
from pathlib import Path
from typing import Iterable
import pandas as pd
import pdfplumber
from dateutil import parser as dateparser

from app.schemas.extraction import ExtractionPreview, EmployeeRecord, ShiftRecord, Evidence
try:
    import pytesseract  # type: ignore
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None
    Image = None


def _infer_datetime(value: str) -> datetime | None:
    try:
        return dateparser.parse(value, fuzzy=True)
    except Exception:
        return None


def _infer_time(value: str) -> time | None:
    dt = _infer_datetime(value)
    return dt.time() if dt else None


def _infer_date(value: str) -> date | None:
    dt = _infer_datetime(value)
    return dt.date() if dt else None


def extract_from_csv_xlsx(path: str) -> ExtractionPreview:
    df = pd.read_excel(path) if Path(path).suffix.lower() in {".xlsx", ".xls"} else pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]

    employees: list[EmployeeRecord] = []
    shifts: list[ShiftRecord] = []

    name_col = next((c for c in df.columns if c in {"name", "employee", "employee name"}), None)
    role_col = next((c for c in df.columns if c in {"role", "position", "department"}), None)
    date_col = next((c for c in df.columns if c in {"date", "day"}), None)
    in_col = next((c for c in df.columns if "in" in c and "clock" in c or c in {"start", "start time", "shift start"}), None)
    out_col = next((c for c in df.columns if "out" in c and "clock" in c or c in {"end", "end time", "shift end"}), None)
    status_col = next((c for c in df.columns if c in {"status", "approved"}), None)
    location_col = next((c for c in df.columns if c in {"location", "site"}), None)

    seen_names: set[str] = set()
    for _, row in df.iterrows():
        name = str(row.get(name_col, "")).strip() if name_col else ""
        if name:
            if name not in seen_names:
                employees.append(
                    EmployeeRecord(
                        name=name,
                        role=str(row.get(role_col, "")).strip() or None if role_col else None,
                        evidence=Evidence(file_type="xlsx" if path.endswith("x") else "csv", source_hint=name_col or "", raw_text=name),
                        confidence=0.9,
                    )
                )
                seen_names.add(name)

        if date_col and (in_col or out_col):
            d = row.get(date_col)
            date_val = None
            if isinstance(d, (datetime, date)):
                date_val = d if isinstance(d, date) and not isinstance(d, datetime) else d.date()
            else:
                date_val = _infer_date(str(d))

            start_val = _infer_time(str(row.get(in_col))) if in_col else None
            end_val = _infer_time(str(row.get(out_col))) if out_col else None
            if date_val and (start_val or end_val):
                shifts.append(
                    ShiftRecord(
                        employee_name=name or None,
                        role=str(row.get(role_col, "")).strip() or None if role_col else None,
                        date=date_val,
                        start_time=start_val,
                        end_time=end_val,
                        status=str(row.get(status_col, "")).strip() or None if status_col else None,
                        location=str(row.get(location_col, "")).strip() or None if location_col else None,
                        evidence=Evidence(
                            file_type="xlsx" if path.endswith("x") else "csv",
                            source_hint=f"row={_}",
                            raw_text=" ".join(str(v) for v in row.to_dict().values())[:500],
                        ),
                        confidence=0.7,
                    )
                )

    needs_review = []
    for i, s in enumerate(shifts):
        if not (s.employee_name and s.date and s.start_time and s.end_time):
            needs_review.append(f"shift[{i}] missing core fields")

    return ExtractionPreview(
        file_type="xlsx" if path.endswith("x") else "csv",
        employees=employees,
        shifts=shifts,
        needs_review_fields=needs_review,
    )


def extract_from_pdf(path: str) -> ExtractionPreview:
    employees: list[EmployeeRecord] = []
    shifts: list[ShiftRecord] = []
    needs_review: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            # very light heuristic for names and times
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            for ln in lines:
                # detect times like 9:00 or 9a – 5p
                if any(tok in ln.lower() for tok in [":", "am", "pm", "–", "-"]):
                    dt = _infer_datetime(ln)
                    if dt:
                        # best-effort; mark review
                        shifts.append(
                            ShiftRecord(
                                evidence=Evidence(file_type="pdf", source_hint=f"page {page_num}", raw_text=ln),
                                confidence=0.3,
                            )
                        )
                        needs_review.append(f"pdf_line page {page_num}: '{ln[:40]}'")
                else:
                    if any(ch.isalpha() for ch in ln) and len(ln.split()) <= 3:
                        employees.append(
                            EmployeeRecord(
                                name=ln,
                                evidence=Evidence(file_type="pdf", source_hint=f"page {page_num}", raw_text=ln),
                                confidence=0.2,
                            )
                        )

    return ExtractionPreview(file_type="pdf", employees=employees, shifts=shifts, needs_review_fields=needs_review)


def extract_preview(path: str) -> ExtractionPreview:
    suffix = Path(path).suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return extract_from_csv_xlsx(path)
    if suffix in {".xlsx", ".xls"}:
        return extract_from_csv_xlsx(path)
    if suffix in {".pdf"}:
        return extract_from_pdf(path)
    # images: minimal OCR if available
    if pytesseract and Image:
        try:
            text = pytesseract.image_to_string(Image.open(path))
            preview = ExtractionPreview(file_type="image")
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            for ln in lines:
                if any(tok in ln.lower() for tok in [":", "am", "pm", "–", "-"]):
                    preview.needs_review_fields.append(f"image_line_time: {ln[:40]}")
                else:
                    if any(ch.isalpha() for ch in ln) and len(ln.split()) <= 3:
                        preview.employees.append(
                            EmployeeRecord(name=ln, evidence=Evidence(file_type="image", source_hint="ocr", raw_text=ln), confidence=0.2)
                        )
            if not preview.employees:
                preview.needs_review_fields.append("image_ocr_low_signal")
            return preview
        except Exception:
            pass
    return ExtractionPreview(file_type="image", employees=[], shifts=[], needs_review_fields=["image_ocr_not_available"]) 


