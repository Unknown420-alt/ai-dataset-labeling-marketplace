from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON
from app.core.database import Base


class DataItem(Base):
    __tablename__ = "data_items"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("label_tasks.id"), nullable=False)
    row_index = Column(Integer, nullable=False)
    content_json = Column(JSON, nullable=False)
    ai_suggestion = Column(JSON, nullable=True)
    ai_confidence = Column(Float, default=0.0)
    final_label = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
