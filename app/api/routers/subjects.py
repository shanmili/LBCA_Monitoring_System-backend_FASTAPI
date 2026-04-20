from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import AsyncSession, get_current_user, get_db, require_admin
from app.schemas.subject import SubjectCreate, SubjectOut, SubjectUpdate
from app.services.subject_service import (
    ServiceError,
    create_subject,
    delete_subject,
    get_subject,
    list_subjects,
    update_subject,
)


router = APIRouter(tags=["subjects"])


@router.get("/api/subjects/")
async def list_subjects_route(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    rows = await list_subjects(db)
    return [SubjectOut.model_validate(row).model_dump(mode="json") for row in rows]


@router.get("/api/subjects/{subject_id}")
async def get_subject_route(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    row = await get_subject(db, subject_id)
    if not row:
        return JSONResponse(status_code=404, content={"error": "Subject not found."})
    return SubjectOut.model_validate(row).model_dump(mode="json")


@router.post("/api/subjects")
async def create_subject_route(
    payload: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await create_subject(db, payload.model_dump())
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Subject created successfully.",
            "subject": SubjectOut.model_validate(row).model_dump(mode="json"),
        },
    )


@router.put("/api/subjects/{subject_id}")
@router.patch("/api/subjects/{subject_id}")
async def update_subject_route(
    subject_id: int,
    payload: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        row = await update_subject(db, subject_id, payload.model_dump(exclude_unset=True))
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {
        "message": "Subject updated successfully.",
        "subject": SubjectOut.model_validate(row).model_dump(mode="json"),
    }


@router.delete("/api/subjects/{subject_id}")
async def delete_subject_route(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        await delete_subject(db, subject_id)
    except ServiceError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return {"message": "Subject deleted successfully."}
