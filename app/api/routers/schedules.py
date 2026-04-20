from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin
from app.schemas.schedule import ScheduleCreate, ScheduleOut, ScheduleUpdate
from app.services.schedule_service import (
    ServiceError,
    create_schedule,
    delete_schedule,
    get_schedule,
    list_schedules,
    update_schedule,
)


router = APIRouter(tags=["schedules"])


@router.get("/api/schedules/")
async def list_schedules_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_schedules(db)
    return [ScheduleOut.model_validate(row).model_dump(mode="json") for row in rows]


@router.get("/api/schedules/{schedule_id}")
async def get_schedule_route(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_schedule(db, schedule_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Schedule not found."})
    return ScheduleOut.model_validate(row).model_dump(mode="json")


@router.post("/api/schedules")
async def create_schedule_route(
    payload: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await create_schedule(db, payload.model_dump())
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Schedule created successfully.",
            "schedule": ScheduleOut.model_validate(row).model_dump(mode="json"),
        },
    )


@router.put("/api/schedules/{schedule_id}")
@router.patch("/api/schedules/{schedule_id}")
async def update_schedule_route(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await update_schedule(db, schedule_id, payload.model_dump(exclude_unset=True))
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {
        "message": "Schedule updated successfully.",
        "schedule": ScheduleOut.model_validate(row).model_dump(mode="json"),
    }


@router.delete("/api/schedules/{schedule_id}")
async def delete_schedule_route(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        await delete_schedule(db, schedule_id)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {"message": "Schedule deleted successfully."}
