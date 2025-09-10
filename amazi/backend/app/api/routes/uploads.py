from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from pathlib import Path

from app.core.config import get_settings
from app.db.database import get_db
from app.models.models import TimesheetUpload, ExtractionRun
from app.schemas.extraction import ExtractionPreview, UploadPreviewResponse
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
async def confirm_extraction(upload_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    # Placeholder until mapping UI posts normalized data
    return {"status": "ok", "upload_id": upload_id}

