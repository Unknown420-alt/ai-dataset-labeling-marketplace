"""End-to-end test: signup -> login -> create dataset -> create task -> list.

Uses the real dev database (marketplace.db) so it exercises the full stack:
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


def _create_dataset_and_task(client):
    """Shared helper: signup, create dataset, create task. Returns (dataset_id, headers)."""
    email = _fresh_email()
    res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "full_name": "Flow Tester", "password": "secret123", "role": "owner"},
    )
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}

    res = client.post(
        "/api/v1/datasets/",
        json={"name": "cats", "description": "cat photos", "file_type": "csv"},
        headers=headers,
    )
    dataset_id = res.json()["id"]

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
    email = _fresh_email()

    res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "full_name": "Flow Tester", "password": "secret123", "role": "owner"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert "access_token" in body
    assert body["user"]["email"] == email

    headers = {"Authorization": f"Bearer {body['access_token']}"}

    res = client.post(
        "/api/v1/datasets/",
        json={"name": "cats", "description": "cat photos", "file_type": "csv"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    dataset_id = res.json()["id"]

    res = client.get("/api/v1/datasets/", headers=headers)
    assert res.status_code == 200
    assert any(d["id"] == dataset_id for d in res.json())

    res = client.get("/api/v1/datasets/999999", headers=headers)
    assert res.status_code == 404


def test_login_issues_jwt(client):
    email = _fresh_email()

    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "full_name": "Login Tester", "password": "secret123", "role": "labeler"},
    )

    res = client.post("/api/v1/auth/login", json={"email": email, "password": "secret123"})
    assert res.status_code == 200, res.text
    assert "access_token" in res.json()

    res = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-pass"})
    assert res.status_code == 401


def test_create_and_list_label_task(client):
    dataset_id, headers = _create_dataset_and_task(client)

    res = client.get("/api/v1/tasks/", headers=headers)
    assert res.status_code == 200
    tasks = res.json()
    mine = [t for t in tasks if t["title"] == "label cats"]
    assert len(mine) >= 1
    assert any(t["dataset_id"] == dataset_id for t in mine)


def test_protected_route_requires_token(client):
    res = client.get("/api/v1/datasets/")
    assert res.status_code == 401
