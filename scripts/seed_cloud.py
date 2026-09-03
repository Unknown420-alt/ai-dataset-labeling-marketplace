"""
Seed demo data on cloud (Supabase direct URL) or local.
Usage:
  # cloud (run once after first deploy, uses DIRECT_URL = 5432)
  DIRECT_URL=postgresql+asyncpg://...:5432/... python scripts/seed_cloud.py
  # local
  python scripts/seed_cloud.py
Idempotent — skips if demo users already exist.
"""
import asyncio
import os
import sys

# allow running as `python scripts/seed_cloud.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.security import hash_password  # noqa: E402
from sqlalchemy import select  # noqa: E402


DEMO_USERS = [
    {"email": "owner@demo.com", "password": "ReviewPass123", "role": "OWNER", "name": "Demo Owner"},
    {"email": "labeler@demo.com", "password": "ReviewPass123", "role": "LABELER", "name": "Demo Labeler"},
]


async def main():
    db_url = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL", "")
    masked = db_url.split("@")[-1] if "@" in db_url else "(local .env)"
    print(f"[seed] using DB ...@{masked}")

    async with AsyncSessionLocal() as db:
        for u in DEMO_USERS:
            exists = (await db.execute(select(User).where(User.email == u["email"]))).scalars().first()
            if exists:
                print(f"[seed] skip {u['email']} already exists")
                continue
            user = User(
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
                full_name=u["name"],
            )
            db.add(user)
            print(f"[seed] created {u['email']} / {u['password']}")
        await db.commit()
        print("[seed] done — try login at /api/v1/auth/login")


if __name__ == "__main__":
    asyncio.run(main())
