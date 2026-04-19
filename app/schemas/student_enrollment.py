from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


EndOfYearStatusType = Literal["Promoted", "Retained", "Dropped", "Graduated"]


class StudentEnrollmentCreate(BaseModel):
    student_id: int
    grade_level_id: int
    section_id: int
    school_year_id: int
    enrollment_date: Optional[str] = None
    next_grade_level_id: Optional[int] = None
    is_active: bool = True
    end_of_year_status: Optional[EndOfYearStatusType] = None


class StudentEnrollmentWithStudentCreate(BaseModel):
    # --- Student fields ---
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    birth_date: str
    gender: Literal["Male", "Female"]
    address: str
    guardian_first_name: str
    guardian_mid_name: Optional[str] = None
    guardian_last_name: str
    guardian_contact: str
    guardian_relationship: Literal["Parent", "Guardian", "Other"]

    # --- Enrollment fields ---
    grade_level_id: int
    section_id: int
    school_year_id: int
    enrollment_date: Optional[str] = None
    next_grade_level_id: Optional[int] = None
    is_active: bool = True


class StudentEnrollmentUpdate(BaseModel):
    grade_level_id: Optional[int] = None
    section_id: Optional[int] = None
    school_year_id: Optional[int] = None
    next_grade_level_id: Optional[int] = None
    enrollment_date: Optional[str] = None
    is_active: Optional[bool] = None
    end_of_year_status: Optional[EndOfYearStatusType] = None


class StudentEnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enrollment_id: int
    student_id: int
    grade_level_id: int
    section_id: int
    school_year_id: int
    enrolled_by: Optional[UUID]
    next_grade_level_id: Optional[int]
    enrollment_date: Optional[str]
    is_active: bool
    end_of_year_status: Optional[str]