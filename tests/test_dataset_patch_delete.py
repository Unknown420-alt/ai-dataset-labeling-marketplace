"""TDD tests for PATCH and DELETE /api/v1/datasets/{id}.

PATCH: rename (owner-only, 403 non-owner, 404 unknown)
DELETE: owner-only, 409 if label_tasks exist, 404 unknown
"""

import time
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def _fresh_email():
    return f"pd_{int(time.time() * 1000)}@example.com"


def _signup(client, role="owner"):
    email = _fresh_email()
    res = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "full_name": "Patch/Delete Tester",
            "password": "Str0ng!Pass",
            "role": role,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    return email, {"Authorization": f"Bearer {body['access_token']}"}


def _create_dataset(client, headers, name="test-ds"):
    res = client.post(
        "/api/v1/datasets/",
        json={"name": name, "description": "original", "file_type": "csv"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]["id"]


# ── PATCH tests ──────────────────────────────────────────────────────


def test_patch_rename_success(client):
    """Owner can rename their dataset → 200 + updated name."""
    _, headers = _signup(client)
    ds_id = _create_dataset(client, headers, name="old-name")

    res = client.patch(
        f"/api/v1/datasets/{ds_id}",
        json={"name": "new-name"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is True
    assert body["data"]["name"] == "new-name"
    assert body["data"]["id"] == ds_id


def test_patch_403_non_owner(client):
    """Non-owner cannot rename another user's dataset → 403."""
    owner_email, owner_headers = _signup(client)
    ds_id = _create_dataset(client, owner_headers)

    _, other_headers = _signup(client)
    res = client.patch(
        f"/api/v1/datasets/{ds_id}",
        json={"name": "stolen"},
        headers=other_headers,
    )
    assert res.status_code == 403, res.text
    assert res.json()["success"] is False


def test_patch_404_unknown_id(client):
    """PATCH unknown dataset id → 404."""
    _, headers = _signup(client)
    res = client.patch(
        "/api/v1/datasets/999999",
        json={"name": "x"},
        headers=headers,
    )
    assert res.status_code == 404, res.text
    assert res.json()["success"] is False


# ── DELETE tests ─────────────────────────────────────────────────────


def test_delete_success(client):
    """Owner can delete their dataset (no tasks) → 200."""
    _, headers = _signup(client)
    ds_id = _create_dataset(client, headers)

    res = client.delete(f"/api/v1/datasets/{ds_id}", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["success"] is True

    # Confirm gone
    res = client.get(f"/api/v1/datasets/{ds_id}", headers=headers)
    assert res.status_code == 404


def test_delete_403_non_owner(client):
    """Non-owner cannot delete another user's dataset → 403."""
    _, owner_headers = _signup(client)
    ds_id = _create_dataset(client, owner_headers)

    _, other_headers = _signup(client)
    res = client.delete(f"/api/v1/datasets/{ds_id}", headers=other_headers)
    assert res.status_code == 403, res.text
    assert res.json()["success"] is False


def test_delete_404_unknown_id(client):
    """DELETE unknown dataset id → 404."""
    _, headers = _signup(client)
    res = client.delete("/api/v1/datasets/999999", headers=headers)
    assert res.status_code == 404, res.text
    assert res.json()["success"] is False


def test_delete_409_label_tasks_exist(client):
    """DELETE blocked when label_tasks reference this dataset → 409."""
    _, headers = _signup(client)
    ds_id = _create_dataset(client, headers)

    # Create a label_task referencing this dataset
    res = client.post(
        "/api/v1/tasks/",
        json={
            "dataset_id": ds_id,
            "title": "blocking-task",
            "instructions": "label stuff",
            "label_schema": {"a": "a", "b": "b"},
            "num_labelers": 1,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text

    # Now try to delete → 409
    res = client.delete(f"/api/v1/datasets/{ds_id}", headers=headers)
    assert res.status_code == 409, res.text
    assert res.json()["success"] is False
    assert "label_tasks" in res.json()["message"].lower() or "task" in res.json()["message"].lower()
