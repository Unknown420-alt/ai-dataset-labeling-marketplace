import enum
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Float,
)
from app.core.database import Base, utcnow


class TaskStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class LabelTask(Base):
    __tablename__ = "label_tasks"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    title = Column(String(255), nullable=False)
    instructions = Column(Text, nullable=False)
    label_schema = Column(JSON, nullable=False)
    num_labelers = Column(Integer, default=3, nullable=False)
    ai_enabled = Column(Integer, default=0, nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
