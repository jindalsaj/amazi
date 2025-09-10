from datetime import date, time
from typing import Literal
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    file_type: Literal["csv", "xlsx", "pdf", "image"]
    source_hint: str
    raw_text: str | None = None


class EmployeeRecord(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    wage: float | None = None
    min_hours: float | None = None
    max_hours: float | None = None
    evidence: Evidence | None = None
    confidence: float = 1.0


class ShiftRecord(BaseModel):
    employee_name: str | None = None
    role: str | None = None
    date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    unpaid_break_min: int | None = None
    status: str | None = None
    location: str | None = None
    evidence: Evidence | None = None
    confidence: float = 1.0


class ExtractionPreview(BaseModel):
    file_type: str
    employees: list[EmployeeRecord] = Field(default_factory=list)
    shifts: list[ShiftRecord] = Field(default_factory=list)
    needs_review_fields: list[str] = Field(default_factory=list)

class UploadPreviewResponse(BaseModel):
    upload_id: int
    preview: ExtractionPreview


class EmployeeInput(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    wage: float | None = None
    min_hours: float | None = None
    max_hours: float | None = None


class ShiftInput(BaseModel):
    employee_name: str
    role: str | None = None
    date: date
    start_time: time
    end_time: time
    unpaid_break_min: int | None = None
    status: str | None = None
    location: str | None = None


class ConfirmPayload(BaseModel):
    employees: list[EmployeeInput] = Field(default_factory=list)
    shifts: list[ShiftInput] = Field(default_factory=list)

