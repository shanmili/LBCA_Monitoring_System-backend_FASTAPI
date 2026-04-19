from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import EarlyWarning, Student, StudentEnrollment, StudentPace
from app.services.student_service import ServiceError


# ---------------------------------------------------------------------------
# StudentPace
# ---------------------------------------------------------------------------

async def list_paces(
    db: AsyncSession,
    student_id: int | None = None,
    enrollment_id: int | None = None,
) -> list[StudentPace]:
    query = (
        select(StudentPace)
        .options(selectinload(StudentPace.student))
        .order_by(StudentPace.updated_at.desc())
    )
    if student_id is not None:
        query = query.where(StudentPace.student_id == student_id)
    if enrollment_id is not None:
        query = query.where(StudentPace.enrollment_id == enrollment_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_pace(db: AsyncSession, pace_id: int) -> StudentPace | None:
    result = await db.execute(
        select(StudentPace)
        .options(selectinload(StudentPace.student))
        .where(StudentPace.pace_id == pace_id)
    )
    return result.scalar_one_or_none()


async def create_pace(db: AsyncSession, payload: dict) -> StudentPace:
    if not (await db.get(Student, payload["student_id"])):
        raise ServiceError(404, {"student_id": ["Student does not exist."]})
    if not (await db.get(StudentEnrollment, payload["enrollment_id"])):
        raise ServiceError(404, {"enrollment_id": ["Enrollment does not exist."]})

    pace = StudentPace(**payload)
    db.add(pace)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"detail": "Could not create pace record."})

    await db.refresh(pace)
    return await get_pace(db, pace.pace_id)


async def update_pace(db: AsyncSession, pace_id: int, changes: dict) -> StudentPace:
    pace = await get_pace(db, pace_id)
    if not pace:
        raise ServiceError(404, {"error": "Pace record not found."})

    for key, value in changes.items():
        setattr(pace, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"detail": "Update failed."})

    await db.refresh(pace)
    return await get_pace(db, pace_id)


async def delete_pace(db: AsyncSession, pace_id: int) -> None:
    pace = await get_pace(db, pace_id)
    if not pace:
        raise ServiceError(404, {"error": "Pace record not found."})

    await db.delete(pace)
    await db.commit()


# ---------------------------------------------------------------------------
# EarlyWarning
# ---------------------------------------------------------------------------

async def list_warnings(
    db: AsyncSession,
    student_id: int | None = None,
    enrollment_id: int | None = None,
    risk_level: str | None = None,
) -> list[EarlyWarning]:
    query = (
        select(EarlyWarning)
        .options(selectinload(EarlyWarning.student))
        .order_by(EarlyWarning.created_at.desc())
    )
    if student_id is not None:
        query = query.where(EarlyWarning.student_id == student_id)
    if enrollment_id is not None:
        query = query.where(EarlyWarning.enrollment_id == enrollment_id)
    if risk_level is not None:
        query = query.where(EarlyWarning.risk_level == risk_level)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_warning(db: AsyncSession, warning_id: int) -> EarlyWarning | None:
    result = await db.execute(
        select(EarlyWarning)
        .options(selectinload(EarlyWarning.student))
        .where(EarlyWarning.warning_id == warning_id)
    )
    return result.scalar_one_or_none()


async def create_warning(db: AsyncSession, payload: dict) -> EarlyWarning:
    if not (await db.get(Student, payload["student_id"])):
        raise ServiceError(404, {"student_id": ["Student does not exist."]})

    warning = EarlyWarning(**payload)
    db.add(warning)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"detail": "Could not create early warning."})

    await db.refresh(warning)
    return await get_warning(db, warning.warning_id)


async def update_warning(db: AsyncSession, warning_id: int, changes: dict) -> EarlyWarning:
    warning = await get_warning(db, warning_id)
    if not warning:
        raise ServiceError(404, {"error": "Early warning not found."})

    for key, value in changes.items():
        setattr(warning, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"detail": "Update failed."})

    await db.refresh(warning)
    return await get_warning(db, warning_id)


async def delete_warning(db: AsyncSession, warning_id: int) -> None:
    warning = await get_warning(db, warning_id)
    if not warning:
        raise ServiceError(404, {"error": "Early warning not found."})

    await db.delete(warning)
    await db.commit()