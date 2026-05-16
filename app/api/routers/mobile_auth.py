# app/api/routers/mobile_auth.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AsyncSession, get_db
from app.models.students import Student, StudentEnrollment
from auth import create_access_token, create_refresh_token
from database import get_db
from dependencies import get_current_user


from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth import decode_token

_bearer = HTTPBearer()

async def _get_student_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    payload = decode_token(credentials.credentials)
    student_id = payload.get("sub")
    role = payload.get("role")

    if not student_id or role != "parent":
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    return {"student_id": int(student_id)}


router = APIRouter(tags=["Mobile Auth"])


class ParentLoginRequest(BaseModel):
    username: str   # the student's login_id, e.g. S001
    password: str   # defaults to login_id on the mobile side


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

    # Password = login_id (the mobile app pre-fills this as default)
    if not student or payload.password.strip() != login_id:
        raise HTTPException(status_code=401, detail="Invalid student ID or password.")

    # Issue a JWT so the mobile apiClient can attach it as Bearer
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
    current_user_payload: dict = Depends(_get_student_from_token),
):
    student_id = current_user_payload["student_id"]

    result = await db.execute(
        select(Student)
        .options(selectinload(Student.enrollments).selectinload(StudentEnrollment.grade_level))
        .options(selectinload(Student.enrollments).selectinload(StudentEnrollment.section))
        .where(Student.student_id == student_id)
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    # Get the active enrollment for grade/section info
    active = next((e for e in student.enrollments if e.is_active), None)

    return {
        "student_id": student.student_id,
        "login_id": student.login_id,
        "first_name": student.first_name,
        "middle_name": student.middle_name,
        "last_name": student.last_name,
        "grade_level": active.grade_level.grade_level_name if active else None,
        "section": active.section.section_name if active else None,
        "guardian_first_name": student.guardian_first_name,
        "guardian_last_name": student.guardian_last_name,
        "guardian_contact": student.guardian_contact,
    }