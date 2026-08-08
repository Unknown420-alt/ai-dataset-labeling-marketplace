from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class DataItemPublic(BaseModel):
    id: int
    task_id: int
    row_index: int
    content_json: dict
    ai_suggestion: Optional[Any] = None
    ai_confidence: float
    final_label: Optional[Any] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SubmissionCreate(BaseModel):
    label_value: dict


class SubmissionPublic(BaseModel):
    id: int
    item_id: int
    labeler_id: int
    label_value: dict
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskClaimPublic(BaseModel):
    id: int
    task_id: int
    labeler_id: int
    assigned_count: int
    status: str
    claimed_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
