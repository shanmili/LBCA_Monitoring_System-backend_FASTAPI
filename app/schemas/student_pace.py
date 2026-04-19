from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


RiskLevelType = Literal["critical", "high", "moderate", "low"]
WarningStatusType = Literal["Critical", "At Risk", "Warning", "On Track"]
TrendType = Literal["declining", "stable", "improving"]


# ---------------------------------------------------------------------------
# StudentPace schemas
# ---------------------------------------------------------------------------

class StudentPaceCreate(BaseModel):
    student_id: int
    enrollment_id: int
    subject: str
    pace_percent: float = 0.0
    paces_behind: int = 0


class StudentPaceUpdate(BaseModel):
    subject: Optional[str] = None
    pace_percent: Optional[float] = None
    paces_behind: Optional[int] = None


class StudentPaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pace_id: int
    student_id: int
    student_name: Optional[str] = None   # populated by service
    enrollment_id: int
    subject: str
    pace_percent: float
    paces_behind: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# EarlyWarning schemas
# ---------------------------------------------------------------------------

class EarlyWarningCreate(BaseModel):
    student_id: int
    enrollment_id: Optional[int] = None
    subject: str
    teacher: str
    risk_level: RiskLevelType
    paces_behind: int = 0
    pace_percent: float = 0.0
    attendance: float = 0.0
    status: WarningStatusType
    trend: TrendType
    last_activity: str = "Today"


class EarlyWarningUpdate(BaseModel):
    subject: Optional[str] = None
    teacher: Optional[str] = None
    risk_level: Optional[RiskLevelType] = None
    paces_behind: Optional[int] = None
    pace_percent: Optional[float] = None
    attendance: Optional[float] = None
    status: Optional[WarningStatusType] = None
    trend: Optional[TrendType] = None
    last_activity: Optional[str] = None


class EarlyWarningOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    warning_id: int
    student_id: int
    student_name: Optional[str] = None   # populated by service
    enrollment_id: Optional[int]
    subject: str
    teacher: str
    risk_level: str
    paces_behind: int
    pace_percent: float
    attendance: float
    status: str
    trend: str
    last_activity: str
    created_at: datetime
    updated_at: datetime