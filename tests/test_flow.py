"""End-to-end test: signup -> login -> create dataset -> create task -> list.

Uses an isolated SQLite database (see conftest) so it exercises the full stack:
JWT auth -> router -> service -> SQLAlchemy -> SQLite -> back.
"""

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def _fresh_email():
    return f"it_{int(time.time() * 1000)}@example.com"


def _signup(client, role="owner"):
    email = _fresh_email()
    res = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "full_name": "Flow Tester",
            "password": "secret123",
            "role": role,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    return email, {"Authorization": f"Bearer {body['access_token']}"}


def _create_dataset_and_task(client):
    """Shared helper: signup, create dataset, create task. Returns (dataset_id, headers)."""
    _, headers = _signup(client)

    res = client.post(
        "/api/v1/datasets/",
        json={"name": "cats", "description": "cat photos", "file_type": "csv"},
        headers=headers,
    )
    dataset_id = res.json()["data"]["id"]

    res = client.post(
        "/api/v1/tasks/",
        json={
            "dataset_id": dataset_id,
            "title": "label cats",
            "instructions": "say cat or dog",
            "label_schema": {"cat": "cat", "dog": "dog"},
            "num_labelers": 2,
        },
        headers=headers,
    )
    assert res.status_code == 201
    return dataset_id, headers


def test_auth_and_dataset_flow(client):
    email, headers = _signup(client)

    res = client.post(
        "/api/v1/datasets/",
        json={"name": "cats", "description": "cat photos", "file_type": "csv"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    dataset_id = res.json()["data"]["id"]

    res = client.get("/api/v1/datasets/", headers=headers)
    assert res.status_code == 200
    assert any(d["id"] == dataset_id for d in res.json()["data"])

    res = client.get("/api/v1/datasets/999999", headers=headers)
    assert res.status_code == 404
    assert res.json()["success"] is False


def test_login_issues_jwt(client):
    email, _ = _signup(client, role="labeler")

    res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secret123"}
    )
    assert res.status_code == 200, res.text
    assert "access_token" in res.json()["data"]

    res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-pass"}
    )
    assert res.status_code == 401
    assert res.json()["success"] is False


def test_create_and_list_label_task(client):
    dataset_id, headers = _create_dataset_and_task(client)

    res = client.get("/api/v1/tasks/", headers=headers)
    assert res.status_code == 200
    tasks = res.json()["data"]
    mine = [t for t in tasks if t["title"] == "label cats"]
    assert len(mine) >= 1
    assert any(t["dataset_id"] == dataset_id for t in mine)


def test_protected_route_requires_token(client):
    res = client.get("/api/v1/datasets/")
    assert res.status_code == 401


def test_me_endpoint(client):
    email, headers = _signup(client)
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["email"] == email
