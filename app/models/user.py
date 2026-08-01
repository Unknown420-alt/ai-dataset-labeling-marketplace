import enum
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, Integer, String
from app.core.database import Base


class UserRole(str, enum.Enum):
    OWNER = "owner"
    LABELER = "labeler"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.LABELER, nullable=False)
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
