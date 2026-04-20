from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin
from app.schemas.teacher_availability import TeacherAvailabilityCreate, TeacherAvailabilityOut, TeacherAvailabilityUpdate
from app.services.teacher_availability_service import (
    ServiceError,
    create_teacher_availability,
    delete_teacher_availability,
    get_teacher_availability,
    list_teacher_availabilities,
    update_teacher_availability,
)


router = APIRouter(tags=["teacher_availabilities"])


@router.get("/api/teacher-availabilities/")
async def list_teacher_availabilities_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_teacher_availabilities(db)
    return [TeacherAvailabilityOut.model_validate(row).model_dump(mode="json") for row in rows]


@router.get("/api/teacher-availabilities/{availability_id}")
async def get_teacher_availability_route(
    availability_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_teacher_availability(db, availability_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Teacher availability not found."})
    return TeacherAvailabilityOut.model_validate(row).model_dump(mode="json")


@router.post("/api/teacher-availabilities")
async def create_teacher_availability_route(
    payload: TeacherAvailabilityCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await create_teacher_availability(db, payload.model_dump())
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Teacher availability created successfully.",
            "availability": TeacherAvailabilityOut.model_validate(row).model_dump(mode="json"),
        },
    )


@router.put("/api/teacher-availabilities/{availability_id}")
@router.patch("/api/teacher-availabilities/{availability_id}")
async def update_teacher_availability_route(
    availability_id: int,
    payload: TeacherAvailabilityUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await update_teacher_availability(db, availability_id, payload.model_dump(exclude_unset=True))
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {
        "message": "Teacher availability updated successfully.",
        "availability": TeacherAvailabilityOut.model_validate(row).model_dump(mode="json"),
    }


@router.delete("/api/teacher-availabilities/{availability_id}")
async def delete_teacher_availability_route(
    availability_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        await delete_teacher_availability(db, availability_id)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {"message": "Teacher availability deleted successfully."}
