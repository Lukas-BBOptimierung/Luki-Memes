from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def list_users(db: AsyncSession, limit: int = 6) -> list[User]:
    """Fetch a few users for the UI preview."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_portal_stats(db: AsyncSession) -> dict[str, int]:
    """Lightweight stats to make the landing page feel alive."""
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    verified_users = await db.scalar(
        select(func.count()).select_from(User).where(User.is_verified.is_(True))
    ) or 0
    active_users = await db.scalar(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    ) or 0

    return {
        "total": int(total_users),
        "verified": int(verified_users),
        "active": int(active_users),
    }
