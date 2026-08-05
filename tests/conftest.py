"""Test fixtures.

Points the app at a throwaway SQLite database so test runs never touch the
real dev database (marketplace.db). Env vars must be set before the app is
imported, hence the top-of-file assignment.
"""
import os
import asyncio

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_marketplace.db"

import pytest

from app.core.database import engine, Base
import app.models  # noqa: F401  (register all tables on Base.metadata)


@pytest.fixture(scope="session", autouse=True)
def _fresh_database():
    async def create_all():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_all())
    yield
    asyncio.run(engine.dispose())

    try:
        os.remove("test_marketplace.db")
    except OSError:
        pass