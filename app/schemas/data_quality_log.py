from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DataQualityLogCreate(BaseModel):
    student_id: int
    teacher_id: Optional[str] = None
    student_pace_id: Optional[int] = None
    issue_type: str
    resolved: Optional[bool] = False


class DataQualityLogUpdate(BaseModel):
    student_id: Optional[int] = None
    teacher_id: Optional[str] = None
    student_pace_id: Optional[int] = None
    issue_type: Optional[str] = None
    resolved: Optional[bool] = None
    resolved_date: Optional[datetime] = None


class DataQualityLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: int
    student_id: int
    teacher_id: Optional[str]
    student_pace_id: Optional[int]
    issue_type: str
    resolved: bool
    resolved_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
