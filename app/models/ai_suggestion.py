from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String
from app.core.database import Base, utcnow


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("data_items.id"), nullable=False)
    model_name = Column(String(100), nullable=False)
    confidence_score = Column(Float, default=0.0, nullable=False)
    prediction_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
