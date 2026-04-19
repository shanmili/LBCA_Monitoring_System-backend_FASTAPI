from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin
from app.schemas.grade_level import GradeLevelCreate, GradeLevelOut, GradeLevelUpdate
from app.services.grade_level_service import (
    ServiceError,
    create_grade_level,
    delete_grade_level,
    get_grade_level,
    list_grade_levels,
    update_grade_level,
)


router = APIRouter(tags=["grade_levels"])


@router.get("/api/grade-levels/")
async def list_grade_levels_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_grade_levels(db)
    return [GradeLevelOut.model_validate(row).model_dump(mode="json") for row in rows]


@router.get("/api/grade-levels/{grade_level_id}")
async def get_grade_level_route(
    grade_level_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_grade_level(db, grade_level_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Grade level not found."})
    return GradeLevelOut.model_validate(row).model_dump(mode="json")


@router.post("/api/grade-levels")
async def create_grade_level_route(
    payload: GradeLevelCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await create_grade_level(db, payload.model_dump())
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Grade level created successfully.",
            "grade_level": GradeLevelOut.model_validate(row).model_dump(mode="json"),
        },
    )


@router.put("/api/grade-levels/{grade_level_id}")
@router.patch("/api/grade-levels/{grade_level_id}")
async def update_grade_level_route(
    grade_level_id: int,
    payload: GradeLevelUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await update_grade_level(db, grade_level_id, payload.model_dump(exclude_unset=True))
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {
        "message": "Grade level updated successfully.",
        "grade_level": GradeLevelOut.model_validate(row).model_dump(mode="json"),
    }


@router.delete("/api/grade-levels/{grade_level_id}")
async def delete_grade_level_route(
    grade_level_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        await delete_grade_level(db, grade_level_id)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {"message": "Grade level deleted successfully."}
