from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MemeTemplate(Base):
    __tablename__ = "meme_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(length=200), nullable=False)
    file_path: Mapped[str] = mapped_column(String(length=512), nullable=False)
    original_name: Mapped[Optional[str]] = mapped_column(
        String(length=255), nullable=True
    )
    uploaded_by: Mapped[str] = mapped_column(String(length=120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Meme(Base):
    __tablename__ = "memes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(length=200), nullable=False)
    file_path: Mapped[str] = mapped_column(String(length=512), nullable=False)
    original_name: Mapped[Optional[str]] = mapped_column(
        String(length=255), nullable=True
    )
    uploaded_by: Mapped[str] = mapped_column(String(length=120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MemeReaction(Base):
    __tablename__ = "meme_reactions"
    __table_args__ = (
        UniqueConstraint("meme_id", "user_name", name="uq_meme_reaction"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meme_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("memes.id", ondelete="cascade"), nullable=False
    )
    user_name: Mapped[str] = mapped_column(String(length=120), nullable=False)
    reaction: Mapped[str] = mapped_column(String(length=8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
