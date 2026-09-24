"""Unit tests for password hashing and JWT token helpers."""

from app.services.security import (
    hash_password,
    verify_password,
    make_token,
    verify_token,
)


def test_password_round_trip():
    hashed = hash_password("Str0ng!Pass")
    assert hashed != "Str0ng!Pass"
    assert verify_password("Str0ng!Pass", hashed)


def test_password_rejects_wrong_value():
    hashed = hash_password("Str0ng!Pass")
    assert not verify_password("wrong-pass", hashed)


def test_make_and_verify_token():
    token = make_token({"sub": "7", "role": "owner"})
    payload = verify_token(token)
    assert payload["sub"] == "7"
    assert payload["role"] == "owner"
