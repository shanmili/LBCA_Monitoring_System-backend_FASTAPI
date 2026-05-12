from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin
from app.schemas.student_pace import (
    EarlyWarningCreate,
    EarlyWarningOut,
    EarlyWarningUpdate,
    StudentPaceCreate,
    StudentPaceOut,
    StudentPaceUpdate,
)
from app.services.student_pace_service import (
    ServiceError,
    create_pace,
    create_warning,
    delete_pace,
    delete_warning,
    get_pace,
    get_warning,
    list_paces,
    list_warnings,
    update_pace,
    update_warning,
)

router = APIRouter(tags=["student_pace"])


def _to_pace_out(row) -> dict:
    out = StudentPaceOut.model_validate(row).model_dump(mode="json")
    out["student_name"] = f"{row.student.first_name} {row.student.last_name}"
    return out


def _to_warning_out(row) -> dict:
    out = EarlyWarningOut.model_validate(row).model_dump(mode="json")
    out["student_name"] = f"{row.student.first_name} {row.student.last_name}"
    return out


# ===========================================================================
# StudentPace endpoints
# ===========================================================================

@router.get("/api/student-paces/")
async def list_paces_route(
    student_id: int | None = Query(default=None),
    enrollment_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_paces(db, student_id=student_id, enrollment_id=enrollment_id)
    return [_to_pace_out(row) for row in rows]


@router.get("/api/student-paces/{pace_id}")
async def get_pace_route(
    pace_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_pace(db, pace_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Pace record not found."})
    return _to_pace_out(row)


# Convenience: all paces for a specific student
@router.get("/api/students/{student_id}/paces")
async def list_student_paces_route(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_paces(db, student_id=student_id)
    if not rows:
        return JSONResponse(
            status_code=404,
            content={"error": "No pace records found for this student."},
        )
    return [_to_pace_out(row) for row in rows]


@router.post("/api/student-paces")
async def create_pace_route(
    payload: StudentPaceCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        row = await create_pace(db, payload.model_dump())
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Pace record created successfully.",
            "pace": _to_pace_out(row),
        },
    )


@router.put("/api/student-paces/{pace_id}")
@router.patch("/api/student-paces/{pace_id}")
async def update_pace_route(
    pace_id: int,
    payload: StudentPaceUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        row = await update_pace(db, pace_id, payload.model_dump(exclude_unset=True))
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {
        "message": "Pace record updated successfully.",
        "pace": _to_pace_out(row),
    }


@router.delete("/api/student-paces/{pace_id}")
async def delete_pace_route(
    pace_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        await delete_pace(db, pace_id)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {"message": "Pace record deleted successfully."}


# ===========================================================================
# EarlyWarning endpoints
# ===========================================================================

@router.get("/api/early-warnings/")
async def list_warnings_route(
    student_id: int | None = Query(default=None),
    enrollment_id: int | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_warnings(
        db,
        student_id=student_id,
        enrollment_id=enrollment_id,
        risk_level=risk_level,
    )
    return [_to_warning_out(row) for row in rows]


@router.get("/api/early-warnings/critical")
async def list_critical_warnings_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_warnings(db, risk_level="critical")
    return [_to_warning_out(row) for row in rows]


@router.get("/api/early-warnings/{warning_id}")
async def get_warning_route(
    warning_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_warning(db, warning_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Early warning not found."})
    return _to_warning_out(row)


# Convenience: all warnings for a specific student
@router.get("/api/students/{student_id}/warnings")
async def list_student_warnings_route(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_warnings(db, student_id=student_id)
    if not rows:
        return {"message": "No warnings for this student."}
    return [_to_warning_out(row) for row in rows]


@router.post("/api/early-warnings")
async def create_warning_route(
    payload: EarlyWarningCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await create_warning(db, payload.model_dump())
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Early warning created successfully.",
            "warning": _to_warning_out(row),
        },
    )


@router.put("/api/early-warnings/{warning_id}")
@router.patch("/api/early-warnings/{warning_id}")
async def update_warning_route(
    warning_id: int,
    payload: EarlyWarningUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await update_warning(db, warning_id, payload.model_dump(exclude_unset=True))
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {
        "message": "Early warning updated successfully.",
        "warning": _to_warning_out(row),
    }


@router.delete("/api/early-warnings/{warning_id}")
async def delete_warning_route(
    warning_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        await delete_warning(db, warning_id)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {"message": "Early warning deleted successfully."}