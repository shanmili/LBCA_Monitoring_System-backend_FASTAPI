from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin
from app.schemas.student import StudentOut
from app.schemas.student_enrollment import (
    StudentEnrollmentCreate,
    StudentEnrollmentOut,
    StudentEnrollmentUpdate,
    StudentEnrollmentWithStudentCreate,
)
from app.services.student_enrollment_service import (
    ServiceError,
    create_enrollment,
    create_enrollment_with_student,
    delete_enrollment,
    get_enrollment,
    list_enrollments,
    update_enrollment,
)

router = APIRouter(tags=["Student Enrollments"])


def _to_enrollment_out(row) -> dict:
    """Serialize enrollment with embedded student info for the PACE table."""
    base = StudentEnrollmentOut.model_validate(row).model_dump(mode="json")
    # Embed student name fields so the frontend doesn't need a second request
    if row.student:
        base["student"] = {
            "student_id":  row.student.student_id,
            "first_name":  row.student.first_name,
            "middle_name": row.student.middle_name,
            "last_name":   row.student.last_name,
            "login_id":    row.student.login_id,
        }
    else:
        base["student"] = None
    return base


@router.get("/api/enrollments/")
async def list_enrollments_route(
    student_id:      int | None = Query(default=None),
    school_year_id:  int | None = Query(default=None),
    section_id:      int | None = Query(default=None),
    grade_level_id:  int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_enrollments(
        db,
        student_id=student_id,
        school_year_id=school_year_id,
        section_id=section_id,
        grade_level_id=grade_level_id,
    )
    return [_to_enrollment_out(row) for row in rows]


@router.get("/api/enrollments/{enrollment_id}")
async def get_enrollment_route(
    enrollment_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_enrollment(db, enrollment_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Enrollment not found."})
    return _to_enrollment_out(row)


@router.get("/api/students/{student_id}/enrollments")
async def list_enrollments_by_student_route(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_enrollments(db, student_id=student_id)
    return [_to_enrollment_out(row) for row in rows]


@router.post("/api/enrollments")
async def create_enrollment_route(
    payload: StudentEnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    data = payload.model_dump()
    data["enrolled_by"] = current_user.id  # auto-set from authenticated user

    try:
        row = await create_enrollment(db, data)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Enrollment created successfully.",
            "enrollment": _to_enrollment_out(row),
        },
    )


@router.post("/api/enrollments/with-student")
async def create_enrollment_with_student_route(
    payload: StudentEnrollmentWithStudentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    data = payload.model_dump()
    data["enrolled_by"] = current_user.id  # auto-set from authenticated user
    data["created_by"] = current_user.id

    try:
        student, enrollment = await create_enrollment_with_student(db, data)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Student and enrollment created successfully.",
            "student_login_id": student.login_id,
            "student_login_password": student.login_id,
            "student": StudentOut.model_validate(student).model_dump(mode="json"),
            "enrollment": _to_enrollment_out(enrollment),
        },
    )


@router.put("/api/enrollments/{enrollment_id}")
@router.patch("/api/enrollments/{enrollment_id}")
async def update_enrollment_route(
    enrollment_id: int,
    payload: StudentEnrollmentUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await update_enrollment(db, enrollment_id, payload.model_dump(exclude_unset=True))
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {
        "message": "Enrollment updated successfully.",
        "enrollment": _to_enrollment_out(row),
    }


@router.delete("/api/enrollments/{enrollment_id}")
async def delete_enrollment_route(
    enrollment_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        await delete_enrollment(db, enrollment_id)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {"message": "Enrollment deleted successfully."}