"""
activity_log.py — thin helper that writes to the existing AuditLog table
for EVERY significant event: login, logout, data mutations, etc.

Usage inside any route:
    from activity_log import log_event
    await log_event(db, actor_id=staff.id, action="login_success",
                    detail="device=iPhone 13", ip=request.client.host)
"""

from __future__ import annotations
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models import AuditLog


# Full list of action strings used across the codebase.
# Add new ones here as you expand — having them in one place prevents typos.
class Action:
    # Auth
    LOGIN_SUCCESS      = "login_success"
    LOGIN_FAILED       = "login_failed"
    LOGOUT             = "logout"
    OTP_VERIFIED       = "otp_verified"
    TOKEN_REFRESHED    = "token_refreshed"
    ACCOUNT_LOCKED     = "account_locked"
    ACCOUNT_PERM_LOCK  = "account_permanently_locked"
    PASSWORD_RESET_REQ = "password_reset_requested"
    PASSWORD_RESET_OK  = "password_reset_applied"
    PASSWORD_CHANGED   = "password_changed"

    # User management (already existed)
    APPROVE_USER        = "approve_user"
    REJECT_USER         = "reject_user"
    DEACTIVATE_USER     = "deactivate_user"
    REACTIVATE_USER     = "reactivate_user"
    FORCE_RESET_PASSWORD = "force_reset_password"

    # Academic data mutations
    STUDENT_CREATED    = "student_created"
    STUDENT_UPDATED    = "student_updated"
    STUDENT_DELETED    = "student_deleted"
    SECTION_CREATED    = "section_created"
    SECTION_UPDATED    = "section_updated"
    SECTION_DELETED    = "section_deleted"
    SCHEDULE_CREATED   = "schedule_created"
    SCHEDULE_UPDATED   = "schedule_updated"
    SCHEDULE_DELETED   = "schedule_deleted"
    ENROLLMENT_CREATED = "enrollment_created"
    ENROLLMENT_UPDATED = "enrollment_updated"
    ENROLLMENT_DELETED = "enrollment_deleted"


async def log_event(
    db:            AsyncSession,
    action:        str,
    actor_id=None,          # UUID of the staff member doing the action (None = system)
    target_user_id=None,    # UUID of the staff row being affected (if any)
    detail:        Optional[str] = None,
    ip:            Optional[str] = None,
) -> None:
    """
    Insert one row into audit_logs.
    The caller must commit the session afterwards (or the surrounding
    route already commits — then this row goes along with it).
    """
    detail_parts = []
    if detail:
        detail_parts.append(detail)
    if ip:
        detail_parts.append(f"ip={ip}")

    db.add(AuditLog(
        admin_id=actor_id,
        target_user_id=target_user_id,
        action=action,
        detail="; ".join(detail_parts) if detail_parts else None,
    ))
