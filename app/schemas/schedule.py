from typing import Optional
from datetime import time, datetime
from pydantic import BaseModel, ConfigDict


class ScheduleCreate(BaseModel):
    section_id: int
    day: str
    time_start: time
    time_end: time
    classroom: str


class ScheduleUpdate(BaseModel):
    section_id: Optional[int] = None
    day: Optional[str] = None
    time_start: Optional[time] = None
    time_end: Optional[time] = None
    classroom: Optional[str] = None


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    schedule_id: int
    section_id: int
    day: str
    time_start: time
    time_end: time
    classroom: str
