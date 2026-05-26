from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class Student(Base):
    __tablename__ = "students"

    student_id = Column(Integer, primary_key=True, index=True)
    # Login ID (e.g. S001) – stored here after creation
    login_id = Column(String(20), unique=True, nullable=True, index=True)

    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=False)
    birth_date = Column(String(15), nullable=False)
    gender = Column(String(10), nullable=False)           # Male | Female
    address = Column(String(255), nullable=False)

    guardian_first_name = Column(String(50), nullable=False)
    guardian_mid_name = Column(String(50), nullable=True)
    guardian_last_name = Column(String(50), nullable=False)
    guardian_contact = Column(String(15), nullable=False)
    guardian_relationship = Column(String(10), nullable=False)     # Parent | Guardian | Other

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    # FK to the Staff who created this student record
    created_by = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)

    enrollments = relationship("StudentEnrollment", back_populates="student", cascade="all, delete-orphan")
    paces = relationship("StudentPace", back_populates="student", cascade="all, delete-orphan")
    early_warnings = relationship("EarlyWarning", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Student {self.last_name}, {self.first_name}>"


class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"

    enrollment_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    grade_level_id = Column(
        Integer,
        ForeignKey("grade_levels.grade_level_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    section_id = Column(
        Integer,
        ForeignKey("sections.section_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    school_year_id = Column(
        Integer,
        ForeignKey("school_years.school_year_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    enrolled_by = Column(
        UUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
    next_grade_level_id = Column(
        Integer,
        ForeignKey("grade_levels.grade_level_id", ondelete="SET NULL"),
        nullable=True,
    )
    enrollment_date = Column(String(20), nullable=True)   # stored as ISO date string
    is_active = Column(Boolean, default=True, nullable=False)
    # Promoted | Retained | Dropped | Graduated
    end_of_year_status = Column(String(20), nullable=True)

    student = relationship("Student", back_populates="enrollments")
    grade_level = relationship(
        "GradeLevel",
        foreign_keys=[grade_level_id],
        backref="enrollments",
    )
    next_grade_level = relationship(
        "GradeLevel",
        foreign_keys=[next_grade_level_id],
    )
    section = relationship("Section", backref="enrollments")
    school_year = relationship("SchoolYear", backref="enrollments")
    paces = relationship("StudentPace", back_populates="enrollment", cascade="all, delete-orphan")
    early_warnings = relationship("EarlyWarning", back_populates="enrollment", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<StudentEnrollment student_id={self.student_id} school_year_id={self.school_year_id}>"


class StudentPace(Base):
    __tablename__ = "student_paces"

    pace_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrollment_id = Column(
        Integer,
        ForeignKey("student_enrollments.enrollment_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject = Column(String(100), nullable=False)
    pace_percent = Column(Float, default=0.0, nullable=False)   # % of curriculum completed
    paces_behind = Column(Integer, default=0, nullable=False)   # number of paces behind standard

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="paces")
    enrollment = relationship("StudentEnrollment", back_populates="paces")

    def __repr__(self) -> str:
        return f"<StudentPace student_id={self.student_id} subject={self.subject} pace={self.pace_percent}%>"


class EarlyWarning(Base):
    __tablename__ = "early_warnings"

    warning_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrollment_id = Column(
        Integer,
        ForeignKey("student_enrollments.enrollment_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    subject = Column(String(100), nullable=False)
    teacher = Column(String(100), nullable=False)
    risk_level = Column(String(20), nullable=False)   # critical | high | moderate | low
    paces_behind = Column(Integer, default=0, nullable=False)
    pace_percent = Column(Float, default=0.0, nullable=False)
    attendance = Column(Float, default=0.0, nullable=False)     # attendance %
    status = Column(String(20), nullable=False)                 # Critical | At Risk | Warning | On Track
    trend = Column(String(20), nullable=False)                  # declining | stable | improving
    last_activity = Column(String(100), default="Today", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="early_warnings")
    enrollment = relationship("StudentEnrollment", back_populates="early_warnings")

    def __repr__(self) -> str:
        return f"<EarlyWarning student_id={self.student_id} subject={self.subject} risk={self.risk_level}>"