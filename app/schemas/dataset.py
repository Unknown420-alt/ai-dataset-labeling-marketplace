from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None
    file_type: str


class DatasetCreate(DatasetBase):
    pass


class DatasetPublic(BaseModel):
    id: int
    name: str
    description: Optional[str]
    file_type: str
    total_items: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
