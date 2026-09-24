"""Password policy, OTP verification, and OTP login."""

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _force_dev_mail(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.smtp_host", "")
    monkeypatch.setattr("app.core.config.settings.smtp_user", "")


def _fresh_email(prefix="otp"):
    return f"{prefix}_{int(time.time() * 1000)}@example.com"


def test_password_rules_endpoint(client):
    res = client.get("/api/v1/auth/password-rules")
    assert res.status_code == 200
    keys = [r["key"] for r in res.json()["data"]]
    assert keys == ["length", "upper", "lower", "digit", "special"]


def test_weak_password_rejected(client):
    res = client.post(
        "/api/v1/auth/signup",
        json={
            "email": _fresh_email("weak"),
            "full_name": "Weak",
            "password": "secret123",
            "role": "labeler",
        },
    )
    assert res.status_code == 422, res.text
    assert "Missing" in res.json()["message"]


def _signup_unverified(client, role="labeler"):
    email = _fresh_email(role)
    res = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "full_name": "OTP Tester",
            "password": "Str0ng!Pass",
            "role": role,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()["data"]
    assert body["requires_verification"] is True
    assert body["user"]["email_verified"] is False
    assert "dev_code" in body
    return email, body["dev_code"]


def test_signup_verify_then_login(client):
    email, code = _signup_unverified(client)

    res = client.post(
        "/api/v1/auth/otp/verify", json={"email": email, "code": "000000"}
    )
    assert res.status_code == 401

    res = client.post("/api/v1/auth/otp/verify", json={"email": email, "code": code})
    assert res.status_code == 200, res.text
    assert res.json()["data"]["user"]["email_verified"] is True

    res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass"}
    )
    assert res.status_code == 200, res.text
    assert "access_token" in res.json()["data"]


def test_code_single_use(client):
    email, code = _signup_unverified(client)
    res = client.post("/api/v1/auth/otp/verify", json={"email": email, "code": code})
    assert res.status_code == 200
    res = client.post("/api/v1/auth/otp/verify", json={"email": email, "code": code})
    assert res.status_code == 401


def test_otp_login_flow(client):
    email, code = _signup_unverified(client)
    client.post("/api/v1/auth/otp/verify", json={"email": email, "code": code})

    res = client.post(
        "/api/v1/auth/otp/request", json={"email": email, "purpose": "login"}
    )
    assert res.status_code == 200, res.text
    login_code = res.json()["data"]["dev_code"]

    res = client.post("/api/v1/auth/otp/login", json={"email": email, "code": "000000"})
    assert res.status_code == 401

    res = client.post(
        "/api/v1/auth/otp/login", json={"email": email, "code": login_code}
    )
    assert res.status_code == 200, res.text
    assert "access_token" in res.json()["data"]


def test_otp_login_unknown_email_leaks_nothing(client):
    res = client.post(
        "/api/v1/auth/otp/request",
        json={"email": "nobody-here@example.com", "purpose": "login"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["sent_via"] == "none"
    assert "dev_code" not in res.json()["data"]
