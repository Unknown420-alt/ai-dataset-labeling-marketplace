"""Test fixtures.

Points the app at a throwaway SQLite database so test runs never touch the
real dev database (marketplace.db). Env vars must be set before the app is
imported, hence the top-of-file assignment.
"""

import os
import asyncio
import shutil

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_marketplace.db")
os.environ["PYCAPSTONE_TESTING"] = "1"

import pytest

from app.core.database import engine, Base
import app.models  # noqa: F401  (register all tables on Base.metadata)


@pytest.fixture(autouse=True)
def _dev_mail_only(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.smtp_host", "")
    monkeypatch.setattr("app.core.config.settings.smtp_user", "")


@pytest.fixture(scope="session", autouse=True)
def _fresh_database():
    from app.services import training as training_svc

    training_svc.clear_cache()
    shutil.rmtree(training_svc.MODEL_DIR, ignore_errors=True)

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
