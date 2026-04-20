from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class Schedule(Base):
    __tablename__ = "schedules"

    schedule_id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False, index=True)
    day = Column(String(20), nullable=False)
    time_start = Column(Time, nullable=False)
    time_end = Column(Time, nullable=False)
    classroom = Column(String(50), nullable=False)

    section = relationship("Section", backref="schedules")


class TeacherAvailability(Base):
    __tablename__ = "teacher_availabilities"

    availability_id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    day = Column(String(20), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    location = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    teacher = relationship("Staff", backref="availabilities")


class DataQualityLog(Base):
    __tablename__ = "data_quality_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True, index=True)
    student_pace_id = Column(Integer, ForeignKey("student_paces.pace_id", ondelete="SET NULL"), nullable=True, index=True)
    issue_type = Column(String(100), nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    resolved_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = relationship("Student", backref="quality_logs")
    teacher = relationship("Staff", backref="quality_logs")
    student_pace = relationship("StudentPace", backref="quality_logs")
