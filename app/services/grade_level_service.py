from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GradeLevel


class ServiceError(Exception):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail


async def list_grade_levels(db: AsyncSession) -> list[GradeLevel]:
    result = await db.execute(select(GradeLevel).order_by(GradeLevel.grade_level_id.asc()))
    return list(result.scalars().all())


async def get_grade_level(db: AsyncSession, grade_level_id: int) -> GradeLevel | None:
    result = await db.execute(
        select(GradeLevel).where(GradeLevel.grade_level_id == grade_level_id)
    )
    return result.scalar_one_or_none()


async def create_grade_level(db: AsyncSession, payload: dict) -> GradeLevel:
    grade_level = GradeLevel(**payload)
    db.add(grade_level)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"level": ["grade level with this level already exists."]})

    await db.refresh(grade_level)
    return grade_level


async def update_grade_level(db: AsyncSession, grade_level_id: int, changes: dict) -> GradeLevel:
    grade_level = await get_grade_level(db, grade_level_id)
    if not grade_level:
        raise ServiceError(404, {"error": "Grade level not found."})

    for key, value in changes.items():
        setattr(grade_level, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"level": ["grade level with this level already exists."]})

    await db.refresh(grade_level)
    return grade_level


async def delete_grade_level(db: AsyncSession, grade_level_id: int) -> None:
    grade_level = await get_grade_level(db, grade_level_id)
    if not grade_level:
        raise ServiceError(404, {"error": "Grade level not found."})

    await db.delete(grade_level)
    await db.commit()
