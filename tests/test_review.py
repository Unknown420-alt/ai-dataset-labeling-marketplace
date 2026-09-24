"""Review queue, consensus, and export endpoints."""

import asyncio
import io
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def _fresh_email(prefix="rv"):
    return f"{prefix}_{int(time.time() * 1000)}_{id(object()) % 1000}@example.com"


def _signup(client, role):
    res = client.post(
        "/api/v1/auth/signup",
        json={
            "email": _fresh_email(role),
            "full_name": "Review Tester",
            "password": "Str0ng!Pass",
            "role": role,
        },
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['data']['access_token']}"}


def _seed_task_with_items(client, owner_headers, labeler_headers, n=3):
    res = client.post(
        "/api/v1/datasets/",
        json={"name": "review_ds", "description": "d", "file_type": "csv"},
        headers=owner_headers,
    )
    dataset_id = res.json()["data"]["id"]
    res = client.post(
        "/api/v1/tasks/",
        json={
            "dataset_id": dataset_id,
            "title": "review task",
            "instructions": "cat or dog",
            "label_schema": {"cat": "cat", "dog": "dog"},
            "num_labelers": 2,
        },
        headers=owner_headers,
    )
    task_id = res.json()["data"]["id"]
    csv_data = io.BytesIO(
        ('"the cat sleeps",cat\n"dog barks",dog\n"a cat naps",cat\n').encode()
    )
    res = client.post(
        f"/api/v1/tasks/{task_id}/items/upload",
        files={"file": ("s.csv", csv_data, "text/csv")},
        headers=owner_headers,
    )
    assert res.status_code == 201, res.text
    res = client.post(f"/api/v1/tasks/{task_id}/claim", headers=labeler_headers)
    assert res.status_code == 201, res.text
    res = client.get(f"/api/v1/tasks/{task_id}/items", headers=labeler_headers)
    return task_id, res.json()["data"]


def test_review_accept_and_reject(client):
    owner = _signup(client, "owner")
    labeler = _signup(client, "labeler")
    task_id, items = _seed_task_with_items(client, owner, labeler)

    res = client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler,
    )
    sub_id = res.json()["data"]["id"]
    assert res.json()["data"]["status"] == "pending"

    # Labeler cannot review.
    res = client.post(
        f"/api/v1/submissions/{sub_id}/review",
        json={"decision": "accepted"},
        headers=labeler,
    )
    assert res.status_code == 403

    # Owner accepts.
    res = client.post(
        f"/api/v1/submissions/{sub_id}/review",
        json={"decision": "accepted"},
        headers=owner,
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "accepted"

    # Owner rejects -> final_label cleared (no other accepted submission).
    res = client.post(
        f"/api/v1/submissions/{sub_id}/review",
        json={"decision": "rejected"},
        headers=owner,
    )
    assert res.status_code == 200
    res = client.get(f"/api/v1/tasks/{task_id}/items", headers=owner)
    updated = next(i for i in res.json()["data"] if i["id"] == items[0]["id"])
    assert updated["final_label"] is None

    # Review of missing submission 404s.
    res = client.post(
        "/api/v1/submissions/999999/review",
        json={"decision": "accepted"},
        headers=owner,
    )
    assert res.status_code == 404


def test_submissions_list_scoping(client):
    owner = _signup(client, "owner")
    labeler = _signup(client, "labeler")
    task_id, items = _seed_task_with_items(client, owner, labeler)
    client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler,
    )
    res = client.get(f"/api/v1/tasks/{task_id}/submissions", headers=owner)
    assert res.status_code == 200
    assert len(res.json()["data"]) == 1
    assert res.json()["data"][0]["labeler_email"]
    res = client.get(
        f"/api/v1/tasks/{task_id}/submissions?status=pending", headers=owner
    )
    assert len(res.json()["data"]) == 1


def test_consensus_majority(client):
    owner = _signup(client, "owner")
    lab1 = _signup(client, "labeler")
    lab2 = _signup(client, "labeler")
    task_id, items = _seed_task_with_items(client, owner, lab1)
    client.post(f"/api/v1/tasks/{task_id}/claim", headers=lab2)
    client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=lab1,
    )
    client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "dog"}},
        headers=lab2,
    )
    res = client.get(f"/api/v1/tasks/{task_id}/consensus", headers=owner)
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    first = next(i for i in body["items"] if i["item_id"] == items[0]["id"])
    assert first["submission_count"] == 2
    assert first["agreement"] == 0.5


def test_export_csv_and_json(client):
    owner = _signup(client, "owner")
    labeler = _signup(client, "labeler")
    task_id, items = _seed_task_with_items(client, owner, labeler)
    client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler,
    )
    res = client.get(f"/api/v1/tasks/{task_id}/export?format=csv", headers=owner)
    assert res.status_code == 200, res.text
    assert "final_label" in res.text
    res = client.get(f"/api/v1/tasks/{task_id}/export?format=json", headers=owner)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) == 3
    # Labeler cannot export.
    res = client.get(f"/api/v1/tasks/{task_id}/export?format=csv", headers=labeler)
    assert res.status_code == 403


def test_gold_flow_and_leaderboard(client):
    owner = _signup(client, "owner")
    labeler = _signup(client, "labeler")
    other = _signup(client, "labeler")
    task_id, items = _seed_task_with_items(client, owner, labeler)
    client.post(f"/api/v1/tasks/{task_id}/claim", headers=other)

    # Only owners can mark gold.
    res = client.post(
        f"/api/v1/data_items/{items[0]['id']}/gold",
        json={"gold_label": {"label": "cat"}},
        headers=labeler,
    )
    assert res.status_code == 403
    res = client.post(
        f"/api/v1/data_items/{items[0]['id']}/gold",
        json={"gold_label": {"label": "cat"}},
        headers=owner,
    )
    assert res.status_code == 200, res.text

    # Correct answer on gold item reports gold_correct=true.
    res = client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler,
    )
    assert res.json()["data"]["gold_correct"] is True
    # Wrong answer reports false.
    res = client.post(
        f"/api/v1/data_items/{items[1]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler,
    )
    assert res.json()["data"]["gold_correct"] is None
    client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "dog"}},
        headers=other,
    )
    # Same labeler cannot submit twice on one item.
    res = client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler,
    )
    assert res.status_code == 409
    res = client.get(f"/api/v1/tasks/{task_id}/leaderboard", headers=owner)
    assert res.status_code == 200, res.text
    board = res.json()["data"]
    assert len(board) == 2
    entry = next(e for e in board if e["submitted"] == 2)
    assert entry["gold_answered"] == 1
    assert entry["gold_correct"] == 1
    assert entry["gold_accuracy"] == 1.0
    other_entry = next(e for e in board if e["submitted"] == 1)
    assert other_entry["gold_accuracy"] == 0.0
    # Labeler cannot see the leaderboard.
    res = client.get(f"/api/v1/tasks/{task_id}/leaderboard", headers=labeler)
    assert res.status_code == 403


def test_items_unlabeled_first(client):
    owner = _signup(client, "owner")
    labeler = _signup(client, "labeler")
    task_id, items = _seed_task_with_items(client, owner, labeler)
    client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler,
    )
    res = client.get(f"/api/v1/tasks/{task_id}/items", headers=labeler)
    got = res.json()["data"]
    assert got[-1]["id"] == items[0]["id"]
    assert all(i["final_label"] is None for i in got[:-1])


def test_analytics_overview(client):
    owner = _signup(client, "owner")
    labeler = _signup(client, "labeler")
    task_id, items = _seed_task_with_items(client, owner, labeler)
    client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler,
    )
    res = client.get("/api/v1/analytics/overview", headers=owner)
    assert res.status_code == 200, res.text
    body = res.json()["data"]
    assert body["datasets"] == 1
    assert body["tasks"] == 1
    assert body["items"] == 3
    assert body["labeled"] == 1
    assert body["submissions"] == 1
    assert len(body["per_task"]) == 1
    assert body["per_task"][0]["task_id"] == task_id
    assert len(body["daily_submissions"]) == 14
    assert sum(d["count"] for d in body["daily_submissions"]) == 1
    # Labeler with no datasets gets zeros, not someone else's numbers.
    res = client.get("/api/v1/analytics/overview", headers=labeler)
    assert res.json()["data"]["tasks"] == 0


def test_audit_log_records_reviews(client):
    from app.core.database import AsyncSessionLocal
    from app.models import AuditLog
    from sqlalchemy import select

    async def _count():
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select(AuditLog))).scalars().all()
            return [(r.action, r.target_type) for r in rows]

    owner = _signup(client, "owner")
    labeler = _signup(client, "labeler")
    task_id, items = _seed_task_with_items(client, owner, labeler)
    client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler,
    )
    sub_id = client.get(f"/api/v1/tasks/{task_id}/submissions", headers=owner).json()[
        "data"
    ][0]["id"]
    client.post(
        f"/api/v1/submissions/{sub_id}/review",
        json={"decision": "accepted"},
        headers=owner,
    )
    client.get(f"/api/v1/tasks/{task_id}/export?format=csv", headers=owner)
    entries = asyncio.run(_count())
    actions = [a for a, _ in entries]
    assert "submission_accepted" in actions
    assert "export_csv" in actions


def test_multilabel_submit_and_train_rejected(client):
    owner = _signup(client, "owner")
    labeler = _signup(client, "labeler")
    res = client.post(
        "/api/v1/datasets/",
        json={"name": "ml_ds", "description": "d", "file_type": "csv"},
        headers=owner,
    )
    dataset_id = res.json()["data"]["id"]
    res = client.post(
        "/api/v1/tasks/",
        json={
            "dataset_id": dataset_id,
            "title": "multi task",
            "instructions": "pick all that apply",
            "label_schema": {"cat": "cat", "dog": "dog", "bird": "bird"},
            "num_labelers": 1,
            "is_multilabel": True,
        },
        headers=owner,
    )
    assert res.status_code == 201, res.text
    assert res.json()["data"]["is_multilabel"] is True
    task_id = res.json()["data"]["id"]
    csv_data = io.BytesIO(b'"cat and dog",cat\n')
    client.post(
        f"/api/v1/tasks/{task_id}/items/upload",
        files={"file": ("m.csv", csv_data, "text/csv")},
        headers=owner,
    )
    client.post(f"/api/v1/tasks/{task_id}/claim", headers=labeler)
    items = client.get(f"/api/v1/tasks/{task_id}/items", headers=labeler).json()["data"]

    res = client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler,
    )
    assert res.status_code == 422
    res = client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"labels": ["cat", "fish"]}},
        headers=labeler,
    )
    assert res.status_code == 422
    res = client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"labels": ["dog", "cat"]}},
        headers=labeler,
    )
    assert res.status_code == 201, res.text
    assert res.json()["data"]["label_value"] == {"labels": ["cat", "dog"]}


def test_mine_and_gold_coverage(client):
    owner = _signup(client, "owner")
    labeler = _signup(client, "labeler")
    task_id, items = _seed_task_with_items(client, owner, labeler)
    client.post(
        f"/api/v1/data_items/{items[0]['id']}/gold",
        json={"gold_label": {"label": "cat"}},
        headers=owner,
    )
    client.post(
        f"/api/v1/data_items/{items[0]['id']}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler,
    )
    res = client.get("/api/v1/analytics/mine", headers=labeler)
    assert res.status_code == 200, res.text
    me = res.json()["data"]
    assert me["submitted"] == 1
    assert me["gold_accuracy"] == 1.0
    assert me["tasks_claimed"] == 1
    assert len(me["daily_submissions"]) == 14
    res = client.get("/api/v1/analytics/overview", headers=owner)
    body = res.json()["data"]
    assert body["gold_coverage"] > 0
    assert body["gold_accuracy"] == 1.0
