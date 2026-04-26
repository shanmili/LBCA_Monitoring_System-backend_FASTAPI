from fastapi import FastAPI, HTTPException, Depends, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import os
from typing import List, Optional

from database import get_db
from models import Staff, StaffDevice, OTPCode, PasswordReset, AuditLog
from schemas import (
    StaffRegisterRequest, StaffLoginRequest, TokenResponse, OTPVerifyRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest,
    StaffResponse, AuditLogResponse
)
from auth import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, generate_otp, check_password_reset_lockout,
    validate_password_strength
)
from dependencies import get_current_user, get_current_admin, get_current_user_from_refresh
from pydantic import BaseModel, field_validator
from app.api.routers import school_years, grade_levels, sections

from fastapi.middleware.cors import CORSMiddleware

from database import Base, async_engine
from models import *

app = FastAPI(title="LBCA API", version="1.0.0")

@app.on_event("startup")
async def startup():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

allowed_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5177",
]

extra = os.getenv("ALLOWED_ORIGINS", "")
if extra:
    allowed_origins += [o.strip() for o in extra.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== LOCKOUT POLICY ====================

LOCKOUT_MINUTES = [30, 60, 120, 240, 480]  # duration per lockout tier
MAX_ATTEMPTS    = 3                         # wrong passwords before a lockout
MAX_LOCKOUTS    = len(LOCKOUT_MINUTES)      # 5 lockouts → permanent lock


# ==================== INLINE SCHEMAS ====================

class UserStatusUpdate(BaseModel):
    account_status:   str                   # "approved" | "rejected" | "active"
    rejection_reason: Optional[str] = None

class PasswordUpdate(BaseModel):
    password:                 str
    requires_password_change: bool = True

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


# ==================== HELPER ====================

async def write_audit(
    db: AsyncSession,
    admin_id,
    target_user_id,
    action: str,
    detail: str = None,
):
    """Insert one audit log row."""
    db.add(AuditLog(
        admin_id=admin_id,
        target_user_id=target_user_id,
        action=action,
        detail=detail,
    ))
    # caller is responsible for db.commit()


# ==============================================================
# TABLE 1 — staff
# POST   /api/users              — register (public)
# GET    /api/users              — list all users (admin)
# GET    /api/users/me           — own profile (authenticated)
# PATCH  /api/users/me           — change own password (authenticated)
# PATCH  /api/users/{id}         — approve / reject / reactivate / force-reset (admin)
# DELETE /api/users/{id}         — soft-delete / deactivate (admin)
# GET    /api/users/audit-logs   — view audit log (admin)
# ==============================================================

@app.post("/api/users", status_code=status.HTTP_201_CREATED, tags=["Public"])
async def register(staff_data: StaffRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Public self-registration — creates a pending staff account."""
    result = await db.execute(select(Staff).where(Staff.email == staff_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_staff = Staff(
        email=staff_data.email,
        password_hash=get_password_hash(staff_data.password),
        first_name=staff_data.first_name,
        last_name=staff_data.last_name,
        middle_name=staff_data.middle_name,
        contact_number=staff_data.contact_number,
        role="teacher",
        account_status="pending",
        is_approved=False,
    )
    db.add(new_staff)
    await db.commit()
    await db.refresh(new_staff)
    return {"message": "Registration successful. Awaiting admin approval.", "user_id": str(new_staff.id)}


@app.get("/api/users", response_model=List[StaffResponse], tags=["Admin"])
async def list_users(
    account_status: Optional[str] = Query(None),
    current_user: Staff = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin — list all staff, optionally filtered by ?account_status=pending."""
    query = select(Staff)
    if account_status:
        query = query.where(Staff.account_status == account_status)
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/api/users/me", response_model=StaffResponse, tags=["Profile"])
async def get_own_profile(current_user: Staff = Depends(get_current_user)):
    """Authenticated user — fetch own profile."""
    return current_user


@app.patch("/api/users/me", tags=["Profile"])
async def change_own_password(
    request: ChangePasswordRequest,
    current_user: Staff = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Authenticated user — change own password."""
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    current_user.password_hash = get_password_hash(request.new_password)
    current_user.requires_password_change = False
    await db.commit()
    return {"message": "Password changed successfully"}


@app.patch("/api/users/{user_id}", tags=["Admin"])
async def update_user(
    user_id: str,
    body: UserStatusUpdate | PasswordUpdate,
    current_user: Staff = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin — update a user record.
    • Send { password }        to force-reset password (also clears any lock).
    • Send { account_status }  to approve / reject / reactivate.
    """
    result = await db.execute(select(Staff).where(Staff.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if isinstance(body, PasswordUpdate):
        target.password_hash             = get_password_hash(body.password)
        target.requires_password_change  = body.requires_password_change
        target.login_attempts            = 0
        target.locked_until              = None
        target.lockout_count             = 0
        target.permanent_lock            = False
        await write_audit(
            db, current_user.id, target.id,
            action="force_reset_password",
            detail=f"requires_password_change={body.requires_password_change}",
        )
        await db.commit()
        return {"message": f"Password updated for {target.email}. All lockouts cleared."}

    # UserStatusUpdate path
    if body.account_status == "approved":
        target.is_approved    = True
        target.account_status = "approved"
        target.is_active      = True
        target.approved_at    = datetime.now(timezone.utc)
        target.approved_by    = current_user.id
        await write_audit(db, current_user.id, target.id, action="approve_user")

    elif body.account_status == "rejected":
        if not body.rejection_reason:
            raise HTTPException(status_code=400, detail="rejection_reason is required")
        target.account_status   = "rejected"
        target.rejection_reason = body.rejection_reason
        target.is_approved      = False
        target.is_active        = False
        await write_audit(
            db, current_user.id, target.id,
            action="reject_user",
            detail=body.rejection_reason,
        )

    elif body.account_status == "active":
        if target.is_active:
            raise HTTPException(status_code=400, detail="User is already active")
        target.is_active      = True
        target.account_status = "approved"
        await write_audit(db, current_user.id, target.id, action="reactivate_user")

    else:
        raise HTTPException(status_code=400, detail="Invalid account_status value")

    await db.commit()
    await db.refresh(target)
    return target


@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"])
async def deactivate_user(
    user_id: str,
    current_user: Staff = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin — soft-delete (mark inactive)."""
    result = await db.execute(select(Staff).where(Staff.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    target.is_active      = False
    target.account_status = "inactive"
    await write_audit(db, current_user.id, target.id, action="deactivate_user")
    await db.commit()


@app.get("/api/users/audit-logs", response_model=List[AuditLogResponse], tags=["Admin"])
async def get_audit_logs(
    target_user_id: Optional[str] = Query(None, description="Filter by the user the action was performed on"),
    action:         Optional[str] = Query(None, description="Filter by action type"),
    current_user:   Staff = Depends(get_current_admin),
    db:             AsyncSession = Depends(get_db),
):
    """
    Admin — view audit logs.
    Optionally filter by ?target_user_id=... or ?action=approve_user etc.
    Results are ordered newest first.
    """
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if target_user_id:
        query = query.where(AuditLog.target_user_id == target_user_id)
    if action:
        query = query.where(AuditLog.action == action)
    result = await db.execute(query)
    return result.scalars().all()


# ==============================================================
# TABLE 2 — sessions
# POST   /api/sessions     — login (create session)
# PUT    /api/sessions/me  — refresh tokens (requires REFRESH token)
# DELETE /api/sessions/me  — logout
# ==============================================================

@app.post("/api/sessions", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def login(login_data: StaffLoginRequest, db: AsyncSession = Depends(get_db)):
    """Create a session (login). Returns tokens or signals that 2FA is required."""
    result = await db.execute(select(Staff).where(Staff.email == login_data.email))
    staff  = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # ── permanent lock ─────────────────────────────────────────────────────────
    if staff.permanent_lock:
        raise HTTPException(
            status_code=403,
            detail="Account permanently locked due to too many failed attempts. Contact your administrator."
        )

    # ── temporary lockout ──────────────────────────────────────────────────────
    if staff.locked_until and staff.locked_until > datetime.now(timezone.utc):
        remaining     = int((staff.locked_until - datetime.now(timezone.utc)).total_seconds() // 60)
        next_duration = LOCKOUT_MINUTES[min(staff.lockout_count, MAX_LOCKOUTS - 1)]
        raise HTTPException(
            status_code=401,
            detail=f"Account locked. Try again in {remaining} minute(s). "
                   f"Warning: next lockout will be {next_duration} minutes."
        )

    # ── approval check ─────────────────────────────────────────────────────────
    if not staff.is_approved:
        raise HTTPException(status_code=403, detail="Account pending admin approval")

    # ── wrong password ─────────────────────────────────────────────────────────
    if not verify_password(login_data.password, staff.password_hash):
        staff.login_attempts += 1

        if staff.login_attempts >= MAX_ATTEMPTS:
            staff.lockout_count += 1

            if staff.lockout_count >= MAX_LOCKOUTS:
                staff.permanent_lock  = True
                staff.login_attempts  = 0
                staff.locked_until    = None
                await db.commit()
                raise HTTPException(
                    status_code=403,
                    detail="Account permanently locked due to too many failed attempts. Contact your administrator."
                )

            duration             = LOCKOUT_MINUTES[staff.lockout_count - 1]
            staff.locked_until   = datetime.now(timezone.utc) + timedelta(minutes=duration)
            staff.login_attempts = 0
            await db.commit()
            raise HTTPException(
                status_code=401,
                detail=f"Too many failed attempts. Account locked for {duration} minutes "
                       f"(lockout {staff.lockout_count}/{MAX_LOCKOUTS})."
            )

        await db.commit()
        attempts_left = MAX_ATTEMPTS - staff.login_attempts
        raise HTTPException(
            status_code=401,
            detail=f"Invalid credentials. {attempts_left} attempt(s) remaining before lockout."
        )

    # ── successful login — reset all lockout state ─────────────────────────────
    staff.login_attempts = 0
    staff.locked_until   = None
    staff.lockout_count  = 0
    await db.commit()

    # ── device / 2FA check ─────────────────────────────────────────────────────
    result = await db.execute(
        select(StaffDevice).where(
            StaffDevice.staff_id == staff.id,
            StaffDevice.device_id == login_data.device_id,
            StaffDevice.is_trusted == True,
        )
    )
    device = result.scalar_one_or_none()

    requires_2fa = not device
    if device and device.last_2fa_verified:
        days_since = (datetime.now(timezone.utc) - device.last_2fa_verified).days
        if days_since >= int(os.getenv("TWO_FACTOR_DAYS_INTERVAL", 90)):
            requires_2fa = True

    if requires_2fa:
        otp_code   = generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=int(os.getenv("OTP_EXPIRY_MINUTES", 10))
        )
        db.add(OTPCode(staff_id=staff.id, code=otp_code, purpose="login", expires_at=expires_at))
        await db.commit()
        print(f"OTP for {staff.email}: {otp_code}", flush=True)
        return TokenResponse(requires_2fa=True, user_id=str(staff.id))

    access_token  = create_access_token({"sub": str(staff.id)})
    refresh_token = create_refresh_token({"sub": str(staff.id)})
    expires_at    = datetime.now(timezone.utc) + timedelta(
        minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    )

    if not device:
        device = StaffDevice(
            staff_id=staff.id,
            device_id=login_data.device_id,
            device_name=login_data.device_name,
            is_trusted=True,
            last_2fa_verified=datetime.now(timezone.utc),
        )
        db.add(device)
        await db.flush()

    from models import Session as StaffSession
    db.add(StaffSession(
        staff_id=staff.id,
        device_id=device.id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    ))
    await db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@app.put("/api/sessions/me", response_model=TokenResponse, tags=["Authentication"])
async def refresh_session(
    user_and_session: tuple = Depends(get_current_user_from_refresh),
    db: AsyncSession = Depends(get_db),
):
    """
    Replace session tokens.
    IMPORTANT: Send the REFRESH token in the Authorization header here,
    not the access token.
    """
    current_user, session = user_and_session

    access_token  = create_access_token({"sub": str(current_user.id)})
    refresh_token = create_refresh_token({"sub": str(current_user.id)})
    expires_at    = datetime.now(timezone.utc) + timedelta(
        minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    )
    session.access_token  = access_token
    session.refresh_token = refresh_token
    session.expires_at    = expires_at
    await db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@app.delete("/api/sessions/me", status_code=status.HTTP_204_NO_CONTENT, tags=["Authentication"])
async def logout(
    current_user: Staff = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invalidate all active sessions (logout)."""
    from models import Session as StaffSession

    result = await db.execute(
        select(StaffSession).where(
            StaffSession.staff_id == current_user.id,
            StaffSession.is_active == True,
        )
    )
    for session in result.scalars().all():
        session.is_active = False
    await db.commit()


# ==============================================================
# TABLE 3 — otp_codes
# POST  /api/otp  — verify login OTP and complete session creation
# ==============================================================

@app.post("/api/otp", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def verify_otp(verify_data: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    """Verify a login OTP and issue tokens (completes 2FA login)."""
    result = await db.execute(
        select(OTPCode).where(
            OTPCode.staff_id == verify_data.user_id,
            OTPCode.code == verify_data.code,
            OTPCode.purpose == "login",
            OTPCode.is_used == False,
            OTPCode.expires_at > datetime.now(timezone.utc),
        )
    )
    otp = result.scalar_one_or_none()
    if not otp:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")

    otp.is_used = True
    await db.commit()

    result = await db.execute(
        select(StaffDevice).where(
            StaffDevice.staff_id == verify_data.user_id,
            StaffDevice.device_id == verify_data.device_id,
        )
    )
    device = result.scalar_one_or_none()

    if device:
        device.last_used         = datetime.now(timezone.utc)
        device.last_2fa_verified = datetime.now(timezone.utc)
    else:
        device = StaffDevice(
            staff_id=verify_data.user_id,
            device_id=verify_data.device_id,
            device_name=verify_data.device_name,
            is_trusted=True,
            last_2fa_verified=datetime.now(timezone.utc),
        )
        db.add(device)
        await db.flush()

    result = await db.execute(select(Staff).where(Staff.id == verify_data.user_id))
    staff  = result.scalar_one()

    access_token  = create_access_token({"sub": str(staff.id)})
    refresh_token = create_refresh_token({"sub": str(staff.id)})
    expires_at    = datetime.now(timezone.utc) + timedelta(
        minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    )

    from models import Session as StaffSession
    db.add(StaffSession(
        staff_id=staff.id,
        device_id=device.id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    ))
    await db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# ==============================================================
# TABLE 4 — password_resets
# POST   /api/password-reset  — request OTP (forgot password)
# PATCH  /api/password-reset  — verify OTP and apply new password
# ==============================================================

@app.post("/api/password-reset", status_code=status.HTTP_202_ACCEPTED, tags=["Password Reset"])
async def request_password_reset(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send a password-reset OTP to the user's registered contact."""
    result = await db.execute(select(Staff).where(Staff.email == request.email))
    staff  = result.scalar_one_or_none()

    if not staff:
        return {"message": "If that email exists, an OTP will be sent"}

    result       = await db.execute(select(PasswordReset).where(PasswordReset.staff_id == staff.id))
    reset_record = result.scalar_one_or_none()

    if not reset_record:
        reset_record = PasswordReset(staff_id=staff.id)
        db.add(reset_record)
        await db.commit()
        await db.refresh(reset_record)

    if check_password_reset_lockout(reset_record):
        remaining = (reset_record.locked_until - datetime.now(timezone.utc)).seconds // 60
        raise HTTPException(status_code=429, detail=f"Too many attempts. Try again in {remaining} minutes")

    if reset_record.window_start:
        hours_since = (datetime.now(timezone.utc) - reset_record.window_start).total_seconds() / 3600
        if hours_since > 24:
            reset_record.request_count = 1
            reset_record.window_start  = datetime.now(timezone.utc)
        else:
            reset_record.request_count += 1

    max_attempts = int(os.getenv("MAX_PASSWORD_RESET_ATTEMPTS", 3))
    if reset_record.request_count > max_attempts:
        reset_record.locked_until = datetime.now(timezone.utc) + timedelta(
            hours=24
        )
        await db.commit()
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in 30 minutes")

    await db.commit()

    otp_code   = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv("OTP_EXPIRY_MINUTES", 10)))
    otp = OTPCode(
        staff_id=staff.id,
        code=otp_code,
        purpose="password_reset",
        expires_at=expires_at,
    )
    db.add(otp)
    await db.commit()
    await db.refresh(otp)

    print(f"PASSWORD RESET OTP for {staff.email}: {otp_code}", flush=True)
    return {"message": "OTP sent to your email/phone"}


@app.patch("/api/password-reset", tags=["Password Reset"])
async def apply_password_reset(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db), tags=["Password Reset"]):
    """Verify OTP token and set the new password."""
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    result = await db.execute(
        select(OTPCode).where(
            OTPCode.code == request.token,
            OTPCode.purpose == "password_reset",
            OTPCode.is_used == False,
            OTPCode.expires_at > datetime.now(timezone.utc),
        )
    )
    otp = result.scalar_one_or_none()
    if not otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    result = await db.execute(select(Staff).where(Staff.id == otp.staff_id))
    staff  = result.scalar_one()

    staff.password_hash            = get_password_hash(request.new_password)
    staff.requires_password_change = False
    staff.login_attempts           = 0
    staff.locked_until             = None
    staff.lockout_count            = 0
    staff.permanent_lock           = False
    otp.is_used = True

    result       = await db.execute(select(PasswordReset).where(PasswordReset.staff_id == staff.id))
    reset_record = result.scalar_one_or_none()
    if reset_record:
        reset_record.request_count = 0
        reset_record.window_start  = None
        reset_record.locked_until  = None
        reset_record.reset_token   = None
        reset_record.token_expires = None

    await db.commit()
    return {"message": "Password reset successful. You can now login."}

@app.post("/api/password-reset/validate-otp", tags=["Password Reset"])
async def validate_reset_otp(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Validate password reset OTP before showing password form."""
    body = await request.json()
    email = body.get("email")
    code = body.get("code")
    
    if not email or not code:
        raise HTTPException(status_code=400, detail="Email and code are required")
    
    # Find user
    result = await db.execute(select(Staff).where(Staff.email == email))
    staff = result.scalar_one_or_none()
    
    if not staff:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Find valid OTP
    result = await db.execute(
        select(OTPCode).where(
            OTPCode.staff_id == staff.id,
            OTPCode.code == code,
            OTPCode.purpose == "password_reset",
            OTPCode.is_used == False,
            OTPCode.expires_at > datetime.now(timezone.utc),
        )
    )
    otp = result.scalar_one_or_none()
    
    if not otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    return {"valid": True, "message": "OTP verified successfully"}

# ==============================================================
# TABLE 5 — staff_devices
# Managed internally by /api/sessions and /api/otp.
# No direct public endpoint needed.
# ==============================================================

# Academic module routers
app.include_router(school_years.router)
app.include_router(grade_levels.router)
app.include_router(sections.router)

from app.api.routers import students, student_enrollments, student_pace
app.include_router(students.router)
app.include_router(student_enrollments.router)
app.include_router(student_pace.router)

from app.api.routers import subjects, schedules, teacher_availabilities, data_quality_logs
app.include_router(subjects.router)
app.include_router(schedules.router)
app.include_router(teacher_availabilities.router)
app.include_router(data_quality_logs.router)