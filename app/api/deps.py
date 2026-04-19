from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user
from models import Staff


async def require_admin(user: Staff = Depends(get_current_user)) -> Staff:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user


__all__ = ["get_db", "get_current_user", "require_admin", "AsyncSession", "Staff"]
