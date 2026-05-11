from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import uuid


class Staff(Base):
    __tablename__ = "staff"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email                    = Column(String(255), unique=True, nullable=False, index=True)
    password_hash            = Column(String(255), nullable=False)
    first_name               = Column(String(100), nullable=False)
    last_name                = Column(String(100), nullable=False)
    middle_name              = Column(String(100), nullable=True)
    contact_number           = Column(String(20), nullable=False)
    role                     = Column(String(20), nullable=False)
    profile_pic              = Column(Text, nullable=True)
    account_status           = Column(String(20), nullable=False, default="pending")
    rejection_reason         = Column(Text, nullable=True)
    is_active                = Column(Boolean, default=True)
    is_approved              = Column(Boolean, default=False)
    requires_password_change = Column(Boolean, default=False)
    login_attempts           = Column(Integer, default=0)
    locked_until             = Column(DateTime(timezone=True), nullable=True)
    lockout_count            = Column(Integer, default=0)
    permanent_lock           = Column(Boolean, default=False)
    approved_at              = Column(DateTime(timezone=True), nullable=True)
    approved_by              = Column(UUID(as_uuid=True), nullable=True)
    created_at               = Column(DateTime(timezone=True), server_default=func.now())
    updated_at               = Column(DateTime(timezone=True), onupdate=func.now())

    devices         = relationship("StaffDevice", back_populates="staff", cascade="all, delete-orphan")
    sessions        = relationship("Session", back_populates="staff", cascade="all, delete-orphan")
    otp_codes       = relationship("OTPCode", back_populates="staff", cascade="all, delete-orphan")
    password_resets = relationship("PasswordReset", back_populates="staff", cascade="all, delete-orphan")
    audit_logs      = relationship("AuditLog", foreign_keys="AuditLog.target_user_id", back_populates="target_user", cascade="all, delete-orphan")


class StaffDevice(Base):
    __tablename__ = "staff_devices"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id          = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    device_id         = Column(String(255), nullable=False)
    device_name       = Column(String(255), nullable=True)
    ip_address        = Column(INET, nullable=True)
    user_agent        = Column(Text, nullable=True)
    last_used         = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_trusted        = Column(Boolean, default=True)
    last_2fa_verified = Column(DateTime(timezone=True), nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    staff    = relationship("Staff", back_populates="devices")
    sessions = relationship("Session", back_populates="device", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_staff_devices_staff_id", "staff_id"),
        Index("ix_staff_devices_device_id", "device_id"),
    )


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id   = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    code       = Column(String(6), nullable=False)
    purpose    = Column(String(20), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used    = Column(Boolean, default=False)
    attempts   = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    staff = relationship("Staff", back_populates="otp_codes")

    __table_args__ = (
        Index("ix_otp_codes_staff_id", "staff_id"),
        Index("ix_otp_codes_expires_at", "expires_at"),
    )


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id      = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    request_count = Column(Integer, default=1)
    window_start  = Column(DateTime(timezone=True), server_default=func.now())
    locked_until  = Column(DateTime(timezone=True), nullable=True)
    reset_token   = Column(String(255), unique=True, nullable=True)
    token_expires = Column(DateTime(timezone=True), nullable=True)
    is_admin_reset = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    staff = relationship("Staff", back_populates="password_resets")

    __table_args__ = (
        Index("ix_password_resets_staff_id", "staff_id"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id                        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id                  = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    device_id                 = Column(UUID(as_uuid=True), ForeignKey("staff_devices.id", ondelete="CASCADE"), nullable=False)
    access_token              = Column(Text, nullable=False)
    refresh_token             = Column(Text, nullable=False)
    expires_at                = Column(DateTime(timezone=True), nullable=False)
    last_activity             = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active                 = Column(Boolean, default=True)
    inactivity_timeout_minutes = Column(Integer, default=10)
    created_at                = Column(DateTime(timezone=True), server_default=func.now())

    staff  = relationship("Staff", back_populates="sessions")
    device = relationship("StaffDevice", back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_staff_id", "staff_id"),
        Index("ix_sessions_device_id", "device_id"),
        Index("ix_sessions_refresh_token", "refresh_token"),
        Index("ix_sessions_last_activity", "last_activity"),
    )


# ==============================================================
# AuditLog — records every admin action
#
# action values:
#   "approve_user"        — admin approved a registration
#   "reject_user"         — admin rejected a registration
#   "deactivate_user"     — admin soft-deleted a user
#   "reactivate_user"     — admin restored a deactivated user
#   "force_reset_password"— admin set a temp password for a user
# ==============================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id       = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    target_user_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    action         = Column(String(50), nullable=False)
    detail         = Column(Text, nullable=True)   # extra context, e.g. rejection reason
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    # admin who performed the action
    admin       = relationship("Staff", foreign_keys=[admin_id])
    # user the action was performed on
    target_user = relationship("Staff", foreign_keys=[target_user_id], back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_admin_id", "admin_id"),
        Index("ix_audit_logs_target_user_id", "target_user_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

# ==============================================================
# ClassSchedule — connects teachers, subjects, and sections for scheduling
# ==============================================================

class ClassSchedule(Base):
    __tablename__ = "class_schedules"

    class_schedule_id = Column(Integer, primary_key=True, index=True)
    school_year_id = Column(Integer, nullable=False, index=True)  # References school_years table
    section_id = Column(Integer, nullable=False, index=True)  # References sections table
    subject_id = Column(Integer, nullable=False, index=True)  # References subjects table
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(String(20), nullable=False)  # Monday, Tuesday, Wednesday, Thursday, Friday
    start_time = Column(String(10), nullable=False)   # HH:MM format (e.g., "08:00")
    end_time = Column(String(10), nullable=False)     # HH:MM format (e.g., "09:00")
    room = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    teacher = relationship("Staff", foreign_keys=[teacher_id])

    __table_args__ = (
        # Prevent duplicate schedules for same section at same time
        Index("ix_class_schedules_section_day_time", "section_id", "day_of_week", "start_time"),
        # Prevent teacher from being double-booked
        Index("ix_class_schedules_teacher_day_time", "teacher_id", "day_of_week", "start_time"),
        # Prevent same teacher from teaching same subject in same section
        Index("ix_class_schedules_teacher_subject_section", "teacher_id", "subject_id", "section_id", "school_year_id"),
    )