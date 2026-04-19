from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin
from app.schemas.section import SectionCreate, SectionOut, SectionUpdate
from app.services.section_service import (
    ServiceError,
    create_section,
    delete_section,
    get_grade_level,
    get_section,
    list_sections,
    update_section,
)


router = APIRouter(tags=["sections"])


def to_section_out(row) -> dict:
    return SectionOut(
        section_id=row.section_id,
        grade_level=row.grade_level_id,
        grade_level_display=row.grade_level.level,
        section_code=row.section_code,
        name=row.name,
    ).model_dump(mode="json")


@router.get("/api/sections/")
async def list_sections_route(
    grade_level_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_sections(db, grade_level_id=grade_level_id)
    return [to_section_out(row) for row in rows]


@router.get("/api/grade-levels/{grade_level_id}/sections")
async def list_sections_by_grade_level_route(
    grade_level_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    grade_level = await get_grade_level(db, grade_level_id)
    if not grade_level:
        return JSONResponse(status_code=404, content={"error": "Grade level not found."})

    rows = await list_sections(db, grade_level_id=grade_level_id)
    return [to_section_out(row) for row in rows]


@router.get("/api/sections/{section_id}")
async def get_section_route(
    section_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_section(db, section_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Section not found."})
    return to_section_out(row)


@router.post("/api/sections")
async def create_section_route(
    payload: SectionCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await create_section(db, payload.model_dump())
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Section created successfully.",
            "section": to_section_out(row),
        },
    )


@router.put("/api/sections/{section_id}")
@router.patch("/api/sections/{section_id}")
async def update_section_route(
    section_id: int,
    payload: SectionUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await update_section(db, section_id, payload.model_dump(exclude_unset=True))
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {
        "message": "Section updated successfully.",
        "section": to_section_out(row),
    }


@router.delete("/api/sections/{section_id}")
async def delete_section_route(
    section_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        await delete_section(db, section_id)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {"message": "Section deleted successfully."}
