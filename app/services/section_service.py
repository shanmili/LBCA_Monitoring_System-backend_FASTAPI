from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import GradeLevel, Section


class ServiceError(Exception):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail


async def list_sections(db: AsyncSession, grade_level_id: int | None = None) -> list[Section]:
    query = select(Section).options(selectinload(Section.grade_level))
    if grade_level_id is not None:
        query = query.where(Section.grade_level_id == grade_level_id)
    query = query.order_by(Section.section_id.asc())

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_section(db: AsyncSession, section_id: int) -> Section | None:
    result = await db.execute(
        select(Section)
        .options(selectinload(Section.grade_level))
        .where(Section.section_id == section_id)
    )
    return result.scalar_one_or_none()


async def get_grade_level(db: AsyncSession, grade_level_id: int) -> GradeLevel | None:
    result = await db.execute(
        select(GradeLevel).where(GradeLevel.grade_level_id == grade_level_id)
    )
    return result.scalar_one_or_none()


async def create_section(db: AsyncSession, payload: dict) -> Section:
    grade_level_id = payload["grade_level"]
    grade_level = await get_grade_level(db, grade_level_id)
    if not grade_level:
        raise ServiceError(400, {"grade_level": ["Grade level does not exist."]})

    section = Section(
        grade_level_id=grade_level_id,
        section_code=payload["section_code"],
        name=payload["name"],
    )
    db.add(section)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"section_code": ["section with this section code already exists."]})

    return await get_section(db, section.section_id)


async def update_section(db: AsyncSession, section_id: int, changes: dict) -> Section:
    section = await get_section(db, section_id)
    if not section:
        raise ServiceError(404, {"error": "Section not found."})

    grade_level_id = changes.pop("grade_level", None)
    if grade_level_id is not None:
        grade_level = await get_grade_level(db, grade_level_id)
        if not grade_level:
            raise ServiceError(400, {"grade_level": ["Grade level does not exist."]})
        section.grade_level_id = grade_level_id

    for key, value in changes.items():
        setattr(section, key, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ServiceError(400, {"section_code": ["section with this section code already exists."]})

    return await get_section(db, section.section_id)


async def delete_section(db: AsyncSession, section_id: int) -> None:
    section = await get_section(db, section_id)
    if not section:
        raise ServiceError(404, {"error": "Section not found."})

    await db.delete(section)
    await db.commit()
