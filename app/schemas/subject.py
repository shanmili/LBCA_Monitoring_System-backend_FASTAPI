from typing import Optional

from pydantic import BaseModel, ConfigDict


class SubjectCreate(BaseModel):
    grade_level_id: int
    subject_name: str
    subject_code: str
    is_active: Optional[bool] = True


class SubjectUpdate(BaseModel):
    grade_level_id: Optional[int] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    is_active: Optional[bool] = None


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject_id: int
    grade_level_id: int
    subject_name: str
    subject_code: str
    is_active: bool
