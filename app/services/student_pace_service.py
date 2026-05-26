from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import EarlyWarning, Student, StudentEnrollment, StudentPace
from app.services.student_service import ServiceError


# ---------------------------------------------------------------------------
# Risk recalculation helpers
# Whenever pace_percent changes these keep EarlyWarning in sync automatically.
# ---------------------------------------------------------------------------

def _risk_from_pct(pct: float) -> str:
    """Derive risk level purely from pace percentage."""
    if pct < 60:
        return "critical"
    if pct < 75:
        return "high"
    if pct < 85:
        return "moderate"
    return "low"


def _status_from_risk(risk: str) -> str:
    return {
        "critical": "Critical",
        "high": "At Risk",
        "moderate": "Warning",
        "low": "On Track",
    }.get(risk, "On Track")


async def _sync_warning_for_pace(db: AsyncSession, pace: StudentPace) -> None:
    """
    After a StudentPace update, find any linked EarlyWarning for the same
    student + subject and recalculate risk_level, status, and pace_percent
    so they never go stale.
    """
    result = await db.execute(
        select(EarlyWarning).where(
            EarlyWarning.student_id == pace.student_id,
            EarlyWarning.subject == pace.subject,
        )
    )
    warnings = list(result.scalars().all())
    if not warnings:
        return

    new_pct = float(pace.pace_percent)
    new_risk = _risk_from_pct(new_pct)
    new_status = _status_from_risk(new_risk)

    for w in warnings:
        w.pace_percent = new_pct
        w.paces_behind = pace.paces_behind
        w.risk_level = new_risk
        w.status = new_status

    await db.commit()


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
    pace = await get_pace(db, pace_id)

    # Keep any linked EarlyWarning rows in sync with the new pace_percent
    await _sync_warning_for_pace(db, pace)

    return pace


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