
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin
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


@router.get("/api/students/")
async def list_students_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    # list_students now returns enriched dicts — return them directly
    return await list_students(db)


@router.get("/api/students/{student_id}")
async def get_student_route(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_student(db, student_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Student not found."})
    # get_student now returns an enriched dict — return it directly
    return row


@router.post("/api/students")
async def create_student_route(
    payload: StudentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    data = payload.model_dump()
    data["created_by"] = current_user.id   # auto-set from authenticated user

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
    _admin=Depends(require_admin),
):
    try:
        row = await update_student(db, student_id, payload.model_dump(exclude_unset=True))
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