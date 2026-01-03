import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Fallback für lokale Entwicklung, später per ENV überschrieben
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Für Async Treiber umschreiben, damit postgres (psycopg2) / sqlite ohne Anpassung laufen
if DATABASE_URL.startswith("postgresql+psycopg2"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2", "postgresql+asyncpg", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine, autocommit=False, autoflush=False, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
