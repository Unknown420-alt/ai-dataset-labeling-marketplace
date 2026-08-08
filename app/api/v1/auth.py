from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User
from app.schemas.user import UserCreate, UserLogin, UserPublic, AuthResponse
from app.services.security import (
    hash_password,
    verify_password,
    make_token,
    get_current_user,
)
from app.services.responses import ok

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_auth_response(user: User) -> AuthResponse:
    token = make_token({"sub": str(user.id), "role": user.role})
    return AuthResponse(access_token=token, user=UserPublic.model_validate(user))


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return ok(_build_auth_response(user), "Account created")


@router.post("/login")
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Wrong email or password")

    return ok(_build_auth_response(user), "Logged in")


@router.get("/me")
async def read_users_me(current: User = Depends(get_current_user)):
    return ok(UserPublic.model_validate(current), "Current user")


@router.post("/refresh")
async def refresh_token(current: User = Depends(get_current_user)):
    return ok(_build_auth_response(current), "Token refreshed")
