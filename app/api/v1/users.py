from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.schemas.user import UserCreate, UserPublic
from app.services.security import hash_password, make_token, authenticate
from app.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="email already taken")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login")
async def login(email: str, password: str, db: AsyncSession = Depends(get_db)):
    user = await authenticate(db, email, password)
    if not user:
        raise HTTPException(status_code=401, detail="wrong email or password")

    token = make_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}
