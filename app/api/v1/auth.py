import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import User
from app.models.otp import OTPCode, hash_code
from app.schemas.user import UserCreate, UserLogin, UserPublic, AuthResponse
from app.services.security import (
    hash_password,
    verify_password,
    make_token,
    get_current_user,
)
from app.services.password import validate_password, password_rules_hint
from app.services.responses import ok
from app.services.mail import send_otp_email

router = APIRouter(prefix="/auth", tags=["auth"])

OTP_TTL_MINUTES = 10


class OTPRequest(BaseModel):
    email: EmailStr
    purpose: str = "verify"


class OTPVerify(BaseModel):
    email: EmailStr
    code: str


def _build_auth_response(user: User) -> AuthResponse:
    token = make_token({"sub": str(user.id), "role": user.role})
    return AuthResponse(access_token=token, user=UserPublic.model_validate(user))


async def _issue_otp(db: AsyncSession, email: str, purpose: str) -> dict:
    code = f"{secrets.randbelow(900000) + 100000}"
    db.add(
        OTPCode(
            email=email.lower(),
            code_hash=hash_code(code),
            purpose=purpose,
            expires_at=datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES),
        )
    )
    await db.commit()
    try:
        sent_via = send_otp_email(email, code, purpose)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    out = {"sent_via": sent_via, "expires_in_minutes": OTP_TTL_MINUTES}
    if sent_via == "dev-log":
        out["dev_code"] = code
    return out


async def _consume_otp(db: AsyncSession, email: str, code: str, purpose: str) -> None:
    res = await db.execute(
        select(OTPCode)
        .where(
            OTPCode.email == email.lower(),
            OTPCode.purpose == purpose,
            OTPCode.consumed == 0,
        )
        .order_by(OTPCode.created_at.desc())
    )
    latest = res.scalars().first()
    if (
        latest is None
        or latest.code_hash != hash_code(code.strip())
        or latest.expires_at < datetime.utcnow()
    ):
        raise HTTPException(status_code=401, detail="Wrong or expired code")
    latest.consumed = 1
    await db.commit()


@router.get("/password-rules")
async def get_password_rules():
    return ok(password_rules_hint(), "Password rules")


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    validate_password(payload.password)
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        email_verified=0,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    otp = await _issue_otp(db, user.email, "verify")
    body = _build_auth_response(user).model_dump()
    body["requires_verification"] = True
    if "dev_code" in otp:
        body["dev_code"] = otp["dev_code"]
    return ok(body, "Account created — verify the code sent to your email")


@router.post("/otp/request")
async def request_otp(payload: OTPRequest, db: AsyncSession = Depends(get_db)):
    if payload.purpose not in ("verify", "login"):
        raise HTTPException(status_code=422, detail="Purpose must be verify or login")
    if payload.purpose == "login":
        res = await db.execute(select(User).where(User.email == payload.email))
        if res.scalar_one_or_none() is None:
            return ok({"sent_via": "none"}, "If the email exists, a code was sent")
    otp = await _issue_otp(db, payload.email, payload.purpose)
    return ok(otp, "Code sent")


@router.post("/otp/verify")
async def verify_otp(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    await _consume_otp(db, payload.email, payload.code, "verify")
    res = await db.execute(select(User).where(User.email == payload.email))
    user = res.scalar_one_or_none()
    if user is not None and not user.email_verified:
        user.email_verified = 1
        await db.commit()
        await db.refresh(user)
        return ok(_build_auth_response(user), "Email verified")
    return ok({"verified": True}, "Email verified")


@router.post("/login")
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Verify your email first — check for the code we sent at signup",
        )
    return ok(_build_auth_response(user), "Logged in")


@router.post("/otp/login")
async def login_with_otp(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    await _consume_otp(db, payload.email, payload.code, "login")
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if not user.email_verified:
        user.email_verified = 1
        await db.commit()
        await db.refresh(user)
    return ok(_build_auth_response(user), "Logged in with code")


@router.get("/me")
async def read_users_me(current: User = Depends(get_current_user)):
    return ok(UserPublic.model_validate(current), "Current user")


@router.post("/refresh")
async def refresh_token(current: User = Depends(get_current_user)):
    return ok(_build_auth_response(current), "Token refreshed")
