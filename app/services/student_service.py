from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Student


class ServiceError(Exception):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_login_id(student_id: int) -> str:
    """Mirrors Django's S### pattern."""
    return f"S{student_id:03d}"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def list_students(db: AsyncSession) -> list[Student]:
    result = await db.execute(select(Student).order_by(Student.student_id.asc()))
    return list(result.scalars().all())


async def get_student(db: AsyncSession, student_id: int) -> Student | None:
    result = await db.execute(
        select(Student).where(Student.student_id == student_id)
    )
    return result.scalar_one_or_none()


async def create_student(db: AsyncSession, payload: dict) -> Student:
    """
    Creates a Student record and automatically assigns a login_id (S###).
    The login_id is set after the first commit so we have the PK.
    """
    student = Student(**payload)
    db.add(student)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"detail": "Unable to create student. Verify the data and try again."})

    # Assign login_id based on PK
    student.login_id = _generate_login_id(student.student_id)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"login_id": ["Generated login ID is already in use."]})

    await db.refresh(student)
    return student


async def update_student(db: AsyncSession, student_id: int, changes: dict) -> Student:
    student = await get_student(db, student_id)
    if not student:
        raise ServiceError(404, {"error": "Student not found."})

    for key, value in changes.items():
        setattr(student, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"detail": "Update failed due to a data conflict."})

    await db.refresh(student)
    return student


async def delete_student(db: AsyncSession, student_id: int) -> None:
    student = await get_student(db, student_id)
    if not student:
        raise ServiceError(404, {"error": "Student not found."})

    await db.delete(student)
    await db.commit()