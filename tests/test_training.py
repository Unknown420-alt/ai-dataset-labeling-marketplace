"""TDD tests for POST /api/v1/datasets/{id}/train and /predict.

Train: owner trains TF-IDF + MultinomialNB on labeled data → returns accuracy
Predict: owner predicts label for text → returns label + confidence
"""

import asyncio
import io
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
            "password": "Str0ng!Pass",
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


def test_suggest_needs_training_then_fills_unlabeled(client):
    """Suggest without a model → 422; after train → fills suggestions."""
    _, headers = _signup(client)
    dataset_id = _create_dataset(client, headers, name="suggest-ds")
    texts = [
        ("I love this phone", "positive"),
        ("I adore this phone", "positive"),
        ("Great phone, love it", "positive"),
        ("Excellent device", "positive"),
        ("Superb quality phone", "positive"),
        ("Terrible phone", "negative"),
        ("Awful device", "negative"),
        ("Horrible phone experience", "negative"),
        ("Worst purchase ever", "negative"),
        ("Hate this phone", "negative"),
    ]
    unlabeled = ["I love this gadget", "Terrible gadget", "What a superb thing"]
    _seed_labeled_items(dataset_id, texts)

    async def _add_unlabeled():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select

            task = (
                (
                    await db.execute(
                        select(LabelTask).where(LabelTask.dataset_id == dataset_id)
                    )
                )
                .scalars()
                .first()
            )
            for i, text in enumerate(unlabeled, start=100):
                db.add(
                    DataItem(
                        task_id=task.id,
                        row_index=i,
                        content_json={"text": text},
                    )
                )
            await db.commit()

    asyncio.run(_add_unlabeled())

    res = client.post(f"/api/v1/datasets/{dataset_id}/suggest", headers=headers)
    assert res.status_code == 422, res.text

    res = client.post(f"/api/v1/datasets/{dataset_id}/train", headers=headers)
    assert res.status_code == 200, res.text

    res = client.post(f"/api/v1/datasets/{dataset_id}/suggest", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["suggested"] == 3

    res = client.post(f"/api/v1/datasets/{dataset_id}/suggest", headers=headers)
    assert res.json()["data"]["suggested"] == 3


def test_llm_suggest_fails_closed_without_key(client):
    _, headers = _signup(client)
    dataset_id = _create_dataset(client, headers, name="llm-ds")
    res = client.post(
        f"/api/v1/datasets/{dataset_id}/suggest-llm", json={}, headers=headers
    )
    assert res.status_code == 422, res.text
    assert "OPENAI_API_KEY" in res.json()["message"]


def test_llm_suggest_mocked_success(client, monkeypatch):
    from app.services import llm as llm_svc

    async def _noop(*a, **k):
        return None

    def _fake_suggest(api_key, model, instructions, labels, texts):
        assert labels == ["cat", "dog"]
        return {0: "cat", 1: "dog"}

    monkeypatch.setattr(llm_svc, "suggest_batch", _fake_suggest)
    monkeypatch.setattr("app.core.config.settings.openai_api_key", "test-key")
    _, headers = _signup(client)
    dataset_id = _create_dataset(client, headers, name="llm-ok-ds")
    res = client.post(
        "/api/v1/tasks/",
        json={
            "dataset_id": dataset_id,
            "title": "t",
            "instructions": "pick",
            "label_schema": {"cat": "cat", "dog": "dog"},
            "num_labelers": 1,
        },
        headers=headers,
    )
    task_id = res.json()["data"]["id"]
    csv_data = io.BytesIO(b'"a cat",cat\n"a dog",dog\n')
    client.post(
        f"/api/v1/tasks/{task_id}/items/upload",
        files={"file": ("s.csv", csv_data, "text/csv")},
        headers=headers,
    )
    res = client.post(
        f"/api/v1/datasets/{dataset_id}/suggest-llm", json={}, headers=headers
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["suggested"] == 2
    monkeypatch.setattr("app.core.config.settings.openai_api_key", "")


def test_train_reports_evaluation_method(client):
    _, headers = _signup(client)
    dataset_id = _create_dataset(client, headers, name="eval-ds")
    texts = [(f"good thing number {i}", "positive") for i in range(12)]
    texts += [(f"bad thing number {i}", "negative") for i in range(12)]
    _seed_labeled_items(dataset_id, texts)
    res = client.post(f"/api/v1/datasets/{dataset_id}/train", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["evaluation"] == "held-out 20%"


def test_model_survives_cache_clear_and_multilabel_trains(client):
    """Disk persistence: clear memory cache → predict still works."""
    from app.services import training as tsvc

    _, headers = _signup(client)
    dataset_id = _create_dataset(client, headers, name="persist-ds")
    texts = [(f"good phone number {i}", "positive") for i in range(6)]
    texts += [(f"bad phone number {i}", "negative") for i in range(6)]
    _seed_labeled_items(dataset_id, texts)
    res = client.post(f"/api/v1/datasets/{dataset_id}/train", headers=headers)
    assert res.status_code == 200, res.text
    tsvc.clear_cache()
    res = client.post(
        f"/api/v1/datasets/{dataset_id}/predict",
        json={"text": "good phone"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["label"] == "positive"


def test_multilabel_train_predict_suggest(client):
    """Multilabel tasks train, predict lists, and suggest writes label lists."""
    _, headers = _signup(client)
    dataset_id = _create_dataset(client, headers, name="multi-ds")

    async def _seed():
        async with AsyncSessionLocal() as db:
            task = LabelTask(
                dataset_id=dataset_id,
                title="multi",
                instructions="pick all",
                label_schema={"cat": "cat", "dog": "dog"},
                status="open",
                is_multilabel=1,
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)
            samples = [
                ("cat sleeps here", ["cat"]),
                ("dog barks loudly", ["dog"]),
                ("cat and dog play", ["cat", "dog"]),
                ("my cat naps", ["cat"]),
                ("big dog runs", ["dog"]),
                ("cat meets dog", ["cat", "dog"]),
                ("little cat purrs", ["cat"]),
                ("old dog sleeps", ["dog"]),
                ("cat dog friends", ["cat", "dog"]),
                ("cute cat yawns", ["cat"]),
                ("wild dog howls", ["dog"]),
                ("cat plus dog", ["cat", "dog"]),
            ]
            for i, (text, labels) in enumerate(samples):
                db.add(
                    DataItem(
                        task_id=task.id,
                        row_index=i,
                        content_json={"text": text},
                        final_label={"labels": labels},
                    )
                )
            db.add(
                DataItem(
                    task_id=task.id,
                    row_index=99,
                    content_json={"text": "cat naps quietly"},
                )
            )
            await db.commit()
            return task.id

    task_id = asyncio.run(_seed())
    res = client.post(f"/api/v1/datasets/{dataset_id}/train", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["task_type"] == "multilabel"

    res = client.post(
        f"/api/v1/datasets/{dataset_id}/predict",
        json={"text": "cat and dog together"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert set(res.json()["data"]["labels"]) == {"cat", "dog"}

    res = client.post(f"/api/v1/datasets/{dataset_id}/suggest", headers=headers)
    assert res.json()["data"]["suggested"] == 1
