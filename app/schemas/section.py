from typing import Optional

from pydantic import BaseModel


class SectionCreate(BaseModel):
    grade_level: int
    section_code: str
    name: str


class SectionUpdate(BaseModel):
    grade_level: Optional[int] = None
    section_code: Optional[str] = None
    name: Optional[str] = None


class SectionOut(BaseModel):
    section_id: int
    grade_level: int
    grade_level_display: str
    section_code: str
    name: str
