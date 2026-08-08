from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from app.core.database import Base, utcnow


class TaskClaim(Base):
    __tablename__ = "task_claims"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("label_tasks.id"), nullable=False)
    labeler_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="available", nullable=False)
    claimed_at = Column(DateTime, default=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
