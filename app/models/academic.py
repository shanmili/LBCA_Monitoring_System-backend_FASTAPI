from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class SchoolYear(Base):
    __tablename__ = "school_years"

    school_year_id = Column(Integer, primary_key=True, index=True)
    year = Column(String(20), unique=True, nullable=False, index=True)
    is_current = Column(Boolean, default=False, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)


class GradeLevel(Base):
    __tablename__ = "grade_levels"

    grade_level_id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(20), nullable=False)

    sections = relationship("Section", back_populates="grade_level")


class Section(Base):
    __tablename__ = "sections"

    section_id = Column(Integer, primary_key=True, index=True)
    grade_level_id = Column(Integer, ForeignKey("grade_levels.grade_level_id", ondelete="CASCADE"), nullable=False, index=True)
    section_code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(30), nullable=False)

    grade_level = relationship("GradeLevel", back_populates="sections")


class Subject(Base):
    __tablename__ = "subjects"

    subject_id = Column(Integer, primary_key=True, index=True)
    grade_level_id = Column(Integer, ForeignKey("grade_levels.grade_level_id", ondelete="CASCADE"), nullable=False, index=True)
    subject_name = Column(String(255), nullable=False, index=True)
    subject_code = Column(String(50), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    grade_level = relationship("GradeLevel", backref="subjects")


class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"

    assignment_id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    teacher = relationship("Staff", backref="assignments")
    section = relationship("Section", backref="teacher_assignments")
