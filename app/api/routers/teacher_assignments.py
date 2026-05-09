from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin
from app.schemas.teacher_assignment import TeacherAssignmentCreate, TeacherAssignmentOut
from app.services.teacher_assignment_service import (
    ServiceError,
    create_teacher_assignment,
    delete_teacher_assignment,
    get_teacher_assignment,
    list_teacher_assignments,
)


router = APIRouter(tags=["teacher_assignments"], redirect_slashes=False)


def to_teacher_assignment_out(row) -> dict:
    return TeacherAssignmentOut(
        assignment_id=row.assignment_id,
        teacher_id=row.teacher_id,
        section_id=row.section_id,
        teacher_name=f"{row.teacher.first_name} {row.teacher.last_name}" if row.teacher else None,
        section_code=row.section.section_code if row.section else None,
        section_name=row.section.name if row.section else None,
    ).model_dump(mode="json")


@router.get("/api/teacher-assignments/")
async def list_teacher_assignments_route(
    section_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_teacher_assignments(db, section_id=section_id)
    return [to_teacher_assignment_out(row) for row in rows]


@router.get("/api/teacher-assignments/{assignment_id}")
async def get_teacher_assignment_route(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_teacher_assignment(db, assignment_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Assignment not found."})
    return to_teacher_assignment_out(row)


@router.post("/api/teacher-assignments/")
async def create_teacher_assignment_route(
    payload: TeacherAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        assignment = await create_teacher_assignment(db, payload.model_dump())
        return to_teacher_assignment_out(assignment)
    except ServiceError as e:
        return JSONResponse(status_code=e.status_code, content=e.detail)


@router.delete("/api/teacher-assignments/{assignment_id}")
async def delete_teacher_assignment_route(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        await delete_teacher_assignment(db, assignment_id)
        return JSONResponse(status_code=204, content={})
    except ServiceError as e:
        return JSONResponse(status_code=e.status_code, content=e.detail)
