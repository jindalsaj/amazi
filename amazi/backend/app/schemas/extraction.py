from datetime import date, time
from typing import Literal, Union, TYPE_CHECKING
from pydantic import BaseModel, Field, field_serializer

if TYPE_CHECKING:
    from datetime import date as DateType, time as TimeType
else:
    DateType = date
    TimeType = time


class Evidence(BaseModel):
    file_type: Literal["csv", "xlsx", "pdf", "image"]
    source_hint: str
    raw_text: Union[str, None] = None


class EmployeeRecord(BaseModel):
    name: str
    role: Union[str, None] = None
    email: Union[str, None] = None
    phone: Union[str, None] = None
    wage: Union[float, None] = None
    min_hours: Union[float, None] = None
    max_hours: Union[float, None] = None
    evidence: Union[Evidence, None] = None
    confidence: float = 1.0


class ShiftRecord(BaseModel):
    employee_name: Union[str, None] = None
    role: Union[str, None] = None
    date: Union[DateType, None] = None
    start_time: Union[TimeType, None] = None
    end_time: Union[TimeType, None] = None
    unpaid_break_min: Union[int, None] = None
    status: Union[str, None] = None
    location: Union[str, None] = None
    evidence: Union[Evidence, None] = None
    confidence: float = 1.0

    @field_serializer('date')
    def serialize_date(self, value: Union[DateType, None]) -> Union[str, None]:
        return value.isoformat() if value else None

    @field_serializer('start_time')
    def serialize_start_time(self, value: Union[TimeType, None]) -> Union[str, None]:
        return value.isoformat() if value else None

    @field_serializer('end_time')
    def serialize_end_time(self, value: Union[TimeType, None]) -> Union[str, None]:
        return value.isoformat() if value else None


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
    role: Union[str, None] = None
    email: Union[str, None] = None
    phone: Union[str, None] = None
    wage: Union[float, None] = None
    min_hours: Union[float, None] = None
    max_hours: Union[float, None] = None


class ShiftInput(BaseModel):
    employee_name: str
    role: Union[str, None] = None
    date: DateType
    start_time: TimeType
    end_time: TimeType
    unpaid_break_min: Union[int, None] = None
    status: Union[str, None] = None
    location: Union[str, None] = None

    @field_serializer('date')
    def serialize_date(self, value: DateType) -> str:
        return value.isoformat()

    @field_serializer('start_time')
    def serialize_start_time(self, value: TimeType) -> str:
        return value.isoformat()

    @field_serializer('end_time')
    def serialize_end_time(self, value: TimeType) -> str:
        return value.isoformat()


class ConfirmPayload(BaseModel):
    employees: list[EmployeeInput] = Field(default_factory=list)
    shifts: list[ShiftInput] = Field(default_factory=list)

