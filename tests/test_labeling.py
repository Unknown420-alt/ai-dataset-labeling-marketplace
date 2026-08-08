"""Labeler flow: claim a task -> upload items -> list items -> submit labels.

Uses the isolated test database (see conftest) and exercises the full stack.
"""

import io
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def _fresh_email():
    return f"lb_{int(time.time() * 1000)}@example.com"


def _signup(client, role):
    res = client.post(
        "/api/v1/auth/signup",
        json={
            "email": _fresh_email(),
            "full_name": "Labeling Tester",
            "password": "secret123",
            "role": role,
        },
    )
    assert res.status_code == 201, res.text
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_task(client):
    """Owner creates a dataset + task. Returns task_id."""
    owner_headers = _signup(client, role="owner")
    res = client.post(
        "/api/v1/datasets/",
        json={"name": "review_cats", "description": "cat photos", "file_type": "csv"},
        headers=owner_headers,
    )
    dataset_id = res.json()["data"]["id"]
    res = client.post(
        "/api/v1/tasks/",
        json={
            "dataset_id": dataset_id,
            "title": "label review cats",
            "instructions": "cat or dog",
            "label_schema": {"cat": "cat", "dog": "dog"},
            "num_labelers": 1,
        },
        headers=owner_headers,
    )
    return res.json()["data"]["id"]


def test_full_labeling_flow(client):
    owner_headers = _signup(client, role="owner")
    labeler_headers = _signup(client, role="labeler")

    res = client.post(
        "/api/v1/datasets/",
        json={"name": "cats_flow", "description": "cat photos", "file_type": "csv"},
        headers=owner_headers,
    )
    dataset_id = res.json()["data"]["id"]

    res = client.post(
        "/api/v1/tasks/",
        json={
            "dataset_id": dataset_id,
            "title": "label cats flow",
            "instructions": "cat or dog",
            "label_schema": {"cat": "cat", "dog": "dog"},
            "num_labelers": 1,
        },
        headers=owner_headers,
    )
    task_id = res.json()["data"]["id"]

    csv_data = io.BytesIO(
        (
            '"the cat is sleeping",cat\n"dog barked",dog\n"a cup of coffee",cat\n'
        ).encode()
    )
    res = client.post(
        f"/api/v1/tasks/{task_id}/items/upload",
        files={"file": ("sample_cats.csv", csv_data, "text/csv")},
        headers=owner_headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["data"]["uploaded"] == 3

    res = client.post(f"/api/v1/tasks/{task_id}/claim", headers=labeler_headers)
    assert res.status_code == 201, res.text
    assert res.json()["data"]["status"] == "claimed"

    res = client.post(f"/api/v1/tasks/{task_id}/claim", headers=labeler_headers)
    assert res.status_code == 409

    res = client.get(f"/api/v1/tasks/{task_id}/items", headers=labeler_headers)
    assert res.status_code == 200
    items = res.json()["data"]
    assert len(items) == 3

    item_id = items[0]["id"]
    res = client.post(
        f"/api/v1/data_items/{item_id}/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler_headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["data"]["source"] == "human"

    res = client.get(f"/api/v1/tasks/{task_id}/items", headers=owner_headers)
    assert res.status_code == 200
    updated = next(i for i in res.json()["data"] if i["id"] == item_id)
    assert updated["final_label"] == {"label": "cat"}


def test_claim_requires_auth(client):
    task_id = _seed_task(client)
    res = client.post(f"/api/v1/tasks/{task_id}/claim")
    assert res.status_code == 401


def test_submit_to_missing_item_404(client):
    labeler_headers = _signup(client, role="labeler")
    res = client.post(
        "/api/v1/data_items/999999/submission",
        json={"label_value": {"label": "cat"}},
        headers=labeler_headers,
    )
    assert res.status_code == 404
