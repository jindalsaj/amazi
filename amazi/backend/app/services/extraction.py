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
    """Enhanced datetime parsing that handles many common formats."""
    if not value or not isinstance(value, str):
        return None
    
    value = str(value).strip()
    if not value or value.lower() in ['', 'nan', 'none', 'null']:
        return None
    
    # Try dateparser first (handles most cases)
    try:
        result = dateparser.parse(value, fuzzy=True)
        if result:
            return result
    except Exception:
        pass
    
    # Additional manual parsing for common formats
    import re
    
    # Common date patterns
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # MM/DD/YYYY, DD/MM/YYYY, etc.
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',    # YYYY/MM/DD
        r'(\d{1,2})\s+(\w{3,9})\s+(\d{2,4})',    # DD Month YYYY
        r'(\w{3,9})\s+(\d{1,2}),?\s+(\d{2,4})',  # Month DD, YYYY
    ]
    
    # Common time patterns
    time_patterns = [
        r'(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm)?',  # HH:MM:SS AM/PM
        r'(\d{1,2})\s*(am|pm)',                        # H AM/PM
        r'(\d{1,2})\.(\d{2})\s*(am|pm)?',             # H.MM AM/PM
    ]
    
    # Try to parse as date only
    for pattern in date_patterns:
        match = re.search(pattern, value, re.IGNORECASE)
        if match:
            try:
                if '/' in value or '-' in value:
                    parts = re.split(r'[/-]', value)
                    if len(parts) == 3:
                        # Try different interpretations
                        for fmt in ['%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%m/%d/%y', '%d/%m/%y']:
                            try:
                                return datetime.strptime(value, fmt)
                            except ValueError:
                                continue
                else:
                    # Try month name formats
                    for fmt in ['%d %B %Y', '%B %d, %Y', '%d %b %Y', '%b %d, %Y']:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
            except Exception:
                continue
    
    # Try to parse as time only
    for pattern in time_patterns:
        match = re.search(pattern, value, re.IGNORECASE)
        if match:
            try:
                # Extract time components
                time_str = match.group(0)
                if 'am' in time_str.lower() or 'pm' in time_str.lower():
                    for fmt in ['%I:%M %p', '%I %p', '%I.%M %p']:
                        try:
                            return datetime.strptime(time_str, fmt)
                        except ValueError:
                            continue
                else:
                    for fmt in ['%H:%M', '%H:%M:%S']:
                        try:
                            return datetime.strptime(time_str, fmt)
                        except ValueError:
                            continue
            except Exception:
                continue
    
    return None


def _infer_time(value: str) -> time | None:
    """Enhanced time parsing with decimal hour support."""
    if not value or not isinstance(value, str):
        return None
    
    value = str(value).strip()
    if not value or value.lower() in ['', 'nan', 'none', 'null']:
        return None
    
    # Handle decimal hour format (e.g., 9.000, 11.150, 17.100)
    if '.' in value and value.replace('.', '').isdigit():
        try:
            decimal_hours = float(value)
            if 0 <= decimal_hours <= 23.999:
                hours = int(decimal_hours)
                minutes = int((decimal_hours - hours) * 60)
                # Round to nearest minute to handle floating point precision
                if minutes >= 60:
                    hours += 1
                    minutes = 0
                if hours >= 24:
                    hours = 23
                    minutes = 59
                return time(hours, minutes)
        except (ValueError, OverflowError):
            pass
    
    # For 4-digit numbers that look like times (HHMM), try time parsing first
    if len(value) == 4 and value.isdigit():
        hours = int(value[:2])
        minutes = int(value[2:])
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            return time(hours, minutes)
    
    # For 3-digit numbers that look like times (HMM), try time parsing first
    if len(value) == 3 and value.isdigit():
        hours = int(value[0])
        minutes = int(value[1:])
        if 0 <= hours <= 9 and 0 <= minutes <= 59:
            return time(hours, minutes)
    
    # Try datetime parsing for other formats
    dt = _infer_datetime(value)
    if dt:
        return dt.time()
    
    # Manual time parsing
    import re
    
    # Common time patterns
    time_patterns = [
        r'(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm)?',  # HH:MM:SS AM/PM
        r'(\d{1,2})\s*(am|pm)',                        # H AM/PM
        r'(\d{1,2})\.(\d{2})\s*(am|pm)?',             # H.MM AM/PM
        r'(\d{2})(\d{2})\s*(am|pm)?',                 # HHMM AM/PM (4 digits)
        r'(\d{1,2})(\d{2})\s*(am|pm)?',               # HMM AM/PM (3 digits)
        r'(\d{2})(\d{2})(?::(\d{2}))?\s*(am|pm)?',    # HHMM:SS AM/PM
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, value, re.IGNORECASE)
        if match:
            try:
                time_str = match.group(0)
                if 'am' in time_str.lower() or 'pm' in time_str.lower():
                    for fmt in ['%I:%M %p', '%I %p', '%I.%M %p', '%I%M %p', '%I%M:%S %p']:
                        try:
                            return datetime.strptime(time_str, fmt).time()
                        except ValueError:
                            continue
                else:
                    # Handle HHMM format (4 digits)
                    if len(time_str) == 4 and time_str.isdigit():
                        try:
                            hours = int(time_str[:2])
                            minutes = int(time_str[2:])
                            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                                return time(hours, minutes)
                        except ValueError:
                            pass
                    # Handle HMM format (3 digits)
                    elif len(time_str) == 3 and time_str.isdigit():
                        try:
                            hours = int(time_str[0])
                            minutes = int(time_str[1:])
                            if 0 <= hours <= 9 and 0 <= minutes <= 59:
                                return time(hours, minutes)
                        except ValueError:
                            pass
                    # Standard formats
                    for fmt in ['%H:%M', '%H:%M:%S', '%H%M', '%H%M:%S']:
                        try:
                            return datetime.strptime(time_str, fmt).time()
                        except ValueError:
                            continue
            except Exception:
                continue
    
    return None


def _infer_date(value: str) -> date | None:
    """Enhanced date parsing with day-of-week support."""
    if not value or not isinstance(value, str):
        return None
    
    value = str(value).strip()
    if not value or value.lower() in ['', 'nan', 'none', 'null']:
        return None
    
    # Handle day-of-week format (e.g., "Monday", "Tuesday", etc.)
    day_names = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    if value.lower() in day_names:
        # For day-of-week, we'll need a reference date or current week
        # For now, return None as we need more context (like a week start date)
        # This will be handled in the extraction logic
        return None
    
    # Try datetime parsing first
    dt = _infer_datetime(value)
    if dt:
        return dt.date()
    
    # Manual date parsing
    import re
    
    # Common date patterns
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # MM/DD/YYYY, DD/MM/YYYY, etc.
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',    # YYYY/MM/DD
        r'(\d{1,2})\s+(\w{3,9})\s+(\d{2,4})',    # DD Month YYYY
        r'(\w{3,9})\s+(\d{1,2}),?\s+(\d{2,4})',  # Month DD, YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, value, re.IGNORECASE)
        if match:
            try:
                if '/' in value or '-' in value:
                    parts = re.split(r'[/-]', value)
                    if len(parts) == 3:
                        # Try different interpretations
                        for fmt in ['%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%m/%d/%y', '%d/%m/%y']:
                            try:
                                return datetime.strptime(value, fmt).date()
                            except ValueError:
                                continue
                else:
                    # Try month name formats
                    for fmt in ['%d %B %Y', '%B %d, %Y', '%d %b %Y', '%b %d, %Y']:
                        try:
                            return datetime.strptime(value, fmt).date()
                        except ValueError:
                            continue
            except Exception:
                continue
    
    return None


def extract_from_csv_xlsx(path: str) -> ExtractionPreview:
    df = pd.read_excel(path) if Path(path).suffix.lower() in {".xlsx", ".xls"} else pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]

    employees: list[EmployeeRecord] = []
    shifts: list[ShiftRecord] = []

    # Enhanced column detection for various timesheet formats
    name_col = next((c for c in df.columns if c in {"name", "employee", "employee name"}), None)
    role_col = next((c for c in df.columns if c in {"role", "position", "department"}), None)
    date_col = next((c for c in df.columns if c in {"date", "day"}), None)
    
    # Look for various time column patterns
    in_col = next((c for c in df.columns if any(term in c for term in ["in", "start", "clock in", "log in", "time in"])), None)
    out_col = next((c for c in df.columns if any(term in c for term in ["out", "end", "clock out", "log out", "time out"])), None)
    
    # Look for split shift columns (lunch breaks)
    lunch_start_col = next((c for c in df.columns if any(term in c for term in ["lunch start", "break start", "lunch begins"])), None)
    lunch_end_col = next((c for c in df.columns if any(term in c for term in ["lunch end", "break end", "lunch ends"])), None)
    
    # Look for multiple time in/out pairs (split shifts)
    time_in_cols = [c for c in df.columns if "time in" in c]
    time_out_cols = [c for c in df.columns if "time out" in c]
    
    status_col = next((c for c in df.columns if c in {"status", "approved"}), None)
    location_col = next((c for c in df.columns if c in {"location", "site"}), None)
    
    # Check if this is a per-person timesheet (single employee)
    is_per_person_sheet = len(df) > 0 and (not name_col or df[name_col].nunique() <= 1)

    seen_names: set[str] = set()
    week_start_date = None  # For day-of-week based dates
    
    for _, row in df.iterrows():
        name = str(row.get(name_col, "")).strip() if name_col else ""
        
        # For per-person sheets, try to extract name from other sources
        if not name and is_per_person_sheet:
            # Look for name in other columns or use a default
            name = "Employee"  # Default for per-person sheets
        
        if name and name not in seen_names:
            employees.append(
                EmployeeRecord(
                    name=name,
                    role=str(row.get(role_col, "")).strip() or None if role_col else None,
                    evidence=Evidence(file_type="xlsx" if path.endswith("x") else "csv", source_hint=name_col or "", raw_text=name),
                    confidence=0.9,
                )
            )
            seen_names.add(name)

        if date_col and (in_col or out_col or lunch_start_col or lunch_end_col or time_in_cols or time_out_cols):
            d = row.get(date_col)
            date_val = None
            
            # Handle date parsing
            from datetime import datetime as dt
            if isinstance(d, (dt, date)):
                date_val = d if isinstance(d, date) and not isinstance(d, dt) else d.date()
            else:
                date_str = str(d)
                date_val = _infer_date(date_str)
                
                # Handle day-of-week format
                if not date_val and date_str.lower() in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                    # For day-of-week, we need a reference week start date
                    # This is a simplified approach - in practice, you'd need more context
                    if not week_start_date:
                        # Use current week's Monday as reference
                        from datetime import datetime as dt, timedelta
                        today = dt.now().date()
                        week_start_date = today - timedelta(days=today.weekday())
                    
                    day_offset = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].index(date_str.lower())
                    date_val = week_start_date + timedelta(days=day_offset)

            # Handle multiple time in/out pairs (split shifts)
            if time_in_cols and time_out_cols:
                # Multiple time periods in one day - create separate shifts for each period
                for i, (time_in_col, time_out_col) in enumerate(zip(time_in_cols, time_out_cols)):
                    start_val = _infer_time(str(row.get(time_in_col)))
                    end_val = _infer_time(str(row.get(time_out_col)))
                    
                    if date_val and start_val and end_val:
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
                                    source_hint=f"row={_} (period {i+1})",
                                    raw_text=" ".join(str(v) for v in row.to_dict().values())[:500],
                                ),
                                confidence=0.7,
                            )
                        )
            
            # Handle split shifts with lunch breaks (traditional format)
            elif lunch_start_col and lunch_end_col:
                # This is a split shift format with lunch break
                start_val = _infer_time(str(row.get(in_col))) if in_col else None
                lunch_start_val = _infer_time(str(row.get(lunch_start_col)))
                lunch_end_val = _infer_time(str(row.get(lunch_end_col)))
                end_val = _infer_time(str(row.get(out_col))) if out_col else None
                
                if date_val and (start_val or end_val):
                    # Calculate total hours excluding lunch break
                    total_hours = None
                    if start_val and end_val and lunch_start_val and lunch_end_val:
                        # Calculate work time excluding lunch
                        from datetime import datetime as dt
                        morning_hours = (dt.combine(date_val, lunch_start_val) - dt.combine(date_val, start_val)).total_seconds() / 3600
                        afternoon_hours = (dt.combine(date_val, end_val) - dt.combine(date_val, lunch_end_val)).total_seconds() / 3600
                        total_hours = morning_hours + afternoon_hours
                    
                    shifts.append(
                        ShiftRecord(
                            employee_name=name or None,
                            role=str(row.get(role_col, "")).strip() or None if role_col else None,
                            date=date_val,
                            start_time=start_val,
                            end_time=end_val,
                            unpaid_break_min=int(total_hours * 60) if total_hours else None,
                            status=str(row.get(status_col, "")).strip() or None if status_col else None,
                            location=str(row.get(location_col, "")).strip() or None if location_col else None,
                            evidence=Evidence(
                                file_type="xlsx" if path.endswith("x") else "csv",
                                source_hint=f"row={_} (split shift)",
                                raw_text=" ".join(str(v) for v in row.to_dict().values())[:500],
                            ),
                            confidence=0.7,
                        )
                    )
            
            # Standard single shift
            else:
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


