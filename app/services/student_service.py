
from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Student
from app.models.students import StudentEnrollment, StudentPace, EarlyWarning


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


def _enrich(student: Student) -> dict:
    """
    Convert a Student ORM object to a plain dict enriched with:
      - section_name   (from active enrollment → section)
      - grade_level_display
      - pace_percent   (avg across all pace records)
      - attendance     (avg from early_warnings, or 0 if none)
      - subjects       (list for the Profile PACE tab)
    """
    # ── active enrollment ────────────────────────────────────────────────
    active_enroll = None
    if student.enrollments:
        active_enroll = next(
            (e for e in student.enrollments if e.is_active),
            student.enrollments[0],
        )

    section_name        = ""
    grade_level_display = ""
    if active_enroll:
        if active_enroll.section:
            section_name = active_enroll.section.name or ""
        if active_enroll.grade_level:
            grade_level_display = active_enroll.grade_level.level or ""

    # ── pace_percent: average of all pace records ────────────────────────
    paces       = student.paces or []
    pace_percent = round(
        sum(p.pace_percent for p in paces) / len(paces), 1
    ) if paces else 0.0

    # ── attendance: take from most recent early_warning, fallback 0 ─────
    warnings   = sorted(
        student.early_warnings or [],
        key=lambda w: w.updated_at,
        reverse=True,
    )
    attendance = warnings[0].attendance if warnings else 0.0

    # ── subjects list for ProfilePaceTab ────────────────────────────────
    # Groups pace records by subject and exposes completed/total/testScore
    subj_map: dict[str, list] = {}
    for p in paces:
        subj_map.setdefault(p.subject, []).append(p)

    subjects = []
    for subj_name, records in subj_map.items():
        avg_pct   = sum(r.pace_percent for r in records) / len(records)
        completed = sum(1 for r in records if r.pace_percent >= 80)
        total     = len(records)
        status    = "Behind" if avg_pct < 80 else "On Track"
        subjects.append({
            "name":      subj_name,
            "completed": completed,
            "total":     total,
            "testScore": round(avg_pct, 1),   # use pace_percent as proxy for test score
            "status":    status,
        })

    # ── attendance summary for ProfileAttendanceTab ──────────────────────
    present = round(attendance, 1)
    absent  = round(max(0.0, 100.0 - attendance - 5), 1)
    late    = round(max(0.0, 100.0 - present - absent), 1)
    attendance_summary = {"present": present, "late": late, "absent": absent}

    return {
        # original fields
        "student_id":            student.student_id,
        "login_id":              student.login_id,
        "first_name":            student.first_name,
        "middle_name":           student.middle_name,
        "last_name":             student.last_name,
        "birth_date":            student.birth_date,
        "gender":                student.gender,
        "address":               student.address,
        "guardian_first_name":   student.guardian_first_name,
        "guardian_mid_name":     student.guardian_mid_name,
        "guardian_last_name":    student.guardian_last_name,
        "guardian_contact":      student.guardian_contact,
        "guardian_relationship": student.guardian_relationship,
        "created_at":            student.created_at.isoformat() if student.created_at else None,
        "updated_at":            student.updated_at.isoformat() if student.updated_at else None,
        "created_by":            str(student.created_by) if student.created_by else None,
        # ── enriched fields the frontend needs ──────────────────────────
        "section_name":          section_name,
        "section":               section_name,          # alias used by some components
        "grade_level_display":   grade_level_display,
        "pace_percent":          pace_percent,
        "pacePercent":           pace_percent,          # camelCase alias
        "attendance":            attendance,
        "subjects":              subjects,
        "attendanceSummary":     attendance_summary,
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def list_students(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Student)
        .options(
            selectinload(Student.enrollments)
            .selectinload(StudentEnrollment.section),
            selectinload(Student.enrollments)
            .selectinload(StudentEnrollment.grade_level),
            selectinload(Student.paces),
            selectinload(Student.early_warnings),
        )
        .order_by(Student.student_id.asc())
    )
    students = list(result.scalars().all())
    return [_enrich(s) for s in students]


async def get_student(db: AsyncSession, student_id: int) -> dict | None:
    result = await db.execute(
        select(Student)
        .options(
            selectinload(Student.enrollments)
            .selectinload(StudentEnrollment.section),
            selectinload(Student.enrollments)
            .selectinload(StudentEnrollment.grade_level),
            selectinload(Student.paces),
            selectinload(Student.early_warnings),
        )
        .where(Student.student_id == student_id)
    )
    student = result.scalar_one_or_none()
    return _enrich(student) if student else None


async def create_student(db: AsyncSession, payload: dict) -> Student:
    """
    Creates a Student record and automatically assigns a login_id (S###).
    Returns the raw ORM object (caller handles serialisation).
    """
    student = Student(**payload)
    db.add(student)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"detail": "Unable to create student. Verify the data and try again."})

    student.login_id = _generate_login_id(student.student_id)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"login_id": ["Generated login ID is already in use."]})

    await db.refresh(student)
    return student


async def update_student(db: AsyncSession, student_id: int, changes: dict) -> Student:
    result = await db.execute(
        select(Student).where(Student.student_id == student_id)
    )
    student = result.scalar_one_or_none()
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
    result = await db.execute(
        select(Student).where(Student.student_id == student_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise ServiceError(404, {"error": "Student not found."})

    await db.delete(student)
    await db.commit()