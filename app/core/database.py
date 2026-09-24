import os
import ssl
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings


def normalize_url(url: str) -> str:
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    if not (url.startswith("postgres://") or url.startswith("postgresql://")):
        return url
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    # asyncpg (pinned 0.30) rejects unknown connect kwargs — Neon adds
    # channel_binding and sslmode, so strip both and use an SSL context.
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in ("channel_binding", "sslmode")]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _unverified_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _engine_kwargs(url: str) -> dict:
    kw: dict = {"echo": False}
    if "ssl=require" in url or "sslmode=require" in url:
        kw["connect_args"] = {"ssl": _unverified_ssl_context()}
    if os.environ.get("PYCAPSTONE_TESTING") == "1":
        # Tests hop event loops (fixtures, TestClient portals). A pooled
        # asyncpg connection is pinned to the loop that opened it and blows
        # up with "Event loop is closed" when reused. NullPool opens a fresh
        # connection per session instead — slower, but correct under tests.
        kw["poolclass"] = NullPool
    elif not url.startswith("sqlite"):
        kw.update(pool_size=10, max_overflow=20, pool_pre_ping=True)
    return kw


engine = create_async_engine(
    normalize_url(settings.database_url),
    **_engine_kwargs(settings.database_url),
)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
