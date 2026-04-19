from datetime import date

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SchoolYear


class ServiceError(Exception):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail


def _ensure_date_order(start_date: date, end_date: date) -> None:
    if end_date <= start_date:
        raise ServiceError(400, {"end_date": "End date must be after start date."})


async def list_school_years(db: AsyncSession) -> list[SchoolYear]:
    result = await db.execute(select(SchoolYear).order_by(SchoolYear.school_year_id.desc()))
    return list(result.scalars().all())


async def get_current_school_year(db: AsyncSession) -> SchoolYear | None:
    result = await db.execute(select(SchoolYear).where(SchoolYear.is_current.is_(True)))
    return result.scalar_one_or_none()


async def get_school_year(db: AsyncSession, school_year_id: int) -> SchoolYear | None:
    result = await db.execute(
        select(SchoolYear).where(SchoolYear.school_year_id == school_year_id)
    )
    return result.scalar_one_or_none()


async def create_school_year(db: AsyncSession, payload: dict) -> SchoolYear:
    _ensure_date_order(payload["start_date"], payload["end_date"])

    if payload.get("is_current", False):
        await db.execute(
            update(SchoolYear).where(SchoolYear.is_current.is_(True)).values(is_current=False)
        )

    school_year = SchoolYear(**payload)
    db.add(school_year)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"year": ["school year with this year already exists."]})

    await db.refresh(school_year)
    return school_year


async def update_school_year(db: AsyncSession, school_year_id: int, changes: dict) -> SchoolYear:
    school_year = await get_school_year(db, school_year_id)
    if not school_year:
        raise ServiceError(404, {"error": "School year not found."})

    start_date = changes.get("start_date", school_year.start_date)
    end_date = changes.get("end_date", school_year.end_date)
    _ensure_date_order(start_date, end_date)

    if changes.get("is_current", False):
        await db.execute(
            update(SchoolYear)
            .where(SchoolYear.school_year_id != school_year_id)
            .values(is_current=False)
        )

    for key, value in changes.items():
        setattr(school_year, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"year": ["school year with this year already exists."]})

    await db.refresh(school_year)
    return school_year


async def delete_school_year(db: AsyncSession, school_year_id: int) -> None:
    school_year = await get_school_year(db, school_year_id)
    if not school_year:
        raise ServiceError(404, {"error": "School year not found."})

    if school_year.is_current:
        raise ServiceError(400, {"error": "Cannot delete the currently active school year."})

    await db.delete(school_year)
    await db.commit()
