from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Subject


class ServiceError(Exception):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail


async def list_subjects(db: AsyncSession) -> list[Subject]:
    result = await db.execute(select(Subject).order_by(Subject.subject_id.asc()))
    return list(result.scalars().all())


async def get_subject(db: AsyncSession, subject_id: int) -> Subject | None:
    result = await db.execute(
        select(Subject).where(Subject.subject_id == subject_id)
    )
    return result.scalar_one_or_none()


async def create_subject(db: AsyncSession, payload: dict) -> Subject:
    subject = Subject(**payload)
    db.add(subject)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"subject_code": ["subject with this code already exists."]})

    await db.refresh(subject)
    return subject


async def update_subject(db: AsyncSession, subject_id: int, changes: dict) -> Subject:
    subject = await get_subject(db, subject_id)
    if not subject:
        raise ServiceError(404, {"error": "Subject not found."})

    for key, value in changes.items():
        setattr(subject, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"subject_code": ["subject with this code already exists."]})

    await db.refresh(subject)
    return subject


async def delete_subject(db: AsyncSession, subject_id: int) -> None:
    subject = await get_subject(db, subject_id)
    if not subject:
        raise ServiceError(404, {"error": "Subject not found."})

    await db.delete(subject)
    await db.commit()
