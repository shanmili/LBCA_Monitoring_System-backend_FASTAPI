import re
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


# ── shared password rule ───────────────────────────────────────────────────────
# At least 6 characters, 1 uppercase, 1 lowercase, 1 special character.

PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]).{6,}$'
)

def validate_password_strength(value: str) -> str:
    if not PASSWORD_PATTERN.match(value):
        raise ValueError(
            "Password must be at least 6 characters and contain "
            "at least one uppercase letter, one lowercase letter, "
            "and one special character (!@#$%^&* etc.)"
        )
    return value


# ── request schemas ────────────────────────────────────────────────────────────

class StaffRegisterRequest(BaseModel):
    email:          EmailStr
    password:       str
    first_name:     str
    last_name:      str
    middle_name:    Optional[str] = None
    contact_number: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class StaffLoginRequest(BaseModel):
    email:       EmailStr
    password:    str
    device_id:   str
    device_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token:  Optional[str] = None   # None when requires_2fa=True
    refresh_token: Optional[str] = None   # None when requires_2fa=True
    token_type:    str = "bearer"
    requires_2fa:  bool = False
    user_id:       Optional[str] = None
    debug_otp:     Optional[str] = None


class OTPVerifyRequest(BaseModel):
    user_id:     str
    code:        str
    device_id:   str
    device_name: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token:            str
    new_password:     str
    confirm_password: str

    @field_validator("new_password")
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


class AdminResetPasswordRequest(BaseModel):
    user_id:       str
    temp_password: str

    @field_validator("temp_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)


class StaffResponse(BaseModel):
    id:             UUID
    email:          EmailStr
    first_name:     str
    last_name:      str
    role:           str
    account_status: str
    is_approved:    bool
    created_at:     datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id:             UUID
    admin_id:       Optional[UUID]
    target_user_id: Optional[UUID]
    action:         str
    detail:         Optional[str]
    created_at:     datetime

    class Config:
        from_attributes = True