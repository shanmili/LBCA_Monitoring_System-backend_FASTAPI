from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin
from app.schemas.school_year import SchoolYearCreate, SchoolYearOut, SchoolYearUpdate
from app.services.school_year_service import (
    ServiceError,
    create_school_year,
    delete_school_year,
    get_current_school_year,
    get_school_year,
    list_school_years,
    update_school_year,
)


router = APIRouter(tags=["school_years"])


@router.get("/api/school-years/")
async def list_school_years_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_school_years(db)
    return [SchoolYearOut.model_validate(row).model_dump(mode="json") for row in rows]


@router.get("/api/school-years/current/")
async def get_current_school_year_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_current_school_year(db)
    if not row:
        return JSONResponse(status_code=404, content={"error": "No active school year found."})
    return SchoolYearOut.model_validate(row).model_dump(mode="json")


@router.get("/api/school-years/{school_year_id}")
async def get_school_year_route(
    school_year_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_school_year(db, school_year_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "School year not found."})
    return SchoolYearOut.model_validate(row).model_dump(mode="json")


@router.post("/api/school-years")
async def create_school_year_route(
    payload: SchoolYearCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await create_school_year(db, payload.model_dump())
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "School year created successfully.",
            "school_year": SchoolYearOut.model_validate(row).model_dump(mode="json"),
        },
    )


@router.put("/api/school-years/{school_year_id}")
@router.patch("/api/school-years/{school_year_id}")
async def update_school_year_route(
    school_year_id: int,
    payload: SchoolYearUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await update_school_year(db, school_year_id, payload.model_dump(exclude_unset=True))
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {
        "message": "School year updated successfully.",
        "school_year": SchoolYearOut.model_validate(row).model_dump(mode="json"),
    }


@router.delete("/api/school-years/{school_year_id}")
async def delete_school_year_route(
    school_year_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        await delete_school_year(db, school_year_id)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {"message": "School year deleted successfully."}
