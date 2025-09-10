from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import Employee, Shift


router = APIRouter(tags=["data"])


@router.get("/employees")
async def list_employees(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Employee).where(Employee.org_id == 1).order_by(Employee.name))
    items = [
        {
            "id": e.id,
            "name": e.name,
            "role": e.role,
            "email": e.email,
            "phone": e.phone,
        }
        for e in res.scalars().all()
    ]
    return {"items": items}


@router.get("/shifts")
async def list_shifts(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Shift).where(Shift.org_id == 1).order_by(Shift.date))
    items = [
        {
            "id": s.id,
            "date": s.date.isoformat(),
            "start_time": s.start_time.isoformat(timespec="minutes"),
            "end_time": s.end_time.isoformat(timespec="minutes"),
            "employee_id": s.employee_id,
            "role": s.role,
            "status": s.status,
        }
        for s in res.scalars().all()
    ]
    return {"items": items}

