from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import TeacherAssignment, Section
from models import Staff


class ServiceError(Exception):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail


async def list_teacher_assignments(db: AsyncSession, section_id: int | None = None) -> list[TeacherAssignment]:
    query = select(TeacherAssignment).options(
        selectinload(TeacherAssignment.teacher),
        selectinload(TeacherAssignment.section)
    )
    if section_id is not None:
        query = query.where(TeacherAssignment.section_id == section_id)
    query = query.order_by(TeacherAssignment.assignment_id.asc())

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_teacher_assignment(db: AsyncSession, assignment_id: int) -> TeacherAssignment | None:
    result = await db.execute(
        select(TeacherAssignment)
        .options(
            selectinload(TeacherAssignment.teacher),
            selectinload(TeacherAssignment.section)
        )
        .where(TeacherAssignment.assignment_id == assignment_id)
    )
    return result.scalar_one_or_none()


async def get_section(db: AsyncSession, section_id: int) -> Section | None:
    result = await db.execute(
        select(Section).where(Section.section_id == section_id)
    )
    return result.scalar_one_or_none()


async def create_teacher_assignment(db: AsyncSession, payload: dict) -> TeacherAssignment:
    teacher_id = payload["teacher_id"]
    section_id = payload["section_id"]
    
    # Verify teacher exists
    result = await db.execute(
        select(Staff).where(Staff.id == teacher_id)
    )
    if not result.scalar_one_or_none():
        raise ServiceError(404, {"teacher_id": ["Teacher not found."]})
    
    # Verify section exists
    section = await get_section(db, section_id)
    if not section:
        raise ServiceError(404, {"section_id": ["Section not found."]})

    # Check if assignment already exists
    existing = await db.execute(
        select(TeacherAssignment).where(
            (TeacherAssignment.teacher_id == teacher_id) &
            (TeacherAssignment.section_id == section_id)
        )
    )
    if existing.scalar_one_or_none():
        raise ServiceError(400, {"error": ["Teacher is already assigned to this section."]})

    assignment = TeacherAssignment(teacher_id=teacher_id, section_id=section_id)
    db.add(assignment)

    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        # Check if it's a foreign key error (teacher_id doesn't exist)
        if "teacher_id" in str(e) or "staff" in str(e).lower():
            raise ServiceError(404, {"teacher_id": ["Teacher not found."]})
        raise ServiceError(400, {"error": ["Error creating assignment."]})

    return await get_teacher_assignment(db, assignment.assignment_id)


async def delete_teacher_assignment(db: AsyncSession, assignment_id: int) -> bool:
    assignment = await get_teacher_assignment(db, assignment_id)
    if not assignment:
        raise ServiceError(404, {"error": "Assignment not found."})

    await db.delete(assignment)
    try:
        await db.commit()
        return True
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"error": "Error deleting assignment."})
