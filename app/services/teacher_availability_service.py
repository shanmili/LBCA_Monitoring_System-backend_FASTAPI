from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TeacherAvailability


class ServiceError(Exception):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail


async def list_teacher_availabilities(db: AsyncSession) -> list[TeacherAvailability]:
    result = await db.execute(select(TeacherAvailability).order_by(TeacherAvailability.availability_id.asc()))
    return list(result.scalars().all())


async def get_teacher_availability(db: AsyncSession, availability_id: int) -> TeacherAvailability | None:
    result = await db.execute(
        select(TeacherAvailability).where(TeacherAvailability.availability_id == availability_id)
    )
    return result.scalar_one_or_none()


async def create_teacher_availability(db: AsyncSession, payload: dict) -> TeacherAvailability:
    availability = TeacherAvailability(**payload)
    db.add(availability)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"error": ["Failed to create teacher availability."]})

    await db.refresh(availability)
    return availability


async def update_teacher_availability(db: AsyncSession, availability_id: int, changes: dict) -> TeacherAvailability:
    availability = await get_teacher_availability(db, availability_id)
    if not availability:
        raise ServiceError(404, {"error": "Teacher availability not found."})

    for key, value in changes.items():
        setattr(availability, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"error": ["Failed to update teacher availability."]})

    await db.refresh(availability)
    return availability


async def delete_teacher_availability(db: AsyncSession, availability_id: int) -> None:
    availability = await get_teacher_availability(db, availability_id)
    if not availability:
        raise ServiceError(404, {"error": "Teacher availability not found."})

    await db.delete(availability)
    await db.commit()
