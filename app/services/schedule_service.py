from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Schedule


class ServiceError(Exception):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail


async def list_schedules(db: AsyncSession) -> list[Schedule]:
    result = await db.execute(select(Schedule).order_by(Schedule.schedule_id.asc()))
    return list(result.scalars().all())


async def get_schedule(db: AsyncSession, schedule_id: int) -> Schedule | None:
    result = await db.execute(
        select(Schedule).where(Schedule.schedule_id == schedule_id)
    )
    return result.scalar_one_or_none()


async def create_schedule(db: AsyncSession, payload: dict) -> Schedule:
    schedule = Schedule(**payload)
    db.add(schedule)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"error": ["Failed to create schedule."]})

    await db.refresh(schedule)
    return schedule


async def update_schedule(db: AsyncSession, schedule_id: int, changes: dict) -> Schedule:
    schedule = await get_schedule(db, schedule_id)
    if not schedule:
        raise ServiceError(404, {"error": "Schedule not found."})

    for key, value in changes.items():
        setattr(schedule, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"error": ["Failed to update schedule."]})

    await db.refresh(schedule)
    return schedule


async def delete_schedule(db: AsyncSession, schedule_id: int) -> None:
    schedule = await get_schedule(db, schedule_id)
    if not schedule:
        raise ServiceError(404, {"error": "Schedule not found."})

    await db.delete(schedule)
    await db.commit()
