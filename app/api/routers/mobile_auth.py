from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from auth import create_access_token, create_refresh_token, decode_token
from app.models.students import Student, StudentEnrollment

router = APIRouter(tags=["Mobile Auth"])

_bearer = HTTPBearer()


class ParentLoginRequest(BaseModel):
    username: str
    password: str


async def _get_student_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    payload = decode_token(credentials.credentials)
    student_id = payload.get("sub")
    role = payload.get("role")

    if not student_id or role != "parent":
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    return {"student_id": int(student_id)}


@router.post("/api/parent/login/")
async def parent_login(
    payload: ParentLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    login_id = payload.username.strip()

    result = await db.execute(
        select(Student).where(Student.login_id == login_id)
    )
    student = result.scalar_one_or_none()

    if not student or payload.password.strip() != login_id:
        raise HTTPException(status_code=401, detail="Invalid student ID or password.")

    access_token = create_access_token({"sub": str(student.student_id), "role": "parent"})
    refresh_token = create_refresh_token({"sub": str(student.student_id), "role": "parent"})

    return {
        "token": access_token,
        "refresh_token": refresh_token,
        "student_id": student.student_id,
        "login_id": student.login_id,
    }


@router.get("/api/parent/student-info/")
async def parent_student_info(
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(_get_student_from_token),
):
    student_id = current["student_id"]

    result = await db.execute(
        select(Student)
        .options(
            selectinload(Student.enrollments).selectinload(StudentEnrollment.grade_level),
            selectinload(Student.enrollments).selectinload(StudentEnrollment.section),
        )
        .where(Student.student_id == student_id)
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    active = next((e for e in student.enrollments if e.is_active), None)

    return {
        "student_id": student.student_id,
        "login_id": student.login_id,
        "first_name": student.first_name,
        "middle_name": student.middle_name,
        "last_name": student.last_name,
        "grade_level": active.grade_level.name if active else None,
        "section": active.section.name if active else None,
        "guardian_first_name": student.guardian_first_name,
        "guardian_last_name": student.guardian_last_name,
        "guardian_contact": student.guardian_contact,
    }