from typing import Optional
from datetime import time, datetime
from pydantic import BaseModel, ConfigDict


class TeacherAvailabilityCreate(BaseModel):
    teacher_id: str
    day: str
    start_time: time
    end_time: time
    location: str
    is_active: Optional[bool] = True


class TeacherAvailabilityUpdate(BaseModel):
    teacher_id: Optional[str] = None
    day: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class TeacherAvailabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    availability_id: int
    teacher_id: str
    day: str
    start_time: time
    end_time: time
    location: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
