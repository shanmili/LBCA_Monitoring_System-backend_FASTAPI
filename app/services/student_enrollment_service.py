from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import GradeLevel, Section, SchoolYear, Student, StudentEnrollment
from app.services.student_service import ServiceError, create_student


async def _verify_fks(
    db: AsyncSession,
    grade_level_id: int,
    section_id: int,
    school_year_id: int,
) -> None:
    if not (await db.get(GradeLevel, grade_level_id)):
        raise ServiceError(400, {"grade_level_id": ["Grade level does not exist."]})
    if not (await db.get(Section, section_id)):
        raise ServiceError(400, {"section_id": ["Section does not exist."]})
    if not (await db.get(SchoolYear, school_year_id)):
        raise ServiceError(400, {"school_year_id": ["School year does not exist."]})


async def list_enrollments(
    db: AsyncSession,
    student_id: int | None = None,
    school_year_id: int | None = None,
    section_id: int | None = None,
    grade_level_id: int | None = None,
) -> list[StudentEnrollment]:
    query = (
        select(StudentEnrollment)
        .options(
            selectinload(StudentEnrollment.student),
            selectinload(StudentEnrollment.grade_level),
            selectinload(StudentEnrollment.section),
            selectinload(StudentEnrollment.school_year),
        )
        .order_by(StudentEnrollment.enrollment_id.asc())
    )
    if student_id is not None:
        query = query.where(StudentEnrollment.student_id == student_id)
    if school_year_id is not None:
        query = query.where(StudentEnrollment.school_year_id == school_year_id)
    if section_id is not None:
        query = query.where(StudentEnrollment.section_id == section_id)
    if grade_level_id is not None:
        query = query.where(StudentEnrollment.grade_level_id == grade_level_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_enrollment(db: AsyncSession, enrollment_id: int) -> StudentEnrollment | None:
    result = await db.execute(
        select(StudentEnrollment)
        .options(
            selectinload(StudentEnrollment.student),
            selectinload(StudentEnrollment.grade_level),
            selectinload(StudentEnrollment.section),
            selectinload(StudentEnrollment.school_year),
        )
        .where(StudentEnrollment.enrollment_id == enrollment_id)
    )
    return result.scalar_one_or_none()


async def create_enrollment(db: AsyncSession, payload: dict) -> StudentEnrollment:
    await _verify_fks(
        db,
        payload["grade_level_id"],
        payload["section_id"],
        payload["school_year_id"],
    )

    enrollment = StudentEnrollment(**payload)
    db.add(enrollment)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"detail": "Could not create enrollment."})

    await db.refresh(enrollment)
    return await get_enrollment(db, enrollment.enrollment_id)


async def create_enrollment_with_student(
    db: AsyncSession, payload: dict
) -> tuple[Student, StudentEnrollment]:
    student_fields = {
        "first_name": payload["first_name"],
        "middle_name": payload.get("middle_name"),
        "last_name": payload["last_name"],
        "birth_date": payload["birth_date"],
        "gender": payload["gender"],
        "address": payload["address"],
        "guardian_first_name": payload["guardian_first_name"],
        "guardian_mid_name": payload.get("guardian_mid_name"),
        "guardian_last_name": payload["guardian_last_name"],
        "guardian_contact": payload["guardian_contact"],
        "guardian_relationship": payload["guardian_relationship"],
        "created_by": payload.get("created_by"),
    }

    enrollment_fields = {
        "grade_level_id": payload["grade_level_id"],
        "section_id": payload["section_id"],
        "school_year_id": payload["school_year_id"],
        "enrollment_date": payload.get("enrollment_date"),
        "next_grade_level_id": payload.get("next_grade_level_id"),
        "is_active": payload.get("is_active", True),
        "enrolled_by": payload.get("enrolled_by"),
    }

    await _verify_fks(
        db,
        enrollment_fields["grade_level_id"],
        enrollment_fields["section_id"],
        enrollment_fields["school_year_id"],
    )

    student = await create_student(db, student_fields)

    enrollment_fields["student_id"] = student.student_id
    enrollment = StudentEnrollment(**enrollment_fields)
    db.add(enrollment)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"detail": "Could not create enrollment."})

    await db.refresh(enrollment)
    enrollment = await get_enrollment(db, enrollment.enrollment_id)
    return student, enrollment


async def update_enrollment(
    db: AsyncSession, enrollment_id: int, changes: dict
) -> StudentEnrollment:
    enrollment = await get_enrollment(db, enrollment_id)
    if not enrollment:
        raise ServiceError(404, {"error": "Enrollment not found."})

    for key, value in changes.items():
        setattr(enrollment, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"detail": "Update failed."})

    await db.refresh(enrollment)
    return await get_enrollment(db, enrollment_id)


async def delete_enrollment(db: AsyncSession, enrollment_id: int) -> None:
    enrollment = await get_enrollment(db, enrollment_id)
    if not enrollment:
        raise ServiceError(404, {"error": "Enrollment not found."})

    await db.delete(enrollment)
    await db.commit()