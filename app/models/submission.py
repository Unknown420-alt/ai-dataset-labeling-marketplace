from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from app.core.database import Base, utcnow


class LabelSubmission(Base):
    __tablename__ = "label_submissions"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("data_items.id"), nullable=False)
    labeler_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    label_value = Column(JSON, nullable=False)
    source = Column(String(50), default="human")
    created_at = Column(DateTime, default=utcnow, nullable=False)
