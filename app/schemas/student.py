from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


GenderType = Literal["Male", "Female"]
RelationshipType = Literal["Parent", "Guardian", "Other"]


class StudentCreate(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    birth_date: str
    gender: GenderType
    address: str
    guardian_first_name: str
    guardian_mid_name: Optional[str] = None
    guardian_last_name: str
    guardian_contact: str
    guardian_relationship: RelationshipType

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        if v not in ("Male", "Female"):
            raise ValueError("gender must be 'Male' or 'Female'.")
        return v

    @field_validator("guardian_relationship")
    @classmethod
    def validate_relationship(cls, v: str) -> str:
        if v not in ("Parent", "Guardian", "Other"):
            raise ValueError("guardian_relationship must be 'Parent', 'Guardian', or 'Other'.")
        return v


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[GenderType] = None
    address: Optional[str] = None
    guardian_first_name: Optional[str] = None
    guardian_mid_name: Optional[str] = None
    guardian_last_name: Optional[str] = None
    guardian_contact: Optional[str] = None
    guardian_relationship: Optional[RelationshipType] = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    login_id: Optional[str]
    first_name: str
    middle_name: Optional[str]
    last_name: str
    birth_date: str
    gender: str
    address: str
    guardian_first_name: str
    guardian_mid_name: Optional[str]
    guardian_last_name: str
    guardian_contact: str
    guardian_relationship: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]