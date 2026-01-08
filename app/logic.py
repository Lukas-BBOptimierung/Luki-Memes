from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Meme, MemeReaction, MemeTemplate


async def list_templates(db: AsyncSession) -> list[MemeTemplate]:
    result = await db.execute(
        select(MemeTemplate).order_by(MemeTemplate.created_at.desc())
    )
    return list(result.scalars().all())


async def list_memes(db: AsyncSession) -> list[Meme]:
    result = await db.execute(select(Meme).order_by(Meme.created_at.desc()))
    return list(result.scalars().all())


async def get_template(
    db: AsyncSession, template_id: int
) -> Optional[MemeTemplate]:
    result = await db.execute(
        select(MemeTemplate).where(MemeTemplate.id == template_id)
    )
    return result.scalars().first()


async def get_meme(db: AsyncSession, meme_id: int) -> Optional[Meme]:
    result = await db.execute(select(Meme).where(Meme.id == meme_id))
    return result.scalars().first()


async def create_template(
    db: AsyncSession,
    title: str,
    file_path: str,
    original_name: Optional[str],
    uploaded_by: str,
) -> MemeTemplate:
    template = MemeTemplate(
        title=title,
        file_path=file_path,
        original_name=original_name,
        uploaded_by=uploaded_by,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def create_meme(
    db: AsyncSession,
    title: str,
    file_path: str,
    original_name: Optional[str],
    uploaded_by: str,
) -> Meme:
    meme = Meme(
        title=title,
        file_path=file_path,
        original_name=original_name,
        uploaded_by=uploaded_by,
    )
    db.add(meme)
    await db.commit()
    await db.refresh(meme)
    return meme


async def get_meme_stats(db: AsyncSession) -> dict[str, int]:
    template_count = (
        await db.scalar(select(func.count()).select_from(MemeTemplate)) or 0
    )
    meme_count = await db.scalar(select(func.count()).select_from(Meme)) or 0
    return {"templates": int(template_count), "memes": int(meme_count)}


async def get_reaction_counts(
    db: AsyncSession, meme_ids: list[int]
) -> dict[int, dict[str, int]]:
    if not meme_ids:
        return {}
    result = await db.execute(
        select(MemeReaction.meme_id, MemeReaction.reaction, func.count())
        .where(MemeReaction.meme_id.in_(meme_ids))
        .group_by(MemeReaction.meme_id, MemeReaction.reaction)
    )
    counts: dict[int, dict[str, int]] = {}
    for meme_id, reaction, count in result.all():
        counts.setdefault(meme_id, {"like": 0, "dislike": 0})
        counts[meme_id][reaction] = int(count)
    for meme_id in meme_ids:
        counts.setdefault(meme_id, {"like": 0, "dislike": 0})
    return counts


async def get_user_reactions(
    db: AsyncSession, meme_ids: list[int], user_name: str
) -> dict[int, str]:
    if not meme_ids:
        return {}
    result = await db.execute(
        select(MemeReaction.meme_id, MemeReaction.reaction).where(
            MemeReaction.meme_id.in_(meme_ids),
            MemeReaction.user_name == user_name,
        )
    )
    return {meme_id: reaction for meme_id, reaction in result.all()}


async def set_reaction(
    db: AsyncSession, meme_id: int, user_name: str, reaction: str
) -> None:
    result = await db.execute(
        select(MemeReaction).where(
            MemeReaction.meme_id == meme_id,
            MemeReaction.user_name == user_name,
        )
    )
    existing = result.scalars().first()
    if existing:
        if existing.reaction == reaction:
            return
        existing.reaction = reaction
        await db.commit()
        return
    db.add(
        MemeReaction(
            meme_id=meme_id,
            user_name=user_name,
            reaction=reaction,
        )
    )
    await db.commit()
