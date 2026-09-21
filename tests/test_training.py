"""TDD tests for POST /api/v1/datasets/{id}/train and /predict.

Train: owner trains TF-IDF + MultinomialNB on labeled data → returns accuracy
Predict: owner predicts label for text → returns label + confidence
"""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models import DataItem, LabelTask


@pytest.fixture()
def client():
    return TestClient(app)


def _fresh_email(prefix="train"):
    return f"{prefix}_{int(time.time() * 1000)}@example.com"


def _signup(client, role="owner"):
    email = _fresh_email()
    res = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "full_name": "Train Tester",
            "password": "secret123",
            "role": role,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    return email, {"Authorization": f"Bearer {body['access_token']}"}


def _create_dataset(client, headers, name="train-ds"):
    res = client.post(
        "/api/v1/datasets/",
        json={"name": name, "description": "for training", "file_type": "csv"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]["id"]


def _seed_labeled_items(dataset_id, texts_labels):
    """Insert DataItems with final_label set via direct DB access."""

    async def _insert():
        async with AsyncSessionLocal() as db:
            task = LabelTask(
                dataset_id=dataset_id,
                title="train-task",
                instructions="label these",
                label_schema={
                    "positive": "positive",
                    "negative": "negative",
                    "neutral": "neutral",
                },
                status="open",
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)

            for i, (text, label) in enumerate(texts_labels):
                item = DataItem(
                    task_id=task.id,
                    row_index=i,
                    content_json={"text": text},
                    final_label={"label": label},
                )
                db.add(item)
            await db.commit()

    asyncio.run(_insert())


# ── Helper: labeled data for sentiment (15 rows, 3 classes) ──────────

SENTIMENT_DATA = [
    ("I absolutely love this product", "positive"),
    ("Best purchase I have made all year", "positive"),
    ("Customer service was incredibly helpful", "positive"),
    ("Exceeded my expectations in every way", "positive"),
    ("Really happy with how this turned out", "positive"),
    ("Game changer for my daily routine", "positive"),
    ("Terrible experience will never buy again", "negative"),
    ("Broke after two days total waste", "negative"),
    ("Waited 3 weeks for delivery", "negative"),
    ("Not what I ordered very frustrating", "negative"),
    ("The worst customer support ever", "negative"),
    ("Arrived damaged refund is a nightmare", "negative"),
    ("It is okay nothing special really", "neutral"),
    ("Meh it does the job but I expected more", "neutral"),
    ("Decent product fair price no complaints", "neutral"),
]


# ── TRAIN tests ──────────────────────────────────────────────────────


def test_train_success(client):
    """Owner trains on 15 labeled rows → 200 + accuracy field."""
    _, headers = _signup(client)
    ds_id = _create_dataset(client, headers, name="train-ok")
    _seed_labeled_items(ds_id, SENTIMENT_DATA)

    res = client.post(f"/api/v1/datasets/{ds_id}/train", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert "accuracy" in data
    assert 0.0 <= data["accuracy"] <= 1.0
    assert data["labeled_count"] == 15
    assert "total_items" in data


def test_train_403_non_owner(client):
    """Non-owner cannot train another user's dataset → 403."""
    _, owner_headers = _signup(client)
    ds_id = _create_dataset(client, owner_headers, name="train-owner-only")
    _seed_labeled_items(ds_id, SENTIMENT_DATA)

    _, other_headers = _signup(client)
    res = client.post(f"/api/v1/datasets/{ds_id}/train", headers=other_headers)
    assert res.status_code == 403, res.text
    assert res.json()["success"] is False


def test_train_404_unknown_id(client):
    """Train unknown dataset id → 404."""
    _, headers = _signup(client)
    res = client.post("/api/v1/datasets/999999/train", headers=headers)
    assert res.status_code == 404, res.text
    assert res.json()["success"] is False


def test_train_422_too_few_labels(client):
    """Train with < 10 labeled rows → 422."""
    _, headers = _signup(client)
    ds_id = _create_dataset(client, headers, name="train-few")
    # Only 5 labeled items — below minimum of 10
    _seed_labeled_items(ds_id, SENTIMENT_DATA[:5])

    res = client.post(f"/api/v1/datasets/{ds_id}/train", headers=headers)
    assert res.status_code == 422, res.text
    assert res.json()["success"] is False


# ── PREDICT tests ────────────────────────────────────────────────────


def test_predict_success(client):
    """Owner trains then predicts → 200 + label field."""
    _, headers = _signup(client)
    ds_id = _create_dataset(client, headers, name="predict-ok")
    _seed_labeled_items(ds_id, SENTIMENT_DATA)

    # Train first so model is cached
    res = client.post(f"/api/v1/datasets/{ds_id}/train", headers=headers)
    assert res.status_code == 200, res.text

    # Predict
    res = client.post(
        f"/api/v1/datasets/{ds_id}/predict",
        json={"text": "This is an amazing product"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert "label" in data
    assert data["label"] in ("positive", "negative", "neutral")
    assert "confidence" in data
    assert 0.0 <= data["confidence"] <= 1.0


def test_predict_403_non_owner(client):
    """Non-owner cannot predict on another user's dataset → 403."""
    _, owner_headers = _signup(client)
    ds_id = _create_dataset(client, owner_headers, name="predict-owner")
    _seed_labeled_items(ds_id, SENTIMENT_DATA)

    # Train as owner
    client.post(f"/api/v1/datasets/{ds_id}/train", headers=owner_headers)

    _, other_headers = _signup(client)
    res = client.post(
        f"/api/v1/datasets/{ds_id}/predict",
        json={"text": "hello"},
        headers=other_headers,
    )
    assert res.status_code == 403, res.text
    assert res.json()["success"] is False


def test_predict_404_unknown_id(client):
    """Predict on unknown dataset id → 404."""
    _, headers = _signup(client)
    res = client.post(
        "/api/v1/datasets/999999/predict",
        json={"text": "hello"},
        headers=headers,
    )
    assert res.status_code == 404, res.text
    assert res.json()["success"] is False
