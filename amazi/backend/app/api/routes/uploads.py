from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from pathlib import Path

from app.core.config import get_settings
from app.db.database import get_db
from app.models.models import TimesheetUpload, ExtractionRun, Employee, Shift
from app.schemas.extraction import (
    ExtractionPreview,
    UploadPreviewResponse,
    ConfirmPayload,
)
from app.services.storage import save_upload_locally
from app.services.extraction import extract_preview


router = APIRouter(tags=["uploads"])


@router.post("/uploads/timesheet", response_model=UploadPreviewResponse)
async def upload_timesheet(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if not ext or ext not in settings.allowed_file_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    size = 0
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb}MB limit")

    saved_path = save_upload_locally(file)

    preview = extract_preview(saved_path)

    result = await db.execute(
        insert(TimesheetUpload).values(
            org_id=1,  # TODO: wire to auth/org later
            file_url=saved_path,
            file_type=ext,
            status="uploaded",
        ).returning(TimesheetUpload.id)
    )
    upload_id = result.scalar_one()
    await db.execute(
        insert(ExtractionRun).values(
            upload_id=upload_id,
            result_json=preview.model_dump(),
            confidence_summary={
                "employees": len(preview.employees),
                "shifts": len(preview.shifts),
            },
            needs_review=bool(preview.needs_review_fields),
        )
    )
    await db.commit()
    return UploadPreviewResponse(upload_id=upload_id, preview=preview)


@router.post("/uploads/{upload_id}/confirm")
async def confirm_extraction(upload_id: int, payload: ConfirmPayload, db: AsyncSession = Depends(get_db)) -> dict:
    org_id = 1  # TODO: replace with auth/org

    # Load existing employees by name
    names = [e.name.strip() for e in payload.employees if e.name.strip()]
    existing = {}
    if names:
        res = await db.execute(select(Employee).where(Employee.org_id == org_id, Employee.name.in_(names)))
        for emp in res.scalars().all():
            existing[emp.name] = emp.id

    # Insert missing employees
    inserted = 0
    for e in payload.employees:
        if e.name.strip() and e.name.strip() not in existing:
            result = await db.execute(
                insert(Employee)
                .values(
                    org_id=org_id,
                    name=e.name.strip(),
                    role=e.role,
                    email=e.email,
                    phone=e.phone,
                    wage=e.wage,
                    min_hours=e.min_hours,
                    max_hours=e.max_hours,
                )
                .returning(Employee.id)
            )
            existing[e.name.strip()] = result.scalar_one()
            inserted += 1

    # Insert shifts
    shifts_inserted = 0
    for s in payload.shifts:
        emp_id = existing.get(s.employee_name.strip()) if s.employee_name else None
        await db.execute(
            insert(Shift).values(
                org_id=org_id,
                employee_id=emp_id,
                role=s.role,
                date=s.date,
                start_time=s.start_time,
                end_time=s.end_time,
                unpaid_break_min=s.unpaid_break_min,
                status=s.status,
            )
        )
        shifts_inserted += 1

    await db.commit()
    return {"status": "ok", "upload_id": upload_id, "employees_created": inserted, "shifts_created": shifts_inserted}

