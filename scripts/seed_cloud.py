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
import csv
import os
import sys
from pathlib import Path

# allow running as `python scripts/seed_cloud.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.dataset import Dataset, DatasetStatus  # noqa: E402
from app.models.task import LabelTask, TaskStatus  # noqa: E402
from app.models.data_item import DataItem  # noqa: E402
from app.services.security import hash_password  # noqa: E402
from sqlalchemy import select  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

DEMO_USERS = [
    {"email": "owner@demo.com", "password": "ReviewPass123", "role": "OWNER", "name": "Demo Owner"},
    {"email": "labeler@demo.com", "password": "ReviewPass123", "role": "LABELER", "name": "Demo Labeler"},
]

DEMO_DATASETS = [
    {
        "csv": "sentiment.csv",
        "name": "Sentiment Analysis",
        "description": "Product and service sentiment classification (positive/negative/neutral)",
        "labels": ["positive", "negative", "neutral"],
        "task_title": "Label Sentiment",
        "task_instructions": "Read each text and assign a sentiment label: positive, negative, or neutral.",
    },
    {
        "csv": "spam.csv",
        "name": "Email Spam Detection",
        "description": "Classify emails and messages as spam or legitimate",
        "labels": ["spam", "not-spam"],
        "task_title": "Label Spam",
        "task_instructions": "Read each message and mark it as spam or not-spam.",
    },
    {
        "csv": "support-tickets.csv",
        "name": "Support Ticket Triage",
        "description": "Route customer support tickets by category",
        "labels": ["billing", "technical", "account", "feature-request"],
        "task_title": "Label Ticket Category",
        "task_instructions": "Read each support ticket and assign the correct category: billing, technical, account, or feature-request.",
    },
    {
        "csv": "topics.csv",
        "name": "News Topic Classification",
        "description": "Classify news headlines and short articles by topic",
        "labels": ["sports", "politics", "technology", "entertainment", "health"],
        "task_title": "Label News Topic",
        "task_instructions": "Read each news snippet and assign the topic: sports, politics, technology, entertainment, or health.",
    },
    {
        "csv": "product-reviews.csv",
        "name": "Product Review Ratings",
        "description": "Classify product reviews by star rating",
        "labels": ["1-star", "2-star", "3-star", "4-star", "5-star"],
        "task_title": "Label Review Stars",
        "task_instructions": "Read each product review and assign the appropriate star rating from 1-star to 5-star.",
    },
    {
        "csv": "headlines.csv",
        "name": "Clickbait Detection",
        "description": "Identify clickbait vs informative news headlines",
        "labels": ["clickbait", "not-clickbait"],
        "task_title": "Label Clickbait",
        "task_instructions": "Read each headline and decide if it is clickbait or not-clickbait.",
    },
    {
        "csv": "faq-intent.csv",
        "name": "FAQ Intent Detection",
        "description": "Route customer questions to the right support department",
        "labels": ["shipping", "returns", "warranty", "contact", "account"],
        "task_title": "Label FAQ Intent",
        "task_instructions": "Read each customer question and assign the intent: shipping, returns, warranty, contact, or account.",
    },
    {
        "csv": "urgency.csv",
        "name": "Ticket Urgency Detection",
        "description": "Prioritize internal tickets by urgency level",
        "labels": ["low", "medium", "urgent", "critical"],
        "task_title": "Label Urgency Level",
        "task_instructions": "Read each ticket and assign urgency: low, medium, urgent, or critical.",
    },
]


def _read_csv_rows(csv_path: Path):
    """Return list of (text, suggestion_or_None) tuples from a fixture CSV."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return rows
        # skip header if first col looks like a header
        if header[0].strip().lower() in ("text", "content", "sentence"):
            pass  # already consumed
        else:
            # not a header, treat it as data
            suggestion = header[1].strip() if len(header) > 1 and header[1].strip() else None
            rows.append((header[0].strip(), suggestion))
        for row in reader:
            if not row or not row[0].strip():
                continue
            text = row[0].strip()
            suggestion = row[1].strip() if len(row) > 1 and row[1].strip() else None
            rows.append((text, suggestion))
    return rows


async def main():
    db_url = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL", "")
    masked = db_url.split("@")[-1] if "@" in db_url else "(local .env)"
    print(f"[seed] using DB ...@{masked}")

    async with AsyncSessionLocal() as db:
        # --- seed demo users (existing logic) ---
        owner_user = None
        for u in DEMO_USERS:
            exists = (await db.execute(select(User).where(User.email == u["email"]))).scalars().first()
            if exists:
                print(f"[seed] skip {u['email']} already exists")
                if u["role"] == "OWNER":
                    owner_user = exists
                continue
            user = User(
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
                full_name=u["name"],
            )
            db.add(user)
            if u["role"] == "OWNER":
                owner_user = user
            print(f"[seed] created {u['email']} / {u['password']}")
        await db.commit()

        # refresh owner_user to get the id if we just created it
        if owner_user and not owner_user.id:
            await db.refresh(owner_user)

        if not owner_user:
            print("[seed] ERROR: could not find or create demo owner")
            return

        # --- seed 8 demo datasets ---
        for ds_meta in DEMO_DATASETS:
            # check idempotency by dataset name + owner
            exists = (
                await db.execute(
                    select(Dataset).where(
                        Dataset.name == ds_meta["name"],
                        Dataset.owner_id == owner_user.id,
                    )
                )
            ).scalars().first()
            if exists:
                print(f"[seed] skip dataset '{ds_meta['name']}' already exists")
                continue

            csv_path = FIXTURES_DIR / ds_meta["csv"]
            if not csv_path.exists():
                print(f"[seed] WARNING: {csv_path} not found, skipping")
                continue

            csv_rows = _read_csv_rows(csv_path)
            if not csv_rows:
                print(f"[seed] WARNING: {csv_path} is empty, skipping")
                continue

            # create dataset
            dataset = Dataset(
                owner_id=owner_user.id,
                name=ds_meta["name"],
                description=ds_meta["description"],
                storage_url=f"fixtures/{ds_meta['csv']}",
                file_type="csv",
                total_items=len(csv_rows),
                status=DatasetStatus.READY,
            )
            db.add(dataset)
            await db.flush()  # get dataset.id

            # create open labeling task
            label_schema = {label: label for label in ds_meta["labels"]}
            task = LabelTask(
                dataset_id=dataset.id,
                title=ds_meta["task_title"],
                instructions=ds_meta["task_instructions"],
                label_schema=label_schema,
                num_labelers=3,
                ai_enabled=0,
                status=TaskStatus.OPEN,
            )
            db.add(task)
            await db.flush()  # get task.id

            # create data items
            for idx, (text, suggestion) in enumerate(csv_rows, start=1):
                item = DataItem(
                    task_id=task.id,
                    row_index=idx,
                    content_json={"text": text},
                    ai_suggestion={"label": suggestion} if suggestion else None,
                    ai_confidence=1.0 if suggestion else 0.0,
                )
                db.add(item)

            print(f"[seed] created dataset '{ds_meta['name']}' with {len(csv_rows)} items")

        await db.commit()
        print("[seed] done — try login at /api/v1/auth/login")


if __name__ == "__main__":
    asyncio.run(main())
