from typing import Optional

from pydantic import BaseModel, ConfigDict


class GradeLevelCreate(BaseModel):
    level: str
    name: str


class GradeLevelUpdate(BaseModel):
    level: Optional[str] = None
    name: Optional[str] = None


class GradeLevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    grade_level_id: int
    level: str
    name: str
