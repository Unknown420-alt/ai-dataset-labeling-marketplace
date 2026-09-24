"""Password strength policy. Single source of truth for backend + frontend hints."""

RULES = [
    ("length", "At least 8 characters", lambda p: len(p) >= 8),
    ("upper", "One uppercase letter (A–Z)", lambda p: any(c.isupper() for c in p)),
    ("lower", "One lowercase letter (a–z)", lambda p: any(c.islower() for c in p)),
    ("digit", "One number (0–9)", lambda p: any(c.isdigit() for c in p)),
    ("special", "One symbol (!@#$…)", lambda p: any(not c.isalnum() for c in p)),
]


def check_password(password: str) -> dict:
    failed = [key for key, _, rule in RULES if not rule(password or "")]
    return {"ok": len(failed) == 0, "failed": failed}


def password_rules_hint() -> list:
    return [{"key": k, "label": label} for k, label, _ in RULES]


def validate_password(password: str) -> None:
    from fastapi import HTTPException

    result = check_password(password)
    if not result["ok"]:
        missing = [label for key, label, _ in RULES if key in result["failed"]]
        raise HTTPException(
            status_code=422,
            detail="Weak password. Missing: " + "; ".join(missing),
        )
