from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin
from app.schemas.data_quality_log import DataQualityLogCreate, DataQualityLogOut, DataQualityLogUpdate
from app.services.data_quality_log_service import (
    ServiceError,
    create_data_quality_log,
    delete_data_quality_log,
    get_data_quality_log,
    list_data_quality_logs,
    update_data_quality_log,
)


router = APIRouter(tags=["data_quality_logs"])


@router.get("/api/data-quality-logs/")
async def list_data_quality_logs_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_data_quality_logs(db)
    return [DataQualityLogOut.model_validate(row).model_dump(mode="json") for row in rows]


@router.get("/api/data-quality-logs/{log_id}")
async def get_data_quality_log_route(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_data_quality_log(db, log_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Data quality log not found."})
    return DataQualityLogOut.model_validate(row).model_dump(mode="json")


@router.post("/api/data-quality-logs")
async def create_data_quality_log_route(
    payload: DataQualityLogCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await create_data_quality_log(db, payload.model_dump())
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Data quality log created successfully.",
            "log": DataQualityLogOut.model_validate(row).model_dump(mode="json"),
        },
    )


@router.put("/api/data-quality-logs/{log_id}")
@router.patch("/api/data-quality-logs/{log_id}")
async def update_data_quality_log_route(
    log_id: int,
    payload: DataQualityLogUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await update_data_quality_log(db, log_id, payload.model_dump(exclude_unset=True))
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {
        "message": "Data quality log updated successfully.",
        "log": DataQualityLogOut.model_validate(row).model_dump(mode="json"),
    }


@router.delete("/api/data-quality-logs/{log_id}")
async def delete_data_quality_log_route(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        await delete_data_quality_log(db, log_id)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {"message": "Data quality log deleted successfully."}
