from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DataQualityLog


class ServiceError(Exception):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail


async def list_data_quality_logs(db: AsyncSession) -> list[DataQualityLog]:
    result = await db.execute(select(DataQualityLog).order_by(DataQualityLog.log_id.asc()))
    return list(result.scalars().all())


async def get_data_quality_log(db: AsyncSession, log_id: int) -> DataQualityLog | None:
    result = await db.execute(
        select(DataQualityLog).where(DataQualityLog.log_id == log_id)
    )
    return result.scalar_one_or_none()


async def create_data_quality_log(db: AsyncSession, payload: dict) -> DataQualityLog:
    log = DataQualityLog(**payload)
    db.add(log)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"error": ["Failed to create data quality log."]})

    await db.refresh(log)
    return log


async def update_data_quality_log(db: AsyncSession, log_id: int, changes: dict) -> DataQualityLog:
    log = await get_data_quality_log(db, log_id)
    if not log:
        raise ServiceError(404, {"error": "Data quality log not found."})

    for key, value in changes.items():
        setattr(log, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"error": ["Failed to update data quality log."]})

    await db.refresh(log)
    return log


async def delete_data_quality_log(db: AsyncSession, log_id: int) -> None:
    log = await get_data_quality_log(db, log_id)
    if not log:
        raise ServiceError(404, {"error": "Data quality log not found."})

    await db.delete(log)
    await db.commit()
