from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings


def _engine_kwargs(url: str) -> dict:
    kw: dict = {"echo": False}
    if "ssl=require" in url:
        kw["connect_args"] = {"ssl": True}
    if not url.startswith("sqlite"):
        kw.update(pool_size=10, max_overflow=20, pool_pre_ping=True)
    return kw


engine = create_async_engine(settings.database_url, **_engine_kwargs(settings.database_url))
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
