import hashlib
from sqlalchemy import Column, DateTime, Integer, String
from app.core.database import Base, utcnow


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    code_hash = Column(String(64), nullable=False)
    purpose = Column(String(20), nullable=False, default="verify")
    expires_at = Column(DateTime, nullable=False)
    consumed = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
