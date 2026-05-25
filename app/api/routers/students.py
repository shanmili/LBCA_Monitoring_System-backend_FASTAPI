from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin, require_admin_or_teacher
from app.schemas.student import StudentCreate, StudentOut, StudentUpdate
from app.services.student_service import (
    ServiceError,
    create_student,
    delete_student,
    get_student,
    list_students,
    update_student,
)

router = APIRouter(tags=["Students"])

# Fields a student/parent is allowed to update on their own record.
# They cannot touch name, birthdate, gender, or any academic field.
STUDENT_SELF_EDITABLE_FIELDS = {
    "address",
    "guardian_first_name",
    "guardian_mid_name",
    "guardian_last_name",
    "guardian_contact",
    "guardian_relationship",
}


@router.get("/api/students/")
async def list_students_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_students(db)
    return [StudentOut.model_validate(row).model_dump(mode="json") for row in rows]


@router.get("/api/students/{student_id}")
async def get_student_route(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_student(db, student_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Student not found."})
    return StudentOut.model_validate(row).model_dump(mode="json")


@router.post("/api/students")
async def create_student_route(
    payload: StudentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin_or_teacher),
):
    data = payload.model_dump()
    data["created_by"] = current_user.id

    try:
        row = await create_student(db, data)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Student created successfully.",
            "student_login_id": row.login_id,
            "student_login_password": row.login_id,
            "student": StudentOut.model_validate(row).model_dump(mode="json"),
        },
    )


@router.put("/api/students/{student_id}")
@router.patch("/api/students/{student_id}")
async def update_student_route(
    student_id: int,
    payload: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_role = getattr(current_user, "role", None)
    data = payload.model_dump(exclude_unset=True)

    if user_role in ("admin", "teacher"):
        # Full update — no restrictions
        pass

    elif user_role == "parent":
        # The parent token's `id` is the student_id integer (set as `sub` in the JWT).
        # Just compare it directly to the URL parameter.
        token_student_id = getattr(current_user, "id", None)

        if token_student_id is None or int(token_student_id) != student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own profile.",
            )

        # Strip any fields the student is not allowed to change
        forbidden = {k for k in data if k not in STUDENT_SELF_EDITABLE_FIELDS}
        if forbidden:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Students cannot modify: {', '.join(sorted(forbidden))}.",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    try:
        row = await update_student(db, student_id, data)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {
        "message": "Student updated successfully.",
        "student": StudentOut.model_validate(row).model_dump(mode="json"),
    }


@router.delete("/api/students/{student_id}")
async def delete_student_route(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        await delete_student(db, student_id)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {"message": "Student deleted successfully."}