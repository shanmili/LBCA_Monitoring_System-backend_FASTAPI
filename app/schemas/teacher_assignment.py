from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class TeacherAssignmentCreate(BaseModel):
    teacher_id: UUID
    section_id: int


class TeacherAssignmentUpdate(BaseModel):
    teacher_id: Optional[UUID] = None
    section_id: Optional[int] = None


class TeacherAssignmentOut(BaseModel):
    assignment_id: int
    teacher_id: UUID
    section_id: int
    teacher_name: Optional[str] = None
    section_code: Optional[str] = None
    section_name: Optional[str] = None

    class Config:
        from_attributes = True
