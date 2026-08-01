from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LabelTaskBase(BaseModel):
    title: str
    instructions: str
    label_schema: dict
    num_labelers: int = 3
    ai_enabled: bool = False


class LabelTaskCreate(LabelTaskBase):
    dataset_id: int


class LabelTaskPublic(BaseModel):
    id: int
    title: str
    instructions: str
    label_schema: dict
    num_labelers: int
    ai_enabled: bool
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
