from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Staff, Session as StaffSession
from auth import decode_token
from datetime import datetime, timezone

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Parent/student tokens bypass the StaffSession table ──────────────
    if payload.get("role") == "parent":
        return Staff(id=payload.get("sub"), role="parent", is_active=True)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(StaffSession).where(
            StaffSession.access_token == token,
            StaffSession.is_active == True,
            StaffSession.expires_at > now,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=401, detail="Session expired or not found")

    if session.last_activity:
        inactive_seconds = (now - session.last_activity).total_seconds()
        timeout_minutes = session.inactivity_timeout_minutes
        if inactive_seconds > timeout_minutes * 60:
            session.is_active = False
            await db.commit()
            raise HTTPException(
                status_code=401,
                detail=f"Session expired due to {timeout_minutes} minutes of inactivity"
            )

    # Update last activity
    session.last_activity = now
    await db.commit()

    result = await db.execute(select(Staff).where(Staff.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def get_current_user_from_refresh(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> tuple[Staff, StaffSession]:
    """
    Validates a REFRESH token specifically.
    Only used by PUT /api/sessions/me.
    Returns (user, session) so the endpoint can rotate both tokens on the
    same session row.
    """
    token = credentials.credentials
    payload = decode_token(token)

    # Must be a refresh token — reject access tokens explicitly
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid refresh token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Match against the refresh_token column, not access_token
    result = await db.execute(
        select(StaffSession).where(
            StaffSession.refresh_token == token,
            StaffSession.is_active == True,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=401, detail="Refresh token invalid or session expired")

    result = await db.execute(select(Staff).where(Staff.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user, session


async def get_current_admin(
    current_user: Staff = Depends(get_current_user),
) -> Staff:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user