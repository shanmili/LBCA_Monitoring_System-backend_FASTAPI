import re
import hashlib
import random
import uuid
import os
from datetime import datetime, timedelta

from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY                = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM                 = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS   = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# ── password strength rule ─────────────────────────────────────────────────────
# At least 6 characters, 1 uppercase, 1 lowercase, 1 special character.

_PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]).{6,}$'
)

def validate_password_strength(value: str) -> str:
    """
    Raises ValueError if the password does not meet requirements.
    Returns the value unchanged if it passes.
    Used as a Pydantic validator and can also be called directly.
    """
    if not _PASSWORD_PATTERN.match(value):
        raise ValueError(
            "Password must be at least 6 characters and contain "
            "at least one uppercase letter, one lowercase letter, "
            "and one special character (!@#$%^&* etc.)"
        )
    return value


# ── hashing ────────────────────────────────────────────────────────────────────

def _normalize_password(password: str) -> str:
    """
    Pre-hash with SHA-256 before passing to bcrypt.
    Produces a fixed 64-char hex string safely within bcrypt's 72-byte limit
    while preserving full entropy of any-length passwords.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_normalize_password(plain_password), hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(_normalize_password(password))


# ── tokens ─────────────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire    = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire    = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return {}


# ── utilities ──────────────────────────────────────────────────────────────────

def generate_otp() -> str:
    return str(random.randint(100000, 999999))


def generate_device_id(user_agent: str, ip_address: str) -> str:
    data = f"{user_agent}:{ip_address}".encode()
    return hashlib.sha256(data).hexdigest()


def generate_reset_token() -> str:
    return str(uuid.uuid4())


def check_password_reset_lockout(reset_record) -> bool:
    """Returns True if the user is currently locked out of password reset."""
    if reset_record and reset_record.locked_until:
        if datetime.utcnow() < reset_record.locked_until:
            return True
    return False